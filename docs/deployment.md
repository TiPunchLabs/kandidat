# Deployment

## Mental model

```text
kandidat repo (GitLab CI)            homelab-gitops repo                 dockhost (192.168.10.90)
─────────────────────────            ───────────────────                 ────────────────────────
git push main
  lint / test / security
  build     ──► registry.gitlab.com/tipunchlabs/kandidat:<sha>
  build-mcp ──► registry.gitlab.com/tipunchlabs/kandidat/mcp:<sha>
  bump  ──► MR "bump image to <sha>" ──► auto-merged into main
            (edits kandidat/compose.yaml)       │
                                                ▼
                                   CI trigger-komodo-kandidat
                                   (bastion runner, LAN)  ──► POST Komodo listener
                                                                     │
                                                                     ▼
                                                        Komodo pulls homelab-gitops
                                                        docker compose up (Stack kandidat)
```

- **Source of truth**: `kandidat/compose.yaml` in the private repo
  [`tipunchlabs/homelab-gitops`](https://gitlab.com/tipunchlabs/homelab-gitops).
  What runs in prod is whatever image SHA is pinned there.
- **No manual gate**: every push to `main` of kandidat ends in production if all
  stages pass. MR pipelines build images but never bump.
- **Rollback** = `git revert` of the bump commit in homelab-gitops.

> 💡 **Note**: the previous deployment (bastion runner → `ansible-playbook --tags kandidat`
> → `docker compose up`) is gone. Ansible now only does host prep, see
> [Ansible role (host prep only)](#ansible-role-host-prep-only).

------

## Infrastructure overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│  dockhost VM (192.168.10.90)                                         │
│                                                                      │
│  Komodo Core + Periphery (listener on :9120)                         │
│                                                                      │
│  Stack "kandidat" — Docker network: kandidat-net                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │ kandidat         │  │ kandidat-mcp     │  │ db (kandidat-db)  │   │
│  │ kandidat:<sha>   │◄─│ kandidat/mcp:    │  │ postgres:17       │   │
│  │ port 8000        │  │   <sha>          │  │ volume kandidat-db│   │
│  │ /app/data/       │──┼──────────────────┼─►│ port 5432 (intern)│   │
│  │   kandidat (bind)│  │ port 3001        │  │                   │   │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
          ▲ :8000                   ▲ :3001
┌─────────┴─────────────────────────┴──────────────────────────────────┐
│  Caddy (192.168.10.70) — TLS internal                                │
│  https://kandidat.internal      → 192.168.10.90:8000                 │
│  https://kandidat-mcp.internal  → 192.168.10.90:3001                 │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  bastion-60 — GitLab Runner (shell, tag: bastion)                    │
│  Only used by homelab-gitops CI to reach the Komodo listener on the  │
│  LAN. Komodo is never exposed to the Internet.                       │
└──────────────────────────────────────────────────────────────────────┘
```

------

## CI/CD pipeline (kandidat repo)

Defined in `.gitlab-ci.yml`. Uses `workflow:rules` to ensure one pipeline per event.

### Stages

| Stage | Job | Runner | Trigger | What it does |
| --- | --- | --- | --- | --- |
| **lint** | `lint` | GitLab instance | MR + main | `ruff check .` + `ruff format --check .` |
| **test** | `test` | GitLab instance | MR + main | `pytest` with coverage (SQLite in-memory) |
| **security** | `security` | GitLab instance | MR + main | `bandit` code scanning |
| **build** | `build` | GitLab instance (docker:dind) | MR + main | App image, tags `<short-sha>` + `<branch-slug>` |
| **build** | `build-mcp` | GitLab instance (docker:dind) | MR + main | MCP image from `mcp/`, same tags under `/mcp` |
| **release** | `release`, `release-mcp` | GitLab instance (docker:dind) | Git tag only | Build + push `:<tag>` for both images |
| **bump** | `bump` | GitLab instance (alpine) | main only, `on_success` | Pin both images to `<short-sha>` in homelab-gitops |

### Image tagging

| Event | App image | MCP image |
| --- | --- | --- |
| Push to main / MR | `kandidat:<short-sha>` + `kandidat:<branch-slug>` | `kandidat/mcp:<short-sha>` + `kandidat/mcp:<branch-slug>` |
| Git tag (e.g. `v1.2.0`) | `kandidat:v1.2.0` | `kandidat/mcp:v1.2.0` |

All images live under `registry.gitlab.com/tipunchlabs/`.

### Bump job

The `bump` job is the only link between kandidat and production:

```text
1. git clone homelab-gitops (with HOMELAB_GITOPS_TOKEN)
2. checkout -b bump/kandidat-<sha>
3. guard: kandidat/compose.yaml must exist (never create a stub)
4. yq: services.kandidat.image      = kandidat:<sha>
       services["kandidat-mcp"].image = kandidat/mcp:<sha>   (only if the service exists)
5. no diff → exit 0 ("nothing to bump")
6. commit "chore(kandidat): bump image to <sha>", push
7. open MR via GitLab API (remove_source_branch=true)
8. merge MR via API (3 attempts, 5 s apart)
```

Both images are pinned to the **same SHA** on purpose: the MCP server mirrors the API's
tool surface, so letting them drift apart would expose tools that no longer match the
endpoints behind them.

Required CI/CD variables, defined in **kandidat → Settings → CI/CD → Variables**
(project level, not group level, not managed by `gitlab-terraform/`):

| Variable | Content | Flags |
| --- | --- | --- |
| `HOMELAB_GITOPS_TOKEN` | Value of the personal access token `kandidat-bump` (scopes `api` + `write_repository`) | masked, protected, scope `*` |
| `HOMELAB_GITOPS_PROJECT_ID` | Numeric ID of homelab-gitops, used for the MR API calls | masked, protected, scope `*` |

```text
User Settings → Access tokens          kandidat → Settings → CI/CD → Variables
┌──────────────────────────┐   copy    ┌──────────────────────────────────────┐
│ PAT "kandidat-bump"      │ ────────► │ HOMELAB_GITOPS_TOKEN = glpat-…       │
│ expires 2027-08-22       │   value   │ masked ✓  protected ✓  scope *       │
└──────────────────────────┘           └──────────────────────────────────────┘
                                                        │
                                                        ▼
                                         `bump` job in .gitlab-ci.yml
```

- **Protected** means the variable is only injected in pipelines on protected branches
  (`main`), which is also why MR pipelines never bump.
- **Rotation**: generate a new token in *User Settings → Access tokens*, then paste its
  value into the kandidat variable. Nothing else changes.
- The token is a **personal** access token: it acts with the owner's full GitLab rights,
  not only on homelab-gitops. A project access token on homelab-gitops would narrow the
  blast radius, but likely requires a paid GitLab.com tier.
- The variable exists only in the GitLab UI: it cannot be rebuilt from code if the project
  is recreated.

> ⚠️ **Warning**: if the token expires, `bump` fails at `git clone` with
> `HTTP Basic: Access denied`. Everything before it stays green and prod silently stays on
> the previous SHA. There is no alerting on this job — check it when a change does not
> seem to reach prod.

------

## GitOps side (homelab-gitops repo)

### Stack layout

```text
homelab-gitops/
├── .gitlab-ci.yml          # trigger-komodo-<stack> jobs
└── kandidat/
    ├── compose.yaml        # the Stack Komodo deploys (image SHAs pinned here)
    ├── .env.example        # names of the secrets expected by the Stack
    └── README.md
```

### Deploy trigger

A push to `main` touching `kandidat/**` runs the `trigger-komodo-kandidat` job on the
bastion runner. It POSTs a minimal GitLab push payload (`{"ref":"refs/heads/main"}`) to:

```text
http://192.168.10.90:9120/listener/gitlab/stack/<STACK_ID>/deploy
Header X-Gitlab-Token: $KOMODO_WEBHOOK_SECRET
```

Komodo validates the secret, pulls the repo and runs `docker compose up` for the Stack.
Any change to `main` (bump MR, manual edit, `git revert`) triggers a reconcile.

### Services in the Stack

| Service | Image | Port | Notes |
| --- | --- | --- | --- |
| `kandidat` | `registry.gitlab.com/tipunchlabs/kandidat:<sha>` | 8000 | Healthcheck `curl http://localhost:8000/`, waits for `db` healthy |
| `kandidat-mcp` | `registry.gitlab.com/tipunchlabs/kandidat/mcp:<sha>` | 3001 | `KANDIDAT_API_URL=http://kandidat:8000` (compose network), waits for `kandidat` healthy |
| `db` | `postgres:17` | internal | Dedicated to kandidat, volume `kandidat-db`, healthcheck `pg_isready` |

Environment of the app container:

```yaml
SECRET_KEY: "${SECRET_KEY}"
KANDIDAT_ENV: "prod"
FT_DATA_DIR: "/app/data"
DATABASE_URL: "postgresql+psycopg://kandidat:${DB_PASSWORD}@db:5432/kandidat"
```

`DATABASE_URL` uses `db` as hostname (compose service DNS on `kandidat-net`).

### Data

| Data | Location |
| --- | --- |
| PostgreSQL | Named volume `kandidat-db` (dedicated container, not the shared `postgresql` one) |
| Files (candidatures markdown, CVs) | Host bind mount `/app/data/kandidat` → `/app/data` |

------

## Secrets management

| Secret | Stored in | Used by |
| --- | --- | --- |
| `SECRET_KEY` | Komodo Core → Settings → Secrets | App container `SECRET_KEY` |
| `DB_PASSWORD` | Komodo Core → Settings → Secrets | `db` container + app `DATABASE_URL` |
| Registry pull credentials | Komodo (group registry account) | Image pull by Komodo |
| `KOMODO_WEBHOOK_SECRET` | homelab-gitops CI/CD variable (masked) | `trigger-komodo-kandidat` job |
| `HOMELAB_GITOPS_TOKEN` | kandidat CI/CD variable (masked + protected) | `bump` job |

Nothing secret is committed to homelab-gitops; `kandidat/.env.example` only lists the names.

------

## Ansible role (host prep only)

`homelab/dockhost/ansible/roles/kandidat/` no longer deploys anything. It does not log in
to the registry and does not run `docker compose`. What it still does:

- create the `/app/data/kandidat` bind-mount directory, owned by UID/GID 1000 (the
  non-root container user);
- create the `kandidat` user and database in the **shared** `postgresql` container.

> ⚠️ **Warning**: the Stack uses its own `db` container, not the shared `postgresql`
> one. The PostgreSQL part of the role therefore looks like a leftover of the Ansible
> era; the bind-mount directory is the part that still matters.

------

## Docker image

Multi-stage build defined in `Dockerfile`:

```text
┌─────────────────────────────┐
│  Builder (python:3.12-slim) │
│  + uv (from ghcr.io)        │
│  uv sync --frozen --no-dev  │
│  → /app/.venv               │
└──────────────┬──────────────┘
               │ COPY .venv + source
               ▼
┌─────────────────────────────┐
│  Runtime (python:3.12-slim) │
│  + libpango, libcairo,      │
│    libharfbuzz, fonts       │
│  User: kandidat (1000:1000) │
│  CMD: gunicorn              │
│    --bind 0.0.0.0:8000      │
│    --workers 2              │
│    app:create_app()         │
│  Port: 8000                 │
└─────────────────────────────┘
```

System dependencies (libpango, libcairo, libharfbuzz) are required for WeasyPrint
(PDF generation). The MCP server image is built separately from `mcp/Dockerfile`, see
[mcp/README.md](../mcp/README.md).

------

## How to deploy

### Standard deploy

1. Merge an MR into `main` (or push to `main`).
2. lint / test / security / build / build-mcp pass.
3. `bump` opens and merges `chore(kandidat): bump image to <sha>` in homelab-gitops.
4. homelab-gitops CI calls the Komodo listener; Komodo redeploys the Stack.

### Pin a specific image by hand

In homelab-gitops, on a branch, edit `kandidat/compose.yaml` (both `image:` lines,
same SHA), then open an MR. Merging it to `main` triggers the deploy.

### Rollback

```bash
cd homelab-gitops
git switch -c revert/kandidat-<sha>
git revert <bump-commit>          # restores the previous pinned SHA
git push -u origin revert/kandidat-<sha>
# open the MR, merge it → Komodo redeploys the previous image
```

All previously built images stay available in the GitLab Container Registry.

> ⚠️ **Warning**: the next push to kandidat `main` will bump again and overwrite the
> revert. Fix forward in kandidat, or hold merges until the fix lands.

------

## GitHub mirror

The GitLab repository is push-mirrored to GitHub for public visibility. The GitHub
repository is **read-only** — all development (issues, MRs, CI/CD) happens on GitLab.

### Mirror setup

GitLab push mirror is configured in **Settings > Repository > Mirroring repositories**
on the GitLab project. It pushes to `https://github.com/TiPunchLabs/kandidat.git`
on every push to `main`.

### Infrastructure as Code

The GitHub repository itself is managed by Terraform in `github-terraform/`:

```text
github-terraform/
├── providers.tf       # GitHub provider (integrations/github ~> 4.0)
├── main.tf            # github_repository "mirror" resource
├── variables.tf       # github_token, github_owner, repository_name, visibility
└── outputs.tf         # repository_url, full_name, clone_url
```

The resource disables all collaboration features (issues, wiki, projects) and enables
`archive_on_destroy` as a safety net.

### Usage

```bash
cd github-terraform
export TF_VAR_github_token="<GitHub PAT with repo scope>"
terraform plan
terraform apply
```

> **Note**: this is managed independently from `gitlab-terraform/` which handles the
> GitLab project configuration.

------

## Troubleshooting

### A change does not reach prod

1. Check the `bump` job of the kandidat `main` pipeline (expired `HOMELAB_GITOPS_TOKEN`
   is the usual suspect).
2. Check the pinned SHA in homelab-gitops `kandidat/compose.yaml`.
3. Check the `trigger-komodo-kandidat` job in homelab-gitops (HTTP code returned by
   the listener).
4. Check the Stack in the Komodo UI.

### View deployed image tag

```bash
ssh dockhost-90
docker inspect kandidat kandidat-mcp --format '{{ .Name }} {{ .Config.Image }}'
```

### Container and database status

```bash
ssh dockhost-90
docker ps --filter name=kandidat
docker logs kandidat --tail 50
docker logs kandidat-mcp --tail 50
docker exec kandidat-db pg_isready -U kandidat -d kandidat
```

------

> **Document created on**: 2026-03-16
> **Author**: Claude (from infrastructure code analysis), Xavier Gueret (review)
> **Version**: 2.0 — 2026-09-29: rewritten for the Komodo GitOps deployment (bump → homelab-gitops → Komodo)
