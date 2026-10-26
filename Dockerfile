FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.2.1 openpyxl==3.1.5 \
    fastapi==0.162.0 uvicorn==0.49.0 httpx==0.28.1 python-multipart==0.0.32 matplotlib==3.10.8   # second line: the WhatsApp bot
COPY engine engine
COPY ui ui
COPY whatsapp whatsapp
COPY landing-page landing-page
COPY fixtures fixtures
COPY data data
# Build the demo tenant's synthetic ledger (data/tenants/mahesh-cnc) into the image so the first request is not slow (deterministic, seed 7)
RUN python -m engine.ledger
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "ui/server.py"]
