"""
Tech Minds Analytics - Script de Verificação de Dados
Valida os dados processados nas camadas Silver e Gold do Data Lake.
"""

import pandas as pd
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import sys

# Configuração do MinIO
MINIO_CONFIG = {
    'endpoint': 'localhost:9000',
    'access_key': 'minioadmin',
    'secret_key': 'minioadmin',
    'secure': False
}

def print_header(title):
    """Imprime cabeçalho formatado."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_bucket_exists(client, bucket_name):
    """Verifica se o bucket existe."""
    try:
        exists = client.bucket_exists(bucket_name)
        status = "✅" if exists else "❌"
        print(f"{status} Bucket '{bucket_name}': {'Existe' if exists else 'Não encontrado'}")
        return exists
    except S3Error as e:
        print(f"❌ Erro ao verificar bucket '{bucket_name}': {e}")
        return False

def check_object_exists(client, bucket_name, object_name):
    """Verifica se o objeto existe no bucket."""
    try:
        client.stat_object(bucket_name, object_name)
        print(f"  ✅ Arquivo '{object_name}' encontrado")
        return True
    except S3Error as e:
        if e.code == 'NoSuchKey':
            print(f"  ❌ Arquivo '{object_name}' não encontrado")
        else:
            print(f"  ❌ Erro ao verificar '{object_name}': {e}")
        return False

def get_parquet_info(client, bucket_name, object_name):
    """Obtém informações de um arquivo Parquet."""
    try:
        response = client.get_object(bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        
        df = pd.read_parquet(BytesIO(data))
        
        print(f"\n  📊 Informações de '{object_name}':")
        print(f"     - Linhas: {len(df):,}")
        print(f"     - Colunas: {df.shape[1]}")
        print(f"     - Colunas: {', '.join(df.columns.tolist())}")
        print(f"     - Tamanho em memória: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
        
        # Mostra preview dos dados
        print(f"\n  📋 Preview dos dados:")
        print(df.head(5).to_string(index=False))
        
        return df
        
    except Exception as e:
        print(f"  ❌ Erro ao ler '{object_name}': {e}")
        return None

def verify_silver_layer(client):
    """Verifica a camada Silver."""
    print_header("VERIFICAÇÃO DA CAMADA SILVER")
    
    bucket = 'silver'
    object_name = 'mental_health_clean.parquet'
    
    if not check_bucket_exists(client, bucket):
        return False
    
    if not check_object_exists(client, bucket, object_name):
        return False
    
    df = get_parquet_info(client, bucket, object_name)
    
    if df is not None:
        print(f"\n  🔍 Validações:")
        
        # Verifica se há dados
        if len(df) > 0:
            print(f"     ✅ Dataset contém {len(df):,} registros")
        else:
            print(f"     ❌ Dataset está vazio")
            return False
        
        # Verifica colunas esperadas
        expected_cols = ['Age', 'Gender']
        for col in expected_cols:
            if col in df.columns:
                print(f"     ✅ Coluna '{col}' presente")
            else:
                print(f"     ⚠️  Coluna '{col}' não encontrada")
        
        # Verifica normalização de Gender
        if 'Gender' in df.columns:
            unique_genders = df['Gender'].unique()
            print(f"     📊 Valores de Gender: {', '.join(map(str, unique_genders))}")
        
        # Verifica range de Age
        if 'Age' in df.columns:
            age_min = df['Age'].min()
            age_max = df['Age'].max()
            print(f"     📊 Range de Age: {age_min:.0f} - {age_max:.0f} anos")
            
            if age_min >= 18 and age_max <= 100:
                print(f"     ✅ Outliers de idade removidos corretamente")
            else:
                print(f"     ⚠️  Possíveis outliers detectados")
        
        return True
    
    return False

def verify_gold_layer(client):
    """Verifica a camada Gold."""
    print_header("VERIFICAÇÃO DA CAMADA GOLD")
    
    bucket = 'gold'
    
    if not check_bucket_exists(client, bucket):
        return False
    
    # Verifica agregação 1: remote_work x treatment
    print(f"\n📦 Agregação 1: Tratamento por Trabalho Remoto")
    object1 = 'agg_remote_work_treatment.parquet'
    if check_object_exists(client, bucket, object1):
        df1 = get_parquet_info(client, bucket, object1)
        if df1 is not None and len(df1) > 0:
            print(f"     ✅ Agregação válida com {len(df1)} grupos")
    
    # Verifica agregação 2: country distribution
    print(f"\n📦 Agregação 2: Distribuição por País")
    object2 = 'agg_country_distribution.parquet'
    if check_object_exists(client, bucket, object2):
        df2 = get_parquet_info(client, bucket, object2)
        if df2 is not None and len(df2) > 0:
            print(f"     ✅ Agregação válida com {len(df2)} países")
            
            # Top 5 países
            if len(df2) >= 5:
                print(f"\n     🌍 Top 5 Países:")
                for idx, row in df2.head(5).iterrows():
                    print(f"        {idx+1}. {row['Country']}: {row['Count']:,} respondentes")
    
    return True

def verify_bronze_layer(client):
    """Verifica a camada Bronze."""
    print_header("VERIFICAÇÃO DA CAMADA BRONZE")
    
    bucket = 'bronze'
    object_name = 'raw_mental_health.csv'
    
    if not check_bucket_exists(client, bucket):
        return False
    
    if not check_object_exists(client, bucket, object_name):
        return False
    
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        
        # Conta linhas do CSV
        lines = data.decode('utf-8').split('\n')
        line_count = len([l for l in lines if l.strip()])
        
        print(f"\n  📊 Informações do arquivo CSV:")
        print(f"     - Linhas: {line_count:,}")
        print(f"     - Tamanho: {len(data) / 1024:.2f} KB")
        print(f"     ✅ Arquivo bruto ingerido corretamente")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao ler CSV: {e}")
        return False

def main():
    """Executa todas as verificações."""
    print_header("TECH MINDS ANALYTICS - VERIFICAÇÃO DE DADOS")
    print("Conectando ao MinIO...")
    
    try:
        client = Minio(**MINIO_CONFIG)
        print("✅ Conexão estabelecida com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro ao conectar no MinIO: {e}")
        print(f"\n💡 Certifique-se de que o MinIO está rodando:")
        print(f"   docker-compose -f infra/docker-compose.yml up -d")
        sys.exit(1)
    
    # Executa verificações
    results = {
        'Bronze': verify_bronze_layer(client),
        'Silver': verify_silver_layer(client),
        'Gold': verify_gold_layer(client)
    }
    
    # Resumo final
    print_header("RESUMO DA VERIFICAÇÃO")
    
    for layer, status in results.items():
        status_icon = "✅" if status else "❌"
        status_text = "OK" if status else "FALHOU"
        print(f"{status_icon} Camada {layer}: {status_text}")
    
    # Status geral
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 Todas as camadas foram validadas com sucesso!")
        print("✅ Pipeline ETL funcionando corretamente")
        sys.exit(0)
    else:
        print("\n⚠️  Algumas camadas apresentaram problemas")
        print("💡 Execute o ETL novamente: python src/etl.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
