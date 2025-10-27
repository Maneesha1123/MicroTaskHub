# MicroTaskHub System Design

## 1. Solution Overview
MicroTaskHub is a microservice-based task coordination application. It allows teams to create users, define tasks, and manage progress through a lightweight web interface. A Node.js frontend serves the user experience and proxies API calls to two FastAPI services. Persistent data is stored in PostgreSQL, and the full stack is intended to run on Kubernetes using configuration-as-code manifests.

### Key Capabilities
- Create, update, and delete users, with safeguards preventing removal while tasks are in progress.
- Manage tasks through their lifecycle, including status transitions and deletion restrictions until completion.
- Authenticate browser sessions through a shared bearer token distributed via the frontend login form.
- Deploy reproducibly to Kubernetes using manifests in `k8s/`, with secrets, horizontal scaling hooks, and ingress routing pre-defined.

## 2. Architecture Design
### 2.1 Component Catalogue
| Component | Type | Responsibilities | Implementation | Kubernetes Workload |
| --- | --- | --- | --- | --- |
| Frontend | UI + gateway | Serves static SPA, handles login, forwards authenticated API calls to backend services, enforces CORS-free access | Node.js + Express (`services/frontend`) | `k8s/frontend.yaml` Deployment + Service |
| User Service | Domain API | Manages user records, enforces unique emails, exposes CRUD endpoints, blocks deletion when tasks are active | FastAPI + SQLAlchemy (`services/user-service`) | `k8s/user-service.yaml` Deployment + Service |
| Task Service | Domain API | Manages task lifecycle, validates assignees against User Service, filters tasks by assignee/status | FastAPI + SQLAlchemy (`services/task-service`) | `k8s/task-service.yaml` Deployment + Service |
| PostgreSQL | Persistence | Stores user and task data, provides durable state across pod restarts | PostgreSQL 15 (`k8s/postgres.yaml`) | StatefulSet + headless Service |
| Ingress | Edge routing | Directs `/users`, `/tasks`, and `/` paths to the correct services | NGINX ingress (`k8s/ingress.yaml`) | Ingress resource |
| Autoscalers | Operations | Demonstrates CPU-based horizontal scaling of API services | Kubernetes HPA (`k8s/hpa.yaml`) | HorizontalPodAutoscaler |

### 2.2 Interactions & Patterns
1. **Ingress Routing**: External requests land on NGINX ingress and are routed by path to the frontend or API services.
2. **Frontend Proxy**: The frontend authenticates users and forwards API calls with the shared bearer token to maintain a single origin for browsers.
3. **User Service**: Provides REST endpoints for creating, updating, listing, and deleting users. Deletion is guarded by a synchronous check to the Task Service.
4. **Task Service**: Handles task CRUD, validates assignee IDs via User Service calls, and blocks deletion unless a task is completed.
5. **PostgreSQL Storage**: Both services persist entities in shared tables managed via SQLAlchemy models.

### 2.3 Architecture Principles
- **Microservices & Bounded Contexts**: Users and tasks live in separate services, each deployed and scaled independently.
- **API Gateway Pattern**: The combination of ingress and frontend proxy centralises external access, reducing CORS complexity.
- **Stateless Services with Stateful Backing**: Application pods remain stateless, relying on Kubernetes secrets and config; only PostgreSQL maintains persistent state.
- **Configuration as Code**: Kubernetes manifests act as the canonical definition for deployments, secrets, ingress, and autoscaling.
- **Security by Default**: Shared bearer tokens protect API access; frontend login is mandatory before data interactions.

## 3. Component-to-Microservice Mapping
| Functional Area | Microservice / Module | Container Image | Kubernetes Resource |
| --- | --- | --- | --- |
| Web experience & auth | `services/frontend` | `microtaskhub-frontend` | `k8s/frontend.yaml` |
| User management | `services/user-service` | `microtaskhub-user-service` | `k8s/user-service.yaml` |
| Task management | `services/task-service` | `microtaskhub-task-service` | `k8s/task-service.yaml` |
| Persistence | `postgres` | `postgres:15-alpine` | `k8s/postgres.yaml` |
| Platform routing & scaling | Ingress, HPA | N/A | `k8s/ingress.yaml`, `k8s/hpa.yaml`, `k8s/kustomization.yaml` |

## 4. Benefits
- **Independent Scaling**: Each API has its own deployment and optional HPA, allowing targeted scale-out based on workload.
- **Clear Ownership**: Bounded contexts reduce coupling; teams can evolve user and task logic independently.
- **Operational Simplicity**: Stateless services with health probes simplify rolling updates, and manifests capture desired state declaratively.
- **Extensibility**: Adding new services or analytics pipelines is straightforward using the same ingress and secret patterns.
- **Security Baseline**: Mandatory login and bearer tokens prevent anonymous API access in demo environments.

## 5. Challenges & Mitigations
| Challenge | Impact | Mitigation Strategies |
| --- | --- | --- |
| Cross-service dependency (Task → User) | User Service downtime blocks task operations | Keep services co-located, add retries/circuit breakers, explore asynchronous validation via messaging |
| Shared database across services | Schema changes can create cross-team friction | Adopt database migrations, enforce schema governance, consider splitting schemas if domains diverge |
| Secret management | Kubernetes secrets are base64 encoded only | Restrict RBAC, enable etcd encryption, integrate SealedSecrets or cloud secret managers |
| Minimal auth model | Shared token lacks user-level access control | Extend to OIDC/OAuth with per-user tokens, implement role-based checks in services |
| Network exposure | Ingress is HTTP-only by default | Terminate TLS at ingress, enforce HTTPS redirects, optionally add WAF capabilities |
| Observability gaps | Limited visibility into latency and errors | Add structured logging, distributed tracing (OpenTelemetry), and metrics exporters |

## 6. Security Considerations
- **Bearer Token Gatekeeping**: Both services require a shared token supplied through `k8s/app-secrets.yaml`; the frontend login form issues it to authenticated sessions.
- **Secrets Distribution**: Database URLs, auth tokens, and service base URLs are injected via Kubernetes secrets, keeping sensitive data out of images and source.
- **Runtime Hardening**: Health probes, resource limits, and non-root containers (where supported) reduce risk from noisy neighbors and unhealthy pods.
- **Future Enhancements**:
  - Enforce TLS and mutual auth for inter-service communication (Service Mesh or mTLS).
  - Add `NetworkPolicy` resources to limit database access solely to API pods.
  - Implement image signing and vulnerability scanning prior to deployment.
  - Expand auth to user-level granularity with refresh tokens and role-based APIs.

## 7. Summary
MicroTaskHub showcases a microservices architecture where independent FastAPI services collaborate via REST, a Node.js frontend provides cohesive UX and auth, and Kubernetes manifests orchestrate deployment. The design balances simplicity and best practices—stateless services, clear domain boundaries, and foundational security—while leaving room for enterprise-grade enhancements such as stronger IAM, observability, and secret management.
