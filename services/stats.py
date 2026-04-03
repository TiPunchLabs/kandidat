"""Shared stats computation service for candidatures."""

from services.candidature import CATEGORIES, PRIORITES, STATUTS, TYPES, list_candidatures


def compute_stats() -> dict:
    """Compute statistics across all candidatures.

    Returns a dict with keys:
    - total: int
    - by_statut: dict[str, int]
    - by_type: dict[str, int]
    - by_priorite: dict[str, int]
    - by_categorie: dict[str, int]
    - timeline: list[dict] sorted by date_candidature (entries with a date only)
    """
    candidatures = list_candidatures()

    by_statut = {s: sum(1 for c in candidatures if c.get("statut") == s) for s in STATUTS}
    by_type = {t: sum(1 for c in candidatures if c.get("type") == t) for t in TYPES}
    by_priorite = {p: sum(1 for c in candidatures if c.get("priorite") == p) for p in PRIORITES}
    by_categorie = {
        cat: sum(1 for c in candidatures if c.get("categorie_entreprise", "entreprise") == cat) for cat in CATEGORIES
    }

    timeline = sorted(
        [c for c in candidatures if c.get("date_candidature")],
        key=lambda c: c["date_candidature"],
    )

    return {
        "total": len(candidatures),
        "by_statut": by_statut,
        "by_type": by_type,
        "by_priorite": by_priorite,
        "by_categorie": by_categorie,
        "timeline": timeline,
    }
