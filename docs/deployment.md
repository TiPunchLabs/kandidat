# Deployment

## Mental model

```text
Developer          GitLab CI                Bastion (192.168.1.60)        Dockhost (192.168.1.90)
─────────          ─────────                ──────────────────────        ───────────────────────
git push   ──►   lint/test/security
  main             build image ──► registry.gitlab.com/tipunchlabs/kandidat:<sha>
                   deploy (manual) ──► SSH ──► ansible-playbook ──► SSH ──► docker pull + run
                                                  --tags kandidat
                                                  -e image_tag=<sha>
```

The deploy is a **manual gate** on the `main` branch. Nothing reaches production without
an explicit click in GitLab CI.

------

## Infrastructure overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Dockhost VM (192.168.1.90)                                          │
│  3 cores, 10 GB RAM, 100 GB SSD                                     │
│                                                                      │
│  Docker network: db-net (external, shared)                           │
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐    │
│  │  postgresql           │    │  kandidat                        │    │
│  │  postgres:17.4        │    │  registry.gitlab.com/            │    │
│  │  port: 5432           │◄───│    tipunchlabs/kandidat:<sha>   │    │
│  │  data: /app/data/     │    │  port: 8000                     │    │
│  │    postgresql/        │    │  data: /app/data/kandidat/      │    │
│  │  config: /opt/        │    │  config: /opt/kandidat/         │    │
│  │    postgresql/config/ │    │    docker-compose.yml            │    │
│  └──────────────────────┘    └──────────────────────────────────┘    │
│                                                                      │
│  UFW: 22 (SSH), 5432 (PostgreSQL), 8000 (kandidat)                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Bastion VM (192.168.1.60)                                           │
│  GitLab Runner (shell executor, tags: bastion, homelab, shell)       │
│  ~/homelab/ — cloned repo with Ansible playbooks + roles             │
│  Secrets via pass + GPG (Ansible vault password, registry tokens)    │
└──────────────────────────────────────────────────────────────────────┘
```

------

## CI/CD pipeline

Defined in `.gitlab-ci.yml`. Uses `workflow:rules` to ensure one pipeline per event.

### Stages

| Stage | Runner | Trigger | What it does |
| --- | --- | --- | --- |
| **lint** | GitLab instance | MR + main push | `ruff check .` + `ruff format --check .` |
| **test** | GitLab instance | MR + main push | `pytest` with coverage (SQLite in-memory) |
| **security** | GitLab instance | MR + main push | `bandit` code scanning |
| **build** | GitLab instance (docker:dind) | MR + main push | Build Docker image, push to registry with commit SHA tag |
| **release** | GitLab instance (docker:dind) | Git tag only | Re-tag image with version tag |
| **deploy** | Bastion (self-hosted) | Main only, **manual gate** | Ansible playbook on bastion → dockhost |

### Image tagging

| Event | Tag pushed to registry |
| --- | --- |
| Push to main | `registry.gitlab.com/tipunchlabs/kandidat:<short-sha>` |
| Push to MR branch | `registry.gitlab.com/tipunchlabs/kandidat:<branch-slug>` |
| Git tag (e.g. `v1.2.0`) | `registry.gitlab.com/tipunchlabs/kandidat:v1.2.0` |

### Deploy job

```yaml
deploy:
  stage: deploy
  tags: [bastion]            # runs on bastion-60 self-hosted runner
  when: manual               # requires manual click in GitLab UI
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - cd ~/homelab/dockhost
    - ~/.local/bin/uv run ansible-playbook ansible/deploy.yml
        --tags kandidat
        -e "kandidat_image_tag=$CI_COMMIT_SHORT_SHA"
```

The `kandidat_image_tag` variable overrides the Ansible default (`main`) with the
specific commit SHA that was built in the build stage.

------

## Docker image

Multi-stage build defined in `Dockerfile`:

```text
┌─────────────────────────────┐
│  Builder (python:3.12-slim) │
│  + uv (from ghcr.io)       │
│  uv sync --frozen --no-dev  │
│  → /app/.venv               │
└──────────────┬──────────────┘
               │ COPY .venv + source
               ▼
┌─────────────────────────────┐
│  Runtime (python:3.12-slim) │
│  + libpango, libcairo,     │
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
(PDF generation).

------

## Ansible deployment

### What happens when deploy runs

The Ansible playbook `dockhost/ansible/deploy.yml` with `--tags kandidat` executes
the `kandidat` role:

```text
1. PostgreSQL setup (idempotent)
   ├── Check if user 'kandidat' exists in postgresql container
   ├── CREATE USER kandidat (if missing)
   ├── Check if database 'kandidat' exists
   └── CREATE DATABASE kandidat (if missing)

2. Application directories
   ├── /opt/kandidat/ (docker-compose location)
   └── /app/data/kandidat/ (persistent data, UID 1000)

3. Registry authentication
   └── docker login registry.gitlab.com (deploy token from vault)

4. Container deployment
   ├── Render docker-compose.yml from template (with image tag + vault secrets)
   ├── docker compose up -d (pull: always, recreate: auto)
   └── Wait for healthcheck: curl http://localhost:8000/ (10 retries, 3s delay)
```

### Ansible role: kandidat

```text
dockhost/ansible/roles/kandidat/
├── defaults/main.yml       # Default variables (registry, ports, paths)
├── tasks/main.yml          # Main task sequence
├── handlers/main.yml       # Restart handler
└── templates/
    └── docker-compose.yml.j2   # Docker Compose template with vault refs
```

Key defaults:

| Variable | Default | Overridden by |
| --- | --- | --- |
| `kandidat_registry` | `registry.gitlab.com/tipunchlabs/kandidat` | — |
| `kandidat_image_tag` | `main` | CI deploy job (`-e kandidat_image_tag=<sha>`) |
| `kandidat_port` | `8000` | — |
| `kandidat_data_dir` | `/app/data/kandidat` | — |
| `kandidat_uid` | `1000` | — |

### Docker Compose on dockhost

Rendered from Jinja2 template to `/opt/kandidat/docker-compose.yml`:

```yaml
services:
  kandidat:
    image: registry.gitlab.com/tipunchlabs/kandidat:<sha>
    container_name: kandidat
    restart: always
    ports:
      - "8000:8000"
    environment:
      SECRET_KEY: "<from vault>"
      KANDIDAT_ENV: "prod"
      FT_DATA_DIR: "/app/data"
      DATABASE_URL: "<from vault>"    # postgresql+psycopg://kandidat:***@postgresql:5432/kandidat
    volumes:
      - /app/data/kandidat:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - db-net

networks:
  db-net:
    external: true
```

Note: the `DATABASE_URL` uses `postgresql` as hostname (Docker container DNS on `db-net`),
not `192.168.1.90` or `localhost`.

------

## PostgreSQL

Deployed by the `postgresql` Ansible role, also on dockhost.

| Setting | Value |
| --- | --- |
| Image | `postgres:17.4` (pinned by digest) |
| Port | 5432 (exposed on dockhost) |
| Data | `/app/data/postgresql/` (persistent) |
| Config | `/opt/postgresql/config/postgresql.conf` + `pg_hba.conf` |
| Network | `db-net` (shared with kandidat) |
| Max connections | 100 |
| Shared buffers | 256MB |

### Access control (pg_hba.conf)

| Source | Auth method |
| --- | --- |
| Local (unix socket) | trust |
| Loopback (127.0.0.1) | trust |
| Docker network (172.0.0.0/8) | md5 |
| Homelab subnet (192.168.1.0/24) | md5 |
| All others | reject |

### Database and user

Created by the `kandidat` Ansible role (not the `postgresql` role):

```sql
CREATE USER kandidat WITH PASSWORD '<vault_kandidat_db_password>';
CREATE DATABASE kandidat OWNER kandidat ENCODING 'UTF8';
```

------

## Secrets management

All secrets are stored in **Ansible Vault** (encrypted YAML files) and injected at deploy time.

| Secret | Vault variable | Used by |
| --- | --- | --- |
| Flask secret key | `vault_kandidat_secret_key` | kandidat container `SECRET_KEY` |
| Database URL | `vault_kandidat_database_url` | kandidat container `DATABASE_URL` |
| DB user password | `vault_kandidat_db_password` | PostgreSQL `CREATE USER` |
| Registry username | `vault_kandidat_registry_user` | `docker login` (deploy token) |
| Registry password | `vault_kandidat_registry_password` | `docker login` (deploy token) |
| PostgreSQL superuser pwd | `vault_postgresql_password` | PostgreSQL container `POSTGRES_PASSWORD` |

Vault files location: `dockhost/ansible/group_vars/dockhost/vault/config.yml`

The vault password is stored in `pass` on the bastion VM, loaded via `.envrc`:
```bash
export ANSIBLE_VAULT_PASSWORD=$(pass ansible/vault)
```

------

## Network and firewall

### Docker network

```text
db-net (external bridge network)
├── postgresql (hostname: postgresql, port 5432)
└── kandidat   (hostname: kandidat, port 8000)
```

The `db-net` network is created as a pre-task in the dockhost deploy playbook
(`docker network create db-net`). Both containers join it.

### UFW rules on dockhost

| Port | Protocol | Purpose |
| --- | --- | --- |
| 22 | TCP | SSH access |
| 5432 | TCP | PostgreSQL (homelab access) |
| 8000 | TCP | kandidat web application |

------

## How to deploy

### Standard deploy (via CI)

1. Push to `main` (or merge an MR)
2. Wait for lint/test/security/build to pass
3. Click the **manual deploy button** in GitLab CI
4. The bastion runner executes the Ansible playbook
5. Dockhost pulls the new image and restarts the container

### Manual deploy (from bastion)

SSH into the bastion and run directly:

```bash
cd ~/homelab/dockhost
~/.local/bin/uv run ansible-playbook ansible/deploy.yml \
    --tags kandidat \
    -e "kandidat_image_tag=<commit-sha>"
```

### Rollback

Deploy a previous commit SHA:

```bash
cd ~/homelab/dockhost
~/.local/bin/uv run ansible-playbook ansible/deploy.yml \
    --tags kandidat \
    -e "kandidat_image_tag=<previous-sha>"
```

All previously built images are available in the GitLab Container Registry.

------

## Homelab code sync

The bastion's copy of `~/homelab/` is kept in sync with GitLab via a CI job in the
homelab repo itself:

```yaml
# homelab/.gitlab-ci.yml
sync-bastion:
  tags: [bastion]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - cd ~/homelab && git fetch origin main && git reset --hard origin/main
```

This means any change to Ansible roles or playbooks pushed to the homelab repo is
automatically synced to the bastion before the next deploy.

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

### Check container status on dockhost

```bash
ssh dockhost-90
docker ps                           # running containers
docker logs kandidat --tail 50      # app logs
docker logs postgresql --tail 50    # db logs
```

### Check database connectivity

```bash
ssh dockhost-90
docker exec postgresql pg_isready -U kandidat -d kandidat
```

### Force pull and restart

```bash
ssh bastion-60
cd ~/homelab/dockhost
~/.local/bin/uv run ansible-playbook ansible/deploy.yml --tags kandidat
```

### View deployed image tag

```bash
ssh dockhost-90
docker inspect kandidat --format '{{ .Config.Image }}'
```

------

> **Document created on**: 2026-03-16
> **Author**: Claude (from infrastructure code analysis), Xavier Gueret (review)
> **Version**: 1.0
