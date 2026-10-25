FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy==1.26.4 pandas==2.2.1 openpyxl==3.1.5
COPY engine engine
COPY ui ui
COPY fixtures fixtures
COPY data data
# Build the synthetic ledger into the image so the first request is not slow (deterministic, seed 7)
RUN python -m engine.ledger
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "ui/server.py"]
