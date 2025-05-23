FROM python:3.11-slim

# Instalar dependencias necesarias para PyPortfolioOpt
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Limpiar dependencias de compilación (mantener git para posibles actualizaciones)
RUN apt-get remove -y gcc g++ cmake && \
    apt-get autoremove -y && \
    apt-get clean

# Copiar aplicación
COPY main.py .

# Usuario no-root
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]