# LBMS deployment: GitHub + Vercel + PostgreSQL

This version keeps SQLite for local Windows development and uses PostgreSQL when `DATABASE_URL` is set. Vercel deployments must have a hosted PostgreSQL database because the Vercel function filesystem is not persistent storage.

## 1. Create a hosted PostgreSQL database

Create a database with a provider such as Neon or Supabase. Copy its PostgreSQL connection string. Keep the string private.

## 2. Set Vercel environment variables

In Vercel, open the LBMS project → Settings → Environment Variables and add:

- `DATABASE_URL`: the PostgreSQL connection string from your database provider.
- `SECRET_KEY`: a long random value generated privately, for example with `python -c "import secrets; print(secrets.token_hex(32))"`.

Apply them to Production (and Preview if you use preview deployments). Redeploy after adding or changing environment variables.

## 3. Push the project to GitHub

From Windows Command Prompt, in the project folder:

```bat
git init
git branch -M main
git add .
git status
git commit -m "Prepare LBMS for Vercel and PostgreSQL"
git remote add origin https://github.com/YOUR_USERNAME/LBMS.git
git push -u origin main
```

Replace the repository URL with your own. The `.gitignore` excludes local databases and secret files. Do not force-add `.env` or the SQLite database to GitHub.

If the folder is already a Git repository, do not run `git init` again; use `git add .`, `git commit`, and `git push` instead. If `origin` already exists, use `git remote set-url origin https://github.com/YOUR_USERNAME/LBMS.git`.

## 4. Import to Vercel

Open https://vercel.com/new, import the GitHub repository, keep the project root as `./`, and deploy. This project includes `vercel.json` and `api/index.py` for the Flask entry point.

## 5. Optional: migrate your existing SQLite data

The deployed app will create its tables and seed demonstration records if the hosted database is empty. To transfer records from your local `library_management_system.db`, install dependencies locally, set `DATABASE_URL` in Command Prompt, and run:

```bat
pip install -r requirements.txt
set DATABASE_URL=YOUR_POSTGRES_CONNECTION_STRING
python migrate_sqlite_to_postgres.py
```

The default migration skips conflicting records. To replace all five hosted LBMS tables with the local SQLite contents, run `python migrate_sqlite_to_postgres.py --replace`. This is destructive: back up the hosted database first, and only type `REPLACE` when prompted if you are certain.

## 6. Test the deployment

Open `https://YOUR-VERCEL-DOMAIN/health` and confirm it returns `{"status":"ok","service":"LBMS"}`. Then test login/signup, book issue/return, fines, library cards, and the No-Due Certificate. Add a test record and confirm it remains after a redeployment.

## Demo accounts

The original project seeds demo accounts only when the `Users` table is empty:

- Student: `fathima` / `fathima123`
- Staff: `staff101` / `admin123`
- Student: `rahul` / `rahul123`
- Student: `ananya` / `ananya123`

These are demonstration credentials from the source project. Change or remove them before using this application with real users. Do not use the demo passwords in a production deployment.

## Notes

- `DATABASE_URL` must point to PostgreSQL, not SQLite.
- `SECRET_KEY` must be configured on Vercel.
- Static files remain under Flask's `static/` directory and templates under `templates/`.
- Do not commit credentials, `.env`, or the local SQLite database to a public repository.
