"""File management service for candidature attachments."""

import logging
from pathlib import Path

from werkzeug.utils import secure_filename

from services.database import Candidature, Fichier, db

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".md", ".pdf", ".docx", ".jpeg", ".jpg", ".png", ".txt", ".js", ".html"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Extension → type mapping
_TYPE_MAP = {
    ".md": "markdown",
    ".pdf": "pdf",
    ".docx": "docx",
    ".jpeg": "image",
    ".jpg": "image",
    ".png": "image",
    ".txt": "text",
    ".js": "script",
    ".html": "html",
}


def _data_dir() -> Path:
    from flask import current_app

    return Path(current_app.config["FT_DATA_DIR"])


def _candidatures_dir() -> Path:
    return _data_dir() / "candidatures"


def detect_file_type(extension: str) -> str:
    """Map a file extension to a type label."""
    return _TYPE_MAP.get(extension.lower(), "other")


def validate_upload(filename: str, content_length: int) -> str:
    """Validate file extension and size. Return the secured filename.

    Raises ValueError if invalid.
    """
    if not filename:
        raise ValueError("Nom de fichier manquant")

    secured = secure_filename(filename)
    if not secured:
        raise ValueError("Nom de fichier invalide")

    ext = Path(secured).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Extension '{ext}' non autorisee. Extensions acceptees : {allowed}")

    if content_length > MAX_FILE_SIZE:
        raise ValueError(f"Fichier trop volumineux ({content_length} octets). Maximum : {MAX_FILE_SIZE} octets")

    return secured


def upload_fichier(slug: str, file) -> Fichier:
    """Upload a file for a candidature.

    1. Validate the file (extension, size)
    2. Check candidature exists
    3. Save to disk: FT_DATA_DIR/candidatures/<slug>/<filename>
    4. Insert or update DB entry
    5. Return the Fichier object
    """
    # Read content to check size
    content = file.read()
    file.seek(0)

    secured_name = validate_upload(file.filename, len(content))

    # Check candidature exists
    candidature = db.session.get(Candidature, slug)
    if candidature is None:
        raise ValueError(f"Candidature '{slug}' non trouvee")

    ext = Path(secured_name).suffix.lower()
    file_type = detect_file_type(ext)

    # Save to disk
    cand_dir = _candidatures_dir() / slug
    cand_dir.mkdir(parents=True, exist_ok=True)
    dest = cand_dir / secured_name
    dest.write_bytes(content)

    # Insert or update DB
    chemin = f"candidatures/{slug}/{secured_name}"
    existing = Fichier.query.filter_by(slug=slug, nom=secured_name).first()
    if existing:
        existing.chemin = chemin
        existing.type = file_type
        fichier = existing
    else:
        fichier = Fichier(slug=slug, nom=secured_name, chemin=chemin, type=file_type)
        db.session.add(fichier)

    db.session.commit()
    return fichier


def delete_fichier(slug: str, nom: str) -> bool:
    """Delete a file from disk and DB.

    Returns True if deleted, False if not found.
    """
    fichier = Fichier.query.filter_by(slug=slug, nom=nom).first()
    if fichier is None:
        return False

    # Delete from disk
    file_path = _candidatures_dir() / slug / nom
    if file_path.is_file():
        file_path.unlink()

    # Delete from DB
    db.session.delete(fichier)
    db.session.commit()
    return True


def get_fichier_path(slug: str, nom: str) -> Path | None:
    """Return the absolute path of a file on disk.

    Validates that the resolved path stays within the candidature directory (anti path-traversal).
    Returns None if invalid or not found.
    """
    cand_dir = _candidatures_dir() / slug
    file_path = (cand_dir / nom).resolve()

    # Security: ensure the path is within the candidature directory
    try:
        file_path.relative_to(cand_dir.resolve())
    except ValueError:
        return None

    if not file_path.is_file():
        return None

    return file_path
