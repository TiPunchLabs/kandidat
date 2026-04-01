"""Match scoring service — evaluates CV vs job offer fit using LLM."""

import json
import logging

from services.database import Candidature, db
from services.llm import get_provider
from services.settings import get_cv_reference_html, get_setting

logger = logging.getLogger(__name__)

DEFAULT_MATCH_SYSTEM_PROMPT = (
    "Tu es un expert en recrutement IT. "
    "Tu recois un CV au format HTML et une offre d'emploi.\n\n"
    "Ta mission : evaluer le pourcentage de correspondance entre le profil du candidat et le poste.\n\n"
    "Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte :\n"
    '{"score": <number 0-100>, "strengths": ["..."], "weaknesses": ["..."], "missing": ["..."]}\n\n'
    "Regles :\n"
    "- score : pourcentage de match global (0 = aucune correspondance, 100 = profil parfait)\n"
    "- strengths : 2-4 points forts du candidat pour ce poste (en francais)\n"
    "- weaknesses : 1-3 points faibles ou lacunes (en francais)\n"
    "- missing : 1-3 competences demandees absentes du CV (en francais)\n"
    "- Sois objectif et factuel, base-toi uniquement sur le contenu du CV et de l'offre\n"
    "- Retourne UNIQUEMENT le JSON, sans commentaire ni explication"
)

DEFAULT_MATCH_USER_PROMPT_TEMPLATE = """Voici le CV du candidat :

{cv_html}

---

Offre d'emploi :
- Poste : {poste}
- Entreprise : {entreprise}
- Description :
{contenu}

Evalue le match entre ce CV et cette offre. Retourne uniquement le JSON."""


def get_match_system_prompt() -> str:
    """Get the match system prompt from settings, or return the default."""
    return get_setting("match_system_prompt") or DEFAULT_MATCH_SYSTEM_PROMPT


def get_match_user_prompt_template() -> str:
    """Get the match user prompt template from settings, or return the default."""
    return get_setting("match_user_prompt") or DEFAULT_MATCH_USER_PROMPT_TEMPLATE


def evaluate_match(slug: str) -> dict:
    """Evaluate how well the reference CV matches a job offer.

    Args:
        slug: Candidature slug

    Returns:
        dict with match_score (float) and match_details (dict)

    Raises:
        ValueError: If no CV reference is configured or contenu is empty
        ConnectionError: If LLM provider is unreachable
        TimeoutError: If LLM call times out
    """
    candidature = db.session.get(Candidature, slug)
    if candidature is None:
        raise ValueError(f"Candidature '{slug}' non trouvee")

    cv_html = get_cv_reference_html()
    if not cv_html:
        raise ValueError("CV de reference non configure. Uploadez un CV dans les parametres.")

    if not candidature.contenu or not candidature.contenu.strip():
        raise ValueError("Le contenu de l'offre est vide. Ajoutez une description avant d'evaluer le match.")

    system_prompt = get_match_system_prompt()
    user_prompt = get_match_user_prompt_template().format(
        cv_html=cv_html,
        poste=candidature.poste or "Non precise",
        entreprise=candidature.entreprise,
        contenu=candidature.contenu,
    )

    provider = get_provider()
    logger.info("Evaluating match for '%s' via %s", slug, type(provider).__name__)
    raw_response = provider.complete(system_prompt, user_prompt)

    result = _parse_match_response(raw_response)

    candidature.match_score = result["match_score"]
    candidature.match_details = json.dumps(result["match_details"], ensure_ascii=False)
    db.session.commit()
    logger.info("Match score for '%s': %s%%", slug, result["match_score"])

    return result


def _parse_match_response(raw: str) -> dict:
    """Parse LLM JSON response into match result.

    Args:
        raw: Raw LLM response string (should be JSON)

    Returns:
        dict with match_score (float) and match_details (dict)

    Raises:
        ValueError: If response is not valid JSON or missing required fields
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Reponse LLM invalide (JSON attendu) : {e}") from e

    if "score" not in data:
        raise ValueError("Reponse LLM invalide : champ 'score' manquant")

    score = float(data["score"])
    score = max(0, min(100, score))

    return {
        "match_score": score,
        "match_details": {
            "strengths": data.get("strengths", []),
            "weaknesses": data.get("weaknesses", []),
            "missing": data.get("missing", []),
        },
    }
