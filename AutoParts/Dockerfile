# Stage 1: install dependencies (dev for tests)
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: run tests (uses deps)
FROM node:18-alpine AS test
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=test
# Si tus tests necesitan servicios (DB), usa docker-compose en CI
RUN npm test

# Stage 3: production image
FROM node:18-alpine AS runtime
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "src/server.js"]
