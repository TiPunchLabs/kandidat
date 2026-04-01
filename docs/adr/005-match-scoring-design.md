# ADR-005: Match scoring with structured JSON output and persisted score

## Status

Accepted

## Context

Users need a quick assessment of how well their CV matches a job offer before investing time in a full adaptation. The evaluation should be objective, structured, and persistent so it can be displayed on the dashboard and detail pages.

## Decision

Implement match scoring as a dedicated service (`services/match_evaluator.py`) with the following design:

1. **Input**: The global CV reference HTML and the candidature's job description (poste, entreprise, contenu).

2. **LLM call**: Uses `provider.complete()` (same Protocol as other features) with a system prompt instructing the LLM to return **only** a JSON object: `{"score": 0-100, "strengths": [...], "weaknesses": [...], "missing": [...]}`.

3. **Parsing**: The raw response is cleaned (strips markdown code fences), parsed as JSON, and validated for the required `score` field. The score is clamped to 0-100.

4. **Persistence**: `match_score` (Float) and `match_details` (JSON-encoded TEXT) are stored directly on the Candidature model. No separate table -- the score is a property of the candidature.

5. **Display**: A colored badge (red <40, orange 40-69, green >=70) on the detail page and dashboard table. Collapsible details section shows strengths, weaknesses, and missing skills.

6. **Prompts**: Configurable via settings (`match_system_prompt`, `match_user_prompt`), with defaults in code.

## Consequences

- Re-evaluation overwrites the previous score -- no history of match scores is kept.
- The score depends on LLM quality and prompt tuning; results may vary between providers.
- Storing details as JSON text (not JSONB) works on both SQLite and PostgreSQL but prevents database-level querying of individual fields.
- The structured JSON contract with the LLM is fragile -- malformed responses raise a ValueError with a clear message.
