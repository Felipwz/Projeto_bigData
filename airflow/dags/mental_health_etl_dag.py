"""
Tech Minds Analytics - Airflow DAG
Pipeline ETL automatizado para processar dados de saúde mental na tecnologia.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from etl import MinIOETL, bronze_layer, silver_layer, gold_layer

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


def initialize_minio():
    """Task 1: Inicializa conexão com MinIO e cria buckets."""
    print("🔧 Inicializando MinIO...")
    
    etl_client = MinIOETL()
    buckets = [
        os.getenv('BUCKET_BRONZE', 'bronze'),
        os.getenv('BUCKET_SILVER', 'silver'),
        os.getenv('BUCKET_GOLD', 'gold')
    ]
    etl_client.ensure_buckets_exist(buckets)
    
    print("✅ MinIO inicializado com sucesso!")
    return "MinIO pronto"


def run_bronze_layer():
    """Task 2: Executa camada Bronze (ingestão de dados brutos)."""
    print("📥 Executando camada Bronze...")
    
    etl_client = MinIOETL()
    bronze_layer(etl_client)
    
    print("✅ Camada Bronze concluída!")
    return "Bronze layer processado"


def run_silver_layer():
    """Task 3: Executa camada Silver (limpeza e padronização)."""
    print("🧹 Executando camada Silver...")
    
    etl_client = MinIOETL()
    silver_layer(etl_client)
    
    print("✅ Camada Silver concluída!")
    return "Silver layer processado"


def run_gold_layer():
    """Task 4: Executa camada Gold (agregações analíticas)."""
    print("🏆 Executando camada Gold...")
    
    etl_client = MinIOETL()
    gold_layer(etl_client)
    
    print("✅ Camada Gold concluída!")
    return "Gold layer processado"


def validate_pipeline():
    """Task 5: Valida os dados processados."""
    print("🔍 Validando pipeline...")
    
    etl_client = MinIOETL()
    
    # Verifica se os arquivos existem
    try:
        # Bronze
        etl_client.client.stat_object('bronze', 'raw_mental_health.csv')
        print("✅ Bronze: raw_mental_health.csv encontrado")
        
        # Silver
        etl_client.client.stat_object('silver', 'mental_health_clean.parquet')
        print("✅ Silver: mental_health_clean.parquet encontrado")
        
        # Gold
        etl_client.client.stat_object('gold', 'agg_remote_work_treatment.parquet')
        etl_client.client.stat_object('gold', 'agg_country_distribution.parquet')
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
