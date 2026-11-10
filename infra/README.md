# TwinEU Infrastructure

*Automated deployment and configuration of the TwinEU distributed infrastructure.*

## Documentation

* [Architecture Overview](./docs/ARCHITECTURE.md)
* [Deployment Commands](./docs/deployment-commands.md)
* [Deploy to mac environment](./docs/deploy-on-mac.md)
* [Deploy to prod-ready server](./docs/deploy-on-opf.md)
* [Setup TwinEU-Core services](./docs/setup-services.md)
* [Endpoints Reference](./docs/endpoints-reference.md)
* [Deployment Commands](./docs/deployment-commands.md)
* [Troubleshooting](./docs/troubleshooting.md)

## Getting Started

Deploy the local infrastructure on Linux (for macOS/OrbStack, see [other platforms](./docs/deploy-on-mac.md)).

## Prerequisites

| Tool                                              | Purpose                                                    | Documentation                                         |
| ------------------------------------------------- | -----------------------------------------------------------| ----------------------------------------------------- |
| [**Make**](https://www.gnu.org/software/make/)    | Single entry point (orchestrates the .venv and execution)  | [Install Make](https://www.gnu.org/software/make/)    |
| [**Python 3**](https://www.python.org/)           | Required to create the isolated .venv virtualenv (Ansible) | [Python](https://www.python.org/)                     |
| [**Docker**](https://docs.docker.com/get-docker/) | Run target containers & images                             | [Install Docker](https://docs.docker.com/get-docker/) |

---


### 1. Setup Vault Password

Create the hidden file containing your Ansible Vault encryption key:
```bash
echo "YourSecretPassword" > .vault_pass.txt
```

### 2. Edit Vault Configuration

Open the Vault configuration file for your environment (e.g., dev):
```bash
make vault-edit ENV=env
```

Paste and adjust the following configuration:

```yaml
---
# Which base_domain is needed
base_domain: "twin.local"

# Auto-generated locally on first run if left blank.
# For production, strictly override with a strong static password.
keycloak_admin_user: "admin"
keycloak_admin_password: "YourStrongKeycloakAdminPassword"

# Uncomment if you are setup a password in your local env
# ansible_become_password: "YourTargetUserSudoPassword"

# Uncomment and edit if you are behind a corporate proxy
# proxy_env:
#   http_proxy: "http://user:pwd@proxy.corporate.local:8080"
#   https_proxy: "http://user:pwd@proxy.corporate.local:8080"
#   no_proxy: "localhost,127.0.0.1,172.17.0.0/16,10.0.0.0/8"
```

*Note: If you let the deployment auto-generate the Keycloak password, you can retrieve it using these commands:*

```bash
# From the Ansible controller (this repo):
cat .generated_secrets/keycloak_admin_password__twineu.txt

# Or directly from Vault on the target host:
ssh orb "VAULT_ADDR=http://127.0.0.1:8200 vault kv get secret/keycloak"
```

### 3. Start Local Target Container

Launch the systemd-enabled Debian container that will host the local stack:

```bash
docker run -d --name twineu_target \
  --privileged \
  --cgroupns=host \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
  -p 80:80 \
  -p 443:443 \
  -p 5353:53/udp \
  -p 5353:53/tcp \
  -p 8080:8080 \
  -p 4646:4646 \
  -p 8500:8500 \
  -p 8200:8200 \
  -p 7233:7233 \
  -p 8333:8333 \
  -p 9333:9333 \
  -p 8090:8090 \
  -p 8334:8334 \
  -e http_proxy="${http_proxy}" \
  -e https_proxy="${https_proxy}" \
  -e no_proxy="${no_proxy},localhost,127.0.0.1,172.17.0.0/16,10.0.0.0/8" \
  geerlingguy/docker-debian12-ansible
```

### 4. Deploy the Stack

Run the final deployment via Make:
```bash
make dev
```

Once deployed, open the portal in your browser (depending on your _base_domain_ config): [https://portal.twin.local](https://portal.twin.local)

You can find all services in [docs/endpoints-reference.md](./docs/endpoints-reference.md)
