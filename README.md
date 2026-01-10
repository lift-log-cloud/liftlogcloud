# Lift Log Cloud
Cloud-native fitness tracking app 

## Repo Branching Strategy

The project uses a simple branching strategy:
- **master** – stable branch containing production-ready code
- **dev** – development branch used for ongoing development and experimentation

New features and changes are implemented in the `dev` branch and merged into `master` once they are stable.


## 1. Overview

LiftLogCloud is a cloud-native web application for tracking strength training workouts.
The system is implemented using a **microservices architecture**, containerized with
**Docker**, orchestrated with **Kubernetes (k3s)**, and backed by a
**PostgreSQL** database.

The application allows users to:
- Register and log in
- Add exercises and workouts
- View workouts in a calendar view
- Analyze training statistics over time
- View one rep max (1RM) progression over time
- Access the application in a scalable, cloud-native environment

---

## 2. Architecture

The application consists of the following components:

### 2.1 Core Service (app-service)
- Handles authentication and user sessions
- Manages workouts and exercises (write operations)
- Serves the UI
- Acts as a proxy to the stats-service for analytics data
- Exposes REST endpoints and HTML pages

### 2.2 Stats Service (stats-service)
- Provides read-only statistics and analytics
- Aggregates workout data
- Integrates an external API for time and timezone data
- Exposes REST endpoints used by the core service

### 2.3 Database
- PostgreSQL relational database
- Shared by both microservices
- Database schema managed via Alembic migrations

---

## 3. Technology Stack

| Component        | Technology |
|------------------|------------|
| Backend          | Python, Flask |
| Database         | PostgreSQL |
| ORM              | SQLAlchemy |
| Migrations       | Alembic / Flask-Migrate |
| Containers       | Docker, Docker Compose |
| Orchestration    | Kubernetes (Minikube, k3s) |
| API Documentation| Swagger (Flasgger) |
| CI/CD            | GitHub repository |
| External API     | TimeZoneDB |

---


## 4. Project Structure
```
LiftLogCloud/
├── app-service/
│ ├── app.py
│ ├── requirements.txt
│ ├── Dockerfile
│ ├── migrations/
│ ├── templates/
│ └── static/
│
├── stats-service/
│ ├── app.py
│ ├── requirements.txt
│ └── Dockerfile
│
├── k8s/
│ ├── 00-namespace.yaml
│ ├── 01-config.yaml
│ ├── 01-secrets.template.yaml
│ ├── 02-postgres.yaml
│ ├── 03-stats.yaml
│ ├── 04-core.yaml
│ └── 05-hpa.yaml
│
├── docker-compose.yml
└── README.md
```

---

## 5. Configuration and Secrets

Sensitive configuration values/keys are **not committed to Git**.

### Secrets (Kubernetes)
- `SECRET_KEY`
- `TIMEZONEDB_API_KEY`

Stored as Kubernetes Secrets:

```bash
kubectl -n liftlog create secret generic liftlog-secrets --from-literal=SECRET_KEY="SECRET_KEY" --from-literal=TIMEZONEDB_API_KEY="TIMEZONEDB_API_KEY"
```

---

## 6. Health Checks

Both microservices expose health endpoints:

| Service | Endpoint  |
| ------- | --------- |
| Core    | `/health` |
| Stats   | `/health` |


Kubernetes monitors these endpoints using:
- livenessProbe
- readinessProbe

This enables automatic restarts and fault detection.

---

## 7. API Documentation

API documentation is generated using Swagger(Flasgger).

Swagger UI Endpoints


| Service | Endpoint  |
| ------- | --------- |
| Core    | `/apidocs/` |
| Stats   | `/apidocs/` |

**Note:**  
API documentation for the **stats microservice** is exposed **only internally** within the Kubernetes cluster.  
To access the Swagger UI for the stats service, a **port-forward** must be created:

```bash
kubectl -n liftlog port-forward svc/stats 5001:5000 --address 0.0.0.0
```
This is not permenant, its a debug/admin tool.


The documentation includes:
- Endpoint descriptions
- Request and response formats
- Example payloads
- Error responses

---

## 8. Deployment
### 8.1 Local Development (via Docker Compose)
```
docker compose build
docker compose up -d
```

Access:
- Core UI: `http://localhost:25590`
- Stats API: `http://localhost:5001`

If migrations dont exist yet:
```
docker compose exec core flask db init     
docker compose exec core flask db migrate -m "init"
docker compose exec core flask db upgrade
docker cp liftlogcloud-core-1:/app/migrations ./app-service/migrations
```


---

### 8.2 Kubernetes (Minikube / k3s)

```
kubectl create namespace liftlog
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-config.yaml
kubectl apply -f k8s/02-postgres.yaml
kubectl apply -f k8s/03-stats.yaml
kubectl apply -f k8s/04-core.yaml
kubectl apply -f k8s/05-hpa.yaml
```

Secrets:

```
kubectl -n liftlog create secret generic liftlog-secrets --from-literal=SECRET_KEY="SECRET_KEY" --from-literal=TIMEZONEDB_API_KEY="TIMEZONEDB_API_KEY"
```

Restart after adding secrets:
```
kubectl -n liftlog rollout restart deploy/core
kubectl -n liftlog rollout restart deploy/stats
```

Check status:

```
kubectl -n liftlog get pods
kubectl -n liftlog get svc
kubectl -n liftlog get hpa
```

The core service is exposed via:
- `LoadBalancer` on port `25590`

Database migrations are applied using:
```
kubectl -n liftlog exec deploy/core -- flask db upgrade
```

To check if migrations were applied correctly you can view tables using:

```
kubectl -n liftlog exec -it deploy/postgres -- psql -U admin -d workouts -c "\dt"
```

Rebuilding and restarting if necessary:
```bash
# rebuild
docker build -t liftlogcloud-core:latest ./app-service
docker build -t liftlogcloud-stats:latest ./stats-service
# reapply
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-config.yaml
kubectl apply -f k8s/02-postgres.yaml
kubectl apply -f k8s/03-stats.yaml
kubectl apply -f k8s/04-core.yaml
kubectl apply -f k8s/05-hpa.yaml

# dont forget the secrets
kubectl -n liftlog create secret generic liftlog-secrets --from-literal=SECRET_KEY="SECRET_KEY" --from-literal=TIMEZONEDB_API_KEY="TIMEZONEDB_API_KEY"

# restart
kubectl -n liftlog rollout restart deployment core
kubectl -n liftlog rollout restart deployment stats
```

---

## 9. Cloud-Native Concepts

The project follows cloud-native best practices:
- Stateless microservices
- Container-based deployment
- Kubernetes orchestration
- Health checks and probes
- Externalized configuration
- Horizontal scalability
- Service isolation

---

## 11. Fault Isolation and Resilience

To ensure fault tolerance and service isolation, the application implements **resilience patterns** in the core microservice when communicating with the stats microservice.

### Implemented Mechanisms

- **Retry**  
  All proxy calls from the core service to the stats service use automatic retries with exponential backoff.  
  This mitigates transient network issues and temporary service overload.

- **Circuit Breaker**  
  A circuit breaker is used to monitor consecutive failures of the stats service.  
  After 5 failed requests, the circuit **OPENS** and blocks further requests for a cooldown period (30s).

- **Graceful Degradation (Fallbacks)**  
  When the stats service is unavailable or the circuit breaker is open, the core service returns **fallback responses** instead of failing:
  - The user interface remains responsive.
  - Non-critical features (statistics) degrade gracefully.
  - Core functionality (calendar, adding workouts, authentication) remains fully operational.

### Service Isolation

The stats microservice is isolated from the core service:
- Failures in the stats service do **not cascade** to the core service.
- The core service continues to serve user requests even if the stats service is unavailable.

### Demonstration of Resilience

Resilience can be observed by stopping the stats service:
- Requests to statistics endpoints return fallback responses.
- The circuit breaker state can be inspected via the `/resilience` endpoint.
- After the cooldown period, the system automatically attempts recovery.

Simulate stats service crash:
```
kubectl -n liftlog scale deployment stats --replicas=0
```

When done scale it back:
```
kubectl -n liftlog scale deployment stats --replicas=1
```

---

## 11. Setup and Prerequisites for Developers

Prerequisites:
- Docker
- Docker Compose
- kubectl
- Minikube or k3s
- git

Setup:
```
gh repo clone NicX02/LiftLogCloud 
cd LiftLogCloud
docker compose up -d
```
