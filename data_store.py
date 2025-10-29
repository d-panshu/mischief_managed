import json
import asyncio
from pathlib import Path
from typing import Dict

class DataStore:
    def __init__(self, wizards_file: Path, notes_meta_file: Path, 
                 share_data_file: Path, default_wizards: Dict[str, str]):
        self.wizards_file = wizards_file
        self.notes_meta_file = notes_meta_file
        self.share_data_file = share_data_file
        self.lock = asyncio.Lock()
        self._init_files(default_wizards)
    
    def _init_files(self, default_wizards: Dict[str, str]):
        if not self.wizards_file.exists():
            self._write_json(self.wizards_file, default_wizards)
        
        if not self.notes_meta_file.exists():
            self._write_json(self.notes_meta_file, {})
        
        if not self.share_data_file.exists():
            self._write_json(self.share_data_file, {
                "shares": {},
                "requests": []
            })
    
    def _read_json(self, filepath: Path) -> dict:
        with open(filepath, "r") as f:
            return json.load(f)
    
    def _write_json(self, filepath: Path, data: dict):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    
    async def get_wizards(self) -> dict:
        async with self.lock:
            return self._read_json(self.wizards_file)
    
    async def add_wizard(self, name: str, api_key: str):
        async with self.lock:
            wizards = self._read_json(self.wizards_file)
            if name in wizards:
                raise ValueError("Wizard already exists")
            wizards[name] = api_key
            self._write_json(self.wizards_file, wizards)
    
    async def get_notes_meta(self) -> dict:
        async with self.lock:
            return self._read_json(self.notes_meta_file)
    
    async def add_note_meta(self, note_id: str, meta: dict):
        async with self.lock:
            notes = self._read_json(self.notes_meta_file)
            notes[note_id] = meta
            self._write_json(self.notes_meta_file, notes)
    
    async def delete_note_meta(self, note_id: str):
        async with self.lock:
            notes = self._read_json(self.notes_meta_file)
            if note_id in notes:
                del notes[note_id]
                self._write_json(self.notes_meta_file, notes)
    
    async def get_share_data(self) -> dict:
        async with self.lock:
            return self._read_json(self.share_data_file)
    
    async def add_share(self, note_id: str, wizard_name: str):
        async with self.lock:
            data = self._read_json(self.share_data_file)
            if note_id not in data["shares"]:
                data["shares"][note_id] = []
            if wizard_name not in data["shares"][note_id]:
                data["shares"][note_id].append(wizard_name)
            self._write_json(self.share_data_file, data)
    
    async def add_request(self, request: dict):
        async with self.lock:
            data = self._read_json(self.share_data_file)
            data["requests"].append(request)
            self._write_json(self.share_data_file, data)
    
    async def update_request_status(self, request_id: str, status: str):
        async with self.lock:
            data = self._read_json(self.share_data_file)
            for req in data["requests"]:
                if req["request_id"] == request_id:
                    req["status"] = status
                    break
            self._write_json(self.share_data_file, data)
    
    async def clear_all_shares(self):
        async with self.lock:
            data = self._read_json(self.share_data_file)
            data["shares"] = {}
            self._write_json(self.share_data_file, data)
    
    async def share_all_notes(self, owner: str, recipient: str):
        async with self.lock:
            notes = self._read_json(self.notes_meta_file)
            data = self._read_json(self.share_data_file)
            
            for note_id, meta in notes.items():
                if meta["owner"] == owner:
                    if note_id not in data["shares"]:
                        data["shares"][note_id] = []
                    if recipient not in data["shares"][note_id]:
                        data["shares"][note_id].append(recipient)
            
            self._write_json(self.share_data_file, data)