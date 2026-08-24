# =============================================================================
# kandidat MCP server — proxy semantique sur l'API REST de kandidat.
#
# Ce serveur est un CLIENT de l'API Flask, pas un second backend : toute la
# logique metier reste dans l'app. Cette image ne porte que la couche MCP.
# =============================================================================

FROM node:22-alpine AS build
WORKDIR /app

# Version epinglee plutot que le pnpm par defaut de l'image : le lockfile est
# en lockfileVersion 9.0 et `--frozen-lockfile` ne doit pas dependre de ce que
# corepack choisit ce mois-ci.
RUN corepack enable && corepack prepare pnpm@10.23.0 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src ./src
RUN pnpm build

# -----------------------------------------------------------------------------
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
# En conteneur, ecouter sur la loopback rendrait le port publie inutilisable.
# Le defaut du code reste 127.0.0.1 pour le developpement local ; c'est l'image
# qui assume l'exposition, puisque c'est elle qu'on deploie derriere un proxy.
ENV MCP_HOST=0.0.0.0

RUN corepack enable && corepack prepare pnpm@10.23.0 --activate

# --prod : typescript, tsx et @types ne servent qu'a la compilation.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod && pnpm store prune

COPY --from=build /app/dist ./dist

# L'image node fournit deja un utilisateur `node` non privilegie.
USER node

EXPOSE 3001

# fetch() est global depuis Node 18 : inutile d'installer curl dans l'image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.MCP_PORT||3001)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/index.js"]
