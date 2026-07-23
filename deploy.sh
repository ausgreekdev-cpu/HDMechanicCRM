#!/bin/bash
# HDMechanicCRM - Production Deploy Script for Linux

set -e

echo "========================================"
echo " HDMechanicCRM Production Deploy"
echo "========================================"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "ERROR: Docker Compose is not installed"
    exit 1
fi

# Check for .env
if [ ! -f ".env" ]; then
    echo ""
    echo "No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env and set these values:"
    echo "  CRM_SECRET_KEY - Generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo "  CRM_ADMIN_PASSWORD - Your admin password"
    echo ""
    ${EDITOR:-nano} .env
    exit 1
fi

# Generate secret key if still default
if grep -q "change-me-to-a-random-64-char-string" .env; then
    echo ""
    echo "WARNING: CRM_SECRET_KEY is still the default value!"
    echo "Generating a new key..."
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-me-to-a-random-64-char-string/$NEW_KEY/" .env
    echo "New key generated and saved to .env"
fi

echo ""
echo "[1/4] Building Docker image..."
docker compose build 2>/dev/null || docker-compose build

echo ""
echo "[2/4] Stopping existing containers..."
docker compose down 2>/dev/null || docker-compose down

echo ""
echo "[3/4] Starting services..."
docker compose up -d 2>/dev/null || docker-compose up -d

echo ""
echo "[4/4] Waiting for health check..."
sleep 10

docker compose ps 2>/dev/null || docker-compose ps

echo ""
echo "========================================"
echo " Deploy Complete!"
echo "========================================"
echo ""
echo " App:    http://localhost"
echo " Health: http://localhost/health"
echo " Logs:   docker compose logs -f web"
echo " Stop:   docker compose down"
echo "========================================"
