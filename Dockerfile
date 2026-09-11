FROM python:3.13-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache build-base postgresql-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -S app \
    && adduser -S -G app -h /app app

COPY --from=builder /install /usr/local

COPY --chown=app:app . .
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media

EXPOSE 8000
USER app

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
