from pydantic import BaseModel
from typing import List

class Wizard(BaseModel):
    name: str
    api_key: str

class WizardResponse(BaseModel):
    name: str

class CreateNoteRequest(BaseModel):
    title: str
    content: str

class NoteResponse(BaseModel):
    note_id: str
    title: str
    owner: str
    created_at: str
    shared_with: List[str] = []

class NoteContentResponse(BaseModel):
    note_id: str
    title: str
    content: str
    owner: str
    created_at: str

class ShareNoteRequest(BaseModel):
    note_id: str
    wizard_name: str

class AccessRequestRequest(BaseModel):
    wizard_name: str

class AccessRequestResponse(BaseModel):
    request_id: str
    from_wizard: str
    to_wizard: str
    status: str
    created_at: str

class ApproveRequestRequest(BaseModel):
    request_id: str

class CreateWizardRequest(BaseModel):
    name: str
    api_key: str