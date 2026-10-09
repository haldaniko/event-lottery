FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    DB_NAME=/data/db.sqlite3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput \
    && useradd --create-home --uid 10001 lottery \
    && mkdir -p /data \
    && chown -R lottery:lottery /data /app/staticfiles

USER lottery

EXPOSE 8000
CMD ["sh", "/app/start.sh"]
