FROM apache/airflow:2.8.0-python3.11

USER root

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow

WORKDIR /opt/airflow

# Copia requirements e instala dependências Python como airflow user
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código fonte
COPY airflow/dags/ ./dags/
COPY datasets/ ./datasets/
COPY src/ ./src/

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV AIRFLOW_HOME=/opt/airflow
