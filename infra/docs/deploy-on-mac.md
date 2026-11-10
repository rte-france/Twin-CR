# Deployment on macOS (with Orbstack)

For local deployments and infrastructure testing on macOS, this setup has been validated using [OrbStack](https://orbstack.dev/). 

OrbStack provides a fast, lightweight, and resource-efficient alternative to Docker Desktop, allowing Linux virtual machines and containers to run with native performance on Mac.

## Getting Started 

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
# # Which base_domain is needed, OrbStack can define localhost as local base_domain
base_domain: "localhost"

# Auto-generated locally on first run if left blank.
# For production, strictly override with a strong static password.
keycloak_admin_user: "admin"
keycloak_admin_password: "YourStrongKeycloakAdminPassword"

# Uncomment if you configured a sudo password
# ansible_become_password: "YourTargetUserSudoPassword"

# Uncomment and edit if you are behind a corporate proxy
# proxy_env:
#   http_proxy: "http://user:pwd@proxy.corporate.local:8080"
#   https_proxy: "http://user:pwd@proxy.corporate.local:8080"
#   no_proxy: "localhost,127.0.0.1,172.17.0.0/16,10.0.0.0/8"
```

### 3. Start Local Target on Orbstack

Here are the setup and deployment steps:

```bash
# 1. Create a Debian 12 machine with a "twineu" user
orb create debian:bookworm twineu-dev -u twineu

# 2. Add sudo access without a password and install Python 3
orb -m twineu-dev sudo usermod -aG sudo twineu
orb -m twineu-dev bash -c 'echo "twineu ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/twineu'
orb -m twineu-dev sudo apt update && orb -m twineu-dev sudo apt install -y python3

# 3. Ensure the SSH host alias "orb" resolves (default in OrbStack) 
# Or configure it manually in ~/.ssh/config:
# Host orb
#   HostName <orb-ip-or-name>
#   User twineu
```

### 4. Deploy the Stack

Run the final deployment via Make:
```bash
make dev-mac
```

Once deployed, open the portal in your browser (depending on your _base_domain_ config): [https://portal.localhost](https://portal.localhost)
