"""CV adaptation orchestrator: LLM prompt building, adaptation, and file saving."""

import logging
from pathlib import Path

from flask import current_app

from services.cv_converter import save_cv_files, validate_html
from services.database import Candidature, Fichier, db
from services.llm import get_provider
from services.settings import get_cv_reference_html, get_setting

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Tu es un expert en redaction de CV professionnels. "
    "Tu recois un CV au format HTML et le contexte d'une candidature "
    "(poste, entreprise, description de l'offre).\n\n"
    "Ta mission : adapter le CV pour mettre en avant les competences, "
    "experiences et realisations les plus pertinentes pour le poste vise, "
    "tout en preservant la structure HTML et le style CSS du document original.\n\n"
    "Regles :\n"
    "- Retourne UNIQUEMENT le HTML du CV adapte, sans commentaire ni explication\n"
    "- Preserve la structure HTML (balises, classes CSS, IDs) du CV original\n"
    "- Ne supprime pas de sections, reorganise et reformule le contenu\n"
    "- Mets en avant les competences et experiences pertinentes pour le poste\n"
    "- Adapte le vocabulaire au secteur d'activite de l'entreprise\n"
    "- Garde un ton professionnel et factuel\n"
    "- Ne fabrique pas d'experiences ou de competences fictives"
)


DEFAULT_USER_PROMPT_TEMPLATE = """Voici le CV a adapter :

{cv_html}

---

Contexte de la candidature :
- Poste vise : {poste}
- Entreprise : {entreprise}
- Description de l'offre / contexte :
{contenu}

Adapte ce CV HTML pour cette candidature. Retourne uniquement le HTML adapte."""


def get_system_prompt() -> str:
    """Get the system prompt from settings, or return the default."""
    return get_setting("cv_adapt_system_prompt") or DEFAULT_SYSTEM_PROMPT


def get_user_prompt_template() -> str:
    """Get the user prompt template from settings, or return the default."""
    return get_setting("cv_adapt_user_prompt") or DEFAULT_USER_PROMPT_TEMPLATE


def resolve_cv_html(slug: str) -> str | None:
    """Resolve the CV HTML source for a candidature.

    Priority: candidature-specific HTML fichier > global setting.
    Returns the HTML content string, or None if no CV is configured.
    """
    html_fichier = Fichier.query.filter_by(slug=slug, type="html").first()
    if html_fichier:
        data_dir = Path(current_app.config["FT_DATA_DIR"])
        file_path = data_dir / html_fichier.chemin
        if file_path.is_file():
            return file_path.read_text(encoding="utf-8")

    return get_cv_reference_html()


def build_adaptation_context(slug: str) -> dict:
    """Extract adaptation context from a candidature.

    Returns dict with keys: poste, entreprise, contenu.
    Raises ValueError if candidature not found.
    """
    candidature = db.session.get(Candidature, slug)
    if candidature is None:
        raise ValueError(f"Candidature '{slug}' non trouvee")

    return {
        "poste": candidature.poste or "(non precise)",
        "entreprise": candidature.entreprise,
        "contenu": candidature.contenu or "(aucun contenu d'offre disponible)",
    }


def adapt_cv(slug: str, cv_source: str = "auto") -> dict:
    """Run the full CV adaptation flow: resolve CV, build context, call LLM.

    Args:
        slug: Candidature slug
        cv_source: "auto" (candidature-specific > global), "global", or "candidature"

    Returns:
        dict with adapted_html, provider_used, context, and optional warning
    """
    # Resolve CV HTML
    if cv_source == "candidature":
        html_fichier = Fichier.query.filter_by(slug=slug, type="html").first()
        if html_fichier:
            data_dir = Path(current_app.config["FT_DATA_DIR"])
            file_path = data_dir / html_fichier.chemin
            if file_path.is_file():
                cv_html = file_path.read_text(encoding="utf-8")
            else:
                raise ValueError("Fichier CV specifique introuvable sur le disque")
        else:
            raise ValueError("Aucun fichier HTML trouve pour cette candidature")
    elif cv_source == "global":
        cv_html = get_cv_reference_html()
        if not cv_html:
            raise ValueError("Aucun CV de reference configure. Uploadez-en un dans les parametres.")
    else:
        # Auto-detect: candidature-specific HTML file > global reference
        cv_html = resolve_cv_html(slug)
        if not cv_html:
            raise ValueError("Aucun CV de reference configure. Uploadez-en un dans les parametres.")

    # Build context
    context = build_adaptation_context(slug)

    # Detect missing content for warning
    warning = None
    candidature = db.session.get(Candidature, slug)
    if candidature and not candidature.contenu:
        warning = (
            "Aucun contenu d'offre disponible pour cette candidature. "
            "L'adaptation se base uniquement sur le poste et l'entreprise, "
            "le resultat sera moins precis."
        )

    # Build prompts
    user_prompt = get_user_prompt_template().format(
        cv_html=cv_html,
        poste=context["poste"],
        entreprise=context["entreprise"],
        contenu=context["contenu"],
    )

    # Call LLM
    provider = get_provider()
    adapted_html = provider.adapt_cv(cv_html, get_system_prompt(), user_prompt)

    # Validate the response
    if not validate_html(adapted_html):
        raise ValueError("Le LLM a retourne un HTML invalide ou vide. Essayez de relancer l'adaptation.")

    # Determine provider name
    provider_name = type(provider).__name__.replace("Provider", "").lower()

    result = {
        "adapted_html": adapted_html,
        "provider_used": provider_name,
        "context": {
            "poste": context["poste"],
            "entreprise": context["entreprise"],
            "contenu_preview": context["contenu"][:200],
        },
    }
    if warning:
        result["warning"] = warning
    return result


def save_adapted_cv(slug: str, adapted_html: str) -> list[dict]:
    """Generate PDF + DOCX from adapted HTML and save as Fichier entries.

    Returns list of file info dicts.
    """
    return save_cv_files(adapted_html, slug, prefix="cv_adapte")
