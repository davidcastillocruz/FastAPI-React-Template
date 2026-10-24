# Development image of the frontend: the code is mounted from your computer (see docker-compose.yml)
FROM node:24-slim
WORKDIR /app

# Dependencies first: Docker reuses this layer while package.json and package-lock.json don't change
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# --host: listens outside the container too, so the browser of your computer can open it
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
