# Build stage
FROM node:14-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Skip lint check during build
ENV DISABLE_ESLINT_PLUGIN=true
RUN npm run build

# Production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 