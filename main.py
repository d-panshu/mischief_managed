from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import List
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
from auth import AuthService

# Initialize services
data_store = DataStore(WIZARDS_FILE, NOTES_META_FILE, SHARE_DATA_FILE, DEFAULT_WIZARDS)
encryption_service = EncryptionService(ENCRYPTION_KEY_FILE, NOTES_DIR)
auth_service = AuthService(data_store)

# FastAPI app
app = FastAPI(
    title="Mischief Managed",
    description="A magical note management system for wizards",
    version="1.0.0"
)

# ============================================================================
# WIZARD ENDPOINTS
# ============================================================================

@app.get("/wizards", response_model=List[WizardResponse], tags=["Wizards"])
async def view_wizards():
    """View all wizard names (without API keys)."""
    wizards = await data_store.get_wizards()
    return [WizardResponse(name=name) for name in wizards.keys()]

@app.post("/notes", response_model=NoteResponse, tags=["Notes"])
async def create_note(
    request: CreateNoteRequest,
    wizard: str = Depends(auth_service.get_current_wizard)
):
    """Create a new encrypted note."""
    note_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    meta = {
        "title": request.title,
        "owner": wizard,
        "created_at": created_at
    }
    await data_store.add_note_meta(note_id, meta)
    await encryption_service.write_note(note_id, request.content)
    
    return NoteResponse(
        note_id=note_id,
        title=request.title,
        owner=wizard,
        created_at=created_at,
        shared_with=[]
    )

@app.get("/notes", response_model=List[NoteResponse], tags=["Notes"])
async def view_notes(wizard: str = Depends(auth_service.get_current_wizard)):
    """View all notes owned by or shared with the wizard."""
    notes = await data_store.get_notes_meta()
    share_data = await data_store.get_share_data()
    
    result = []
    for note_id, meta in notes.items():
        if meta["owner"] == wizard or (
            note_id in share_data["shares"] and 
            wizard in share_data["shares"][note_id]
        ):
            shared_with = share_data["shares"].get(note_id, [])
            result.append(NoteResponse(
                note_id=note_id,
                title=meta["title"],
                owner=meta["owner"],
                created_at=meta["created_at"],
                shared_with=shared_with
            ))
    
    return result

@app.get("/notes/{note_id}", response_model=NoteContentResponse, tags=["Notes"])
async def read_note(note_id: str, wizard: str = Depends(auth_service.get_current_wizard)):
    """Read decrypted content of a specific note."""
    if not await auth_service.check_note_access(note_id, wizard):
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    meta = notes[note_id]
    encrypted_content = encryption_service.read_note(note_id)
    decrypted_content = encryption_service.decrypt(encrypted_content)
    
    return NoteContentResponse(
        note_id=note_id,
        title=meta["title"],
        content=decrypted_content,
        owner=meta["owner"],
        created_at=meta["created_at"]
    )

@app.get("/notes/{note_id}/download", response_class=HTMLResponse, tags=["Notes"])
async def download_note(note_id: str, wizard: str = Depends(auth_service.get_current_wizard)):
    """Download note as HTML with decrypted content."""
    if not await auth_service.check_note_access(note_id, wizard):
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = await data_store.get_notes_meta()
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    meta = notes[note_id]
    encrypted_content = encryption_service.read_note(note_id)
    decrypted_content = encryption_service.decrypt(encrypted_content)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{meta['title']}</title>
        <style>
            body {{
                font-family: 'Georgia', serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            .meta {{
                color: #7f8c8d;
                font-size: 0.9em;
                margin-bottom: 20px;
            }}
            .content {{
                line-height: 1.6;
                color: #34495e;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{meta['title']}</h1>
            <div class="meta">
                <strong>Owner:</strong> {meta['owner']} | 
                <strong>Created:</strong> {meta['created_at']}
            </div>
            <div class="content">{decrypted_content}</div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

@app.post("/notes/share", tags=["Sharing"])
async def share_note(
    request: ShareNoteRequest,
    wizard: str = Depends(auth_service.get_current_wizard)
):
    """Share a note with another wizard."""
    notes = await data_store.get_notes_meta()
    
    if request.note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if notes[request.note_id]["owner"] != wizard:
        raise HTTPException(status_code=403, detail="Only owner can share notes")
    
    wizards = await data_store.get_wizards()
    if request.wizard_name not in wizards:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    await data_store.add_share(request.note_id, request.wizard_name)
    
    return {"message": f"Note shared with {request.wizard_name}"}

@app.post("/access-requests", tags=["Sharing"])
async def request_access(
    request: AccessRequestRequest,
    wizard: str = Depends(auth_service.get_current_wizard)
):
    """Request access to all notes from another wizard."""
    wizards = await data_store.get_wizards()
    if request.wizard_name not in wizards:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    if request.wizard_name == wizard:
        raise HTTPException(status_code=400, detail="Cannot request access from yourself")
    
    request_id = str(uuid.uuid4())
    access_request = {
        "request_id": request_id,
        "from_wizard": wizard,
        "to_wizard": request.wizard_name,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    await data_store.add_request(access_request)
    
    return {"message": "Access request sent", "request_id": request_id}

@app.get("/access-requests", response_model=List[AccessRequestResponse], tags=["Sharing"])
async def check_requests(wizard: str = Depends(auth_service.get_current_wizard)):
    """Check incoming access requests."""
    share_data = await data_store.get_share_data()
    
    requests = [
        AccessRequestResponse(**req)
        for req in share_data["requests"]
        if req["to_wizard"] == wizard
    ]
    
    return requests

@app.post("/access-requests/approve", tags=["Sharing"])
async def allow_request(
    request: ApproveRequestRequest,
    wizard: str = Depends(auth_service.get_current_wizard)
):
    """Approve an access request."""
    share_data = await data_store.get_share_data()
    
    access_req = None
    for req in share_data["requests"]:
        if req["request_id"] == request.request_id:
            access_req = req
            break
    
    if not access_req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if access_req["to_wizard"] != wizard:
        raise HTTPException(status_code=403, detail="Not your request")
    
    if access_req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    await data_store.share_all_notes(wizard, access_req["from_wizard"])
    await data_store.update_request_status(request.request_id, "approved")
    
    return {"message": "Access granted"}

@app.delete("/notes/{note_id}", tags=["Notes"])
async def delete_note(note_id: str, wizard: str = Depends(auth_service.get_current_wizard)):
    """Delete own note."""
    notes = await data_store.get_notes_meta()
    
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if notes[note_id]["owner"] != wizard:
        raise HTTPException(status_code=403, detail="Can only delete own notes")
    
    encryption_service.delete_note_file(note_id)
    await data_store.delete_note_meta(note_id)
    
    return {"message": "Note deleted"}

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/admin/notes", response_model=List[NoteResponse], tags=["Admin"])
async def admin_view_all_notes(admin: str = Depends(auth_service.get_admin)):
    """View all notes metadata (admin only)."""
    notes = await data_store.get_notes_meta()
    share_data = await data_store.get_share_data()
    
    result = []
    for note_id, meta in notes.items():
        shared_with = share_data["shares"].get(note_id, [])
        result.append(NoteResponse(
            note_id=note_id,
            title=meta["title"],
            owner=meta["owner"],
            created_at=meta["created_at"],
            shared_with=shared_with
        ))
    
    return result

@app.get("/admin/notes/{note_id}/download", response_class=HTMLResponse, tags=["Admin"])
async def admin_download_note(note_id: str, admin: str = Depends(auth_service.get_admin)):
    """Download encrypted note as HTML (admin only)."""
    notes = await data_store.get_notes_meta()
    
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    encrypted_content = encryption_service.read_note(note_id)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mischief Managed</title>
        <style>
            body {{
                font-family: 'Courier New', monospace;
                max-width: 900px;
                margin: 50px auto;
                padding: 20px;
                background: #1a1a1a;
                color: #00ff00;
            }}
            .container {{
                background: #0d0d0d;
                padding: 40px;
                border: 2px solid #00ff00;
                border-radius: 8px;
            }}
            h1 {{
                text-align: center;
                font-size: 2.5em;
                text-shadow: 0 0 10px #00ff00;
                margin-bottom: 30px;
            }}
            .content {{
                word-break: break-all;
                line-height: 1.4;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ Mischief Managed ⚡</h1>
            <div class="content">{encrypted_content}</div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

@app.delete("/admin/notes/{note_id}", tags=["Admin"])
async def admin_delete_note(note_id: str, admin: str = Depends(auth_service.get_admin)):
    """Delete any note (admin only)."""
    notes = await data_store.get_notes_meta()
    
    if note_id not in notes:
        raise HTTPException(status_code=404, detail="Note not found")
    
    encryption_service.delete_note_file(note_id)
    await data_store.delete_note_meta(note_id)
    
    return {"message": "Note deleted by admin"}

@app.delete("/admin/shares", tags=["Admin"])
async def admin_remove_all_shares(admin: str = Depends(auth_service.get_admin)):
    """Remove all sharing relationships (admin only)."""
    await data_store.clear_all_shares()
    return {"message": "All shares removed"}

@app.post("/admin/wizards", tags=["Admin"])
async def admin_create_wizard(
    request: CreateWizardRequest,
    admin: str = Depends(auth_service.get_admin)
):
    """Create a new wizard (admin only)."""
    try:
        await data_store.add_wizard(request.name, request.api_key)
        return {"message": f"Wizard {request.name} created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "operational",
        "message": "Mischief Managed API is running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)