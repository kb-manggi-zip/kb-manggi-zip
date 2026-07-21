FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성 먼저 (레이어 캐시)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션
COPY . .

# 캐시 디렉터리 (외부 API 응답 파일 캐시)
RUN mkdir -p /app/cache

EXPOSE 8000

# Railway 등은 $PORT 주입 — 없으면 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
