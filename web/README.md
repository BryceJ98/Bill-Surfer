# Bill-Surfer Web

Retro arcade legislative research platform for political science researchers.
Surf theme (day) · Ski theme (night) · Guided by Bodhi the AI surf/ski guide.

---

## Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Frontend | Next.js 14 (App Router) + Tailwind CSS  |
| Backend  | FastAPI (Python 3.12)                   |
| Auth/DB  | Supabase (Postgres + Auth + Storage)    |
| AI       | LiteLLM (Claude, GPT-4, Gemini, Groq…) |
| Reports  | ReportLab PDF generation                |
| Deploy   | Vercel (frontend) + Railway (backend)   |

---

## Local Development

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Open **SQL Editor** and run `supabase/schema.sql`
3. Go to **Storage → New Bucket** → name it `reports`, set to **private**
4. Copy your project URL, anon key, service role key, and JWT secret

### 2. Backend

```bash
cd web/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env:
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY
#   SUPABASE_JWT_SECRET
#   KEY_ENCRYPTION_SECRET  ← generate with the command below
#   ALLOWED_ORIGINS=http://localhost:3000

# Generate an encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 3. Frontend

```bash
cd web/frontend
npm install

cp .env.local.example .env.local
# Fill in .env.local:
#   NEXT_PUBLIC_SUPABASE_URL
#   NEXT_PUBLIC_SUPABASE_ANON_KEY
#   NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# App at http://localhost:3000
```

---

## Deployment

### Backend → Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the `web/backend` directory (or set root to `web/backend`)
3. Railway auto-detects the `Dockerfile`
4. Add environment variables (same as `.env` above)
5. Copy the generated Railway URL (e.g. `https://bill-surfer-api.up.railway.app`)

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → New Project → Import GitHub repo
2. Set **Root Directory** to `web/frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` ← your Railway URL
4. Deploy

### Post-deploy: Update CORS

In Railway, set `ALLOWED_ORIGINS` to your Vercel URL:
```
ALLOWED_ORIGINS=https://your-app.vercel.app
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Next.js (Vercel)              │
│                                         │
│  /            Landing page              │
│  /login       Bodhi-guided onboarding   │
│  /dashboard   Scoreboard + quick actions│
│  /search      Bills, nominations, etc.  │
│  /docket      Personal bill watchlist   │
│  /reports     Report library + generate │
│  /settings    API keys + AI model       │
└──────────────┬──────────────────────────┘
               │ JWT-authenticated HTTPS
┌──────────────▼──────────────────────────┐
│           FastAPI (Railway)             │
│                                         │
│  /keys        Encrypted API key vault   │
│  /docket      Docket CRUD               │
│  /search      Bills + nominations       │
│  /reports     Generate + download PDF   │
│  /export      CSV download              │
│  /chat        Bodhi AI agent            │
│  /settings    Profile + scoreboard      │
│                                         │
│  congress_client.py  ← Congress.gov     │
│  legiscan_client.py  ← LegiScan         │
│  report_generator.py ← AI + ReportLab  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│           Supabase                      │
│                                         │
│  Auth (magic link email)                │
│  Postgres: user_keys, docket, reports   │
│  Storage:  report PDFs                  │
└─────────────────────────────────────────┘
```

---

## User Flow

1. **Land** on the arcade-style homepage
2. **Bodhi** guides through sign-up: email magic link → LegiScan key → Congress key → AI model
3. **Dashboard** shows scoreboard: bills in docket, reports today, active AI model
4. **Search** bills across 50 states or federal, add to docket in one click
5. **Generate reports** — AI writes structured policy analysis, renders to PDF
6. **Export** any dataset as CSV
7. **Chat** with Bodhi anytime via the floating surf emoji button

---

## Adding a New AI Provider

1. Add the provider to `VALID_PROVIDERS` in `backend/app/routers/keys.py`
2. Add it to `AI_MODELS` in `backend/app/routers/settings.py`
3. Add the option to `AI_OPTIONS` in `frontend/app/login/page.tsx`
4. LiteLLM handles the rest — no other changes needed

---

## Key Design Notes

- **API keys are encrypted** with Fernet (AES-128-CBC + HMAC-SHA256) before DB storage
- **Row Level Security** on all Supabase tables — users can only access their own data
- **Report generation is async** — background task, polls every 5 seconds until complete
- **Bodhi** is the same AI model the user configured — it just has a system prompt and tools
- **Bring Your Own Keys** — Bill-Surfer never proxies your API calls through our keys
