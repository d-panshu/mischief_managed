from cryptography.fernet import Fernet
from fastapi import HTTPException
from pathlib import Path
import asyncio

class EncryptionService:
    def __init__(self, key_file: Path, notes_dir: Path):
        self.key_file = key_file
        self.notes_dir = notes_dir
        self.cipher_suite = Fernet(self._get_or_create_key())
    
    def _get_or_create_key(self) -> bytes:
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key
    
    def encrypt(self, content: str) -> str:
        return self.cipher_suite.encrypt(content.encode()).decode()
    
    def decrypt(self, encrypted_content: str) -> str:
        try:
            return self.cipher_suite.decrypt(encrypted_content.encode()).decode()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decrypt content")
    
    async def write_note(self, note_id: str, content: str):
        encrypted = self.encrypt(content)
        note_path = self.notes_dir / f"{note_id}.txt"
        
        await asyncio.sleep(0.01)  # Simulate async I/O
        
        with open(note_path, "w") as f:
            f.write(encrypted)
    
    def read_note(self, note_id: str) -> str:
        note_path = self.notes_dir / f"{note_id}.txt"
        if not note_path.exists():
            raise HTTPException(status_code=404, detail="Note file not found")
        
        with open(note_path, "r") as f:
            return f.read()
    
    def delete_note_file(self, note_id: str):
        note_path = self.notes_dir / f"{note_id}.txt"
        if note_path.exists():
            note_path.unlink()