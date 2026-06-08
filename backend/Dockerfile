FROM python:3.12

WORKDIR /app

COPY backend/requirements.txt ./

RUN pip install -r requirements.txt

COPY backend/ .
COPY apps/admin-frontend/dist ./static/admin

CMD ["sh", "-c", "python -m src.cli.migrate && exec uvicorn --factory src.main:create_app --host 0.0.0.0 --port 8000"]
