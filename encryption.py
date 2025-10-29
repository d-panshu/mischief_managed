import asyncio
from pathlib import Path
from cryptography.fernet import Fernet
from fastapi import HTTPException

class EncryptionService:
    def __init__(self, key_file: Path, notes_dir: Path):
        self.notes_dir = notes_dir
        self.cipher_suite = Fernet(self._load_key(key_file))
    
    def _load_key(self, key_file: Path) -> bytes:
        if key_file.exists():
            return key_file.read_bytes()
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        return key
    
    def encrypt(self, content: str) -> str:
        return self.cipher_suite.encrypt(content.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        try:
            return self.cipher_suite.decrypt(encrypted.encode()).decode()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decrypt content")
    
    async def write_note(self, note_id: str, content: str):
        await asyncio.sleep(0.01)  # Simulate async I/O
        (self.notes_dir / f"{note_id}.txt").write_text(self.encrypt(content))
    
    def read_note(self, note_id: str) -> str:
        path = self.notes_dir / f"{note_id}.txt"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Note file not found")
        return path.read_text()
    
    def delete_note_file(self, note_id: str):
        path = self.notes_dir / f"{note_id}.txt"
        if path.exists():
            path.unlink()