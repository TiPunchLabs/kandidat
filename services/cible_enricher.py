"""Cible enrichment orchestrator: Tavily web search + LLM structured extraction."""

import json
import logging

from services.database import Cible, db
from services.llm import get_provider
from services.settings import get_setting

logger = logging.getLogger(__name__)

ENRICHMENT_SYSTEM_PROMPT = (
    "Tu es un assistant specialise dans la recherche d'informations sur les entreprises. "
    "Tu recois des resultats de recherche web et tu dois en extraire des informations structurees.\n\n"
    "Regles :\n"
    "- Retourne UNIQUEMENT un objet JSON valide, sans commentaire ni explication\n"
    "- N'invente pas d'informations : si tu ne trouves pas une donnee, laisse le champ vide\n"
    "- Pour les URLs, retourne uniquement des URLs completes et valides\n"
    "- Pour les emails, retourne uniquement des emails au format valide\n"
    "- Pour les numeros de telephone, conserve le format original\n"
    "- Pour LinkedIn, retourne l'URL complete du profil"
)

ENRICHMENT_USER_PROMPT_TEMPLATE = """Analyse les resultats de recherche suivants pour l'entreprise "{company_name}" \
et extrait les informations structurees.

Resultats de recherche sur l'entreprise :
{company_results}

Resultats de recherche sur les contacts :
{contact_results}

Retourne un objet JSON avec cette structure exacte :
{{
  "company": {{
    "url": "URL du site officiel ou vide",
    "linkedin": "URL LinkedIn de l'entreprise ou vide",
    "description": "Description courte de l'entreprise ou vide",
    "email": "Email de contact general ou vide"
  }},
  "contacts": [
    {{
      "nom": "Nom de famille",
      "prenom": "Prenom",
      "fonction": "Poste / Fonction",
      "linkedin": "URL LinkedIn du profil ou vide",
      "email": "Email professionnel ou vide",
      "telephone": "Telephone ou vide"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON, sans texte avant ou apres."""


def _get_tavily_client():
    """Get configured Tavily client. Raises ValueError if not configured."""
    api_key = get_setting("tavily_api_key")
    if not api_key:
        raise ValueError("Cle API Tavily non configuree. Configurez-la dans les parametres.")

    from tavily import TavilyClient

    return TavilyClient(api_key=api_key)


def test_tavily_connection() -> dict:
    """Test Tavily API connectivity."""
    client = _get_tavily_client()
    try:
        client.search("test", max_results=1)
        return {"status": "ok", "provider": "tavily"}
    except Exception as e:
        raise ConnectionError(f"Tavily non accessible: {e}") from e


def _search_company_info(client, company_name: str) -> str:
    """Search for company website and LinkedIn page."""
    query = f"{company_name} site officiel linkedin"
    try:
        results = client.search(query, max_results=5, search_depth="basic")
        return _format_search_results(results)
    except Exception as e:
        logger.warning("Tavily search failed for company info: %s", e)
        return "(aucun resultat)"


def _search_contacts(client, company_name: str) -> str:
    """Search for company contacts and leadership."""
    query = f"{company_name} contacts dirigeants equipe linkedin"
    try:
        results = client.search(query, max_results=5, search_depth="basic")
        return _format_search_results(results)
    except Exception as e:
        logger.warning("Tavily search failed for contacts: %s", e)
        return "(aucun resultat)"


def _format_search_results(results: dict) -> str:
    """Format Tavily search results into a readable text block."""
    formatted = []
    for r in results.get("results", []):
        formatted.append(f"- {r.get('title', 'Sans titre')}")
        formatted.append(f"  URL: {r.get('url', '')}")
        formatted.append(f"  {r.get('content', '')[:500]}")
        formatted.append("")
    return "\n".join(formatted) if formatted else "(aucun resultat)"


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Le LLM a retourne un JSON invalide: {e}") from e


def enrich_cible(cible_id: int) -> dict:
    """Run the full enrichment flow: Tavily search + LLM extraction.

    Returns dict with cible_id, cible_name, current data, suggestions, and provider_used.
    """
    cible = db.session.get(Cible, cible_id)
    if cible is None:
        raise ValueError(f"Cible {cible_id} non trouvee")

    # Step 1: Tavily searches
    tavily_client = _get_tavily_client()
    company_results = _search_company_info(tavily_client, cible.nom)
    contact_results = _search_contacts(tavily_client, cible.nom)

    # Step 2: Build LLM prompt
    user_prompt = ENRICHMENT_USER_PROMPT_TEMPLATE.format(
        company_name=cible.nom,
        company_results=company_results,
        contact_results=contact_results,
    )

    # Step 3: Call LLM for structured extraction
    provider = get_provider()
    raw_response = provider.complete(ENRICHMENT_SYSTEM_PROMPT, user_prompt)

    # Step 4: Parse JSON response
    suggestions = _extract_json_from_response(raw_response)

    if "company" not in suggestions:
        suggestions["company"] = {}
    if "contacts" not in suggestions:
        suggestions["contacts"] = []

    provider_name = type(provider).__name__.replace("Provider", "").lower()

    return {
        "cible_id": cible.id,
        "cible_name": cible.nom,
        "current": {
            "url": cible.url,
            "linkedin": cible.linkedin,
            "description": cible.description,
            "email": cible.email,
        },
        "suggestions": suggestions,
        "provider_used": provider_name,
    }


def apply_enrichment(cible_id: int, accepted: dict) -> dict:
    """Apply user-accepted enrichment suggestions.

    Args:
        cible_id: Target company ID.
        accepted: Dict with optional keys 'company' (fields to update) and 'contacts' (list to create).

    Returns summary dict with counts of applied changes.
    """
    from services.cibles import create_contact, update_cible

    cible = db.session.get(Cible, cible_id)
    if cible is None:
        raise ValueError(f"Cible {cible_id} non trouvee")

    result = {"company_updated": False, "contacts_created": 0}

    # Apply company field updates
    company_fields = accepted.get("company", {})
    if company_fields:
        fields_to_update = {k: v for k, v in company_fields.items() if v}
        if fields_to_update:
            update_cible(cible_id, **fields_to_update)
            result["company_updated"] = True

    # Create accepted contacts
    for contact_data in accepted.get("contacts", []):
        if contact_data.get("nom"):
            create_contact(
                cible_id,
                nom=contact_data.get("nom", ""),
                prenom=contact_data.get("prenom", ""),
                email=contact_data.get("email", ""),
                telephone=contact_data.get("telephone", ""),
                linkedin=contact_data.get("linkedin", ""),
                fonction=contact_data.get("fonction", ""),
            )
            result["contacts_created"] += 1

    return result
