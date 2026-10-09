FROM python:3.11-slim

# Evita geração de arquivos .pyc e força flush imediato de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilação se houver
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Cria pasta de dados se necessário
VOLUME /app/data

# Inicia o bot em modo contínuo 24/7
CMD ["python", "main.py"]
