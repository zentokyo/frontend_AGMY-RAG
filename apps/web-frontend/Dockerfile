FROM docker.m.daocloud.io/library/node:20-alpine AS admin-build

WORKDIR /workspace/apps/admin-frontend

COPY apps/admin-frontend/package*.json ./
RUN npm ci

COPY apps/admin-frontend ./
ENV VITE_BASE=/admin/
ENV VITE_API_BASE=/api
RUN npm run build

FROM docker.m.daocloud.io/library/node:20-alpine AS chat-build

WORKDIR /workspace/apps/chat-frontend

COPY apps/chat-frontend/package*.json ./
RUN npm ci

COPY apps/chat-frontend ./
ENV VITE_BASE=/
ENV VITE_API_BASE=/api
RUN npm run build

FROM docker.m.daocloud.io/library/nginx:1.27-alpine

COPY apps/web-frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=chat-build /workspace/apps/chat-frontend/dist /usr/share/nginx/html
COPY --from=admin-build /workspace/apps/admin-frontend/dist /usr/share/nginx/html/admin

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
