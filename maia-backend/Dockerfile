FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia tudo antes do install (hatchling precisa do código para editable)
COPY pyproject.toml .
COPY app/ ./app/

# Instala dependências (sem -e para evitar problemas com hatchling no build)
RUN pip install --no-cache-dir ".[dev]"

# Porta padrão
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
