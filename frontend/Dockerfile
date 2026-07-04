FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
# Regenerate version.json with build timestamp for update detection
RUN echo "{\"build\":\"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"}" > src/assets/version.json
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
