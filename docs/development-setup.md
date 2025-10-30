# Development Setup Guide

## Overview

This guide provides comprehensive instructions for setting up the development environment for the Financial Analysis Platform. Following these steps will ensure all team members have consistent, productive development environments.

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: Minimum 16GB, recommended 32GB
- **Storage**: Minimum 50GB free disk space
- **Processor**: Modern multi-core processor (Intel i5+ or AMD Ryzen 5+)

### Required Accounts
- **GitHub Account**: For code repository access
- **Docker Hub Account**: For container registry access
- **Cloud Provider Account**: AWS, Azure, or GCP for deployment
- **Financial Data API Accounts**:
  - Alpha Vantage API key
  - Financial Modeling Prep API key
  - Yahoo Finance (free access)

## Software Installation

### 1. Version Control - Git
```bash
# Windows (using Chocolatey)
choco install git

# macOS (using Homebrew)
brew install git

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install git
```

**Configuration**:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false
```

### 2. Python 3.11+ Environment
**Windows**:
1. Download Python 3.11+ from [python.org](https://www.python.org/)
2. Install with "Add to PATH" option enabled
3. Verify installation:
```cmd
python --version
pip --version
```

**macOS/Linux**:
```bash
# macOS (using Homebrew)
brew install python@3.11

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

**Python Environment Setup**:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Node.js 18+ and npm
**Windows** (using Chocolatey):
```cmd
choco install nodejs
```

**macOS** (using Homebrew):
```bash
brew install node
```

**Linux** (Ubuntu/Debian):
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Verify Installation**:
```bash
node --version
npm --version
```

### 4. Database - PostgreSQL 15+
**Windows**:
1. Download from [EnterpriseDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Run installer with default settings
3. Set password for postgres user

**macOS** (using Homebrew):
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Database Setup**:
```bash
# Create database user
sudo -u postgres createuser --interactive

# Create databases
sudo -u postgres createdb financial_analysis_dev
sudo -u postgres createdb financial_analysis_test
```

### 5. Redis Cache
**Windows**:
1. Download Redis for Windows from [Microsoft Archive](https://github.com/microsoftarchive/redis/releases)
2. Extract and run redis-server.exe

**macOS** (using Homebrew):
```bash
brew install redis
brew services start redis
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 6. Docker and Docker Compose
**Windows**:
1. Download Docker Desktop from [Docker Hub](https://www.docker.com/products/docker-desktop)
2. Install with WSL 2 backend

**macOS**:
1. Download Docker Desktop from [Docker Hub](https://www.docker.com/products/docker-desktop)
2. Install and start

**Linux**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

## Development Tools

### 1. Integrated Development Environment (IDE)
**Recommended Options**:
- **VS Code**: Lightweight, extensive extensions
- **PyCharm Professional**: Full-featured Python IDE
- **WebStorm**: Frontend development focus

**VS Code Setup**:
```bash
# Install VS Code
# Download from https://code.visualstudio.com/

# Install extensions
code --install-extension ms-python.python
code --install-extension ms-python.flake8
code --install-extension ms-python.black-formatter
code --install-extension bradlc.vscode-tailwindcss
code --install-extension ms-vscode.vscode-typescript-next
code --install-extension esbenp.prettier-vscode
code --install-extension ms-vscode.vscode-json
```

**VS Code Settings** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "typescript.preferences.importModuleSpecifier": "relative"
}
```

### 2. Database Management Tools
**Recommended Tools**:
- **pgAdmin**: PostgreSQL administration
- **DBeaver**: Universal database tool
- **TablePlus**: Modern database client

**pgAdmin Installation**:
- Download from [pgAdmin website](https://www.pgadmin.org/download/)
- Configure connection to local PostgreSQL instance

### 3. API Testing Tools
**Postman**:
1. Download from [Postman website](https://www.postman.com/downloads/)
2. Create workspace for project APIs
3. Import API collections when available

## Project Setup

### 1. Repository Setup
```bash
# Clone repository (when available)
git clone https://github.com/your-org/financial-analysis-platform.git
cd financial-analysis-platform

# Or initialize new repository
git init
git remote add origin https://github.com/your-org/financial-analysis-platform.git
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source ../venv/bin/activate  # Linux/macOS
# or
..\venv\Scripts\activate     # Windows

# Install Python dependencies
pip install -r requirements-dev.txt

# Environment variables setup
cp .env.example .env
# Edit .env file with your configuration
```

**Environment Variables** (`.env`):
```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/financial_analysis_dev
TEST_DATABASE_URL=postgresql://username:password@localhost:5432/financial_analysis_test

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINANCIAL_MODELING_PREP_API_KEY=your-fmp-key

# Development Settings
DEBUG=True
LOG_LEVEL=DEBUG
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Environment variables setup
cp .env.example .env.local
# Edit .env.local file with your configuration
```

**Frontend Environment Variables** (`.env.local`):
```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Development Settings
NEXT_PUBLIC_DEBUG=true
```

### 4. Database Migration
```bash
# Navigate to backend directory
cd backend

# Run database migrations
alembic upgrade head

# Create initial data (optional)
python scripts/create_initial_data.py
```

## Development Workflow

### 1. Starting Development Services
```bash
# Terminal 1: Start PostgreSQL and Redis (if not running as services)
# Start PostgreSQL (manual installation)
sudo service postgresql start

# Start Redis (manual installation)
sudo service redis start

# Terminal 2: Backend Development Server
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Frontend Development Server
cd frontend
npm run dev

# Terminal 4: Background Tasks (optional)
cd backend
source ../venv/bin/activate
celery -A app.core.celery worker --loglevel=info
```

### 2. Code Quality Tools
**Python**:
```bash
# Code formatting
black .

# Import sorting
isort .

# Linting
flake8 .

# Type checking
mypy .
```

**TypeScript/JavaScript**:
```bash
# Linting
npm run lint

# Type checking
npm run type-check

# Formatting
npm run format
```

### 3. Testing
```bash
# Backend Testing
cd backend
pytest tests/ -v --cov=app

# Frontend Testing
cd frontend
npm run test
npm run test:e2e
```

### 4. Pre-commit Hooks Setup
```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit manually
pre-commit run --all-files
```

## Docker Development Setup

### 1. Docker Compose Development
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### 2. Development Container (VS Code)
**`.devcontainer/devcontainer.json`**:
```json
{
    "name": "Financial Analysis Platform",
    "dockerComposeFile": "../docker-compose.dev.yml",
    "service": "backend",
    "workspaceFolder": "/app",
    "extensions": [
        "ms-python.python",
        "ms-python.flake8",
        "ms-python.black-formatter"
    ],
    "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python"
    }
}
```

## Troubleshooting

### Common Issues

**1. Python Virtual Environment Issues**:
```bash
# Delete and recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

**2. Database Connection Issues**:
- Verify PostgreSQL is running: `sudo service postgresql status`
- Check connection string in `.env` file
- Verify database exists: `psql -l`

**3. Redis Connection Issues**:
- Verify Redis is running: `redis-cli ping`
- Check Redis configuration in `.env` file

**4. Port Conflicts**:
- Check port usage: `netstat -tulpn | grep :8000`
- Kill processes using ports: `kill -9 <PID>`
- Change ports in configuration files

**5. Node.js Dependency Issues**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall dependencies
npm install
```

## Performance Optimization

### Development Performance Tips
1. **Use SSD Storage**: Faster file operations
2. **Adequate RAM**: Minimum 16GB recommended
3. **Disable Unused Extensions**: In VS Code/IDE
4. **Use Local Database**: Reduce network latency
5. **Configure Code Navigation**: Optimize IDE settings

### Resource Monitoring
```bash
# System resource monitoring
htop          # Linux/macOS
Task Manager  # Windows

# Docker resource usage
docker stats

# Database performance
psql -c "SELECT * FROM pg_stat_activity;"
```

## Security Considerations

### Development Security
1. **Never Commit Secrets**: Use environment variables
2. **Secure API Keys**: Rotate keys regularly
3. **Use HTTPS**: Even in development
4. **Regular Updates**: Keep all tools updated
5. **Firewall Configuration**: Protect development machine

## Next Steps

1. **Verify Setup**: Run all services and test connections
2. **Create Branch**: Set up development branch
3. **Run Tests**: Ensure all tests pass
4. **Set Up CI/CD**: Configure continuous integration
5. **Team Onboarding**: Share setup guide with team members

---

**Document Version**: 1.0
**Created**: October 30, 2025
**Last Updated**: October 30, 2025
**Next Review**: November 30, 2025