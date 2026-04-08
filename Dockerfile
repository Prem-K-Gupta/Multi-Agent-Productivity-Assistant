# ---- Build React frontend ----
FROM node:18-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Build Python backend ----
FROM python:3.12-slim AS final

WORKDIR /app/backend

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy built React frontend into backend/static
COPY --from=frontend-builder /app/dist ./static

# Cloud Run sets PORT env var — default to 8080
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
