# --- build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Vite respects VITE_* envs at build; Railway will inject envs
RUN npm run build

# --- serve stage
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Create nginx configuration
RUN echo 'server { \
  listen 8080; \
  server_name _; \
  gzip on; \
  gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss image/svg+xml; \
  root /usr/share/nginx/html; \
  index index.html; \
  location / { \
    try_files $uri /index.html; \
  } \
  location ~* \.(?:js|css|svg|png|jpg|jpeg|gif|webp|ico)$ { \
    add_header Cache-Control "public, max-age=31536000, immutable"; \
    try_files $uri =404; \
  } \
}' > /etc/nginx/conf.d/default.conf

ENV PORT=8080
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
