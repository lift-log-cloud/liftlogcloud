# Lift Log Cloud
Cloud-native fitness tracking app 

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

*Note: API documentation for the stats microservice is available only via **internal access** on port `5001`. This port is not forwarded, so external access is **unavailable**.*

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

Services are isolated into separate containers
- Failure of the stats-service does not affect core functionality
- Kubernetes automatically restarts unhealthy pods
- Retry and timeout mechanisms are used for inter-service communication

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
