# Event lottery

A tablet lottery built with React and Django REST Framework. The interface and Django Admin are in English. The supplied background, Time to Move logo, and `facelift-small.png` Open Doors logo are in `frontend/src/assets`; older logo variants are in `frontend/src/assets/logo-variants`. The logos appear on either side of the wheel. The interface uses Titillium Web from Google Fonts.

## Run with Docker

Docker Compose starts the React frontend and Django backend. SQLite data is stored in the persistent `lottery_data` volume.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set a long random `DJANGO_SECRET_KEY` in `.env`, then run:

```powershell
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser
```

Open `http://localhost:8080` for the lottery and `http://localhost:8080/admin/` for administration. Players only press **Spin**; there is no access code.

The initial pool contains exactly **200 spins**: 140 no-prize results, 50 small gifts, 5 keyboards, and 5 headphones. Each draw consumes one outcome. In **Draw categories** in Django Admin, edit the remaining quantities directly in the table and click **Save**. Add categories with **Add draw category**. “No prize” is a category with its own finite quantity. A disabled or exhausted category cannot be drawn. Each category has chance weight 1, so its chance follows its remaining quantity. Keyboard and headphone sectors have a slightly larger visual size; this display setting is excluded from the server's draw calculation.

The admin page shows the 200-spin limit, valid draws, available slots, and total active category stock. Keep category stock equal to available slots. The API enforces the 200-spin limit even if stock is accidentally set too high. To correct an accidental extra spin, open **Draw history**, select the draw, and choose **Cancel selected draws and return their outcomes**. Confirming the action restores its category stock and one available spin; the cancelled draw remains in history. Repeating the action cannot restore the same draw twice.

Earlier outcomes are deactivated when this campaign is installed; existing draw history is preserved. The campaign setup is a one-time database migration, so restarting containers does not reset used spins.

For a tablet on the local network, open `http://YOUR-COMPUTER-IP:8080`. Add that IP to `DJANGO_ALLOWED_HOSTS` in `.env` and recreate the containers with `docker compose up -d --force-recreate`. Change `APP_PORT` if needed.

Useful commands:

```powershell
docker compose logs -f
docker compose exec backend python manage.py test
docker compose down
```

`docker compose down` keeps the database volume. Back up `/data/db.sqlite3` from `lottery_data` to preserve stock and draw history.

## Local development

Requires Python 3.11+ and Node.js 20+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`; Django Admin runs at `http://localhost:8000/admin/`. For public deployment, use HTTPS and configure `DJANGO_ALLOWED_HOSTS` and, when needed, `DJANGO_CSRF_TRUSTED_ORIGINS`. PostgreSQL is recommended for many tablets drawing simultaneously.

## Checks

```powershell
cd backend
python manage.py test
cd ..\frontend
npm run build
```
