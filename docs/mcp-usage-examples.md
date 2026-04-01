# 🛠️ MCP Server — Usage Examples

> **Objective**: Practical examples showing how to interact with kandidat via an LLM agent
> (Claude Desktop or Claude Code) through the MCP server.
>
> Each example shows the natural language prompt, the MCP tool(s) called under the hood,
> and the expected result.
>
> **Prerequisites**: kandidat API running + MCP server started (see [configuration.md](configuration.md))

------

## 📖 Table of Contents

1. [Quick Start](#-1-quick-start)
2. [Reading Data](#-2-reading-data)
3. [Creating Data](#-3-creating-data)
4. [Updating Data](#-4-updating-data)
5. [Status Workflow](#-5-status-workflow)
6. [Search and Statistics](#-6-search-and-statistics)
7. [AI Operations](#-7-ai-operations)
8. [Multi-Step Workflows](#-8-multi-step-workflows)
9. [Dangerous Operations](#-9-dangerous-operations)
10. [Tool Reference](#-10-tool-reference)

------

## 🚀 1. Quick Start

Once the MCP server is configured, you can talk to kandidat naturally. The LLM agent
translates your intent into the right API calls.

```text
You:    "What's the status of my job search?"
Agent:  → calls get_stats
        "You have 12 applications total:
         - 2 in draft, 1 sent, 1 followed up
         - 2 in interview, 1 accepted
         - 4 archived, 1 no response
         5 are high priority."
```

No special syntax needed. Just describe what you want.

------

## 📋 2. Reading Data

### List all applications

```text
You:    "Show me all my active candidatures"
Agent:  → calls list_candidatures (no filters — returns all)
```

### Filter by status

```text
You:    "Which applications are waiting for an interview?"
Agent:  → calls list_candidatures({ statut: "entretien" })
```

```text
You:    "List everything I've sent but not followed up on"
Agent:  → calls list_candidatures({ statut: "envoyee" })
```

### Filter by priority

```text
You:    "Show me my high priority applications"
Agent:  → calls list_candidatures({ priorite: "haute" })
```

### Filter by type

```text
You:    "Which ones were spontaneous applications?"
Agent:  → calls list_candidatures({ type: "spontanee" })
```

### Combine filters

```text
You:    "High priority applications that are still in draft"
Agent:  → calls list_candidatures({ statut: "brouillon", priorite: "haute" })
```

### Get application details

```text
You:    "Tell me everything about the Datadog application"
Agent:  → calls get_candidature({ slug: "datadog" })
        Returns: company, position, status, dates, priority, content,
        attached files, linked target company info.
```

### View status history

```text
You:    "Show me the timeline for the GBH application"
Agent:  → calls get_candidature_history({ slug: "gbh-devops" })
        "Timeline for GBH DevOps Lead:
         - 2025-11-20: brouillon (created)
         - 2025-11-20: brouillon → envoyee
         - 2025-12-15: envoyee → relancee (comment: 'Relance par email')
         - 2026-01-10: relancee → entretien (comment: 'RDV RH le 15/01')"
```

### List target companies

```text
You:    "Show me all my target companies"
Agent:  → calls list_cibles
        Returns companies grouped by category:
        grands-groupes, esn, entreprises, cabinets, organisations.
```

### Get company details with contacts

```text
You:    "What do I know about Orange Caraibe?"
Agent:  → calls get_cible_detail({ cible_id: 4 })
        Returns: name, category, website, description, LinkedIn,
        contacts list, and linked active applications.
```

### View settings

```text
You:    "Is the LLM configured?"
Agent:  → calls get_settings
        "LLM provider: claude (model: claude-sonnet-4-20250514).
         CV reference: configured (uploaded 2026-01-15).
         Tavily: configured."
```

------

## ✏️ 3. Creating Data

### Add a target company

```text
You:    "Add Scaleway to my targets, category entreprises,
         website https://www.scaleway.com"
Agent:  → calls create_cible({
           nom: "Scaleway",
           categorie: "entreprises",
           url: "https://www.scaleway.com"
         })
        "Created: Scaleway (id: 15) in entreprises."
```

### Add a contact to a company

```text
You:    "Add a contact for Scaleway: Jean Martin, CTO,
         jean.martin@scaleway.com"
Agent:  → first calls list_cibles to find Scaleway's ID (15)
        → then calls create_contact({
           cible_id: 15,
           nom: "Martin",
           prenom: "Jean",
           fonction: "CTO",
           email: "jean.martin@scaleway.com"
         })
```

### Create a job application

```text
You:    "Create an application for Scaleway, position SRE,
         high priority, location Paris"
Agent:  → first calls list_cibles to find Scaleway's ID (15)
        → then calls create_candidature({
           entreprise: "Scaleway",
           poste: "SRE",
           priorite: "haute",
           localisation: "Paris",
           cible_id: 15
         })
        "Created: candidature 'scaleway' (slug) in brouillon status."
```

> **Note**: The agent must find the `cible_id` first. It will call `list_cibles`
> automatically if you don't provide the ID.

### Create an application with content

```text
You:    "Create an application for OVHcloud, position DevOps Engineer,
         category ESN, spontaneous application. Here's the context:
         They're building a new Kubernetes platform and looking for
         experienced engineers. Contact found on LinkedIn."
Agent:  → calls create_cible({ nom: "OVHcloud", categorie: "esn" })
        → calls create_candidature({
           entreprise: "OVHcloud",
           poste: "DevOps Engineer",
           type: "spontanee",
           cible_id: <new_id>,
           contenu: "# OVHcloud — DevOps Engineer\n\nCandidature spontanee.\n\n
                     ## Contexte\nNouvelle plateforme Kubernetes.\n
                     Contact trouve sur LinkedIn."
         })
```

------

## 🔄 4. Updating Data

### Update application fields

```text
You:    "Change the Scaleway application priority to moyenne"
Agent:  → calls update_candidature({
           slug: "scaleway",
           priorite: "moyenne"
         })
```

```text
You:    "Set the follow-up date for Orange to 2026-04-01"
Agent:  → calls update_candidature({
           slug: "orange-sre",
           date_relance: "2026-04-01"
         })
```

### Update application content

```text
You:    "Add this note to the GBH application: second interview
         scheduled for March 25, with the CTO"
Agent:  → first calls get_candidature({ slug: "gbh-devops" }) to get current content
        → then calls update_candidature({
           slug: "gbh-devops",
           contenu: "<existing content>\n\n## Update 2026-03-16\n
                     2eme entretien prevu le 25/03 avec le CTO."
         })
```

### Update company information

```text
You:    "Update Scaleway's description: French cloud provider,
         alternative to AWS. Add their LinkedIn:
         https://linkedin.com/company/scaleway"
Agent:  → calls update_cible({
           cible_id: 15,
           description: "French cloud provider, alternative to AWS",
           linkedin: "https://linkedin.com/company/scaleway"
         })
```

### Update a contact

```text
You:    "Jean Martin at Scaleway changed his role to VP Engineering"
Agent:  → calls get_cible_detail({ cible_id: 15 }) to find contact_id
        → calls update_contact({
           cible_id: 15,
           contact_id: <id>,
           fonction: "VP Engineering"
         })
```

### Edit a timeline comment

```text
You:    "Add a comment to the last status change of Orange:
         'Waiting for feedback from hiring manager'"
Agent:  → calls get_candidature_history({ slug: "orange-sre" })
        → finds the last entry's historique_id
        → calls update_historique_comment({
           slug: "orange-sre",
           historique_id: <id>,
           commentaire: "Waiting for feedback from hiring manager"
         })
```

------

## 🔀 5. Status Workflow

The status state machine enforces valid transitions. The agent knows the rules
(loaded via the `kandidat://enums` resource) and will refuse invalid transitions.

### Valid status transitions

```text
brouillon  → envoyee, archivee
envoyee    → relancee, sans-reponse, archivee
relancee   → entretien, sans-reponse, archivee
entretien  → acceptee, refusee, archivee
acceptee   → archivee
refusee    → archivee
sans-reponse → archivee
archivee   → (terminal, no transitions out)
```

### Mark as sent

```text
You:    "I just sent my application to Scaleway"
Agent:  → calls update_candidature({
           slug: "scaleway",
           statut: "envoyee",
           commentaire: "CV sent via their careers page"
         })
```

### Record a follow-up

```text
You:    "I followed up with Scaleway by email today"
Agent:  → calls update_candidature({
           slug: "scaleway",
           statut: "relancee",
           date_relance: "2026-03-16",
           commentaire: "Relance par email"
         })
```

### Move to interview stage

```text
You:    "Scaleway called back, I have an interview on April 5th"
Agent:  → calls update_candidature({
           slug: "scaleway",
           statut: "entretien",
           commentaire: "Entretien prevu le 05/04/2026 avec le CTO"
         })
```

### Record acceptance or rejection

```text
You:    "Got the offer from Scaleway!"
Agent:  → calls update_candidature({
           slug: "scaleway",
           statut: "acceptee",
           commentaire: "Offre recue, debut prevu juin 2026"
         })
```

```text
You:    "Scaleway rejected me, they went with an internal candidate"
Agent:  → calls update_candidature({
           slug: "scaleway",
           statut: "refusee",
           commentaire: "Candidat interne prefere"
         })
```

### Invalid transition handling

```text
You:    "Move the Scaleway application directly to interview"
        (current status: brouillon)
Agent:  "I can't do that — the current status is 'brouillon' and
         the only valid transitions are 'envoyee' or 'archivee'.
         Should I mark it as sent first?"
```

### Archive

```text
You:    "Archive the Michael Page application"
Agent:  → calls update_candidature({
           slug: "michael-page-devops",
           statut: "archivee",
           commentaire: "Plus d'interet pour ce poste"
         })
        "Done. Note: this is permanent — archived applications
         cannot be un-archived."
```

------

## 🔍 6. Search and Statistics

### Full-text search

```text
You:    "Search for anything related to Kubernetes"
Agent:  → calls search_candidatures({ query: "Kubernetes" })
        Returns matching applications with relevant context.
```

```text
You:    "Find all applications mentioning 'remote'"
Agent:  → calls search_candidatures({ query: "remote" })
```

### Dashboard statistics

```text
You:    "Give me a summary of my job search"
Agent:  → calls get_stats
        "12 total applications:
         By status: 2 brouillon, 1 envoyee, 1 relancee,
                    2 entretien, 1 acceptee, 1 sans-reponse, 4 archivee
         By type: 10 offre, 2 spontanee
         By priority: 5 haute, 4 moyenne, 3 basse
         By category: 3 entreprise, 3 esn, 4 cabinet, 2 groupe"
```

### Analysis questions

```text
You:    "Which applications should I follow up on?
         Show me those sent more than 2 weeks ago without follow-up."
Agent:  → calls list_candidatures({ statut: "envoyee" })
        → filters by date_candidature < 2 weeks ago
        "1 application needs follow-up:
         - Orange Caraibe (SRE) — sent 2026-01-15, no follow-up yet"
```

```text
You:    "What's my success rate?"
Agent:  → calls get_stats
        "Out of 12 applications:
         - 1 accepted (8.3%)
         - 2 in interview (16.7%)
         - 4 archived/rejected (33.3%)
         - 5 still in progress (41.7%)"
```

------

## 🤖 7. AI Operations

### Enrich a target company

```text
You:    "Can you find more information about Scaleway?"
Agent:  → calls enrich_cible({ cible_id: 15 })
        "Here's what I found:
         Company info:
           - Website: https://www.scaleway.com (confirmed)
           - LinkedIn: https://linkedin.com/company/scaleway
           - Description: European cloud provider, part of iliad Group
         Contacts found:
           - Arnaud de Bermingham (CEO)
           - Damien Lucas (CTO)
         Should I apply these updates?"
```

### Apply enrichment selectively

```text
You:    "Apply the description and LinkedIn, and add Damien Lucas
         as a contact, but skip the CEO"
Agent:  → calls apply_enrichment({
           cible_id: 15,
           accepted: {
             description: "European cloud provider, part of iliad Group",
             linkedin: "https://linkedin.com/company/scaleway",
             contacts: [
               { nom: "Lucas", prenom: "Damien", fonction: "CTO" }
             ]
           }
         })
```

### Adapt CV for an application

```text
You:    "Adapt my CV for the Scaleway SRE application"
Agent:  → calls adapt_cv({ slug: "scaleway" })
        "Here's the adapted CV (HTML preview).
         Key adaptations:
         - Highlighted Kubernetes and cloud infrastructure experience
         - Emphasized monitoring and SRE practices
         - Added relevant certifications
         Should I save it as PDF and DOCX?"
```

### Save adapted CV

```text
You:    "Yes, save it"
Agent:  → calls save_adapted_cv({
           slug: "scaleway",
           adapted_html: "<html>..."
         })
        "Saved: cv_adapte_scaleway.pdf and cv_adapte_scaleway.docx
         attached to the Scaleway application."
```

------

## 🔗 8. Multi-Step Workflows

The agent can chain multiple tools to handle complex requests in one go.

### Complete onboarding of a new target

```text
You:    "I found a job posting at Clever Cloud for a Platform Engineer
         position in Nantes. They're a French PaaS company.
         The hiring manager is Quentin Adam, CEO, quentin@clever-cloud.com.
         Create everything and mark it as sent, I applied today."
Agent:  → 1. create_cible({
              nom: "Clever Cloud",
              categorie: "entreprises",
              url: "https://clever-cloud.com",
              description: "French PaaS company"
            })
         → 2. create_contact({
              cible_id: <new_id>,
              nom: "Adam",
              prenom: "Quentin",
              fonction: "CEO",
              email: "quentin@clever-cloud.com"
            })
         → 3. create_candidature({
              entreprise: "Clever Cloud",
              poste: "Platform Engineer",
              localisation: "Nantes",
              priorite: "haute",
              cible_id: <new_id>,
              type: "offre"
            })
         → 4. update_candidature({
              slug: "clever-cloud",
              statut: "envoyee",
              commentaire: "CV envoye via le site carrieres"
            })
        "Done: Clever Cloud created as target company, contact Quentin Adam
         added, application created and marked as sent."
```

### Weekly review

```text
You:    "Do a weekly review: what needs attention?"
Agent:  → calls get_stats (overview)
        → calls list_candidatures({ statut: "envoyee" }) (pending follow-ups)
        → calls list_candidatures({ statut: "entretien" }) (upcoming interviews)
        → calls list_candidatures({ statut: "brouillon" }) (drafts to send)
        "Weekly review:
         📨 Follow-up needed (sent >7 days ago):
           - Orange Caraibe (SRE) — sent Jan 15, no follow-up
         📅 Active interviews:
           - GBH DevOps Lead — 2nd interview pending
           - Digicel Infra Manager — waiting for CTO feedback
         📝 Drafts to finalize:
           - 2 applications in draft status
         ✅ Won: Hays Consultant (accepted)"
```

### Bulk status update

```text
You:    "I haven't heard back from Sopra Steria in 2 months,
         mark it as no response and archive it"
Agent:  → calls update_candidature({
           slug: "sopra-data",
           statut: "sans-reponse",
           commentaire: "Aucune reponse apres 2 mois et relance"
         })
        → calls update_candidature({
           slug: "sopra-data",
           statut: "archivee",
           commentaire: "Archive apres sans-reponse prolonge"
         })
```

### Compare two applications

```text
You:    "Compare my GBH and Digicel applications"
Agent:  → calls get_candidature({ slug: "gbh-devops" })
        → calls get_candidature({ slug: "digicel-infra" })
        "Comparison:
         | Field        | GBH DevOps Lead    | Digicel Infra Manager |
         |-------------|--------------------|-----------------------|
         | Status      | entretien          | entretien             |
         | Priority    | haute              | haute                 |
         | Location    | Fort-de-France     | Guadeloupe            |
         | Type        | offre              | offre                 |
         | Applied     | 2025-11-20         | 2025-12-01            |
         | Files       | 3 (offre, LM, notes)| 1 (offre)           |"
```

------

## ⚠️ 9. Dangerous Operations

These operations are marked with `destructiveHint: true`. The agent will always ask
for explicit confirmation before proceeding.

### Delete an application

```text
You:    "Delete the test application"
Agent:  "⚠️ This will permanently delete the 'test' application
         and all its attached files. This cannot be undone.
         Are you sure?"
You:    "Yes"
Agent:  → calls delete_candidature({ slug: "test" })
        "Deleted: application 'test' and all attached files."
```

### Delete a target company

```text
You:    "Remove Atos from my targets"
Agent:  "⚠️ Deleting the target company 'Atos' will also permanently
         delete ALL linked applications and their files:
         - atos-sre (archived, 1 file)
         This cascade cannot be undone. Are you sure?"
You:    "Yes"
Agent:  → calls delete_cible({ cible_id: 11 })
```

### Delete a contact

```text
You:    "Remove Jean Martin from Scaleway's contacts"
Agent:  "This will delete the contact Jean Martin from Scaleway.
         Confirm?"
You:    "Yes"
Agent:  → calls get_cible_detail({ cible_id: 15 }) to find contact_id
        → calls delete_contact({ cible_id: 15, contact_id: <id> })
```

------

## 📚 10. Tool Reference

Quick reference of all 23 MCP tools, grouped by action type.

### READ tools (safe, no confirmation needed)

| Tool | Description |
| --- | --- |
| `list_candidatures` | List applications with optional filters (statut, type, priorite, categorie) |
| `get_candidature` | Get full details of one application by slug |
| `get_candidature_history` | Get status change timeline for an application |
| `list_cibles` | List all target companies grouped by category |
| `get_cible_detail` | Get company details with contacts and linked applications |
| `search_candidatures` | Full-text search across all applications |
| `get_stats` | Dashboard statistics (counts by status, type, priority, category) |
| `get_settings` | Current app settings (LLM provider, CV reference, Tavily status) |

### WRITE tools (modify data, no confirmation needed)

| Tool | Description |
| --- | --- |
| `create_candidature` | Create a new application (requires existing cible_id) |
| `update_candidature` | Update fields, change status (with commentaire), modify content |
| `update_historique_comment` | Edit a comment on a status change event |
| `create_cible` | Add a new target company |
| `update_cible` | Update company information |
| `create_contact` | Add a contact to a company |
| `update_contact` | Update contact information |

### DELETE tools (confirmation required)

| Tool | Description |
| --- | --- |
| `delete_candidature` | Delete application + files on disk (irreversible) |
| `delete_cible` | Delete company + ALL linked applications (cascade, irreversible) |
| `delete_contact` | Delete a contact from a company |

### AI tools (may be slow, consume API credits)

| Tool | Description |
| --- | --- |
| `enrich_cible` | Web search + LLM extraction for company info (read-only, returns suggestions) |
| `apply_enrichment` | Apply selected enrichment suggestions to company + contacts |
| `adapt_cv` | Generate LLM-adapted CV HTML for an application (read-only) |
| `save_adapted_cv` | Save adapted CV as PDF + DOCX files |
| `evaluate_match` | Evaluate CV-offer match percentage via LLM (score + strengths/weaknesses/missing) |

------

> **Document created on**: 2026-03-16
> **Author**: Claude (examples), Xavier Gueret (review)
> **Version**: 1.0
