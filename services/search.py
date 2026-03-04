"""Search across candidatures: hybrid DB content + files on disk."""

import re
from pathlib import Path

from services.database import Candidature, Fichier


def _data_dir() -> Path:
    from flask import current_app

    return Path(current_app.config["FT_DATA_DIR"])


def search_candidatures(query: str) -> list[dict]:
    """Search candidatures content (DB) and .md files on disk.

    Returns a list of dicts: {slug, filename, line, context, match}.
    Context includes ~50 chars before and after the match.
    """
    if not query or not query.strip():
        return []

    results = []
    query_lower = query.lower()
    escaped_query = re.escape(query)
    pattern = re.compile(f"(.{{0,50}})({escaped_query})(.{{0,50}})", re.IGNORECASE)

    # 1. Search in candidatures.contenu (DB)
    rows = Candidature.query.filter(Candidature.contenu.contains(query)).order_by(Candidature.slug).all()

    for row in rows:
        slug = row.slug
        contenu = row.contenu
        for line_num, line in enumerate(contenu.split("\n"), start=1):
            if query_lower in line.lower():
                m = pattern.search(line)
                if m:
                    context = f"{m.group(1)}{m.group(2)}{m.group(3)}"
                else:
                    context = line[:120]
                results.append(
                    {
                        "slug": slug,
                        "filename": "index.md",
                        "line": line_num,
                        "context": context,
                        "match": query,
                    }
                )

    # 2. Search in .md files on disk (via fichiers table)
    fichier_rows = Fichier.query.filter_by(type="markdown").order_by(Fichier.slug, Fichier.nom).all()

    for frow in fichier_rows:
        file_path = _data_dir() / frow.chemin
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_num, line in enumerate(content.split("\n"), start=1):
            if query_lower in line.lower():
                m = pattern.search(line)
                if m:
                    context = f"{m.group(1)}{m.group(2)}{m.group(3)}"
                else:
                    context = line[:120]
                results.append(
                    {
                        "slug": frow.slug,
                        "filename": frow.nom,
                        "line": line_num,
                        "context": context,
                        "match": query,
                    }
                )

    return results
