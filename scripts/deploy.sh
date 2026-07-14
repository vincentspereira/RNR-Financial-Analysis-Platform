#!/bin/bash

# RNR Financial Analysis Platform - Deployment Script
# Version: 1.0.0
# Author: System Administrator
# Date: October 31, 2025

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/rnr-financial-analysis-deploy.log"
BACKUP_DIR="/opt/backups/rnr-financial-analysis"
DEPLOY_ENV="${DEPLOY_ENV:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "${BLUE}$*${NC}"
}

log_warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

log_error() {
    log "ERROR" "${RED}$*${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Error handler
error_handler() {
    local line_number=$1
    log_error "Deployment failed at line $line_number"
    log_error "Rolling back changes..."
    rollback_deployment
    exit 1
}

trap 'error_handler $LINENO' ERR

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root. Consider using a dedicated deployment user."
    fi
    
    # Check required commands
    local required_commands=("python3" "pip" "npm" "git" "systemctl" "nginx")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2)
    local required_version="3.11"
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        log_error "Python 3.11+ required, found $python_version"
        exit 1
    fi
    
    # Check Node.js version
    local node_version=$(node --version | cut -d'v' -f2)
    if ! node -e "process.exit(process.version.match(/^v(\d+)/)[1] >= 18 ? 0 : 1)"; then
        log_error "Node.js 18+ required, found $node_version"
        exit 1
    fi
    
    # Check disk space (minimum 5GB free)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local min_space=$((5 * 1024 * 1024))  # 5GB in KB
    if [[ $available_space -lt $min_space ]]; then
        log_error "Insufficient disk space. At least 5GB required."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create backup
create_backup() {
    log_info "Creating deployment backup..."
    
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/backup_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup application files
    if [[ -d "/opt/rnr-financial-analysis" ]]; then
        tar -czf "$backup_path/application.tar.gz" -C /opt rnr-financial-analysis
        log_info "Application files backed up"
    fi
    
    # Backup database
    if command -v pg_dump &> /dev/null; then
        pg_dump -U "${DB_USER:-fin_user}" -h "${DB_HOST:-localhost}" \
                "${DB_NAME:-financial_analysis_prod}" > "$backup_path/database.sql"
        gzip "$backup_path/database.sql"
        log_info "Database backed up"
    fi
    
    # Backup configuration files
    tar -czf "$backup_path/configs.tar.gz" \
        /etc/nginx/sites-available/rnr-financial-analysis \
        /etc/systemd/system/rnr-financial-analysis.service \
        2>/dev/null || true
    
    echo "$backup_path" > /tmp/last_backup_path
    log_success "Backup created at $backup_path"
}

# Setup application directory
setup_application() {
    log_info "Setting up application directory..."
    
    local app_dir="/opt/rnr-financial-analysis"
    
    # Create application directory
    sudo mkdir -p "$app_dir"
    sudo chown -R "$USER:$USER" "$app_dir"
    
    # Copy application files
    if [[ "$PROJECT_ROOT" != "$app_dir" ]]; then
        rsync -av --exclude='.git' --exclude='node_modules' --exclude='venv' \
              "$PROJECT_ROOT/" "$app_dir/"
    fi
    
    cd "$app_dir"
    log_success "Application directory setup complete"
}

# Setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    cd /opt/rnr-financial-analysis/backend
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        log_info "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    
    log_success "Python environment setup complete"
}

# Setup Node.js environment
setup_nodejs_environment() {
    log_info "Setting up Node.js environment..."
    
    cd /opt/rnr-financial-analysis/frontend

    # Install ALL dependencies first — Vite/TypeScript are devDependencies and
    # are required for the build. (`npm ci --production` is deprecated and would
    # strip them before `npm run build`, breaking the build.)
    npm ci

    # Build application
    npm run build

    # Prune to production-only dependencies for the served image
    npm prune --production

    log_success "Node.js environment setup complete"
}

# Setup database
setup_database() {
    log_info "Setting up database..."
    
    cd /opt/rnr-financial-analysis/backend
    source venv/bin/activate
    
    # Run database migrations
    alembic upgrade head
    
    log_success "Database setup complete"
}

# Setup systemd service
setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    cat > /tmp/rnr-financial-analysis.service << EOF
[Unit]
Description=RNR Financial Analysis Platform API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/rnr-financial-analysis/backend
Environment=PATH=/opt/rnr-financial-analysis/backend/venv/bin
ExecStart=/opt/rnr-financial-analysis/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/rnr-financial-analysis.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable rnr-financial-analysis
    
    log_success "Systemd service setup complete"
}

# Setup Nginx
setup_nginx() {
    log_info "Setting up Nginx configuration..."
    
    cat > /tmp/rnr-financial-analysis-nginx << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/rnr-financial-analysis.crt;
    ssl_certificate_key /etc/ssl/private/rnr-financial-analysis.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Frontend
    location / {
        root /opt/rnr-financial-analysis/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
EOF

    sudo mv /tmp/rnr-financial-analysis-nginx /etc/nginx/sites-available/rnr-financial-analysis
    sudo ln -sf /etc/nginx/sites-available/rnr-financial-analysis /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    sudo nginx -t
    
    log_success "Nginx configuration setup complete"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start application service
    sudo systemctl start rnr-financial-analysis
    sudo systemctl status rnr-financial-analysis --no-pager
    
    # Start Nginx
    sudo systemctl restart nginx
    sudo systemctl status nginx --no-pager
    
    log_success "Services started successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for services to start
    sleep 10
    
    # Check if application is responding
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null; then
            log_success "Application health check passed"
            break
        fi
        
        log_info "Waiting for application to start (attempt $attempt/$max_attempts)..."
        sleep 5
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Application failed to start within expected time"
        return 1
    fi
    
    # Test API endpoints
    local api_response=$(curl -s http://localhost:8000/api/v1/health)
    if echo "$api_response" | grep -q '"status":"healthy"'; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        return 1
    fi
    
    # Check database connectivity
    cd /opt/rnr-financial-analysis/backend
    source venv/bin/activate
    if python -c "from app.core.database import engine; engine.connect()"; then
        log_success "Database connectivity verified"
    else
        log_error "Database connectivity failed"
        return 1
    fi
    
    log_success "Deployment verification complete"
}

# Rollback deployment
rollback_deployment() {
    log_warn "Rolling back deployment..."
    
    if [[ -f "/tmp/last_backup_path" ]]; then
        local backup_path=$(cat /tmp/last_backup_path)
        
        if [[ -d "$backup_path" ]]; then
            # Stop services
            sudo systemctl stop rnr-financial-analysis || true
            
            # Restore application files
            if [[ -f "$backup_path/application.tar.gz" ]]; then
                sudo tar -xzf "$backup_path/application.tar.gz" -C /opt/
                log_info "Application files restored"
            fi
            
            # Restore database
            if [[ -f "$backup_path/database.sql.gz" ]]; then
                gunzip -c "$backup_path/database.sql.gz" | \
                    psql -U "${DB_USER:-fin_user}" -h "${DB_HOST:-localhost}" \
                         "${DB_NAME:-financial_analysis_prod}"
                log_info "Database restored"
            fi
            
            # Start services
            sudo systemctl start rnr-financial-analysis || true
            
            log_success "Rollback completed"
        else
            log_error "Backup not found at $backup_path"
        fi
    else
        log_error "No backup information found"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups..."
    
    # Keep only last 10 backups
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | \
        sort -r | tail -n +11 | xargs -r rm -rf
    
    log_success "Old backups cleaned up"
}

# Main deployment function
main() {
    log_info "Starting RNR Financial Analysis Platform deployment..."
    log_info "Environment: $DEPLOY_ENV"
    log_info "Project root: $PROJECT_ROOT"
    
    # Create log directory
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    sudo touch "$LOG_FILE"
    sudo chmod 666 "$LOG_FILE"
    
    # Create backup directory
    sudo mkdir -p "$BACKUP_DIR"
    
    # Run deployment steps
    check_prerequisites
    create_backup
    setup_application
    setup_python_environment
    setup_nodejs_environment
    setup_database
    setup_systemd_service
    setup_nginx
    start_services
    verify_deployment
    cleanup_old_backups
    
    log_success "Deployment completed successfully!"
    log_info "Application is available at: https://$(hostname -f)"
    log_info "API documentation: https://$(hostname -f)/docs"
    log_info "Health check: https://$(hostname -f)/health"
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy the RNR Financial Analysis Platform

OPTIONS:
    -e, --environment ENV    Deployment environment (default: production)
    -h, --help              Show this help message
    --rollback              Rollback to previous deployment
    --verify-only           Only run verification checks

ENVIRONMENT VARIABLES:
    DEPLOY_ENV              Deployment environment
    DB_USER                 Database user (default: fin_user)
    DB_HOST                 Database host (default: localhost)
    DB_NAME                 Database name (default: financial_analysis_prod)

EXAMPLES:
    $0                      # Deploy to production
    $0 -e staging          # Deploy to staging
    $0 --rollback          # Rollback deployment
    $0 --verify-only       # Only verify current deployment

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            DEPLOY_ENV="$2"
            shift 2
            ;;
        --rollback)
            rollback_deployment
            exit 0
            ;;
        --verify-only)
            verify_deployment
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main deployment
main