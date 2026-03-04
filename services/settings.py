"""Settings CRUD service for application-wide configuration."""

from datetime import datetime

from services.database import Setting, db


def get_setting(key: str) -> str | None:
    """Get a setting value by key. Returns None if not found."""
    setting = db.session.get(Setting, key)
    return setting.value if setting else None


def set_setting(key: str, value: str) -> Setting:
    """Set a setting value. Creates or updates the entry."""
    setting = db.session.get(Setting, key)
    if setting:
        setting.value = value
        setting.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    else:
        setting = Setting(key=key, value=value, updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        db.session.add(setting)
    db.session.commit()
    return setting


def get_all_settings() -> dict[str, str]:
    """Get all settings as a key-value dict."""
    settings = Setting.query.all()
    return {s.key: s.value for s in settings}


def upload_cv_reference(html_content: str) -> Setting:
    """Upload or replace the global CV reference HTML."""
    if not html_content.strip():
        raise ValueError("Le contenu HTML du CV est vide")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    set_setting("cv_reference_html", html_content)
    return set_setting("cv_reference_date", now)


def get_cv_reference_html() -> str | None:
    """Get the global CV reference HTML content. Returns None if not configured."""
    return get_setting("cv_reference_html")
