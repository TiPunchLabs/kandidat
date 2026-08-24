# kandidat MCP server

Expose l'API REST de kandidat en outils MCP, pour qu'un agent LLM puisse gérer
les candidatures en langage naturel.

**Proxy sémantique** : toute la logique métier reste dans l'API Flask. Ce
serveur ne fait que traduire des outils typés en appels HTTP.

## Transport

Streamable HTTP, **stateless** — une instance de serveur MCP par requête.

| Route | Méthode | Rôle |
|---|---|---|
| `/health` | GET | sonde de vie |
| `/mcp` | POST | endpoint MCP |

## Variables d'environnement

| Variable | Défaut | Note |
|---|---|---|
| `KANDIDAT_API_URL` | `http://localhost:8000` | cible de l'API Flask |
| `MCP_PORT` | `3001` | port d'écoute |
| `MCP_HOST` | `127.0.0.1` | adresse d'écoute |

> ⚠️ **`MCP_HOST` vaut `127.0.0.1` par défaut, volontairement** : en
> développement le serveur ne doit pas être joignable depuis le réseau.
> En conteneur il faut `0.0.0.0`, sinon la publication de port de Docker ne
> peut pas atteindre la loopback interne — le conteneur démarre, journalise
> `listening`, et refuse toute connexion. L'image pose `MCP_HOST=0.0.0.0`
> elle-même, puisque c'est elle qu'on déploie derrière un reverse proxy.

## Développement

```bash
cd mcp
pnpm install
pnpm dev
```

## Image

```bash
docker build -t kandidat-mcp mcp/
docker run -p 3001:3001 -e KANDIDAT_API_URL=http://<api>:8000 kandidat-mcp
```

Construite par la CI en `${CI_REGISTRY_IMAGE}/mcp:<sha>`, épinglée dans le dépôt
GitOps par le job `bump` — au même SHA que l'image applicative, pour que les
deux ne dérivent jamais l'une de l'autre.

## Outils exposés

23 au total : 16 en lecture, 7 en écriture (`create_*`, `update_*`, `delete_*`,
`save_adapted_cv`, `apply_enrichment`).

> 🔐 L'API kandidat n'a **aucune authentification**, et ce serveur n'en ajoute
> pas — c'est un proxy, pas une passerelle d'accès. Le garde-fou côté agent est
> `hermes tools disable kandidat:<outil>`, qui borne ce que l'agent peut faire,
> pas ce que le réseau peut faire.
