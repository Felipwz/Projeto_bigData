"""
Script para carregar dados do MinIO (bronze, silver, gold) para PostgreSQL
Permite visualização no Metabase através de tabelas SQL

Uso:
  - Dentro do Docker: python src/load_to_postgres.py
  - Fora do Docker: docker-compose exec -T airflow-scheduler python src/load_to_postgres.py
"""

import pandas as pd
import psycopg2
from psycopg2 import sql
from minio import Minio
from io import BytesIO
import logging
import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgresLoader:
    """Classe para carregar dados do MinIO para PostgreSQL."""
    
    def __init__(self):
        """Inicializa conexões com MinIO e PostgreSQL."""
        # Configuração MinIO - use 'minio' para Docker, 'localhost:9000' para host local
        minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.minio_client = Minio(
            endpoint=minio_endpoint,
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            secure=False
        )
        logger.info(f"Conectado ao MinIO em {minio_endpoint}")
        
        # Configuração PostgreSQL - use 'postgres' para Docker, 'localhost' para host local
        postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        postgres_db = os.getenv('POSTGRES_DB', 'airflow')
        postgres_user = os.getenv('POSTGRES_USER', 'airflow')
        postgres_password = os.getenv('POSTGRES_PASSWORD', 'airflow')
        
        try:
            self.postgres_conn = psycopg2.connect(
                host=postgres_host,
                port=postgres_port,
                database=postgres_db,
                user=postgres_user,
                password=postgres_password
            )
            self.postgres_conn.autocommit = True
            self.cursor = self.postgres_conn.cursor()
            logger.info(f"Conectado ao PostgreSQL em {postgres_host}:{postgres_port}/{postgres_db}")
        except psycopg2.OperationalError as e:
            logger.error(f"❌ Erro ao conectar ao PostgreSQL: {e}")
            logger.error("\n📋 COMO EXECUTAR ESTE SCRIPT:")
            logger.error("  1. VIA DOCKER (recomendado):")
            logger.error("     cd /home/guima/Documents/Projeto_bigData/infra")
            logger.error("     docker-compose exec -T airflow-scheduler python /opt/airflow/src/load_to_postgres.py")
            logger.error("\n  2. OU DENTRO DO CONTAINER DIRETAMENTE:")
            logger.error("     docker exec -it tech-minds-airflow-scheduler python /opt/airflow/src/load_to_postgres.py")
            raise
    
    def get_dataframe_from_minio(self, bucket_name, object_name):
        """
        Baixa arquivo do MinIO e retorna DataFrame.
        
        Args:
            bucket_name: Nome do bucket
            object_name: Nome do arquivo
            
        Returns:
            DataFrame carregado
        """
        try:
            response = self.minio_client.get_object(bucket_name, object_name)
            file_data = response.read()
            response.close()
            
            # Determina formato pelo nome do arquivo
            if object_name.endswith('.csv'):
                df = pd.read_csv(BytesIO(file_data))
            elif object_name.endswith('.parquet'):
                df = pd.read_parquet(BytesIO(file_data))
            else:
                raise ValueError(f"Formato desconhecido: {object_name}")
            
            logger.info(f"Carregado {len(df)} linhas de {bucket_name}/{object_name}")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao carregar {bucket_name}/{object_name}: {e}")
            raise
    
    def create_table_from_dataframe(self, table_name, df, drop_if_exists=True):
        """
        Cria tabela no PostgreSQL baseada no DataFrame.
        
        Args:
            table_name: Nome da tabela
            df: DataFrame com os dados
            drop_if_exists: Se deve droppar tabela existente
        """
        # Drop se existir
        if drop_if_exists:
            self.cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            ))
            logger.info(f"Tabela '{table_name}' deletada (se existia)")
        
        # Mapear tipos pandas para PostgreSQL
        # Usar TEXT para tudo para evitar problemas de conversão
        type_map = {
            'int64': 'BIGINT',
            'int32': 'INTEGER',
            'int16': 'SMALLINT',
            'float64': 'DECIMAL',
            'float32': 'DECIMAL',
            'bool': 'BOOLEAN',
            'object': 'TEXT',
            'datetime64[ns]': 'TIMESTAMP'
        }
        
        # Construir comando CREATE TABLE
        columns = []
        for col_name, dtype in df.dtypes.items():
            # Sanitizar nome da coluna
            col_name_safe = col_name.replace(' ', '_').replace('-', '_').lower()
            
            # Tenta mapear o tipo, caso contrário usa TEXT
            pg_type = type_map.get(str(dtype), 'TEXT')
            
            # Para colunas object (texto), sempre usa TEXT
            if dtype == 'object':
                pg_type = 'TEXT'
            
            columns.append(f"{col_name_safe} {pg_type}")
        
        create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
        
        try:
            self.cursor.execute(create_sql)
            logger.info(f"Tabela '{table_name}' criada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar tabela '{table_name}': {e}")
            raise
    
    def insert_dataframe_to_table(self, table_name, df):
        """
        Insere dados do DataFrame na tabela PostgreSQL.
        
        Args:
            table_name: Nome da tabela
            df: DataFrame com os dados
        """
        # Sanitizar nomes de colunas
        df.columns = [col.replace(' ', '_').replace('-', '_').lower() for col in df.columns]
        
        # Converter todos os dados para strings/objetos para evitar overflow
        # Isso é mais seguro já que a tabela aceita TEXT
        df = df.astype(str)
        
        # Preparar inserção
        records = df.values.tolist()
        columns = list(df.columns)
        
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        try:
            # Inserir em batches para evitar problemas de memória
            batch_size = 500
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                self.cursor.executemany(insert_sql, batch)
            
            logger.info(f"Inseridos {len(records)} registros na tabela '{table_name}'")
        except Exception as e:
            logger.error(f"Erro ao inserir dados em '{table_name}': {e}")
            logger.error(f"Detalhes: {df.dtypes}")
            raise
    
    def load_bronze_to_postgres(self):
        """Carrega camada Bronze para PostgreSQL."""
        logger.info("=== CARREGANDO CAMADA BRONZE ===")
        
        bucket = os.getenv('BUCKET_BRONZE', 'bronze')
        try:
            df = self.get_dataframe_from_minio(bucket, 'raw_mental_health.csv')
            self.create_table_from_dataframe('bronze_layer', df)
            self.insert_dataframe_to_table('bronze_layer', df)
            logger.info("Camada Bronze carregada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar Bronze: {e}")
            raise
    
    def load_silver_to_postgres(self):
        """Carrega camada Silver para PostgreSQL."""
        logger.info("=== CARREGANDO CAMADA SILVER ===")
        
        bucket = os.getenv('BUCKET_SILVER', 'silver')
        try:
            df = self.get_dataframe_from_minio(bucket, 'mental_health_clean.parquet')
            self.create_table_from_dataframe('silver_layer', df)
            self.insert_dataframe_to_table('silver_layer', df)
            logger.info("Camada Silver carregada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar Silver: {e}")
            raise
    
    def load_gold_to_postgres(self):
        """Carrega camada Gold para PostgreSQL."""
        logger.info("=== CARREGANDO CAMADA GOLD ===")
        
        bucket = os.getenv('BUCKET_GOLD', 'gold')
        
        # Tabela 1: Agregação por Remote Work e Treatment
        try:
            df = self.get_dataframe_from_minio(bucket, 'agg_remote_work_treatment.parquet')
            self.create_table_from_dataframe('gold_remote_work_treatment', df)
            self.insert_dataframe_to_table('gold_remote_work_treatment', df)
            logger.info("Agregação Remote Work/Treatment carregada")
        except Exception as e:
            logger.warning(f"Tabela 'agg_remote_work_treatment' não encontrada: {e}")
        
        # Tabela 2: Agregação por País
        try:
            df = self.get_dataframe_from_minio(bucket, 'agg_country_distribution.parquet')
            self.create_table_from_dataframe('gold_country_distribution', df)
            self.insert_dataframe_to_table('gold_country_distribution', df)
            logger.info("Agregação Country Distribution carregada")
        except Exception as e:
            logger.warning(f"Tabela 'agg_country_distribution' não encontrada: {e}")
        
        logger.info("Camada Gold carregada com sucesso")
    
    def load_all(self):
        """Carrega todas as camadas para PostgreSQL."""
        try:
            self.load_bronze_to_postgres()
            self.load_silver_to_postgres()
            self.load_gold_to_postgres()
            logger.info("=== TODAS AS CAMADAS CARREGADAS COM SUCESSO ===")
        except Exception as e:
            logger.error(f"Erro geral: {e}")
            raise
        finally:
            self.close()
    
    def close(self):
        """Fecha conexões."""
        if self.cursor:
            self.cursor.close()
        if self.postgres_conn:
            self.postgres_conn.close()
        logger.info("Conexões fechadas")


if __name__ == '__main__':
    loader = PostgresLoader()
    loader.load_all()
