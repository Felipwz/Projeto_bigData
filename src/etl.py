"""
Tech Minds Analytics - Pipeline ETL
Processamento de dados de saúde mental na tecnologia através das camadas Bronze, Silver e Gold.
"""

import pandas as pd
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MinIOETL:
    """Classe para gerenciar o pipeline ETL com MinIO."""
    
    def __init__(self, endpoint=None, access_key=None, secret_key=None):
        """
        Inicializa a conexão com MinIO.
        
        Args:
            endpoint: Endereço do servidor MinIO (usa variável de ambiente se não fornecido)
            access_key: Chave de acesso (usa variável de ambiente se não fornecido)
            secret_key: Chave secreta (usa variável de ambiente se não fornecido)
        """
        self.endpoint = endpoint or os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.access_key = access_key or os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = secret_key or os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False
        )
        logger.info(f"Conectado ao MinIO em {self.endpoint}")
        
    def ensure_buckets_exist(self, buckets=['bronze', 'silver', 'gold']):
        """
        Garante que os buckets necessários existam, criando-os se necessário.
        
        Args:
            buckets: Lista de nomes dos buckets
        """
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Bucket '{bucket}' criado com sucesso")
                else:
                    logger.info(f"Bucket '{bucket}' já existe")
            except S3Error as e:
                logger.error(f"Erro ao verificar/criar bucket '{bucket}': {e}")
                raise
    
    def upload_to_bucket(self, bucket_name, object_name, data, content_type='application/octet-stream'):
        """
        Faz upload de dados para um bucket do MinIO.
        
        Args:
            bucket_name: Nome do bucket
            object_name: Nome do objeto no bucket
            data: Dados em bytes
            content_type: Tipo de conteúdo
        """
        try:
            self.client.put_object(
                bucket_name,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            logger.info(f"Upload concluído: {object_name} -> bucket '{bucket_name}'")
        except S3Error as e:
            logger.error(f"Erro no upload para '{bucket_name}/{object_name}': {e}")
            raise
    
    def download_from_bucket(self, bucket_name, object_name):
        """
        Faz download de dados de um bucket do MinIO.
        
        Args:
            bucket_name: Nome do bucket
            object_name: Nome do objeto no bucket
            
        Returns:
            Dados em bytes
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Download concluído: {object_name} <- bucket '{bucket_name}'")
            return data
        except S3Error as e:
            logger.error(f"Erro no download de '{bucket_name}/{object_name}': {e}")
            raise


def bronze_layer(etl_client, local_file_path=None):
    """
    CAMADA BRONZE: Ingestão de dados brutos.
    Lê o arquivo CSV local e salva no bucket bronze sem transformações.
    
    Args:
        etl_client: Instância do MinIOETL
        local_file_path: Caminho do arquivo CSV local (usa variável de ambiente se não fornecido)
    """
    logger.info("=== INICIANDO CAMADA BRONZE ===")
    
    # Usa variável de ambiente se não fornecido
    if local_file_path is None:
        local_file_path = os.getenv('DATA_PATH', './datasets/mental_health.csv')
    
    bucket_name = os.getenv('BUCKET_BRONZE', 'bronze')
    
    try:
        # Lê o arquivo local
        with open(local_file_path, 'rb') as file:
            csv_data = file.read()
        
        logger.info(f"Arquivo local '{local_file_path}' lido com sucesso ({len(csv_data)} bytes)")
        
        # Salva no bucket bronze
        etl_client.upload_to_bucket(
            bucket_name=bucket_name,
            object_name='raw_mental_health.csv',
            data=csv_data,
            content_type='text/csv'
        )
        
        logger.info("=== CAMADA BRONZE CONCLUÍDA ===")
        
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {local_file_path}")
        raise
    except Exception as e:
        logger.error(f"Erro na camada Bronze: {e}")
        raise


def normalize_gender(gender):
    """
    Normaliza valores da coluna Gender.
    
    Args:
        gender: Valor original do gênero
        
    Returns:
        Gênero normalizado (Male, Female ou Other)
    """
    if pd.isna(gender):
        return 'Other'
    
    gender_str = str(gender).lower().strip()
    
    # Mapeamento para Male
    male_variants = ['male', 'man', 'm', 'cis male', 'male (cis)', 'cis man', 'mail', 'maile', 'mal']
    if any(variant in gender_str for variant in male_variants) and 'female' not in gender_str:
        return 'Male'
    
    # Mapeamento para Female
    female_variants = ['female', 'woman', 'f', 'cis female', 'female (cis)', 'cis woman', 'femake', 'femail']
    if any(variant in gender_str for variant in female_variants):
        return 'Female'
    
    # Todos os outros casos
    return 'Other'


def silver_layer(etl_client):
    """
    CAMADA SILVER: Limpeza e padronização dos dados.
    Lê dados da bronze, aplica transformações e salva como Parquet na silver.
    
    Args:
        etl_client: Instância do MinIOETL
    """
    logger.info("=== INICIANDO CAMADA SILVER ===")
    
    bucket_bronze = os.getenv('BUCKET_BRONZE', 'bronze')
    bucket_silver = os.getenv('BUCKET_SILVER', 'silver')
    age_min = int(os.getenv('AGE_MIN', '18'))
    age_max = int(os.getenv('AGE_MAX', '100'))
    
    try:
        # Lê o CSV do bucket bronze
        csv_data = etl_client.download_from_bucket(bucket_bronze, 'raw_mental_health.csv')
        df = pd.read_csv(BytesIO(csv_data))
        
        logger.info(f"Dados carregados da Bronze: {df.shape[0]} linhas, {df.shape[1]} colunas")
        
        # Normalização de Gender
        if 'Gender' in df.columns:
            logger.info("Normalizando coluna 'Gender'")
            df['Gender'] = df['Gender'].apply(normalize_gender)
            logger.info(f"Distribuição de Gender: {df['Gender'].value_counts().to_dict()}")
        
        # Limpeza de Age (remover outliers)
        if 'Age' in df.columns:
            logger.info("Tratando coluna 'Age'")
            original_count = len(df)
            
            # Preenche valores nulos com a mediana
            age_median = df['Age'].median()
            df['Age'].fillna(age_median, inplace=True)
            
            # Remove outliers (usa variáveis de ambiente)
            df = df[(df['Age'] >= age_min) & (df['Age'] <= age_max)]
            
            removed_count = original_count - len(df)
            logger.info(f"Removidos {removed_count} registros com idade fora do intervalo [{age_min}, {age_max}]")
            logger.info(f"Idade média: {df['Age'].mean():.1f}, Mediana: {df['Age'].median():.1f}")
        
        # Tratamento de valores nulos em colunas críticas
        logger.info("Tratando valores nulos")
        for col in df.columns:
            if df[col].dtype == 'object':  # Colunas de texto
                null_count = df[col].isna().sum()
                if null_count > 0:
                    df[col].fillna('Unknown', inplace=True)
                    logger.info(f"Coluna '{col}': {null_count} valores nulos preenchidos com 'Unknown'")
        
        # Salva como Parquet no bucket silver
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
        parquet_data = parquet_buffer.getvalue()
        
        etl_client.upload_to_bucket(
            bucket_name=bucket_silver,
            object_name='mental_health_clean.parquet',
            data=parquet_data,
            content_type='application/octet-stream'
        )
        
        logger.info(f"Dados limpos salvos na Silver: {df.shape[0]} linhas, {df.shape[1]} colunas")
        logger.info("=== CAMADA SILVER CONCLUÍDA ===")
        
    except Exception as e:
        logger.error(f"Erro na camada Silver: {e}")
        raise


def gold_layer(etl_client):
    """
    CAMADA GOLD: Agregação de dados para análise de BI.
    Lê dados da silver, gera agregações e salva na gold.
    
    Args:
        etl_client: Instância do MinIOETL
    """
    logger.info("=== INICIANDO CAMADA GOLD ===")
    
    bucket_silver = os.getenv('BUCKET_SILVER', 'silver')
    bucket_gold = os.getenv('BUCKET_GOLD', 'gold')
    
    try:
        # Lê o Parquet do bucket silver
        parquet_data = etl_client.download_from_bucket(bucket_silver, 'mental_health_clean.parquet')
        df = pd.read_parquet(BytesIO(parquet_data))
        
        logger.info(f"Dados carregados da Silver: {df.shape[0]} linhas")
        
        # Agregação 1: Tratamento por trabalho remoto
        if 'remote_work' in df.columns and 'treatment' in df.columns:
            logger.info("Gerando agregação: Tratamento por Trabalho Remoto")
            
            agg_remote_treatment = df.groupby('remote_work')['treatment'].value_counts().unstack(fill_value=0)
            agg_remote_treatment = agg_remote_treatment.reset_index()
            
            # Salva agregação 1
            parquet_buffer_1 = BytesIO()
            agg_remote_treatment.to_parquet(parquet_buffer_1, engine='pyarrow', index=False)
            
            etl_client.upload_to_bucket(
                bucket_name=bucket_gold,
                object_name='agg_remote_work_treatment.parquet',
                data=parquet_buffer_1.getvalue(),
                content_type='application/octet-stream'
            )
            
            logger.info(f"Agregação 1 salva: {agg_remote_treatment.shape[0]} grupos")
        
        # Agregação 2: Distribuição por país
        if 'Country' in df.columns:
            logger.info("Gerando agregação: Distribuição por País")
            
            agg_country = df['Country'].value_counts().reset_index()
            agg_country.columns = ['Country', 'Count']
            
            # Salva agregação 2
            parquet_buffer_2 = BytesIO()
            agg_country.to_parquet(parquet_buffer_2, engine='pyarrow', index=False)
            
            etl_client.upload_to_bucket(
                bucket_name=bucket_gold,
                object_name='agg_country_distribution.parquet',
                data=parquet_buffer_2.getvalue(),
                content_type='application/octet-stream'
            )
            
            logger.info(f"Agregação 2 salva: {agg_country.shape[0]} países")
            logger.info(f"Top 5 países: {agg_country.head().to_dict('records')}")
        
        logger.info("=== CAMADA GOLD CONCLUÍDA ===")
        
    except Exception as e:
        logger.error(f"Erro na camada Gold: {e}")
        raise


def run_etl_pipeline():
    """
    Executa o pipeline ETL completo: Bronze -> Silver -> Gold.
    """
    logger.info("========================================")
    logger.info("Tech Minds Analytics - Pipeline ETL")
    logger.info("========================================")
    
    try:
        # Inicializa o cliente MinIO (usa variáveis de ambiente)
        etl_client = MinIOETL()
        
        # Garante que os buckets existam (usa variáveis de ambiente)
        buckets = [
            os.getenv('BUCKET_BRONZE', 'bronze'),
            os.getenv('BUCKET_SILVER', 'silver'),
            os.getenv('BUCKET_GOLD', 'gold')
        ]
        etl_client.ensure_buckets_exist(buckets)
        
        # Executa as camadas do pipeline
        bronze_layer(etl_client)
        silver_layer(etl_client)
        gold_layer(etl_client)
        
        logger.info("========================================")
        logger.info("Pipeline ETL concluído com sucesso!")
        logger.info("========================================")
        
    except Exception as e:
        logger.error("========================================")
        logger.error(f"Pipeline ETL falhou: {e}")
        logger.error("========================================")
        raise


if __name__ == "__main__":
    run_etl_pipeline()
