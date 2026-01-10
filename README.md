Lift Log Cloud


## docker compose start:

`docker compose build`
`docker compose up -d`

### if migrations dont exist yet
`docker compose exec core flask db init     `
`docker compose exec core flask db migrate -m "init"`
`docker compose exec core flask db upgrade`

thats it. 

stopping it:
`docker compose down`
 
or stopping it + remove db data
`docker compose down -v`

to check status:
`docker compose ps`

## minikube start:

`minikube start`
`minikube addons enable metrics-server`

`minikube docker-env | Invoke-Expression`
`docker build -t liftlogcloud-core:latest ./app-service`
`docker build -t liftlogcloud-stats:latest ./stats-service`

`kubectl apply -f k8s/00-namespace.yaml`
`kubectl apply -f k8s/01-config.yaml`
`kubectl apply -f k8s/02-postgres.yaml`
`kubectl apply -f k8s/03-stats.yaml`
`kubectl apply -f k8s/04-core.yaml`
`kubectl apply -f k8s/05-hpa.yaml`

db migration (if not done already):

`kubectl -n liftlog get pods`
`kubectl -n liftlog exec -it <<CORE POD NAME>> -- flask db upgrade`

check db:
`kubectl -n liftlog exec -it <<POSTGRES POD NAME>> -- psql -U admin -d workouts -c "\dt"`

to access:
`minikube service -n liftlog core`

to stop:
`minikube stop`
or
`minikube delete`

to check status:
`kubectl top nodes`
`kubectl -n liftlog get pods`
`kubectl -n liftlog get svc`
`kubectl -n liftlog get hpa`



## To set the keys:

`kubectl -n liftlog delete secret liftlog-secrets`
`kubectl -n liftlog create secret generic liftlog-secrets --from-literal=TIMEZONEDB_API_KEY="TIMEZONE_KEY_HERE" --from-literal=SECRET_KEY="FLASK_KEY_HERE"`

`kubectl apply -f k8s/03-stats.yaml`
`kubectl -n liftlog rollout restart deployment stats`