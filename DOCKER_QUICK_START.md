# Docker Quick Start Guide for Local Development and Production

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Building Docker Images](#building-docker-images)
4. [Running with Docker Compose](#running-with-docker-compose)
5. [Production Deployment](#production-deployment)
6. [Useful Docker Commands](#useful-docker-commands)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Docker Desktop (latest version)
- Docker Compose (v2.0+)
- Git
- Python 3.12 (for local testing)

### Installation

**Windows:**
```bash
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

**macOS:**
```bash
# Using Homebrew
brew install docker docker-compose

# Or download Docker Desktop from:
# https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/automation-orchestrator.git
cd automation-orchestrator
```

### 2. Create Environment File

```bash
# Copy example environment
cp .env.example .env

# Edit for local development
nano .env
```

### 3. Create Data Directories

```bash
mkdir -p ./data
mkdir -p ./logs
mkdir -p ./certs
```

### 4. Start Development Stack

```bash
# Build and start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME                          STATUS
# automation-orchestrator-api   Up 2 seconds
# automation-orchestrator-db    Up 3 seconds
# automation-orchestrator-redis Up 2 seconds
```

### 5. Initialize Database

```bash
# Run database migrations
docker-compose exec api python -m alembic upgrade head

# Create initial data
docker-compose exec api python -m automation_orchestrator.cli init-db
```

### 6. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/dashboard
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **PostgreSQL**: localhost:5432 (orchestrator/orchestrator)
- **Redis**: localhost:6379

---

## Building Docker Images

### 1. Build Development Image

```bash
# Build with default tag
docker build -t automation-orchestrator:latest .

# Build with specific version
docker build -t automation-orchestrator:v1.0.0 .

# Build with build arguments
docker build \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t automation-orchestrator:latest .
```

### 2. Build Multi-Architecture Images

```bash
# Build for ARM64 (Apple Silicon, Raspberry Pi)
docker buildx build --platform linux/arm64 -t automation-orchestrator:latest .

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/automation-orchestrator:latest \
  --push .
```

### 3. Push to Registry

```bash
# Login to Docker Hub
docker login

# Tag and push
docker tag automation-orchestrator:latest your-username/automation-orchestrator:latest
docker push your-username/automation-orchestrator:latest

# Login to GitHub Container Registry
docker login ghcr.io -u your-username

# Tag and push to GitHub
docker tag automation-orchestrator:latest ghcr.io/your-org/automation-orchestrator:latest
docker push ghcr.io/your-org/automation-orchestrator:latest
```

### 4. Security Scanning

```bash
# Scan image for vulnerabilities
docker scout cves automation-orchestrator:latest

# Generate detailed report
docker scout cves automation-orchestrator:latest --format json > cves.json

# Fix vulnerabilities
docker scout recommendations automation-orchestrator:latest
```

---

## Running with Docker Compose

### Development Environment

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Staging Environment

```bash
# Start with production-like setup
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# View all services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml ps
```

### Production Environment

```bash
# Start with production configuration
docker-compose -f docker-compose.prod.yml up -d

# Enable auto-restart
docker-compose -f docker-compose.prod.yml up -d --restart=always

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

---

## Production Deployment

### 1. Prepare Production Environment

```bash
# Create production .env file
cp .env.production.example .env.production

# Edit with production secrets
nano .env.production

# Set proper permissions
chmod 600 .env.production
```

### 2. Build Production Image

```bash
# Build lean production image
docker build -f Dockerfile -t automation-orchestrator:v1.0.0 .

# Tag for registry
docker tag automation-orchestrator:v1.0.0 your-registry/automation-orchestrator:v1.0.0

# Push to registry
docker push your-registry/automation-orchestrator:v1.0.0
```

### 3. Deploy to Server

```bash
# SSH to production server
ssh admin@production-server.com

# Create app directory
sudo mkdir -p /opt/automation-orchestrator
cd /opt/automation-orchestrator

# Copy docker-compose config
sudo cp docker-compose.prod.yml docker-compose.yml

# Create .env with secrets
sudo nano .env

# Pull latest image
sudo docker pull your-registry/automation-orchestrator:v1.0.0

# Start services
sudo docker-compose up -d

# Verify
sudo docker-compose ps
sudo docker-compose logs api
```

### 4. Configure Nginx Reverse Proxy

```bash
# Copy production Nginx config
sudo cp nginx-prod.conf /etc/nginx/sites-available/automation-orchestrator

# Enable site
sudo ln -s /etc/nginx/sites-available/automation-orchestrator \
           /etc/nginx/sites-enabled/automation-orchestrator

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 5. Setup SSL/TLS with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d automation-orchestrator.example.com \
  --email admin@example.com \
  --agree-tos

# Verify certificate
sudo certbot certificates

# Auto-renew (should be automatic)
sudo systemctl enable certbot.timer
```

---

## Useful Docker Commands

### Container Management

```bash
# List all containers
docker ps -a

# View container logs
docker logs container-name
docker logs -f container-name  # Follow logs

# Execute command in container
docker exec -it container-name bash

# Copy files from container
docker cp container-name:/app/logs ./logs

# Stop/start container
docker stop container-name
docker start container-name

# Restart container
docker restart container-name
```

### Image Management

```bash
# List all images
docker images

# Remove image
docker rmi image-name

# Inspect image
docker inspect image-name

# View image layers
docker history image-name
```

### Network

```bash
# List networks
docker network ls

# Inspect network
docker network inspect network-name

# Test connectivity between containers
docker exec container1 curl http://container2:8000
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect volume-name

# Backup volume
docker run --rm -v volume-name:/data -v $(pwd):/backup \
  alpine tar czf /backup/volume-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v volume-name:/data -v $(pwd):/backup \
  alpine tar xzf /backup/volume-backup.tar.gz -C /data
```

### Debugging

```bash
# Inspect container
docker inspect container-name

# View resource usage
docker stats

# Monitor events
docker events --filter type=container

# Debug network issues
docker exec container-name ping container-name-2
docker exec container-name nslookup localhost
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 PID

# Or use different port
docker-compose down
# Edit docker-compose.yml port mappings
docker-compose up -d
```

#### 2. Database Connection Failed

```bash
# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db psql -U orchestrator -c "\c automation_orchestrator"

# Verify network
docker-compose exec api curl http://db:5432
```

#### 3. Out of Disk Space

```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune

# Remove all dangling images
docker image prune -a
```

#### 4. Memory Issues

```bash
# Check memory usage
docker stats

# Limit memory in docker-compose.yml
# services:
#   api:
#     deploy:
#       resources:
#         limits:
#           memory: 512M

# Restart service
docker-compose restart api
```

#### 5. Container Won't Start

```bash
# Check logs
docker-compose logs api

# Inspect container
docker inspect automation-orchestrator-api

# Try rebuilding
docker-compose down
docker-compose build
docker-compose up
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check database health
docker-compose exec db pg_isready -U orchestrator

# Check Redis health
docker-compose exec redis redis-cli ping

# View health status
docker inspect --format='{{json .State.Health}}' container-name | jq
```

---

## Performance Optimization

### 1. Resource Limits

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 2. Caching

```bash
# Use BuildKit for better caching
export DOCKER_BUILDKIT=1
docker build .

# Cache Python packages
docker build --cache-from=automation-orchestrator:latest .
```

### 3. Image Size

```bash
# Check image size
docker images automation-orchestrator

# Use .dockerignore to exclude files
# Already configured in .dockerignore

# Use multi-stage builds
# Already implemented in Dockerfile
```

---

## Maintenance Tasks

### Backup Database

```bash
# Create backup
docker-compose exec db pg_dump -U orchestrator automation_orchestrator > backup.sql

# Restore backup
cat backup.sql | docker-compose exec -T db psql -U orchestrator automation_orchestrator
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build

# Restart services
docker-compose up -d
```

### Monitor Logs

```bash
# Real-time logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail 100 api

# Specific time range
docker-compose logs --since 2024-01-15 --until 2024-01-16 api
```

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

For production support, see PRODUCTION_DEPLOYMENT_GUIDE.md
