FROM python:3.12

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./

RUN pip install --default-timeout=120 -r requirements.txt

COPY backend/ .
COPY apps/admin-frontend/dist ./static/admin

CMD ["sh", "-c", "python -m src.cli.migrate && exec uvicorn --factory src.main:create_app --host 0.0.0.0 --port 8000"]
