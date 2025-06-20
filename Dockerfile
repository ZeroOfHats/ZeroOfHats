# Stage 1: Build Backend
FROM node:18-alpine AS backend

WORKDIR /usr/src/app

# Copy backend package files and install dependencies
# Only copy package.json and package-lock.json (if available) first
# to leverage Docker cache for dependencies
COPY app/backend/package*.json ./
RUN npm install

# Copy backend source code
COPY app/backend/ ./

# Stage 2: Prepare Final Image
FROM node:18-alpine

WORKDIR /usr/src/app

# Copy installed dependencies and backend code from 'backend' stage
# This includes node_modules from the previous stage
COPY --from=backend /usr/src/app ./

# Copy frontend static files into a subfolder in the workdir
# The server.js is configured to serve from '../frontend',
# so if WORKDIR is /usr/src/app, frontend should be at /usr/src/app/frontend
COPY app/frontend/ ./frontend/

# Expose port (ensure this matches the port in server.js, e.g., 3000)
EXPOSE 3000

# Command to run the application
# server.js is in /usr/src/app (WORKDIR) because of COPY --from=backend /usr/src/app ./
CMD ["node", "server.js"]
