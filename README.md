# Aviator Predictor — Full-stack starter
React/Vite frontend + FastAPI backend. Features: red/white package selection, manual MTN MoMo/Telecel Cash/GCB payment instructions, optional proof image, pending payment review, role-protected dashboards, referral links, 70% sub-admin commission ledger, and super-admin soft archive.

## Backend
Python 3.11+
```bash
cd backend
python -m venv .venv
# activate the venv, then:
pip install -r requirements.txt
cp .env.example .env
python create_super_admin.py
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Frontend
```bash
cd frontend
npm install
npm run dev
```
Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env` if needed.

## Important
Starter scaffold; security-review before production. Use HTTPS, PostgreSQL, backups, rate limits, file scanning and audit logs. Manually verify transfers before approving. Demo multiplier values do not predict future Aviator rounds. `DELETE /admin/package-amount/clear-older?days=90` is super-admin-only and soft-archives records.

## Updates in this build
- Package selection is protected behind login; unauthenticated visitors are redirected to the login page.
- Signup includes client-side confirm-password matching.
- Copying a manual payment number displays **“Number copied!”**.
- Predictor generates one weighted-random demonstration target per request and does not animate a multiplier counting up. These values are not forecasts of real Aviator rounds.
- The predictor page includes the red-and-white usage guide at the bottom.

The ZIP supplied for this update contained no aeroplane image asset. The login and signup pages therefore use the existing Lucide plane icon in a red tile as a temporary visual. Add the exact image asset to replace it if you want that specific artwork.

## Build check
The updated JSX and Python files passed syntax checks. A full Vite production build could not be run in this environment because installing the frontend dependencies timed out.


## Latest amendments
- Predictor button displays CALCULATING... and the circle scrambles rapidly for about 2.5 seconds before locking one random demonstration target; NEXT starts the next cycle.
- MTN MoMo, Telecel Cash and GCB bank transfer choices have distinct visual brand marks.
- Signup and staff creation password minimum is six characters (backend-enforced).
- Super Admin, Admin and Sub-Admin accounts have free predictor access; regular users still require an approved package.
- Newly generated referral codes are neutral eight-character codes without role abbreviations. Existing codes in an existing database are not automatically rewritten.
- The red-and-white usage guide is shown on both the predictor and package pages.
- Multiplier signals are randomized demonstrations and cannot reliably predict a real Aviator round.
