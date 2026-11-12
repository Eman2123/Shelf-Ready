# Hugging Face Space (Docker) for the Shelf Ready backend. Free, no credit card.
# The Space repo only needs this file and README.md. The image clones the public GitHub repo at
# build time, so "Factory rebuild" in the Space settings picks up new commits.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user

ARG REPO=https://github.com/Eman2123/Shelf-Ready.git
RUN git clone --depth 1 "$REPO" /home/user/src
WORKDIR /home/user/src/backend
RUN pip install --no-cache-dir . && chown -R user:user /home/user
USER user

ENV PORT=7860
EXPOSE 7860
# Secrets (PAYPAL_*, DATABASE_URL, ADMIN_TOKEN, APP_URL, AIML_API_KEY) are Space secrets, never in git.
CMD ["sh", "-c", "if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
