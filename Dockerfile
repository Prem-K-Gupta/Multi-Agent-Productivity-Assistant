# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src/ src/
COPY public/ public/
COPY index.html vite.config.js eslint.config.js ./
RUN npm run build

# Stage 2: Python backend + static frontend
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend into backend static directory
COPY --from=frontend-build /app/dist ./static

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Start server
CMD ["python", "main.py"]
