from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from typing import List, Optional
import uuid
from datetime import datetime

from config import (
    WIZARDS_FILE, NOTES_META_FILE, SHARE_DATA_FILE, 
    ENCRYPTION_KEY_FILE, NOTES_DIR, DEFAULT_WIZARDS
)
from models import (
    WizardResponse, CreateNoteRequest, NoteResponse, 
    NoteContentResponse, ShareNoteRequest, AccessRequestRequest,
    AccessRequestResponse, ApproveRequestRequest, CreateWizardRequest
)
from data_store import DataStore
from encryption import EncryptionService

# Initialize
data_store = DataStore(WIZARDS_FILE, NOTES_META_FILE, SHARE_DATA_FILE, DEFAULT_WIZARDS)
encryption_service = EncryptionService(ENCRYPTION_KEY_FILE, NOTES_DIR)

app = FastAPI(title="Mischief Managed", version="1.0.0")

# Auth helpers
async def get_wizard(x_api_key: str = Header(...)) -> str:
    wizards = await data_store.get_wizards()
    for name, key in wizards.items():
        if key == x_api_key:
            return name
    raise HTTPException(status_code=401, detail="Invalid API key")

async def get_admin(x_api_key: str = Header(...)) -> str:
    wizard = await get_wizard(x_api_key)
    if wizard != "Dumbledore":
        raise HTTPException(status_code=403, detail="Admin only")
    return wizard

async def check_access(note_id: str, wizard: str) -> bool:
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        return False
    if notes[note_id]["owner"] == wizard:
        return True
    share_data = await data_store.get_share_data()
    return wizard in share_data["shares"].get(note_id, [])

# Wizards
@app.get("/wizards", response_model=List[WizardResponse])
async def view_wizards():
    wizards = await data_store.get_wizards()
    return [WizardResponse(name=name) for name in wizards]

# Notes
@app.post("/notes", response_model=NoteResponse)
async def create_note(req: CreateNoteRequest, wizard: str = Depends(get_wizard)):
    note_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    await data_store.add_note_meta(note_id, {
        "title": req.title,
        "owner": wizard,
        "created_at": created_at
    })
    await encryption_service.write_note(note_id, req.content)
    
    return NoteResponse(
        note_id=note_id,
        title=req.title,
        owner=wizard,
        created_at=created_at,
        shared_with=[]
    )

@app.get("/notes", response_model=List[NoteResponse])
async def view_notes(wizard: str = Depends(get_wizard)):
    notes = await data_store.get_notes_meta()
    share_data = await data_store.get_share_data()
    
    result = []
    for note_id, meta in notes.items():
        if meta["owner"] == wizard or wizard in share_data["shares"].get(note_id, []):
            result.append(NoteResponse(
                note_id=note_id,
                title=meta["title"],
                owner=meta["owner"],
                created_at=meta["created_at"],
                shared_with=share_data["shares"].get(note_id, [])
            ))
    return result

@app.get("/notes/{note_id}", response_model=NoteContentResponse)
async def read_note(note_id: str, wizard: str = Depends(get_wizard)):
    if not await check_access(note_id, wizard):
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    meta = notes[note_id]
    encrypted = encryption_service.read_note(note_id)
    decrypted = encryption_service.decrypt(encrypted)
    
    return NoteContentResponse(
        note_id=note_id,
        title=meta["title"],
        content=decrypted,
        owner=meta["owner"],
        created_at=meta["created_at"]
    )

@app.get("/notes/{note_id}/download", response_class=HTMLResponse)
async def download_note(note_id: str, wizard: str = Depends(get_wizard)):
    if not await check_access(note_id, wizard):
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    meta = notes[note_id]
    encrypted = encryption_service.read_note(note_id)
    decrypted = encryption_service.decrypt(encrypted)
    
    return HTMLResponse(f"""<!DOCTYPE html>
<html>
<head>
    <title>{meta['title']}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        .meta {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }}
        .content {{ line-height: 1.6; color: #34495e; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{meta['title']}</h1>
        <div class="meta"><strong>Owner:</strong> {meta['owner']} | <strong>Created:</strong> {meta['created_at']}</div>
        <div class="content">{decrypted}</div>
    </div>
</body>
</html>""")

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str, wizard: str = Depends(get_wizard)):
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    if notes[note_id]["owner"] != wizard:
        raise HTTPException(status_code=403, detail="Can only delete own notes")
    
    encryption_service.delete_note_file(note_id)
    await data_store.delete_note_meta(note_id)
    return {"message": "Note deleted"}

# Sharing
@app.post("/notes/share")
async def share_note(req: ShareNoteRequest, wizard: str = Depends(get_wizard)):
    notes = await data_store.get_notes_meta()
    if req.note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    if notes[req.note_id]["owner"] != wizard:
        raise HTTPException(status_code=403, detail="Only owner can share")
    
    wizards = await data_store.get_wizards()
    if req.wizard_name not in wizards:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    await data_store.add_share(req.note_id, req.wizard_name)
    return {"message": f"Note shared with {req.wizard_name}"}

@app.post("/access-requests")
async def request_access(req: AccessRequestRequest, wizard: str = Depends(get_wizard)):
    wizards = await data_store.get_wizards()
    if req.wizard_name not in wizards:
        raise HTTPException(status_code=404, detail="Wizard not found")
    if req.wizard_name == wizard:
        raise HTTPException(status_code=400, detail="Cannot request from yourself")
    
    request_id = str(uuid.uuid4())
    await data_store.add_request({
        "request_id": request_id,
        "from_wizard": wizard,
        "to_wizard": req.wizard_name,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    })
    return {"message": "Access request sent", "request_id": request_id}

@app.get("/access-requests", response_model=List[AccessRequestResponse])
async def check_requests(wizard: str = Depends(get_wizard)):
    share_data = await data_store.get_share_data()
    return [AccessRequestResponse(**r) for r in share_data["requests"] if r["to_wizard"] == wizard]

@app.post("/access-requests/approve")
async def allow_request(req: ApproveRequestRequest, wizard: str = Depends(get_wizard)):
    share_data = await data_store.get_share_data()
    
    access_req = next((r for r in share_data["requests"] if r["request_id"] == req.request_id), None)
    if not access_req:
        raise HTTPException(status_code=404, detail="Request not found")
    if access_req["to_wizard"] != wizard:
        raise HTTPException(status_code=403, detail="Not your request")
    if access_req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    
    await data_store.share_all_notes(wizard, access_req["from_wizard"])
    await data_store.update_request_status(req.request_id, "approved")
    return {"message": "Access granted"}

# Admin
@app.get("/admin/notes", response_model=List[NoteResponse])
async def admin_view_all(admin: str = Depends(get_admin)):
    notes = await data_store.get_notes_meta()
    share_data = await data_store.get_share_data()
    
    return [NoteResponse(
        note_id=nid,
        title=meta["title"],
        owner=meta["owner"],
        created_at=meta["created_at"],
        shared_with=share_data["shares"].get(nid, [])
    ) for nid, meta in notes.items()]

@app.get("/admin/notes/{note_id}/download", response_class=HTMLResponse)
async def admin_download(note_id: str, admin: str = Depends(get_admin)):
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    encrypted = encryption_service.read_note(note_id)
    return HTMLResponse(f"""<!DOCTYPE html>
<html>
<head>
    <title>Mischief Managed</title>
    <style>
        body {{ font-family: 'Courier New', monospace; max-width: 900px; margin: 50px auto; padding: 20px; background: #1a1a1a; color: #00ff00; }}
        .container {{ background: #0d0d0d; padding: 40px; border: 2px solid #00ff00; border-radius: 8px; }}
        h1 {{ text-align: center; font-size: 2.5em; text-shadow: 0 0 10px #00ff00; margin-bottom: 30px; }}
        .content {{ word-break: break-all; line-height: 1.4; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Mischief Managed ⚡</h1>
        <div class="content">{encrypted}</div>
    </div>
</body>
</html>""")

@app.delete("/admin/notes/{note_id}")
async def admin_delete(note_id: str, admin: str = Depends(get_admin)):
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    encryption_service.delete_note_file(note_id)
    await data_store.delete_note_meta(note_id)
    return {"message": "Note deleted by admin"}

@app.delete("/admin/shares")
async def admin_clear_shares(admin: str = Depends(get_admin)):
    await data_store.clear_all_shares()
    return {"message": "All shares removed"}

@app.post("/admin/wizards")
async def admin_create_wizard(req: CreateWizardRequest, admin: str = Depends(get_admin)):
    try:
        await data_store.add_wizard(req.name, req.api_key)
        return {"message": f"Wizard {req.name} created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"status": "operational", "message": "Mischief Managed API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)