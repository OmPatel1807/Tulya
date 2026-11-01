# Tulya – Deployment Guide

> **Updated**: 2026-11-01

---

## Architecture

```
GitHub (OmPatel1807/Tulya)
    ├── Render  →  Python FastAPI + frontend served from /frontend/
    │              (same origin, no CORS needed)
    └── Vercel  →  Static frontend only, /api/* proxied to Render
                   (secondary / CDN edge backup)
```

### Deploy Mode

Tulya has two runtime modes controlled by `TULYA_DEPLOY_MODE`:

| Value | What runs | RAM at start | ML packages |
|:------|:----------|:-------------|:------------|
| `precomputed` | Serves pre-built reports only; upload/live-audit returns 503 | ~55 MB | none |
| `live` | Full PDF→ingest→align→audit pipeline | ~1.5 GB (LaBSE model) | torch, sentence-transformers |

Render's **free** plan has a 512 MB RAM limit. Use `precomputed`. Live mode needs a **Standard** plan.

---

## Part 1 – Render (Backend + Full-Stack Frontend)

### One-time setup

1. **Go to** [dashboard.render.com](https://dashboard.render.com/) and sign in with GitHub.

2. **New → Web Service** → Connect repository **`OmPatel1807/Tulya`**.

3. **Service settings**:

   | Field | Value |
   |:------|:------|
   | Name | `tulya` |
   | Region | Singapore or Frankfurt (closest to your users) |
   | Branch | `main` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn backend.app.api.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/healthz` |
   | Plan | **Free** (for demo/precomputed mode) |

4. **Environment Variables** (set in the Render dashboard — never commit values):

   | Key | Notes |
   |:----|:------|
   | `PYTHON_VERSION` | `3.11.9` |
   | `TULYA_DEPLOY_MODE` | `precomputed` |
   | `GEMINI_API_KEY` | Your Gemini key (only needed for `live` mode) |
   | `CORS_ORIGINS` | Comma-separated allowed origins, e.g. `https://tulya.vercel.app,http://localhost:8000` |

5. Click **Deploy**. Build takes ~3 min (no torch install in precomputed mode).

6. Note your service URL: `https://tulya.onrender.com` (or `https://tulya-xxxx.onrender.com`).

7. Verify:
   ```
   curl https://tulya.onrender.com/healthz
   # → {"status":"ok","mode":"precomputed"}
   ```

### Auto-deploy on push

Render auto-deploys every `main` push once connected.

---

## Part 2 – Vercel (Frontend CDN, secondary)

> Vercel is optional. Render already serves the full frontend. Use Vercel for faster edge delivery or a custom domain.

### One-time setup

1. **Go to** [vercel.com/new](https://vercel.com/new) and sign in with GitHub.

2. **Import → `OmPatel1807/Tulya`**.

3. **Project settings**:

   | Field | Value |
   |:------|:------|
   | Framework Preset | Other |
   | Root Directory | `./` (default) |
   | Build & Output | leave all blank (handled by `vercel.json`) |

4. **Before deploying**, update the Render URL in `vercel.json`:
   - Open `vercel.json` in the repo.
   - Replace `https://tulya.onrender.com` with your actual Render service URL.
   - Commit and push.

5. **Environment Variables** on Vercel (none required; `vercel.json` rewrites handle routing):

   | Key | Notes |
   |:----|:------|
   | *(none required)* | The rewrite in `vercel.json` hard-codes the Render backend URL |

6. Click **Deploy**. Vercel builds in ~30 seconds.

7. Your site is live at `https://tulya.vercel.app` (or your chosen domain).

---

## URL Reference

| URL | Destination | Description |
|:----|:------------|:------------|
| `https://tulya.onrender.com/` | Render | 3D Scroll Story (full-stack) |
| `https://tulya.onrender.com/app` | Render | Glass Workspace |
| `https://tulya.onrender.com/healthz` | Render | Health check |
| `https://tulya.onrender.com/docs` | Render | Swagger API docs |
| `https://tulya.vercel.app/` | Vercel → Render | 3D Scroll Story (CDN) |
| `https://tulya.vercel.app/app` | Vercel → Render | Glass Workspace (CDN) |

---

## Waking the Service Before a Demo (Free Plan Sleeps)

Render free services spin down after 15 minutes of inactivity. Cold start is ~30 seconds.

**Wake command** (run ~60 seconds before your demo):
```bash
curl https://tulya.onrender.com/healthz
```

Or open the URL in a browser tab and wait for the response.

---

## Enabling Live Auditing (Paid Plan)

To enable full PDF auditing on Render:

1. Upgrade the Render service to **Standard** plan (minimum 2 GB RAM for LaBSE).
2. Change build command to:
   ```
   pip install -r requirements.txt -r requirements-live.txt
   ```
3. Set `TULYA_DEPLOY_MODE=live` in Render environment variables.
4. Set `GEMINI_API_KEY` for LLM semantic comparison (optional; deterministic mode works without it).

---

## Rollback

To roll back to a previous deployment:

- **Render**: Dashboard → your service → **Deploys** tab → click any previous deploy → **Redeploy**.
- **Vercel**: Dashboard → your project → **Deployments** tab → find the previous deployment → **Promote to Production**.

---

## What Works / What Does Not / Biggest Risk

### ✅ Works
- Precomputed mode: instant start, 55 MB RAM, no ML dependencies, 5 sample reports from catalog.
- Full test suite: 90/90 passing.
- `/healthz` health check for Render.
- Same-origin frontend serving from FastAPI (no CORS configuration needed).
- Vercel reverse-proxy to Render API.
- No secrets in the repository.

### ⚠️ Does Not Work (precomputed mode)
- Live PDF upload auditing returns HTTP 503 with a friendly message.
- Only `right_to_information_2005` has a precomputed report on disk. The other 4 bundled Acts return an empty findings list. To add more: run `python3 -m backend.app.ingest.cli <slug>` locally and commit the resulting `data/processed/<slug>.json`.

### 🚨 Biggest Deployment Risk
**Free-plan cold start** is the main UX risk. Render free services spin down after inactivity. The first request takes ~30 seconds. Mitigation: ping `/healthz` before a demo, or upgrade to a Starter plan (\$7/month) which has no sleep.

**Second risk**: `data/raw/` PDF files (14 MB) are committed to the repo. If you move to Git LFS or remove them, the precomputed pipeline will fail to re-run. The precomputed JSON files in `data/processed/` are the only thing needed in hosted mode.

