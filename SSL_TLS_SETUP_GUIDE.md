# SSL/TLS Configuration Guide

This guide covers setting up HTTPS/SSL/TLS encryption for the Automation Orchestrator API.

## Why SSL/TLS?

- **Encryption in transit** - Protects data from eavesdropping
- **Authentication** - Verifies server identity
- **HSTS support** - Forces HTTPS connections
- **Compliance** - Required for HIPAA, PCI-DSS, SOC 2
- **Security headers** - Enables security best practices

## Option 1: Self-Signed Certificate (Development)

**Generate self-signed certificate (valid for 365 days):**

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

**When prompted, enter:**
```
Country: US
State: Your State
Locality: Your City
Organization: Your Company
Common Name: localhost
```

**Start API with SSL (for testing):**

```bash
uvicorn automation_orchestrator.main:app \
  --host 127.0.0.1 \
  --port 8443 \
  --ssl-keyfile=key.pem \
  --ssl-certfile=cert.pem
```

**Access at:** `https://127.0.0.1:8443/`

## Option 2: Let's Encrypt (Production - Free!)

### Prerequisites
- Domain name (example.com)
- Public IP accessible from internet
- Port 80 and 443 open

### Step 1: Install Certbot

```bash
# On Ubuntu/Debian
sudo apt-get install certbot python3-certbot-nginx

# On Windows (using WSL or Docker)
# Or use alternative: acme.sh
```

### Step 2: Get Certificate

```bash
# Using standalone (no web server required)
sudo certbot certonly --standalone -d example.com -d www.example.com

# Or using DNS challenge (for wildcard)
sudo certbot certonly --dns-route53 -d *.example.com
```

**Certificate saved to:**
- `/etc/letsencrypt/live/example.com/fullchain.pem` (certificate)
- `/etc/letsencrypt/live/example.com/privkey.pem` (private key)

### Step 3: Start Uvicorn with SSL

```bash
uvicorn automation_orchestrator.main:app \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-keyfile=/etc/letsencrypt/live/example.com/privkey.pem \
  --ssl-certfile=/etc/letsencrypt/live/example.com/fullchain.pem
```

### Step 4: Auto-Renewal

```bash
sudo certbot renew --quiet
```

Add to crontab (runs daily):
```bash
0 3 * * * certbot renew --quiet && systemctl reload automation-orchestrator
```

## Option 3: Nginx Reverse Proxy with SSL (Recommended)

This is the recommended production setup.

### Step 1: Install Nginx

```bash
sudo apt-get install nginx certbot python3-certbot-nginx
```

### Step 2: Get Certificate

```bash
sudo certbot certonly --nginx -d example.com -d www.example.com
```

### Step 3: Configure Nginx

Create `/etc/nginx/sites-available/automation-orchestrator`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # SSL/TLS Configuration
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Proxy Configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
    }

    location ~ ~$ {
        deny all;
    }

    # Logging
    access_log /var/log/nginx/automation-orchestrator-access.log;
    error_log /var/log/nginx/automation-orchestrator-error.log;
}
```

### Step 4: Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/automation-orchestrator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: Start Automation Orchestrator

Start the API on localhost without SSL (Nginx handles it):

```bash
uvicorn automation_orchestrator.main:app \
  --host 127.0.0.1 \
  --port 8000
```

**Access at:** `https://example.com/`

## Option 4: Docker with SSL

**Dockerfile:**

```dockerfile
FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/automation_orchestrator ./
COPY cert.pem key.pem ./

CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8443", \
     "--ssl-keyfile=/app/key.pem", \
     "--ssl-certfile=/app/cert.pem"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8443:8443"
    environment:
      JWT_SECRET: your-secret-key
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - api
```

## API Configuration with HTTPS

**Update main.py:**

```python
import ssl
import uvicorn

def run_api(cfg, host="0.0.0.0", port=8000, ssl_certfile=None, ssl_keyfile=None):
    """Start API with optional SSL/TLS"""
    ssl_context = None
    
    if ssl_certfile and ssl_keyfile:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
        print(f"✓ SSL/TLS enabled")
        print(f"  Certificate: {ssl_certfile}")
        print(f"  Key: {ssl_keyfile}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_context=ssl_context,
        log_level="info"
    )
```

**Command line usage:**

```bash
python -m automation_orchestrator.main --api \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-cert cert.pem \
  --ssl-key key.pem
```

## Security Best Practices

### 1. Certificate Validation

**Test certificate chain:**
```bash
openssl s_client -connect example.com:443 -showcerts
```

### 2. Strong Ciphers

**Check cipher configuration:**
```bash
testssl.sh https://example.com
```

### 3. HSTS Header

Enable HTTP Strict-Transport-Security to force HTTPS:

```python
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

def create_app(config: Dict[str, Any]):
    if not app.middleware:
        app = FastAPI()
    
    # Add HSTS middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response
```

### 4. Certificate Pinning

For API clients, implement certificate pinning:

```python
import ssl
import requests

# Create SSL context with pinned certificate
context = ssl.create_default_context()
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED

# Pin specific certificate
context.load_verify_locations('ca_bundle.crt')

response = requests.get(
    'https://example.com/api/...',
    verify=context
)
```

### 5. Automated Renewal Monitoring

```bash
# Check certificate expiration
openssl x509 -in cert.pem -noout -dates

# Set up expiration alerts
certbot renew --dry-run --agree-tos --no-interact --quiet
```

## Troubleshooting

**Certificate not trusted:**
```bash
# Verify certificate can be read
openssl x509 -in cert.pem -text -noout

# Verify key matches certificate
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

**Port 443 in use:**
```bash
# Find process using port 443
sudo lsof -i :443

# Kill process if needed
sudo kill -9 <PID>
```

**Certificate expires:**
```bash
# Renew before expiration
sudo certbot renew --force-renewal

# Auto-renewal status
sudo systemctl status certbot.timer
```

## Production Checklist

- [ ] Certificate authority (Let's Encrypt recommended)
- [ ] SSL/TLS version 1.2+ enabled
- [ ] Strong ciphers configured
- [ ] HSTS header enabled
- [ ] Security headers configured (X-Content-Type-Options, X-Frame-Options, etc.)
- [ ] Nginx reverse proxy with SSL termination
- [ ] Certificate auto-renewal configured
- [ ] Certificate expiration monitoring
- [ ] Regular certificate renewal tests
- [ ] API key authentication enforced
- [ ] Rate limiting enabled
- [ ] Request logging enabled
- [ ] Firewall configured (only allow needed ports)

## Testing HTTPS Connection

```bash
# Test with curl
curl -I https://example.com

# Test API endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://example.com/api/health

# Test with Python
import requests
response = requests.get('https://example.com/api/health',
    verify='/path/to/ca_bundle.crt')
```

## References

- Let's Encrypt: https://letsencrypt.org/
- Certbot: https://certbot.eff.org/
- Mozilla SSL Configuration: https://ssl-config.mozilla.org/
- OWASP TLS: https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/01-Information_Gathering/01-Conduct_Web_Application_Fingerprinting
