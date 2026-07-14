# RNR Financial Analysis Platform - Deployment Guide

**Document Version**: 1.0.0  
**Last Updated**: October 31, 2025  
**Author**: System Administrator  

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Environment Setup](#environment-setup)
4. [Deployment Procedures](#deployment-procedures)
5. [Configuration Parameters](#configuration-parameters)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)

## System Requirements

### Hardware Requirements

#### Minimum Requirements (Development)
- **CPU**: 4 cores, 2.5 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 100 Mbps

#### Recommended Requirements (Production)
- **CPU**: 8 cores, 3.0 GHz
- **RAM**: 32 GB
- **Storage**: 500 GB SSD (with backup)
- **Network**: 1 Gbps
- **Load Balancer**: Required for high availability

### Software Requirements

#### Operating System
- **Linux**: Ubuntu 20.04+ LTS, CentOS 8+, RHEL 8+
- **Windows**: Windows Server 2019+, Windows 10/11 Pro
- **macOS**: macOS 11+ (development only)

#### Runtime Dependencies
- **Python**: 3.11+ (recommended: 3.13.5)
- **Node.js**: 18+ (recommended: 22.17.1)
- **PostgreSQL**: 15+ with TimescaleDB extension
- **Redis**: 7.0+
- **Docker**: 24.0+ (optional but recommended)
- **Docker Compose**: 2.20+ (for containerized deployment)

#### External Services
- **SSL Certificate**: Valid SSL certificate for HTTPS
- **Domain Name**: Configured DNS records
- **Email Service**: SMTP server for notifications
- **External APIs**: Alpha Vantage, Yahoo Finance API keys

## Pre-Deployment Checklist

### Infrastructure Preparation
- [ ] Server provisioning completed
- [ ] Network security groups configured
- [ ] SSL certificates obtained and validated
- [ ] DNS records configured
- [ ] Backup storage configured
- [ ] Monitoring tools installed

### Security Configuration
- [ ] Firewall rules configured
- [ ] SSH keys generated and distributed
- [ ] Database credentials secured
- [ ] API keys obtained and secured
- [ ] Security scanning completed
- [ ] Penetration testing completed

### Dependencies Installation
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] PostgreSQL 15+ installed and configured
- [ ] Redis 7.0+ installed and configured
- [ ] Docker and Docker Compose installed (if using containers)
- [ ] Nginx/Apache configured (if using reverse proxy)

## Environment Setup

### 1. Database Setup

#### PostgreSQL Installation and Configuration
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15

# CentOS/RHEL
sudo dnf install postgresql15-server postgresql15-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE financial_analysis_prod;
CREATE USER fin_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE financial_analysis_prod TO fin_user;
\q
```

#### TimescaleDB Extension
```bash
# Install TimescaleDB
sudo apt install timescaledb-2-postgresql-15

# Enable extension
sudo -u postgres psql -d financial_analysis_prod
CREATE EXTENSION IF NOT EXISTS timescaledb;
\q
```

### 2. Redis Setup

#### Redis Installation and Configuration
```bash
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo dnf install redis

# Configure Redis
sudo nano /etc/redis/redis.conf

# Key configurations:
# bind 127.0.0.1
# port 6379
# requirepass your_redis_password
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 3. Application Environment

#### Backend Environment Setup
```bash
# Create application directory
sudo mkdir -p /opt/rnr-financial-analysis
cd /opt/rnr-financial-analysis

# Clone repository
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

#### Frontend Environment Setup
```bash
# Install Node.js dependencies
cd ../frontend
npm install

# Build production assets
npm run build
```

## Deployment Procedures

### Option 1: Traditional Deployment

#### 1. Backend Deployment
```bash
# Navigate to backend directory
cd /opt/rnr-financial-analysis/backend

# Activate virtual environment
source ../venv/bin/activate

# Set environment variables
export DATABASE_URL="postgresql://fin_user:secure_password_here@localhost:5432/financial_analysis_prod"
export REDIS_URL="redis://:your_redis_password@localhost:6379/0"
export SECRET_KEY="your_secret_key_here"
export ENVIRONMENT="production"

# Run database migrations
alembic upgrade head

# Start application with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

#### 2. Frontend Deployment
```bash
# Copy built assets to web server
sudo cp -r /opt/rnr-financial-analysis/frontend/dist/* /var/www/html/

# Configure Nginx
sudo nano /etc/nginx/sites-available/rnr-financial-analysis

# Nginx configuration:
server {
    listen 80;
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site and restart Nginx
sudo ln -s /etc/nginx/sites-available/rnr-financial-analysis /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### Option 2: Docker Deployment

#### 1. Docker Compose Deployment
```bash
# Navigate to project root
cd /opt/rnr-financial-analysis

# Create production docker-compose file
cp docker-compose.dev.yml docker-compose.prod.yml

# Edit production configuration
nano docker-compose.prod.yml

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f infrastructure/kubernetes/production/

# Verify deployment
kubectl get pods -n rnr-financial-analysis
kubectl get services -n rnr-financial-analysis
```

## Configuration Parameters

### Environment Variables

#### Required Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://password@host:port/db
CELERY_BROKER_URL=redis://password@host:port/1
CELERY_RESULT_BACKEND=redis://password@host:port/2

# Security Configuration
SECRET_KEY=your-256-bit-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_V1_STR=/api/v1

# External API Keys
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINANCIAL_MODELING_PREP_API_KEY=your-fmp-key
YAHOO_FINANCE_API_KEY=your-yahoo-key

# SSL Configuration (Production)
SSL_CERT_FILE=/path/to/certificate.crt
SSL_KEY_FILE=/path/to/private.key

# CORS Configuration
BACKEND_CORS_ORIGINS=["https://your-domain.com"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

#### Optional Variables
```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring Configuration
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# File Storage
FILE_STORAGE_PATH=/opt/rnr-financial-analysis/storage
MAX_FILE_SIZE_MB=10

# Cache Configuration
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE_MB=100
```

## Post-Deployment Verification

### 1. Health Checks

#### API Health Check
```bash
# Test API endpoints
curl -X GET "https://your-domain.com/health"
curl -X GET "https://your-domain.com/api/v1/health"

# Expected responses:
# {"status": "healthy", "version": "1.0.0", ...}
```

#### Database Connectivity
```bash
# Test database connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://fin_user:password@localhost:5432/financial_analysis_prod')
print('Database connection successful')
conn.close()
"
```

#### Redis Connectivity
```bash
# Test Redis connection
redis-cli -h localhost -p 6379 -a your_redis_password ping
# Expected response: PONG
```

### 2. Functional Testing

#### Authentication Testing
```bash
# Test user registration
curl -X POST "https://your-domain.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'

# Test user login
curl -X POST "https://your-domain.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'
```

#### Financial Calculations Testing
```bash
# Test financial ratio calculation
curl -X POST "https://your-domain.com/api/v1/financial/ratios" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{"current_assets": 100000, "current_liabilities": 50000}'
```

### 3. Performance Testing

#### Load Testing
```bash
# Install Apache Bench
sudo apt install apache2-utils

# Test API performance
ab -n 1000 -c 10 https://your-domain.com/api/v1/health

# Expected results:
# - Requests per second: > 100
# - Time per request: < 100ms
# - Failed requests: 0
```

#### Memory and CPU Monitoring
```bash
# Monitor system resources
htop
free -h
df -h

# Monitor application processes
ps aux | grep python
ps aux | grep node
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Issues

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Verify connection parameters
sudo -u postgres psql -c "SELECT version();"

# Check firewall rules
sudo ufw status
sudo iptables -L
```

#### 2. Redis Connection Issues

**Problem**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solutions**:
```bash
# Check Redis status
sudo systemctl status redis

# Test Redis connectivity
redis-cli ping

# Check Redis configuration
sudo nano /etc/redis/redis.conf

# Restart Redis service
sudo systemctl restart redis
```

#### 3. SSL Certificate Issues

**Problem**: `SSL certificate verification failed`

**Solutions**:
```bash
# Verify certificate validity
openssl x509 -in /path/to/certificate.crt -text -noout

# Check certificate expiration
openssl x509 -in /path/to/certificate.crt -noout -dates

# Test SSL configuration
openssl s_client -connect your-domain.com:443
```

#### 4. High Memory Usage

**Problem**: Application consuming excessive memory

**Solutions**:
```bash
# Monitor memory usage
free -h
ps aux --sort=-%mem | head

# Optimize database connections
# Reduce DATABASE_POOL_SIZE in environment variables

# Optimize Redis memory
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### 5. Slow API Response Times

**Problem**: API responses taking longer than expected

**Solutions**:
```bash
# Check database query performance
sudo -u postgres psql -d financial_analysis_prod
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Monitor application logs
tail -f /var/log/rnr-financial-analysis/app.log

# Check system load
uptime
iostat 1 5
```

### Log File Locations

```bash
# Application logs
/var/log/rnr-financial-analysis/app.log
/var/log/rnr-financial-analysis/error.log

# System logs
/var/log/syslog
/var/log/auth.log

# Database logs
/var/log/postgresql/postgresql-15-main.log

# Web server logs
/var/log/nginx/access.log
/var/log/nginx/error.log

# Redis logs
/var/log/redis/redis-server.log
```

## Rollback Procedures

### 1. Application Rollback

#### Traditional Deployment Rollback
```bash
# Stop current application
sudo systemctl stop rnr-financial-analysis

# Restore previous version
cd /opt/rnr-financial-analysis
git checkout previous-stable-tag

# Restore virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Rollback database migrations (if needed)
cd backend
alembic downgrade -1

# Restart application
sudo systemctl start rnr-financial-analysis
```

#### Docker Rollback
```bash
# Rollback to previous image version
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml pull previous-tag
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Database Rollback

```bash
# Create database backup before rollback
pg_dump -U fin_user -h localhost financial_analysis_prod > backup_before_rollback.sql

# Rollback migrations
cd /opt/rnr-financial-analysis/backend
alembic downgrade revision_id

# If complete restore needed
sudo -u postgres psql
DROP DATABASE financial_analysis_prod;
CREATE DATABASE financial_analysis_prod;
\q

psql -U fin_user -h localhost financial_analysis_prod < previous_backup.sql
```

## Monitoring and Maintenance

### 1. System Monitoring

#### Key Metrics to Monitor
- **CPU Usage**: < 80% average
- **Memory Usage**: < 85% of available RAM
- **Disk Usage**: < 80% of available space
- **Network I/O**: Monitor for unusual spikes
- **Database Connections**: Monitor pool usage
- **API Response Times**: < 500ms average
- **Error Rates**: < 1% of total requests

#### Monitoring Tools Setup
```bash
# Install Prometheus (optional)
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
sudo mv prometheus-2.40.0.linux-amd64 /opt/prometheus

# Install Grafana (optional)
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana
```

### 2. Regular Maintenance Tasks

#### Daily Tasks
- [ ] Check system logs for errors
- [ ] Monitor disk space usage
- [ ] Verify backup completion
- [ ] Check API response times

#### Weekly Tasks
- [ ] Review security logs
- [ ] Update system packages
- [ ] Analyze performance metrics
- [ ] Test backup restoration

#### Monthly Tasks
- [ ] Security vulnerability scan
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Documentation updates

### 3. Backup and Recovery

#### Database Backup
```bash
# Create automated backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="financial_analysis_${DATE}.sql"

mkdir -p $BACKUP_DIR
pg_dump -U fin_user -h localhost financial_analysis_prod > $BACKUP_DIR/$BACKUP_FILE
gzip $BACKUP_DIR/$BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

#### Application Backup
```bash
# Backup application files
tar -czf /opt/backups/app_$(date +%Y%m%d).tar.gz /opt/rnr-financial-analysis

# Backup configuration files
tar -czf /opt/backups/config_$(date +%Y%m%d).tar.gz /etc/nginx /etc/redis /etc/postgresql
```

---

## Support and Contact Information

**Technical Support**: support@rnr-financial-analysis-platform.com  
**Emergency Contact**: +1-XXX-XXX-XXXX  
**Documentation**: https://docs.rnr-financial-analysis-platform.com  
**Status Page**: https://status.rnr-financial-analysis-platform.com  

---

**Document Control**  
- **Version**: 1.0.0  
- **Approved By**: System Administrator  
- **Next Review Date**: November 30, 2025