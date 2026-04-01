# ADR-004: CV adaptation via LLM with WeasyPrint PDF and python-docx DOCX output

## Status

Accepted

## Context

kandidat users need to tailor their CV for each job application. The reference CV is stored as HTML (uploaded via settings). The adapted CV must be available as both PDF (for human readers) and DOCX (for ATS parsing). The adaptation itself requires understanding the job context and rewriting CV content accordingly.

## Decision

Split CV adaptation into three concerns:

1. **Orchestrator** (`services/cv_adapter.py`): Resolves the CV source (candidature-specific HTML file > global reference), builds the job context (poste, entreprise, contenu), assembles prompts, calls the LLM via `adapt_cv()`, and validates the output HTML.

2. **Converter** (`services/cv_converter.py`): Converts adapted HTML to two formats:
   - **PDF**: WeasyPrint with injected print-safe CSS (A4 page, zero margins, color preservation).
   - **DOCX**: BeautifulSoup semantic parsing -- extracts structured sections (header, profile, skills, experience, education, projects) and rebuilds them as a styled python-docx document. Falls back to generic tag-based extraction for non-semantic HTML.

3. **Prompts**: System and user prompts are configurable via settings (`cv_adapt_system_prompt`, `cv_adapt_user_prompt`), with sensible defaults in code.

The user flow is: detail page -> loading spinner -> API adapt call -> preview (iframe sandbox) -> confirm -> save PDF + DOCX as Fichier entries.

## Consequences

- WeasyPrint requires system-level dependencies (cairo, pango) but produces faithful PDF output from HTML+CSS.
- The DOCX builder is tightly coupled to the expected CV HTML structure (CSS classes like `experience-item`, `skills-grid`). Non-standard HTML falls back to a generic parser.
- Both formats are generated and saved atomically on confirm, with automatic filename collision handling.
- The preview step lets the user reject poor LLM output before persisting files.
