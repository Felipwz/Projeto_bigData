"""
Tech Minds Analytics - Airflow DAG
Pipeline ETL automatizado para processar dados de saúde mental na tecnologia.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import pandas as pd
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Argumentos padrão da DAG
default_args = {
    'owner': 'tech-minds-analytics',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 11, 26),
}

# Definição da DAG
dag = DAG(
    'mental_health_etl_pipeline',
    default_args=default_args,
    description='Pipeline ETL completo: Bronze -> Silver -> Gold',
    schedule_interval='@daily',  # Executa diariamente
    catchup=False,
    tags=['etl', 'mental-health', 'data-lake'],
)


def get_minio_client():
    """Retorna cliente MinIO configurado."""
    return Minio(
        endpoint=os.getenv('MINIO_ENDPOINT', 'minio:9000'),
        access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        secure=False
    )

def initialize_minio():
    """Task 1: Inicializa conexão com MinIO e cria buckets."""
    print("🔧 Inicializando MinIO...")
    
    client = get_minio_client()
    buckets = [
        os.getenv('BUCKET_BRONZE', 'bronze'),
        os.getenv('BUCKET_SILVER', 'silver'),
        os.getenv('BUCKET_GOLD', 'gold')
    ]
    
    for bucket in buckets:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"✅ Bucket '{bucket}' criado")
            else:
                print(f"✅ Bucket '{bucket}' já existe")
        except S3Error as e:
            print(f"❌ Erro no bucket '{bucket}': {e}")
            raise
    
    print("✅ MinIO inicializado com sucesso!")
    return "MinIO pronto"


def run_bronze_layer():
    """Task 2: Executa camada Bronze (ingestão de dados brutos)."""
    print("📥 Executando camada Bronze...")
    
    client = get_minio_client()
    bucket = os.getenv('BUCKET_BRONZE', 'bronze')
    data_path = os.getenv('DATA_PATH', '/opt/airflow/datasets/mental_health.csv')
    
    # Lê arquivo CSV local
    with open(data_path, 'rb') as file:
        csv_data = file.read()
    
    # Upload para MinIO
    client.put_object(
        bucket,
        'raw_mental_health.csv',
        BytesIO(csv_data),
        length=len(csv_data),
        content_type='text/csv'
    )
    
    print(f"✅ {len(csv_data)} bytes enviados para {bucket}/raw_mental_health.csv")
    return "Bronze layer processado"


def normalize_gender(gender):
    """Normaliza valores de Gender."""
    if pd.isna(gender):
        return 'Other'
    gender_str = str(gender).lower().strip()
    male_variants = ['male', 'man', 'm', 'cis male', 'male (cis)', 'cis man', 'mail', 'maile', 'mal']
    if any(variant in gender_str for variant in male_variants) and 'female' not in gender_str:
        return 'Male'
    female_variants = ['female', 'woman', 'f', 'cis female', 'female (cis)', 'cis woman', 'femake', 'femail']
    if any(variant in gender_str for variant in female_variants):
        return 'Female'
    return 'Other'

def run_silver_layer():
    """Task 3: Executa camada Silver (limpeza e padronização)."""
    print("🧹 Executando camada Silver...")
    
    client = get_minio_client()
    bucket_bronze = os.getenv('BUCKET_BRONZE', 'bronze')
    bucket_silver = os.getenv('BUCKET_SILVER', 'silver')
    age_min = int(os.getenv('AGE_MIN', '18'))
    age_max = int(os.getenv('AGE_MAX', '100'))
    
    # Lê CSV do bronze
    response = client.get_object(bucket_bronze, 'raw_mental_health.csv')
    df = pd.read_csv(BytesIO(response.read()))
    response.close()
    response.release_conn()
    
    print(f"📊 Dados carregados: {len(df)} linhas")
    
    # Normaliza Gender
    if 'Gender' in df.columns:
        df['Gender'] = df['Gender'].apply(normalize_gender)
        print(f"✅ Gender normalizado")
    
    # Limpa Age
    if 'Age' in df.columns:
        df['Age'].fillna(df['Age'].median(), inplace=True)
        original_count = len(df)
        df = df[(df['Age'] >= age_min) & (df['Age'] <= age_max)]
        print(f"✅ Age filtrado: {original_count - len(df)} outliers removidos")
    
    # Trata nulos
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col].fillna('Unknown', inplace=True)
    
    # Salva como Parquet
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
    parquet_data = parquet_buffer.getvalue()
    
    client.put_object(
        bucket_silver,
        'mental_health_clean.parquet',
        BytesIO(parquet_data),
        length=len(parquet_data),
        content_type='application/octet-stream'
    )
    
    print(f"✅ Camada Silver concluída: {len(df)} linhas salvas")
    return "Silver layer processado"


def run_gold_layer():
    """Task 4: Executa camada Gold (agregações analíticas)."""
    print("🏆 Executando camada Gold...")
    
    client = get_minio_client()
    bucket_silver = os.getenv('BUCKET_SILVER', 'silver')
    bucket_gold = os.getenv('BUCKET_GOLD', 'gold')
    
    # Lê Parquet do silver
    response = client.get_object(bucket_silver, 'mental_health_clean.parquet')
    df = pd.read_parquet(BytesIO(response.read()))
    response.close()
    response.release_conn()
    
    print(f"📊 Dados carregados: {len(df)} linhas")
    
    # Agregação 1: remote_work x treatment
    if 'remote_work' in df.columns and 'treatment' in df.columns:
        agg1 = df.groupby('remote_work')['treatment'].value_counts().unstack(fill_value=0).reset_index()
        buffer1 = BytesIO()
        agg1.to_parquet(buffer1, engine='pyarrow', index=False)
        client.put_object(
            bucket_gold,
            'agg_remote_work_treatment.parquet',
            BytesIO(buffer1.getvalue()),
            length=len(buffer1.getvalue()),
            content_type='application/octet-stream'
        )
        print(f"✅ Agregação 1 salva: {len(agg1)} grupos")
    
    # Agregação 2: distribuição por país
    if 'Country' in df.columns:
        agg2 = df['Country'].value_counts().reset_index()
        agg2.columns = ['Country', 'Count']
        buffer2 = BytesIO()
        agg2.to_parquet(buffer2, engine='pyarrow', index=False)
        client.put_object(
            bucket_gold,
            'agg_country_distribution.parquet',
            BytesIO(buffer2.getvalue()),
            length=len(buffer2.getvalue()),
            content_type='application/octet-stream'
        )
        print(f"✅ Agregação 2 salva: {len(agg2)} países")
    
    print("✅ Camada Gold concluída!")
    return "Gold layer processado"


def validate_pipeline():
    """Task 5: Valida os dados processados."""
    print("🔍 Validando pipeline...")
    
    client = get_minio_client()
    
    try:
        # Bronze
        client.stat_object('bronze', 'raw_mental_health.csv')
        print("✅ Bronze: raw_mental_health.csv encontrado")
        
        # Silver
        client.stat_object('silver', 'mental_health_clean.parquet')
        print("✅ Silver: mental_health_clean.parquet encontrado")
        
        # Gold
        client.stat_object('gold', 'agg_remote_work_treatment.parquet')
        client.stat_object('gold', 'agg_country_distribution.parquet')
        print("✅ Gold: Agregações encontradas")
        
        print("✅ Validação concluída com sucesso!")
        return "Pipeline validado"
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        raise


# Definição das Tasks
task_init_minio = PythonOperator(
    task_id='initialize_minio',
    python_callable=initialize_minio,
    dag=dag,
)

task_bronze = PythonOperator(
    task_id='bronze_layer',
    python_callable=run_bronze_layer,
    dag=dag,
)

task_silver = PythonOperator(
    task_id='silver_layer',
    python_callable=run_silver_layer,
    dag=dag,
)

task_gold = PythonOperator(
    task_id='gold_layer',
    python_callable=run_gold_layer,
    dag=dag,
)

task_validate = PythonOperator(
    task_id='validate_pipeline',
    python_callable=validate_pipeline,
    dag=dag,
)

# Task de notificação final (bash simples)
task_notify = BashOperator(
    task_id='notify_completion',
    bash_command='echo "🎉 Pipeline ETL Tech Minds Analytics concluído com sucesso!"',
    dag=dag,
)

# Definição do fluxo (dependencies)
task_init_minio >> task_bronze >> task_silver >> task_gold >> task_validate >> task_notify
