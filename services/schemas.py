"""Pydantic v2 schemas for kandidat validation and serialization."""

import json
import re

from pydantic import BaseModel, field_validator

_VALID_TYPES = {"offre", "spontanee"}
_VALID_PRIORITES = {"haute", "moyenne", "basse"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CandidatureCreate(BaseModel):
    """Schema for creating a new candidature."""

    entreprise: str
    poste: str = ""
    type: str = "offre"
    localisation: str = ""
    priorite: str = "moyenne"
    cible_id: int
    contenu: str = ""

    @field_validator("entreprise")
    @classmethod
    def entreprise_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("entreprise is required")
        return v.strip()

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v not in _VALID_TYPES:
            raise ValueError(f"type must be one of {_VALID_TYPES}")
        return v

    @field_validator("priorite")
    @classmethod
    def priorite_valid(cls, v: str) -> str:
        if v not in _VALID_PRIORITES:
            raise ValueError(f"priorite must be one of {_VALID_PRIORITES}")
        return v


class CandidatureUpdate(BaseModel):
    """Schema for updating a candidature (all fields optional)."""

    statut: str | None = None
    priorite: str | None = None
    categorie_entreprise: str | None = None
    date_candidature: str | None = None
    date_relance: str | None = None
    entreprise: str | None = None
    poste: str | None = None
    type: str | None = None
    localisation: str | None = None
    contenu: str | None = None

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_TYPES:
            raise ValueError(f"type must be one of {_VALID_TYPES}")
        return v

    @field_validator("priorite")
    @classmethod
    def priorite_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_PRIORITES:
            raise ValueError(f"priorite must be one of {_VALID_PRIORITES}")
        return v

    @field_validator("date_candidature", "date_relance")
    @classmethod
    def date_format_valid(cls, v: str | None) -> str | None:
        if v is not None and v != "" and not _DATE_RE.match(v):
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    def non_null_fields(self) -> dict:
        """Return a dict of fields that are not None."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class FichierResponse(BaseModel):
    """Schema for a fichier in API responses."""

    nom: str
    chemin: str
    type: str


class CibleSummary(BaseModel):
    """Minimal cible info embedded in candidature responses."""

    id: int
    nom: str
    categorie: str


class CandidatureResponse(BaseModel):
    """Schema for a candidature in API responses."""

    slug: str
    entreprise: str
    poste: str
    type: str
    statut: str
    date_candidature: str
    date_relance: str
    localisation: str
    priorite: str
    categorie_entreprise: str
    cible_id: int
    cible: CibleSummary | None = None
    tags: list[str]
    contenu: str
    match_score: float | None = None
    match_details: dict | None = None
    fichiers: list[FichierResponse] = []

    @classmethod
    def from_orm(cls, obj) -> "CandidatureResponse":
        """Convert a SQLAlchemy Candidature model to a Pydantic response."""
        tags = obj.tags
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError):
                tags = ["candidature"]

        date_candidature = obj.date_candidature or ""
        date_relance = obj.date_relance or ""

        fichiers = [FichierResponse(nom=f.nom, chemin=f.chemin, type=f.type) for f in obj.fichiers]

        cible_summary = None
        if obj.cible:
            cible_summary = CibleSummary(id=obj.cible.id, nom=obj.cible.nom, categorie=obj.cible.categorie)

        match_details = None
        if obj.match_details:
            try:
                match_details = json.loads(obj.match_details)
            except (json.JSONDecodeError, TypeError):
                match_details = None

        return cls(
            slug=obj.slug,
            entreprise=obj.entreprise,
            poste=obj.poste,
            type=obj.type,
            statut=obj.statut,
            date_candidature=str(date_candidature),
            date_relance=str(date_relance),
            localisation=obj.localisation,
            priorite=obj.priorite,
            categorie_entreprise=obj.categorie_entreprise,
            cible_id=obj.cible_id,
            cible=cible_summary,
            tags=tags,
            contenu=obj.contenu,
            match_score=obj.match_score,
            match_details=match_details,
            fichiers=fichiers,
        )


class HistoriqueStatutResponse(BaseModel):
    """Schema for a historique_statut entry in API responses."""

    id: int
    ancien_statut: str | None
    nouveau_statut: str
    date_changement: str
    commentaire: str | None = None


class ContactCreate(BaseModel):
    """Schema for creating a new contact."""

    nom: str
    prenom: str = ""
    email: str = ""
    telephone: str = ""
    linkedin: str = ""
    fonction: str = ""

    @field_validator("nom")
    @classmethod
    def nom_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nom is required")
        return v.strip()


class ContactUpdate(BaseModel):
    """Schema for updating a contact (all fields optional)."""

    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None
    linkedin: str | None = None
    fonction: str | None = None

    def non_null_fields(self) -> dict:
        """Return a dict of fields that are not None."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ContactResponse(BaseModel):
    """Schema for a contact in API responses."""

    id: int
    nom: str
    prenom: str
    email: str
    telephone: str
    linkedin: str
    fonction: str


class CibleDetailResponse(BaseModel):
    """Schema for a cible detail with contacts and candidatures."""

    id: int
    nom: str
    categorie: str
    contactee: bool
    position: int
    url: str
    description: str
    email: str
    linkedin: str
    inscrit_plateforme: bool
    notes: str = ""
    contacts: list[ContactResponse] = []
    candidatures: list[dict] = []


class CibleCreate(BaseModel):
    """Schema for creating a new cible."""

    nom: str
    categorie: str
    url: str = ""
    description: str = ""
    email: str = ""
    linkedin: str = ""
    inscrit_plateforme: bool = False
    notes: str = ""

    @field_validator("nom")
    @classmethod
    def nom_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nom is required")
        return v.strip()

    @field_validator("categorie")
    @classmethod
    def categorie_valid(cls, v: str | None) -> str | None:
        from services.cibles import CATEGORIES as CIBLE_CATEGORIES

        if v not in CIBLE_CATEGORIES:
            raise ValueError(f"categorie must be one of {set(CIBLE_CATEGORIES)}")
        return v


class CibleUpdate(BaseModel):
    """Schema for updating a cible (all fields optional)."""

    nom: str | None = None
    categorie: str | None = None
    contactee: bool | None = None
    url: str | None = None
    description: str | None = None
    email: str | None = None
    linkedin: str | None = None
    inscrit_plateforme: bool | None = None
    notes: str | None = None

    @field_validator("categorie")
    @classmethod
    def categorie_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from services.cibles import CATEGORIES as CIBLE_CATEGORIES

        if v not in CIBLE_CATEGORIES:
            raise ValueError(f"categorie must be one of {set(CIBLE_CATEGORIES)}")
        return v


class CibleResponse(BaseModel):
    """Schema for a cible in API responses."""

    id: int
    nom: str
    categorie: str
    contactee: bool
    position: int
    url: str
    description: str
    email: str
    linkedin: str
    inscrit_plateforme: bool
    notes: str = ""


class SettingValue(BaseModel):
    """Schema for a single setting value."""

    key: str
    value: str
    updated_at: str


class LLMConfigUpdate(BaseModel):
    """Schema for updating LLM provider configuration."""

    provider: str
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    @field_validator("provider")
    @classmethod
    def provider_valid(cls, v: str) -> str:
        allowed = {"ollama", "claude"}
        if v not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v


class CVReferenceResponse(BaseModel):
    """Schema for CV reference status in API responses."""

    cv_reference_configured: bool
    cv_reference_date: str = ""
