# Graph Report - .  (2026-04-26)

## Corpus Check
- 10 files · ~5,000 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 87 nodes · 112 edges · 13 communities detected
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Application & DB Alert Rules|Application & DB Alert Rules]]
- [[_COMMUNITY_Backend K8s Deployment|Backend K8s Deployment]]
- [[_COMMUNITY_Database & Secrets Config|Database & Secrets Config]]
- [[_COMMUNITY_Monitoring Stack Containers|Monitoring Stack Containers]]
- [[_COMMUNITY_Grafana Dashboards & Panels|Grafana Dashboards & Panels]]
- [[_COMMUNITY_Ingress & Frontend Routing|Ingress & Frontend Routing]]
- [[_COMMUNITY_Nginx Reverse Proxy|Nginx Reverse Proxy]]
- [[_COMMUNITY_Database Init & Extensions|Database Init & Extensions]]
- [[_COMMUNITY_PostgreSQL Monitoring|PostgreSQL Monitoring]]
- [[_COMMUNITY_Redis Monitoring|Redis Monitoring]]
- [[_COMMUNITY_Node Exporter Metrics|Node Exporter Metrics]]
- [[_COMMUNITY_Alertmanager Defaults|Alertmanager Defaults]]
- [[_COMMUNITY_Disk Space Alerts|Disk Space Alerts]]

## God Nodes (most connected - your core abstractions)
1. `Backend Service (K8s)` - 20 edges
2. `Backend Deployment (K8s)` - 11 edges
3. `Frontend Deployment (K8s)` - 11 edges
4. `Grafana Prometheus Datasource` - 11 edges
5. `Backend Container` - 9 edges
6. `Prometheus Container` - 8 edges
7. `Alertmanager Container` - 6 edges
8. `PostgreSQL Service (K8s)` - 5 edges
9. `Redis Service (K8s)` - 5 edges
10. `Frontend Container` - 5 edges

## Surprising Connections (you probably didn't know these)
- `HTTP Request Rate Panel` --references--> `Backend Service (K8s)`  [INFERRED]
  monitoring/grafana/dashboards/platform-overview.json → kubernetes/production/backend-deployment.yaml
- `Error Rate Panel` --references--> `Backend Service (K8s)`  [INFERRED]
  monitoring/grafana/dashboards/platform-overview.json → kubernetes/production/backend-deployment.yaml
- `Response Time P95/P99 Panel` --references--> `Backend Service (K8s)`  [INFERRED]
  monitoring/grafana/dashboards/platform-overview.json → kubernetes/production/backend-deployment.yaml
- `Nginx Backend Upstream` --references--> `Backend Service (K8s)`  [EXTRACTED]
  nginx/nginx.conf → kubernetes/production/backend-deployment.yaml
- `Postgres Exporter` --shares_data_with--> `PostgreSQL Service (K8s)`  [INFERRED]
  monitoring/prometheus.yml → kubernetes/production/backend-deployment.yaml

## Hyperedges (group relationships)
- **Monitoring Pipeline (Prometheus -> Grafana + Alertmanager)** — monitoring_prometheus_container, monitoring_grafana_container, monitoring_alertmanager_container [EXTRACTED 1.00]
- **Production K8s Stack (Frontend -> Backend -> DB + Redis)** — frontend_deployment, backend_deployment, postgres_service_k8s, redis_service_k8s [EXTRACTED 1.00]
- **Platform Overview Dashboard Panels** — grafana_panel_http_request_rate, grafana_panel_error_rate, grafana_panel_websocket_connections, grafana_panel_response_time, grafana_panel_db_connections, grafana_panel_redis_memory, grafana_panel_cpu_usage, grafana_panel_memory_usage [EXTRACTED 1.00]
- **Prometheus Alert Rules** — alert_application_down, alert_high_error_rate, alert_critical_error_rate, alert_high_response_time, alert_db_slow_queries, alert_high_cpu, alert_high_memory, alert_pod_crashloop, alert_db_connections_high, alert_db_down, alert_redis_down, alert_redis_memory_high, alert_ml_prediction_failures, alert_report_gen_failures, alert_websocket_high, alert_failed_logins, alert_suspicious_activity, alert_disk_space, alert_lb_down, alert_sla_violation [EXTRACTED 1.00]
- **Nginx Reverse Proxy to Backend** — nginx_upstream_backend, nginx_standalone_config, backend_service [EXTRACTED 1.00]
- **Frontend Pod Nginx Proxy to Backend Service** — frontend_container, frontend_nginx_config, backend_service [EXTRACTED 1.00]
- **Prometheus Scrape Targets** — prometheus_scrape_backend, prometheus_scrape_frontend, prometheus_scrape_postgres, prometheus_scrape_redis, prometheus_scrape_nginx, prometheus_scrape_node [EXTRACTED 1.00]
- **Grafana Datasources** — grafana_ds_prometheus, grafana_ds_postgresql, grafana_ds_redis [EXTRACTED 1.00]

## Communities

### Community 0 - "Application & DB Alert Rules"
Cohesion: 0.16
Nodes (15): Alert: CriticalErrorRate, Alert: DatabaseSlowQueries, Alert: HighFailedLoginAttempts, Alert: HighErrorRate, Alert: HighResponseTime, Alert: MLModelPredictionFailures, Alert: ReportGenerationFailures, Alert: SLAViolation (+7 more)

### Community 1 - "Backend K8s Deployment"
Cohesion: 0.2
Nodes (14): Alert: HighCPUUsage, Alert: HighMemoryUsage, Alert: PodCrashLooping, Backend Deployment (K8s), Backend HPA, Backend NetworkPolicy, Backend PodDisruptionBudget, Backend ServiceAccount (+6 more)

### Community 2 - "Database & Secrets Config"
Cohesion: 0.24
Nodes (11): App Secret (K8s), Backend ConfigMap, Backend Container, financial_analysis Database, Database Secret (K8s), Grafana PostgreSQL Datasource, Grafana Redis Datasource, PostgreSQL Service (K8s) (+3 more)

### Community 3 - "Monitoring Stack Containers"
Cohesion: 0.27
Nodes (11): Alertmanager Configuration, Alertmanager Data Volume, Grafana Data Volume, Platform Overview Dashboard, Alertmanager Container, Grafana Container, Monitoring Docker Network, Prometheus Container (+3 more)

### Community 4 - "Grafana Dashboards & Panels"
Cohesion: 0.22
Nodes (9): Grafana Prometheus Datasource, CPU Usage by Pod Panel, Database Connections Panel, Error Rate Panel, HTTP Request Rate Panel, Memory Usage by Pod Panel, Redis Memory Panel, Response Time P95/P99 Panel (+1 more)

### Community 5 - "Ingress & Frontend Routing"
Cohesion: 0.4
Nodes (6): Alert: ApplicationDown, Alert: LoadBalancerDown, Critical Alert Receiver, Backend Ingress, Frontend Ingress, Frontend Service (K8s)

### Community 6 - "Nginx Reverse Proxy"
Cohesion: 0.4
Nodes (5): Nginx Exporter, Nginx SSL Configuration, Standalone Nginx Configuration, Nginx Backend Upstream, Nginx Exporter Scrape Job

### Community 7 - "Database Init & Extensions"
Cohesion: 0.5
Nodes (4): pg_trgm Extension, uuid-ossp Extension, Database Init Script, financial_app DB Role

### Community 8 - "PostgreSQL Monitoring"
Cohesion: 0.5
Nodes (4): Alert: DatabaseConnectionsHigh, Alert: DatabaseDown, Postgres Exporter, Postgres Exporter Scrape Job

### Community 9 - "Redis Monitoring"
Cohesion: 0.5
Nodes (4): Alert: RedisDown, Alert: RedisMemoryHigh, Redis Exporter Scrape Job, Redis Exporter

### Community 10 - "Node Exporter Metrics"
Cohesion: 1.0
Nodes (2): Node Exporter, Node Exporter Scrape Job

### Community 11 - "Alertmanager Defaults"
Cohesion: 1.0
Nodes (1): Default Alert Receiver

### Community 12 - "Disk Space Alerts"
Cohesion: 1.0
Nodes (1): Alert: DiskSpaceHigh

## Knowledge Gaps
- **41 isolated node(s):** `uuid-ossp Extension`, `pg_trgm Extension`, `Backend HPA`, `Backend ConfigMap`, `Backend ServiceAccount` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Node Exporter Metrics`** (2 nodes): `Node Exporter`, `Node Exporter Scrape Job`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Alertmanager Defaults`** (1 nodes): `Default Alert Receiver`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Disk Space Alerts`** (1 nodes): `Alert: DiskSpaceHigh`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Backend Service (K8s)` connect `Application & DB Alert Rules` to `Backend K8s Deployment`, `Database & Secrets Config`, `Grafana Dashboards & Panels`, `Ingress & Frontend Routing`, `Nginx Reverse Proxy`?**
  _High betweenness centrality (0.615) - this node is a cross-community bridge._
- **Why does `Backend Container` connect `Database & Secrets Config` to `Application & DB Alert Rules`, `Backend K8s Deployment`?**
  _High betweenness centrality (0.338) - this node is a cross-community bridge._
- **Why does `Grafana Prometheus Datasource` connect `Grafana Dashboards & Panels` to `Monitoring Stack Containers`?**
  _High betweenness centrality (0.307) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Backend Service (K8s)` (e.g. with `HTTP Request Rate Panel` and `Error Rate Panel`) actually correct?**
  _`Backend Service (K8s)` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `uuid-ossp Extension`, `pg_trgm Extension`, `Backend HPA` to the rest of the system?**
  _41 weakly-connected nodes found - possible documentation gaps or missing edges._