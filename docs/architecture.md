# Arquitetura do Sistema - Tech Minds Analytics

## Visão Geral

O sistema implementa uma arquitetura de **Data Lake** com três camadas (Medallion Architecture), processando dados de saúde mental de profissionais de tecnologia desde a ingestão bruta até agregações analíticas.

---

## Diagrama de Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                        FONTE DE DADOS                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ mental_health.csv
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CAMADA BRONZE (Raw Data)                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MinIO Bucket: bronze/                                     │  │
│  │  Arquivo: raw_mental_health.csv                            │  │
│  │  Formato: CSV                                              │  │
│  │  Transformações: Nenhuma (dados brutos)                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ ETL Process
                         │ • Normalização de Gender
                         │ • Filtro de Age (18-100)
                         │ • Tratamento de nulos
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CAMADA SILVER (Cleaned Data)                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MinIO Bucket: silver/                                     │  │
│  │  Arquivo: mental_health_clean.parquet                      │  │
│  │  Formato: Parquet (compressão snappy)                      │  │
│  │  Qualidade: Dados validados e padronizados                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ Aggregation Process
                         │ • Group by remote_work + treatment
                         │ • Count by Country
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                 CAMADA GOLD (Analytics-Ready)                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MinIO Bucket: gold/                                       │  │
│  │  Arquivos:                                                 │  │
│  │    • agg_remote_work_treatment.parquet                     │  │
│  │    • agg_country_distribution.parquet                      │  │
│  │  Formato: Parquet                                          │  │
│  │  Uso: Dashboards, relatórios, análises                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CAMADA DE VISUALIZAÇÃO                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Metabase      │  │  Jupyter        │  │  Verificação    │  │
│  │   Dashboard     │  │  Notebooks      │  │  de Qualidade   │  │
│  │   (BI)          │  │  (EDA)          │  │  (Python)       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Componentes do Sistema

### 1. Data Lake (MinIO)

**Tecnologia:** MinIO (S3-compatible object storage)  
**Portas:** 9000 (API), 9001 (Console Web)  
**Credenciais:** minioadmin / minioadmin

**Buckets:**
- `bronze`: Dados brutos, sem transformações
- `silver`: Dados limpos e validados
- `gold`: Dados agregados para análise

**Formato dos Dados:**
- Bronze: CSV (preserva formato original)
- Silver/Gold: Parquet (compressão, schema, performance)

### 2. Pipeline ETL (Python)

**Tecnologia:** Python 3.11 + Pandas  
**Arquivo:** `src/etl.py`

**Responsabilidades:**
- Conexão com MinIO
- Ingestão de dados brutos
- Limpeza e transformação
- Validação de qualidade
- Geração de agregações

**Configuração:** Arquivo `.env` com variáveis de ambiente

### 3. Dashboard (Metabase)

**Tecnologia:** Metabase (open-source BI)  
**Porta:** 3000  
**Uso:** Visualização de KPIs e métricas

**Conecta-se a:** Dados das camadas Silver e Gold

### 4. Análise Exploratória (Jupyter)

**Tecnologia:** Jupyter Notebook  
**Arquivo:** `notebooks/01_exploratory_analysis.ipynb`

**Conteúdo:**
- Estatísticas descritivas
- Distribuições
- Correlações
- Visualizações

### 5. Validação (Script Python)

**Arquivo:** `src/verify_gold_data.py`

**Responsabilidades:**
- Verificar existência de buckets
- Validar dados processados
- Checar integridade dos arquivos
- Gerar relatório de status

---

## Fluxo de Dados Detalhado

### Fase 1: Ingestão (Bronze Layer)

```python
Input:  datasets/mental_health.csv (CSV local)
Output: bronze/raw_mental_health.csv
```

**Operações:**
1. Leitura do arquivo CSV local
2. Upload direto para MinIO (sem transformações)
3. Preservação do formato original

**Objetivo:** Manter dados brutos para auditoria e reprocessamento

---

### Fase 2: Limpeza (Silver Layer)

```python
Input:  bronze/raw_mental_health.csv
Output: silver/mental_health_clean.parquet
```

**Transformações:**

| Campo | Transformação | Exemplo |
|-------|---------------|---------|
| Gender | Normalização para Male/Female/Other | "cis male" → "Male" |
| Age | Filtro: 18 ≤ age ≤ 100 | 999 → removido |
| Age (nulos) | Preenchimento com mediana | null → 32 |
| Campos texto | Preenchimento com "Unknown" | null → "Unknown" |

**Objetivo:** Dados confiáveis para análise

---

### Fase 3: Agregação (Gold Layer)

```python
Input:  silver/mental_health_clean.parquet
Output: gold/agg_*.parquet
```

**Agregações:**

1. **Tratamento por Trabalho Remoto**
   - Arquivo: `agg_remote_work_treatment.parquet`
   - Grupo: `remote_work`
   - Métrica: Count de `treatment` (Yes/No)

2. **Distribuição por País**
   - Arquivo: `agg_country_distribution.parquet`
   - Grupo: `Country`
   - Métrica: Count de respondentes

**Objetivo:** Dados prontos para dashboards

---

## Estratégias de Governança

### Catalogação

- **Bronze:** Dados originais catalogados com timestamp
- **Silver:** Schema validado (Parquet)
- **Gold:** Documentação de métricas

### Qualidade de Dados

- **Validação:** Script `verify_gold_data.py`
- **Outliers:** Remoção automática (Age)
- **Nulos:** Estratégia de preenchimento documentada
- **Tipagem:** Schema forte no Parquet

### Versionamento

**Atual:** Nome fixo de arquivos (sobrescreve)  
**Futuro:** Delta Lake para versionamento completo

---

## Infraestrutura

### Docker Compose

```yaml
Serviços:
  - minio:     Storage (Data Lake)
  - metabase:  Dashboard (BI)
  - etl-runner: Container Python (opcional)
```

### Volumes

```
minio_data:     Persistência do Data Lake
metabase_data:  Banco H2 do Metabase
```

### Network

```
tech-minds-network: Bridge network interna
```

---

## Decisões de Design

### Por que Pandas em vez de Spark?

**Decisão:** Pandas  
**Justificativa:**
- Dataset pequeno (~1200 registros)
- Setup mais simples
- Menor overhead de infraestrutura
- Adequado para protótipo acadêmico

**Trade-off:** Não escala para datasets > 10GB

### Por que Parquet?

**Decisão:** Parquet para Silver/Gold  
**Justificativa:**
- Compressão ~60% vs CSV
- Leitura colunar eficiente
- Schema tipado
- Compatível com todo ecossistema Big Data

**Trade-off:** Não é human-readable (precisa de ferramentas)

### Por que MinIO?

**Decisão:** MinIO como Data Lake  
**Justificativa:**
- API compatível com S3 (facilita migração)
- Open-source e gratuito
- Docker-friendly
- Excelente para ambientes locais

**Trade-off:** Menor conjunto de features vs S3 real

---

## Pontos de Extensão

### Adicionar Nova Agregação

1. Editar função `gold_layer()` em `etl.py`
2. Adicionar novo DataFrame agregado
3. Salvar como `.parquet` no bucket gold
4. Atualizar documentação

### Adicionar Nova Transformação

1. Editar função `silver_layer()` em `etl.py`
2. Aplicar transformação no DataFrame
3. Documentar regra de negócio
4. Validar com `verify_gold_data.py`

### Integrar Nova Fonte

1. Criar novo script de ingestão
2. Upload para bucket bronze
3. Adaptar ETL para novo schema
4. Adicionar validações específicas

---

## Monitoramento e Logs

### Logs do ETL

```python
Formato: %(asctime)s - %(levelname)s - %(message)s
Níveis: INFO (padrão), ERROR (falhas)
Saída: stdout (console)
```

### Verificação de Saúde

```bash
# Verificar containers
docker-compose ps

# Verificar dados processados
python src/verify_gold_data.py
```

---

## Limitações Conhecidas

1. **Escalabilidade:** Pandas limitado a datasets que cabem em memória
2. **Paralelismo:** Processamento single-threaded
3. **Resiliência:** Sem retry automático em falhas
4. **Versionamento:** Sobrescreve dados (não mantém histórico)
5. **Segurança:** Credenciais hardcoded (mitigado com .env)

---

**Última atualização:** Novembro 2025
