import os
import tempfile
from pathlib import Path

from services.candidature import list_candidatures


def _data_dir() -> Path:
    from flask import current_app

    return Path(current_app.config["FT_DATA_DIR"])


def regenerate_dashboard() -> None:
    """Regenerate 00-Dashboard.md with current candidature data and valid wikilinks."""
    candidatures = list_candidatures()

    lines = []
    lines.append("---")
    lines.append("tags: [dashboard]")
    lines.append("---")
    lines.append("")
    lines.append("# Tableau de bord - Recherche d'emploi")
    lines.append("")
    lines.append("> **Xavier GUERET** - Ingenieur DevOps - Guadeloupe")
    lines.append("")
    lines.append("## Candidatures actives")
    lines.append("")
    lines.append("| Entreprise | Poste | Type | Statut | Date | Localisation | Priorite |")
    lines.append("|---|---|---|---|---|---|---|")

    for c in candidatures:
        entreprise = c.get("entreprise", c["slug"])
        slug = c["slug"]
        poste = c.get("poste", "") or "-"
        ctype = (c.get("type", "") or "").capitalize()
        statut = (c.get("statut", "") or "").capitalize().replace("-", " ")
        date_cand = c.get("date_candidature", "")
        if date_cand:
            # Format date as DD/MM/YYYY if it's YYYY-MM-DD
            try:
                parts = date_cand.split("-")
                if len(parts) == 3:
                    date_cand = f"{parts[2]}/{parts[1]}/{parts[0]}"
            except Exception:  # nosec B110
                pass
        else:
            date_cand = "-"
        localisation = c.get("localisation", "") or "-"
        priorite = (c.get("priorite", "") or "").capitalize()

        wikilink = f"[[candidatures/{slug}/index|{entreprise}]]"
        lines.append(f"| {wikilink} | {poste} | {ctype} | {statut} | {date_cand} | {localisation} | {priorite} |")

    # Statistics
    lines.append("")
    lines.append("## Statistiques")
    lines.append("")
    total = len(candidatures)
    offres = sum(1 for c in candidatures if c.get("type") == "offre")
    spontanees = sum(1 for c in candidatures if c.get("type") == "spontanee")
    envoyees = sum(1 for c in candidatures if c.get("statut") == "envoyee")
    sans_reponse = sum(1 for c in candidatures if c.get("statut") == "sans-reponse")
    brouillon = sum(1 for c in candidatures if c.get("statut") == "brouillon")

    lines.append(f"- **Total** : {total} candidatures")
    lines.append(f"- **Offres** : {offres}")
    lines.append(f"- **Spontanees** : {spontanees}")
    lines.append(f"- **Envoyees** : {envoyees}")
    lines.append(f"- **Sans reponse** : {sans_reponse}")
    lines.append(f"- **Brouillon** : {brouillon}")
    lines.append("")

    content = "\n".join(lines) + "\n"

    # Atomic write
    dashboard_path = _data_dir() / "00-Dashboard.md"
    fd, tmp_path = tempfile.mkstemp(dir=str(_data_dir()), suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(dashboard_path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
