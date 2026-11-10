# Service Endpoints Reference

Depending on your *base_domain* configuration.

| Service              | Access Type  | URL                                                                    | Description                               |
| -------------------- | ------------ | ---------------------------------------------------------------------- | ----------------------------------------- |
| **Unified Portal**   | Web UI       | `https://portal.<base_domain>`                                         | Single portal entrypoint (Homepage)       |
| **Auth Gateway**     | Redirect     | `https://auth.<base_domain>`                                           | Traefik alias redirecting to Keycloak     |
| **Keycloak Admin**   | Web UI       | `https://keycloak.<base_domain>/admin/`                                | IAM realm configuration & user management |
| **Keycloak Account** | Web UI       | `https://keycloak.<base_domain>/realms/twineu/account/`                | User self-service profile and credentials |
| **Nomad**            | Web UI       | `https://nomad.<base_domain>`                                          | Workload orchestrator                     |
| **Consul**           | Web UI       | `https://consul.<base_domain>`                                         | Service mesh and registry                 |
| **Vault**            | Web UI / API | `http://vault.<base_domain>:8200`                                      | Central secrets engine & internal PKI     |
| **Traefik**          | Dashboard    | `http://traefik.<base_domain>:8080/dashboard/`                         | Ingress proxy routing & metrics           |
| **Temporal UI**      | Web UI       | `https://temporal.<base_domain>`                                       | Workflow orchestration dashboard          |
| **Temporal gRPC**    | gRPC API     | `temporal-grpc.<base_domain>:80`                                       | Client worker communication endpoint      |
| **Docker Registry**  | OCI API / UI | `https://registry.<base_domain>` / `https://registry-ui.<base_domain>` | Container image registry                  |
| **Garage S3**        | S3 API / UI  | `http://s3.<base_domain>` / `https://ui.garage.<base_domain>`          | Distributed object storage                |
