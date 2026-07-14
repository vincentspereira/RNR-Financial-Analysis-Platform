# RNR Financial Analysis Platform - Windows Deployment Script
# Version: 1.0.0
# Author: System Administrator

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "deploy",
    
    [Parameter(Mandatory=$false)]
    [switch]$Development = $false
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "=" * 60 -Color $Blue
    Write-ColorOutput "  $Title" -Color $Blue
    Write-ColorOutput "=" * 60 -Color $Blue
    Write-Host ""
}

function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-ColorOutput "✓ Docker found: $dockerVersion" -Color $Green
    }
    catch {
        Write-ColorOutput "✗ Docker not found. Please install Docker Desktop." -Color $Red
        exit 1
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version
        Write-ColorOutput "✓ Docker Compose found: $composeVersion" -Color $Green
    }
    catch {
        Write-ColorOutput "✗ Docker Compose not found." -Color $Red
        exit 1
    }
    
    # Check .env file
    if (Test-Path ".env") {
        Write-ColorOutput "✓ Environment file found" -Color $Green
    }
    else {
        Write-ColorOutput "✗ .env file not found. Creating from template..." -Color $Yellow
        if (Test-Path ".env.production") {
            Copy-Item ".env.production" ".env"
            Write-ColorOutput "✓ .env file created. Please edit it with your settings." -Color $Green
        }
        else {
            Write-ColorOutput "✗ .env.production template not found." -Color $Red
            exit 1
        }
    }
}

function Deploy-Application {
    Write-Header "Deploying RNR Financial Analysis Platform"
    
    $composeFile = if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.prod.yml" }
    $environment = if ($Development) { "Development" } else { "Production" }
    
    Write-ColorOutput "Environment: $environment" -Color $Blue
    Write-ColorOutput "Compose File: $composeFile" -Color $Blue
    
    # Build images
    Write-ColorOutput "Building Docker images..." -Color $Yellow
    docker compose -f $composeFile build
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "✗ Build failed!" -Color $Red
        exit 1
    }
    
    # Start services
    Write-ColorOutput "Starting services..." -Color $Yellow
    docker compose -f $composeFile up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "✗ Deployment failed!" -Color $Red
        exit 1
    }
    
    Write-ColorOutput "✓ Deployment successful!" -Color $Green
    
    # Show service status
    Start-Sleep -Seconds 5
    Show-Status
}

function Show-Status {
    Write-Header "Service Status"
    docker compose -f $(if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.prod.yml" }) ps
    
    Write-Header "Application URLs"
    Write-ColorOutput "Frontend: http://localhost:3030" -Color $Green
    Write-ColorOutput "Backend API: http://localhost:8000" -Color $Green
    Write-ColorOutput "API Documentation: http://localhost:8000/docs" -Color $Green
    Write-ColorOutput "Database: localhost:5432" -Color $Green
    Write-ColorOutput "Redis: localhost:6379" -Color $Green
}

function Stop-Application {
    Write-Header "Stopping RNR Financial Analysis Platform"
    
    $composeFile = if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.prod.yml" }
    docker compose -f $composeFile down
    
    Write-ColorOutput "✓ Application stopped" -Color $Green
}

function Show-Logs {
    Write-Header "Application Logs"
    
    $composeFile = if ($Development) { "docker-compose.dev.yml" } else { "docker-compose.prod.yml" }
    docker compose -f $composeFile logs -f
}

# Main execution
switch ($Action.ToLower()) {
    "deploy" {
        Check-Prerequisites
        Deploy-Application
    }
    "stop" {
        Stop-Application
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "restart" {
        Stop-Application
        Start-Sleep -Seconds 3
        Deploy-Application
    }
    default {
        Write-ColorOutput "Usage: .\deploy.ps1 [-Action deploy|stop|status|logs|restart] [-Development]" -Color $Yellow
        Write-ColorOutput ""
        Write-ColorOutput "Examples:" -Color $Blue
        Write-ColorOutput "  .\deploy.ps1                    # Deploy production"
        Write-ColorOutput "  .\deploy.ps1 -Development       # Deploy development"
        Write-ColorOutput "  .\deploy.ps1 -Action stop       # Stop application"
        Write-ColorOutput "  .\deploy.ps1 -Action status     # Show status"
        Write-ColorOutput "  .\deploy.ps1 -Action logs       # Show logs"
        Write-ColorOutput "  .\deploy.ps1 -Action restart    # Restart application"
    }
}