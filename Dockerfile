FROM node:20-alpine AS admin-builder
WORKDIR /app/admin
COPY apps/admin-frontend/package*.json ./
RUN npm ci
COPY apps/admin-frontend/ ./
RUN npm run build

FROM node:20-alpine
WORKDIR /app/api
COPY apps/api/package*.json ./
RUN npm ci --omit=dev
COPY apps/api/ ./
COPY --from=admin-builder /app/admin/dist ./public
EXPOSE 3001
CMD ["node", "src/app.js"]
