```bash
python -m app.worker
uv run uvicorn app.main:app --reload
```

mettre .twin.eu dans les no_proxy

# opf

x.x.x.x twineu-opf twineu_opf
x.x.x.x ui.garage.twin.eu admin.garage.twin.eu s3.garage.twin.eu s3.twin.eu keycloak.twin.eu temporal.twin.eu registry.twin.eu registry-ui.twin.eu

# Build de l'image (remplacez par l'adresse de votre registry)

docker build -t registry.twin.eu/lobby:latest .

# Push sur le registry

docker push registry.twin.eu/lobby:latest
