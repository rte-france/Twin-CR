# Lobby

## Dev

### Backend

```bash
$ cd backend
$ uv sync
$ source .venv/bin/activate
```

Setup `.env` file:

```bash
$ cp .env.example .env
```

Get `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` from Garage (e.g. `ui.garage.localhost`).

Run Temporal broker:

```bash
$ python -m app.worker
```

Run server in another terminal:

```bash
$ uv run uvicorn app.main:app --reload
```

### Frontend

```bash
$ cd frontend
$ pnpm i
```

Setup `.env` file:

```bash
$ cp .env.example .env
```

Setup variables (note: `VITE_API_TOKEN` is not relevant).

Run application in dev mode:

```bash
$ pnpm dev
```

## Prod

Build and push the `lobby` and `lobby-front` images to the registry. Be aware that the domain name depends on the OPF or DEV environment.

```bash
$ cd backend
$ docker build -t registry.twin.eu/lobby:latest .
$ docker push registry.twin.eu/lobby:latest
```

```bash
$ cd frontend
$ docker build -t registry.twin.eu/lobby-front:latest .
$ docker push registry.twin.eu/lobby-front:latest
```
