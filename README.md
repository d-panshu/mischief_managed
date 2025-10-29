Mischief Managed - FastAPI Backend

A secure note management system for wizards with encryption and sharing capabilities.

##  Project Structure

```
mischief_managed/
├── main.py              # FastAPI routes and endpoints
├── models.py            # Pydantic request/response models
├── auth.py              # Authentication and authorization
├── encryption.py        # Encryption service
├── data_store.py       # Data persistence layer
├── config.py           # Configuration and constants
├── requirements.txt    # Python dependencies
└── README.md           # This file

data/                   # Created automatically
├── wizards_info.json   # Wizard credentials
├── notes_meta.json     # Note metadata
├── share_data.json     # Sharing information
├── .encryption_key     # Encryption key
└── notes/              # Encrypted note files
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py

# Or with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Default API Keys

- **Harry**: `harry_secret_key_123`
- **Hermione**: `hermione_secret_key_456`
- **Ron**: `ron_secret_key_789`
- **Hagrid**: `hagrid_secret_key_012`
- **Dumbledore** (Admin): `dumbledore_admin_key_999`

##  API Documentation

Access interactive API docs at: `http://localhost:8000/docs`

##  Expose with ngrok

```bash
ngrok http 8000
```

Access at: `https://8e0e054a74d7.ngrok-free.app/docs`

##  Features

### Wizard Endpoints
- View all wizards
- Create encrypted notes (async)
- View accessible notes
- Read decrypted content
- Download notes as HTML
- Share notes
- Request/approve access
- Delete own notes

### Admin Endpoints
- View all note metadata
- Download encrypted notes
- Delete any note
- Remove all shares
- Create new wizards

## Security

- Fernet symmetric encryption
- API key authentication
- Role-based access control
- Thread-safe operations

## Example Usage

```python
import requests

# Wizard creates a note
response = requests.post(
    "http://localhost:8000/notes",
    headers={"X-API-Key": "harry_secret_key_123"},
    json={"title": "My Secret", "content": "This is private"}
)

# Admin views all notes (metadata only)
response = requests.get(
    "http://localhost:8000/admin/notes",
    headers={"X-API-Key": "dumbledore_admin_key_999"}
)
