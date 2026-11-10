# Deployment Commands

```bash
# Generic deployment
make deploy ENV=dev TARGET=deb    # Local dev (Docker/Debian)
make deploy ENV=dev TARGET=orb    # Local dev (macOS / OrbStack)
make deploy ENV=opf               # Production OPF

# Shortcuts
make dev                          # Local dev (Docker)
make dev-mac                      # Local dev (OrbStack)
make opf                          # Production OPF

# Target specific roles via tags
make dev TAGS=homepage
make dev TAGS=keycloak
make dev TAGS=hashicorp,temporal
```
