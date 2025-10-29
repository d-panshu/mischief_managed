from pathlib import Path

# Data directories
DATA_DIR = Path("data")
NOTES_DIR = DATA_DIR / "notes"
WIZARDS_FILE = DATA_DIR / "wizards_info.json"
NOTES_META_FILE = DATA_DIR / "notes_meta.json"
SHARE_DATA_FILE = DATA_DIR / "share_data.json"
ENCRYPTION_KEY_FILE = DATA_DIR / ".encryption_key"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
NOTES_DIR.mkdir(exist_ok=True)

# Default wizards
DEFAULT_WIZARDS = {
    "Harry": "harry_secret_key_123",
    "Hermione": "hermione_secret_key_456",
    "Ron": "ron_secret_key_789",
    "Hagrid": "hagrid_secret_key_012",
    "Dumbledore": "dumbledore_admin_key_999"
}