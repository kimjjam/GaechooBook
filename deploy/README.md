# MoodPick deployment

## Current production architecture

- Frontend: Next.js on Vercel (`https://frontend-zeta-woad-62.vercel.app`)
- API: FastAPI on a separate Vercel project (`https://moodpick-backend.vercel.app`)
- Database: OCI Always Free Autonomous Transaction Processing in `ap-tokyo-1`
- Browser API path: `/api/backend/*` on the frontend; the Next.js route forwards to `BACKEND_URL`

The OCI home region is fixed to Japan East (Tokyo). Do not create an OCI VM or
run Caddy for the current deployment.

## Backend production variables

Configure these as Vercel Production environment variables. Never commit their
values.

```text
ORACLE_USER
ORACLE_PASSWORD
ORACLE_DSN=moodpick_low
ORACLE_WALLET_PASSWORD
ORACLE_WALLET_BASE64_1
ORACLE_WALLET_BASE64_2
ORACLE_WALLET_BASE64_3
ORACLE_WALLET_BASE64_4
ORACLE_POOL_MIN=0
ORACLE_POOL_MAX=1
SQLALCHEMY_POOL_SIZE=1
SQLALCHEMY_MAX_OVERFLOW=0
FRONTEND_ORIGIN=https://frontend-zeta-woad-62.vercel.app
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
```

API provider keys from `backend/.env.example` are also configured on the
backend project. The frontend project has:

```text
BACKEND_URL=https://moodpick-backend.vercel.app
```

## Deploy

From the repository root, deploy the frontend because the Vercel project root
directory is `frontend/`:

```bash
vercel --prod --yes
```

Deploy the backend from `backend/`:

```bash
cd backend
vercel --prod --yes
```

## Verify

```bash
curl https://moodpick-backend.vercel.app/health/db
curl https://frontend-zeta-woad-62.vercel.app/api/backend/health/db
```

Both must return `{"status":"ok"}` before testing registration, login,
onboarding, recommendations, and feedback.
