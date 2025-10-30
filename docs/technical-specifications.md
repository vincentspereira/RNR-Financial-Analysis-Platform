# Technical Specifications

## Overview

This document provides detailed technical specifications for the Financial Analysis Platform, including architecture, APIs, data models, and implementation standards.

## System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  React 18+  │  TypeScript  │  Redux Toolkit  │  Tailwind CSS   │
└─────────────────────────────────────────────────────────────────┘
                                │
                               HTTPS/WSS
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI  │  OAuth2  │  Rate Limiting  │  Request Validation   │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Microservices Layer                        │
├─────────────────────────────────────────────────────────────────┤
│ Auth │ Data │ Calculator │ Portfolio │ Scanner │ Report │ Audit  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                              │
├─────────────────────────────────────────────────────────────────┤
│ PostgreSQL │ Redis │ TimescaleDB │ File Storage │ External APIs │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend Services
- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **Authentication**: OAuth2 with JWT tokens
- **Database**: PostgreSQL 15+ with TimescaleDB extension
- **Cache**: Redis 7.0+
- **Task Queue**: Celery with Redis broker
- **Message Queue**: Redis Pub/Sub
- **Containerization**: Docker with multi-stage builds

#### Frontend Application
- **Runtime**: Node.js 18+
- **Framework**: React 18+ with TypeScript 5.0+
- **State Management**: Redux Toolkit with RTK Query
- **Styling**: Tailwind CSS 3.3+
- **Build Tool**: Vite 4.0+
- **Charts**: Chart.js 4.0+ with react-chartjs-2
- **UI Components**: Headless UI with custom components

#### Infrastructure & DevOps
- **Container Orchestration**: Kubernetes 1.28+
- **CI/CD**: GitHub Actions with self-hosted runners
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Secret Management**: HashiCorp Vault or AWS Secrets Manager
- **CDN**: CloudFlare
- **Load Balancer**: NGINX or AWS ALB

## Database Schema

### Core Database Schema

#### Users and Authentication
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    preferences JSONB DEFAULT '{}'
);

-- User sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Financial Data
```sql
-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap DECIMAL(20,2),
    employees INTEGER,
    description TEXT,
    website VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Financial statements (normalized)
CREATE TABLE financial_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    statement_type VARCHAR(20) NOT NULL, -- 'income', 'balance', 'cash_flow'
    period_type VARCHAR(20) NOT NULL,   -- 'quarterly', 'annual'
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    report_date DATE NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    data JSONB NOT NULL,                -- Statement data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, statement_type, period_type, fiscal_year, fiscal_quarter)
);

-- Financial ratios (calculated)
CREATE TABLE financial_ratios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    period_type VARCHAR(20) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    calculation_date DATE NOT NULL,
    -- Liquidity ratios
    current_ratio DECIMAL(10,6),
    quick_ratio DECIMAL(10,6),
    cash_ratio DECIMAL(10,6),
    -- Profitability ratios
    gross_profit_margin DECIMAL(10,6),
    operating_margin DECIMAL(10,6),
    net_profit_margin DECIMAL(10,6),
    roa DECIMAL(10,6),               -- Return on Assets
    roe DECIMAL(10,6),               -- Return on Equity
    -- Leverage ratios
    debt_to_equity DECIMAL(10,6),
    debt_to_assets DECIMAL(10,6),
    interest_coverage_ratio DECIMAL(10,6),
    -- Efficiency ratios
    asset_turnover DECIMAL(10,6),
    inventory_turnover DECIMAL(10,6),
    receivables_turnover DECIMAL(10,6),
    -- Valuation ratios
    pe_ratio DECIMAL(10,6),
    pb_ratio DECIMAL(10,6),
    ps_ratio DECIMAL(10,6),
    ev_ebitda DECIMAL(10,6),
    -- Growth rates
    revenue_growth DECIMAL(10,6),
    earnings_growth DECIMAL(10,6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, period_type, fiscal_year, fiscal_quarter)
);

-- Market data
CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    price_date DATE NOT NULL,
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4) NOT NULL,
    adjusted_close DECIMAL(15,4),
    volume BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, price_date)
);
```

#### Portfolios and User Data
```sql
-- Portfolios
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_value DECIMAL(20,2) DEFAULT 0,
    cash_balance DECIMAL(20,2) DEFAULT 0
);

-- Portfolio holdings
CREATE TABLE portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id),
    symbol VARCHAR(10) NOT NULL,
    shares DECIMAL(15,6) NOT NULL,
    average_cost DECIMAL(15,4) NOT NULL,
    first_purchase_date DATE NOT NULL,
    last_purchase_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, company_id)
);

-- Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id),
    company_id UUID REFERENCES companies(id),
    transaction_type VARCHAR(20) NOT NULL, -- 'buy', 'sell', 'dividend'
    shares DECIMAL(15,6) NOT NULL,
    price DECIMAL(15,4) NOT NULL,
    total_amount DECIMAL(20,2) NOT NULL,
    transaction_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Watchlists
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Watchlist items
CREATE TABLE watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(watchlist_id, company_id)
);
```

## API Specifications

### REST API Design Standards

#### Base URL Structure
```
Production: https://api.financial-analysis.com/v1
Development: http://localhost:8000/v1
```

#### Response Format Standards
```json
{
    "success": true,
    "data": {
        // Response data
    },
    "message": "Operation completed successfully",
    "timestamp": "2025-10-30T10:30:00Z",
    "request_id": "uuid-here"
}
```

#### Error Response Format
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": [
            {
                "field": "email",
                "message": "Invalid email format"
            }
        ]
    },
    "timestamp": "2025-10-30T10:30:00Z",
    "request_id": "uuid-here"
}
```

### Authentication API

#### POST /auth/register
```json
// Request
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
}

// Response 201
{
    "success": true,
    "data": {
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_verified": false
        }
    },
    "message": "User registered successfully"
}
```

#### POST /auth/login
```json
// Request
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}

// Response 200
{
    "success": true,
    "data": {
        "access_token": "jwt-token-here",
        "refresh_token": "refresh-token-here",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
    }
}
```

### Company Data API

#### GET /companies
```json
// Query Parameters
{
    "search": "Apple",
    "sector": "Technology",
    "exchange": "NASDAQ",
    "limit": 20,
    "offset": 0
}

// Response 200
{
    "success": true,
    "data": {
        "companies": [
            {
                "id": "uuid",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": 2800000000000,
                "current_price": 178.45
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0
    }
}
```

#### GET /companies/{symbol}/financials
```json
// Query Parameters
{
    "period": "annual",
    "years": 5
}

// Response 200
{
    "success": true,
    "data": {
        "company": {
            "symbol": "AAPL",
            "name": "Apple Inc."
        },
        "financial_statements": [
            {
                "period_type": "annual",
                "fiscal_year": 2023,
                "income_statement": {
                    "revenue": 383285000000,
                    "gross_profit": 169148000000,
                    "operating_income": 114301000000,
                    "net_income": 99803000000
                },
                "balance_sheet": {
                    "total_assets": 352583000000,
                    "total_liabilities": 290437000000,
                    "shareholders_equity": 62146000000
                },
                "cash_flow_statement": {
                    "operating_cash_flow": 114061000000,
                    "investing_cash_flow": -37844000000,
                    "financing_cash_flow": -108945000000
                }
            }
        ]
    }
}
```

### Financial Ratios API

#### GET /companies/{symbol}/ratios
```json
// Query Parameters
{
    "period": "quarterly",
    "years": 2
}

// Response 200
{
    "success": true,
    "data": {
        "symbol": "AAPL",
        "ratios": [
            {
                "period_type": "quarterly",
                "fiscal_year": 2023,
                "fiscal_quarter": 4,
                "liquidity_ratios": {
                    "current_ratio": 1.73,
                    "quick_ratio": 1.67,
                    "cash_ratio": 0.89
                },
                "profitability_ratios": {
                    "gross_profit_margin": 0.4412,
                    "operating_margin": 0.2982,
                    "net_profit_margin": 0.2604,
                    "roa": 0.2261,
                    "roe": 1.4742
                },
                "leverage_ratios": {
                    "debt_to_equity": 1.7304,
                    "debt_to_assets": 0.6339,
                    "interest_coverage_ratio": 27.45
                },
                "valuation_ratios": {
                    "pe_ratio": 29.85,
                    "pb_ratio": 46.17,
                    "ps_ratio": 7.88,
                    "ev_ebitda": 21.34
                }
            }
        ]
    }
}
```

### Portfolio API

#### GET /portfolios
```json
// Response 200
{
    "success": true,
    "data": {
        "portfolios": [
            {
                "id": "uuid",
                "name": "Growth Portfolio",
                "description": "Long-term growth investments",
                "total_value": 125750.50,
                "cash_balance": 2500.00,
                "holdings_count": 15,
                "day_change": 1250.75,
                "day_change_percent": 1.01,
                "created_at": "2023-01-15T10:30:00Z"
            }
        ]
    }
}
```

#### POST /portfolios/{id}/transactions
```json
// Request
{
    "transaction_type": "buy",
    "symbol": "AAPL",
    "shares": 100,
    "price": 178.45,
    "transaction_date": "2025-10-30",
    "notes": "Fundamental analysis shows strong growth"
}

// Response 201
{
    "success": true,
    "data": {
        "transaction": {
            "id": "uuid",
            "transaction_type": "buy",
            "symbol": "AAPL",
            "shares": 100,
            "price": 178.45,
            "total_amount": 17845.00,
            "transaction_date": "2025-10-30"
        },
        "updated_portfolio": {
            "total_value": 143595.50,
            "cash_balance": -15345.00
        }
    }
}
```

## WebSocket Specifications

### Real-time Data Connection

#### Connection Endpoint
```
Production: wss://api.financial-analysis.com/ws
Development: ws://localhost:8000/ws
```

#### Authentication
```javascript
// After WebSocket connection
{
    "type": "auth",
    "token": "jwt-token-here"
}

// Response
{
    "type": "auth_success",
    "user_id": "uuid"
}
```

#### Real-time Price Updates
```javascript
// Subscribe to symbol
{
    "type": "subscribe",
    "channel": "prices",
    "symbols": ["AAPL", "MSFT", "GOOGL"]
}

// Price update message
{
    "type": "price_update",
    "symbol": "AAPL",
    "price": 178.52,
    "change": 0.07,
    "change_percent": 0.0392,
    "volume": 52341789,
    "timestamp": "2025-10-30T14:30:15Z"
}
```

#### Portfolio Updates
```javascript
// Subscribe to portfolio
{
    "type": "subscribe",
    "channel": "portfolio",
    "portfolio_id": "uuid"
}

// Portfolio update message
{
    "type": "portfolio_update",
    "portfolio_id": "uuid",
    "total_value": 143620.25,
    "day_change": 1275.50,
    "day_change_percent": 0.894,
    "timestamp": "2025-10-30T14:30:15Z"
}
```

## Performance Requirements

### Response Time Requirements
- **API Endpoints**: <500ms (95th percentile)
- **Database Queries**: <200ms (average)
- **Real-time Updates**: <100ms
- **Report Generation**: <30 seconds
- **Data Ingestion**: <5 minutes per 1000 records

### Throughput Requirements
- **Concurrent Users**: 10,000
- **API Requests/Second**: 1,000
- **Database Connections**: 100
- **WebSocket Connections**: 5,000

### Availability Requirements
- **Uptime**: 99.9% (8.76 hours downtime/year)
- **Data Freshness**: 15 seconds for market data
- **Backup Recovery**: 4 hours RTO, 1 hour RPO

## Security Specifications

### Authentication & Authorization
- **OAuth2**: Authorization Code Flow with PKCE
- **JWT Tokens**: RS256 signing, 15-minute access tokens
- **Multi-Factor Authentication**: TOTP-based optional MFA
- **Role-Based Access Control**: Admin, Premium, Basic roles

### Data Protection
- **Encryption at Rest**: AES-256 for all sensitive data
- **Encryption in Transit**: TLS 1.3 for all communications
- **Data Masking**: PII data masked in logs
- **Key Rotation**: Automatic every 90 days

### Compliance Requirements
- **GDPR**: Right to deletion, data portability
- **SOX**: Audit trails for financial data changes
- **PCI-DSS**: Payment card security (if applicable)
- **SEC**: Financial reporting requirements

## Monitoring & Observability

### Application Monitoring
```yaml
# Prometheus metrics configuration
metrics:
  - name: api_requests_total
    type: counter
    labels: [method, endpoint, status_code]

  - name: api_request_duration_seconds
    type: histogram
    buckets: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

  - name: database_connections_active
    type: gauge

  - name: websocket_connections_active
    type: gauge
```

### Logging Standards
```json
{
    "timestamp": "2025-10-30T10:30:00.123Z",
    "level": "INFO",
    "service": "financial-calculator",
    "request_id": "uuid-here",
    "user_id": "uuid-here",
    "message": "Financial ratios calculated successfully",
    "duration_ms": 245,
    "metadata": {
        "symbol": "AAPL",
        "period": "quarterly",
        "ratios_count": 25
    }
}
```

### Health Checks
```yaml
# Health check endpoints
health_checks:
  - endpoint: /health
    checks:
      - database_connection
      - redis_connection
      - external_api_status

  - endpoint: /health/detailed
    checks:
      - database_performance
      - cache_hit_ratio
      - memory_usage
      - disk_space
      - cpu_usage
```

## Deployment Specifications

### Container Specifications

#### Backend Service Container
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Application Container
```dockerfile
# Build stage
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Kubernetes Specifications

#### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: financial-analysis-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: financial-analysis-backend
  template:
    metadata:
      labels:
        app: financial-analysis-backend
    spec:
      containers:
      - name: backend
        image: financial-analysis/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

**Document Version**: 1.0
**Created**: October 30, 2025
**Last Updated**: October 30, 2025
**Next Review**: November 30, 2025