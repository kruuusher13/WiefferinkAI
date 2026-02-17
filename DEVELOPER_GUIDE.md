# Developer Guide — GarageAI

## Local Rapid Prototyping

### Quick Start

```bash
# Start the database
docker-compose up -d

# Start backend (auto-reloads on file changes)
python -m uvicorn bridge.api:app --port 8000 --reload

# Start frontend (auto-reloads on file changes)
cd garage-ai-command-center && pnpm dev
```

Or just:

```bash
./start_all.sh
```

### What you get locally

- **Backend** at `http://localhost:8000` — auto-reloads on any Python file change
- **Dashboard** at `http://localhost:3000` — hot-reloads on any React/TS change
- **Database** at `localhost:1433` — SQL Server via Docker
- **Mic testing** — open `localhost:3000`, click the mic button

### Tips for fast iteration

- Edit Python files → uvicorn reloads automatically (~1s)
- Edit React/TS files → Next.js hot-reloads instantly
- No need to restart anything unless you change `requirements.txt` or `package.json`
- Test API directly: `curl http://localhost:8000/api/rdw-lookup/XX123YY`

---

## Pushing to Google Cloud

### Prerequisites (already set up)

```bash
# Your project and region
gcloud config set project gen-lang-client-0134658653
gcloud config set run/region europe-west4
```

### Deploy Backend (Python/FastAPI)

```bash
# From project root - build and deploy in one command
gcloud run deploy garageai-bridge \
  --source . \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --session-affinity \
  --set-env-vars "GOOGLE_API_KEY=your-key,CORS_ORIGIN=https://garageai-dashboard-1041143034967.europe-west4.run.app"
```

`--source .` builds the Dockerfile in Cloud Build and deploys automatically. No separate build step needed.

### Deploy Dashboard (Next.js)

The dashboard needs the bridge URL baked in at build time, so use `cloudbuild.yaml`:

```bash
# From garage-ai-command-center/
cd garage-ai-command-center

# Build with the bridge URL baked in
gcloud builds submit --config cloudbuild.yaml .

# Deploy the built image
gcloud run deploy garageai-dashboard \
  --image gcr.io/gen-lang-client-0134658653/garageai-dashboard \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi
```

### Quick Reference: What to redeploy when

| Changed | Redeploy |
|---|---|
| Python code (`app/`, `bridge/`) | Backend only |
| Frontend code (`garage-ai-command-center/`) | Dashboard only |
| Both | Both |
| Env vars only | `gcloud run services update <service> --update-env-vars "KEY=val"` (no rebuild) |

### Update env vars without rebuilding

```bash
# Example: update CORS or API keys
gcloud run services update garageai-bridge \
  --region europe-west4 \
  --update-env-vars "CORS_ORIGIN=https://new-url.run.app"
```

---

## Live URLs

| Service | URL |
|---|---|
| Backend | https://garageai-bridge-1041143034967.europe-west4.run.app |
| Dashboard | https://garageai-dashboard-1041143034967.europe-west4.run.app |

---

## Typical Workflow

1. **Code locally** with `--reload` / `pnpm dev`
2. **Test with mic** at `localhost:3000`
3. **Happy?** Push to cloud:
   - Backend: `gcloud run deploy garageai-bridge --source .` (from project root)
   - Dashboard: `cd garage-ai-command-center && gcloud builds submit --config cloudbuild.yaml . && gcloud run deploy garageai-dashboard --image gcr.io/gen-lang-client-0134658653/garageai-dashboard --platform managed --region europe-west4 --allow-unauthenticated --port 3000 --memory 512Mi`
4. **Verify** at the Cloud Run URLs
