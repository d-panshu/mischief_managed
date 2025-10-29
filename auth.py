from fastapi import HTTPException, Header, Depends
from data_store import DataStore

class AuthService:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
    
    async def get_current_wizard(self, x_api_key: str = Header(...)) -> str:
        wizards = await self.data_store.get_wizards()
        for name, key in wizards.items():
            if key == x_api_key:
                return name
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    async def get_admin(self, x_api_key: str = Header(...)) -> str:
        wizards = await self.data_store.get_wizards()
        if wizards.get("Dumbledore") == x_api_key:
            return "Dumbledore"
        raise HTTPException(status_code=403, detail="Admin access required")
    
    async def check_note_access(self, note_id: str, wizard: str) -> bool:
        notes = await self.data_store.get_notes_meta()
        if note_id not in notes:
            return False
        
        note = notes[note_id]
        if note["owner"] == wizard:
            return True
        
        share_data = await self.data_store.get_share_data()
        if note_id in share_data["shares"] and wizard in share_data["shares"][note_id]:
            return True
        
        return False
