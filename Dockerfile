# The MCP server for one customer. Mount the customer's pack and pass their token:
#   docker run -i -v $PWD/kits/C08:/pack -e PACK=/pack/pack.json -e SMARTSHEET_TOKEN=... mcp-resource-packs
FROM node:22-slim AS build
WORKDIR /app
COPY server/package.json server/package-lock.json ./
RUN npm ci
COPY server/tsconfig.json ./
COPY server/src ./src
RUN npx tsc -p tsconfig.json && npm prune --omit=dev

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY server/package.json ./
COPY data/example /example
USER node
ENTRYPOINT ["node", "dist/main.js"]
