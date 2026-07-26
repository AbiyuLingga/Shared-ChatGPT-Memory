FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn app.main:app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
