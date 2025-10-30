# MicroTaskHub
User name and password : admin and changeme
MicroTaskHub is a microservice sample application that ships ready to run on Kubernetes. It contains:
- **User Service** – FastAPI CRUD API whose data lives in PostgreSQL
- **Task Service** – FastAPI API that stores work items and calls the User Service to validate task assignees
- **Frontend** – Node/Express UI that proxies requests to the APIs after handling lightweight login
- **PostgreSQL** – StatefulSet-backed database with persistent storage

## Repository Layout
```
MicroTaskHub/
├── services/              # Source for the frontend, task-service, and user-service containers
├── k8s/                   # Kubernetes namespace, secrets, deployments, ingress, and HPA definitions
├── docs/                  # Architecture, system design, and API reference notes
├── build-push-images.sh   # Helper script to build and push all service images
└── README.md
```

## Deploy to Kubernetes
The manifests are designed to be applied as a unit with Kustomize. Use the steps below to bring up the full stack.

### 1. Prerequisites
- Docker (only required if you plan to build fresh images)
- `kubectl` should be installed
- A Kubernetes cluster with an Ingress controller (nginx is assumed by default)
- Access to an OCI registry (e.g., Docker Hub) if you want to publish custom images

### 2. Build and Publish Images (optional)
The manifests reference prebuilt images hosted at `docker.io/maneeshakanagiri/...:1.0.0`. If you prefer to publish your own:
```bash
./build-push-images.sh <docker-username>
```
Update the `image:` fields in `k8s/user-service.yaml`, `k8s/task-service.yaml`, and `k8s/frontend.yaml` to match the pushed tags.

### 3. Configure Secrets and Settings
Secrets are stored as base64-encoded values in `k8s/app-secrets.yaml` and `k8s/postgres.yaml`. Adjust them before deployment:
- `API_AUTH_TOKEN` – shared bearer token that protects both APIs and the frontend login flow
- `FRONTEND_AUTH_USERNAME` / `FRONTEND_AUTH_PASSWORD` – credentials required to obtain the bearer token through the UI
- `*_DATABASE_URL` – SQLAlchemy connection strings that target the in-cluster PostgreSQL StatefulSet

If your cluster uses a different storage class, update `storageClassName` inside `k8s/postgres.yaml`.

The ingress host defaults to `microtaskhub.com`. Change the host name in `k8s/ingress.yaml` if you want to use a different domain.

### 4. Deploy the Stack
```bash
kubectl apply -f k8s for each file
```

### 5. Verify Rollout
```bash
kubectl get pods -n microtaskhub
kubectl get svc -n microtaskhub
kubectl get ingress -n microtaskhub
```
All pods should reach the `Running` status and the ingress should surface the hostname you configured.

### 6. Access the Application
- **With ingress** – Point the hostname (default `microtaskhub.com`) to your ingress controller. For local clusters you can add an entry to `/etc/hosts`, e.g. `127.0.0.1 microtaskhub.com`. Browse to `http://microtaskhub.com` and sign in with the credentials stored in `k8s/app-secrets.yaml`.
- **Without ingress** – Temporarily port-forward the frontend service and use the same credentials:
  ```bash
  kubectl port-forward -n microtaskhub svc/frontend 8080:80
  ```
  Then browse to `http://localhost:8080`.

### 7. Tear Down
```bash
kubectl delete -k k8s
```

## Configuration Notes
- Each API exposes `/health` for liveness/readiness probes; the frontend uses `/health` as well.
- `k8s/hpa.yaml` enables Horizontal Pod Autoscaling for both FastAPI deployments with a target CPU utilization of 70%.
- The `frontend` deployment reads `USER_SERVICE_URL` and `TASK_SERVICE_URL`; by default they point at the internal cluster services.
- The PostgreSQL StatefulSet uses a headless ClusterIP service so the connection string resolves to `postgres.microtaskhub.svc.cluster.local`.
- Rotate the shared bearer token regularly or integrate with an external secret manager for production use.

## Additional Documentation
- `docs/system-design.md` – detailed component behavior

For questions or enhancements, review the manifests under `k8s/` and adjust resource limits, autoscaling settings, or ingress policies to match your environment.s
