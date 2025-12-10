# Tech Minds Analytics

**Análise de Saúde Mental na Indústria de Tecnologia**

Pipeline completo de ETL e análise de dados sobre saúde mental em profissionais de tecnologia, utilizando arquitetura de Data Lake com camadas Bronze, Silver e Gold.

---

## 📋 Visão Geral

Este projeto implementa uma solução completa de Ciência de Dados/Big Data para análise de pesquisa sobre saúde mental em trabalhadores da área de tecnologia. O sistema coleta dados brutos, processa, limpa e agrega informações para geração de insights através de dashboards e visualizações.

### Objetivo

Analisar padrões de saúde mental na indústria tech, identificando correlações entre fatores como trabalho remoto, idade, gênero, país e busca por tratamento psicológico.

### Escopo

**Incluído:**
- Pipeline ETL automatizado (Bronze → Silver → Gold)
- Data Lake em MinIO (compatível com S3)
- Processamento de dados com Pandas
- Armazenamento em formatos CSV (raw) e Parquet (processado)
- Dashboard de visualização com Metabase
- Notebook de análise exploratória
- Infraestrutura Docker completa

**Não Incluído:**
- Processamento distribuído (Spark)
- Streaming em tempo real
- Machine Learning / Modelos preditivos
- Pipeline de CI/CD

---

**Documentação Confluence**

 - https://vitorguimap.atlassian.net/wiki/external/YTNkMWJjODljZDkzNGViZThmZjlmYjRmMGVjMWQyODk

## 🏗️ Arquitetura

```
┌─────────────────┐
│  Datasets       │ (CSV local)
│  mental_health  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  BRONZE LAYER   │ (Ingestão Bruta)
│   - MinIO       │ raw_mental_health.csv
└────────┬────────┘
         │
         ▼ [Limpeza e Padronização]
         │ • Normalização de Gender
         │ • Remoção de outliers (Age)
         │ • Tratamento de nulos
         │
┌─────────────────┐
│  SILVER LAYER   │ (Dados Limpos)
│   - MinIO       │ mental_health_clean.parquet
└────────┬────────┘
         │
         ▼ [Agregação e Métricas]
         │ • Group by remote_work + treatment
         │ • Count by Country
         │
┌─────────────────┐
│   GOLD LAYER    │ (Dados Analíticos)
│   - MinIO       │ agg_remote_work_treatment.parquet
│                 │ agg_country_distribution.parquet
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   METABASE      │ (Visualização BI)
│  Dashboards     │
└─────────────────┘
```

### Camadas do Data Lake

| Camada | Descrição | Formato | Transformações |
|--------|-----------|---------|----------------|
| **Bronze** | Dados brutos sem alterações | CSV | Nenhuma |
| **Silver** | Dados limpos e padronizados | Parquet | Normalização, limpeza, validação |
| **Gold** | Dados agregados para análise | Parquet | Agregações, métricas, KPIs |

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.11**: Linguagem principal
- **Apache Airflow 2.8**: Orquestração e agendamento de pipelines
- **Pandas**: Processamento de dados
- **MinIO**: Data Lake (storage S3-compatible)
- **PostgreSQL**: Banco de metadados do Airflow
- **Metabase**: Dashboard e BI
- **Docker**: Containerização
- **Jupyter**: Análise exploratória
- **Parquet**: Formato colunar eficiente

### Dependências Python

```
pandas==2.1.4
minio==7.2.0
pyarrow==14.0.1
matplotlib==3.8.2
seaborn==0.13.0
jupyter==1.0.0
python-dotenv==1.0.0
```

---

## 🚀 Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.11+ (para execução local do ETL)
- 4GB RAM disponível

### Passo 1: Subir a Infraestrutura

```bash
# Entre na pasta infra
cd infra

# Inicie os containers (primeira vez pode demorar ~2-3 minutos)
docker-compose up -d

# Aguarde a inicialização do Airflow
docker-compose logs -f airflow-init

# Verifique os serviços
docker-compose ps
```
**No Metabase:**

1. Clique na **engrengem (Admin)** → **Databases**  
2. Clique em **+ Add database**  
3. Selecione **PostgreSQL**  
4. Preencha os campos conforme abaixo:

   - **Database name:** `airflow`
   - **Display name:** `Airflow DB (PostgreSQL)`
   - **Host:** `postgres`
   - **Port:** `5432`
   - **Username:** `airflow`
   - **Password:** `airflow`

5. Clique em **Save**

### Configuração do Data Lake (MinIO) no Metabase

Para visualizar os dados das camadas Silver e Gold, é preciso conectar o Metabase ao MinIO. Como o Metabase não possui um conector nativo para MinIO/S3, a abordagem recomendada neste projeto é carregar os dados agregados (camada Gold) no PostgreSQL para facilitar a visualização.

1.  **Carregar Dados no PostgreSQL:**
    O projeto inclui um script para carregar os dados do MinIO para o PostgreSQL. Execute o seguinte comando no terminal, na raiz do projeto, para popular as tabelas que o Metabase irá ler.

    ```bash
    # O comando abaixo executa o script que lê os arquivos .parquet do MinIO 
    # e os insere como tabelas no banco 'airflow' do PostgreSQL.
    docker-compose -f infra/docker-compose.yml exec airflow-scheduler python /opt/airflow/src/load_to_postgres.py
    ```

2.  **Explorar no Metabase:**
    Após executar o script, novas tabelas (ex: `gold_remote_work_treatment`) estarão disponíveis no database `Airflow DB (PostgreSQL)` dentro do Metabase, prontas para serem usadas em perguntas e dashboards.

**Exemplos de consulta para o dashboard**

```
Camada Bronze

SELECT * FROM bronze_layer LIMIT 10;
SELECT COUNT(*) FROM bronze_layer;
SELECT DISTINCT gender, COUNT(*) FROM bronze_layer GROUP BY gender;
```
```
Camada Silver

SELECT * FROM silver_layer LIMIT 10;
SELECT gender, COUNT(*) FROM silver_layer GROUP BY gender;
SELECT remote_work, treatment, COUNT(*) FROM silver_layer GROUP BY remote_work, treatment;

```
Camada Gold

SELECT * FROM gold_remote_work_treatment;
SELECT * FROM gold_country_distribution ORDER BY count DESC LIMIT 10;
```
gittgt
-- Análise por faixa etária e tratamento
SELECT
    CASE
        WHEN age BETWEEN 18 AND 25 THEN '18-25'
        WHEN age BETWEEN 26 AND 35 THEN '26-35'
        WHEN age BETWEEN 36 AND 45 THEN '36-45'
        WHEN age BETWEEN 46 AND 60 THEN '46-60'
        ELSE '60+'
    END as faixa_etaria,
    treatment,
    COUNT(*) as quantidade
FROM silver_layer
GROUP BY faixa_etaria, treatment
ORDER BY faixa_etaria, treatment;

Comando para alimentar Postgres com os dados do minio

Alterar de acordo com o computador o path
cd /home/guima/Documents/Projeto_bigData/infra && docker-compose exec -T airflow-scheduler python /opt/airflow/src/load_to_postgres.py 2>&1 | tail -30

**Serviços disponíveis:**
- **Airflow UI**: http://localhost:8080 (admin / admin)
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin)
- **MinIO API**: http://localhost:9000
- **Metabase**: http://localhost:3000

### Passo 2: Instalar Dependências Python

```bash
# Retorne à raiz do projeto
cd ..

# Crie um ambiente virtual (opcional mas recomendado)
python -m venv venv
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instale as dependências
pip install -r requirements.txt
```

### Passo 3: Executar o Pipeline ETL

**Opção A - Via Airflow (Recomendado):**
```bash
# 1. Acesse a UI do Airflow: http://localhost:8080
# 2. Login: admin / admin
# 3. Ative a DAG "mental_health_etl_pipeline"
# 4. Clique em "Trigger DAG" para executar
```

**Opção B - Execução Manual:**
```bash
# Execute o script ETL diretamente
python src/etl.py
```

O pipeline executa:
1. Criar buckets no MinIO (bronze, silver, gold)
2. Ler `datasets/mental_health.csv`
3. Processar dados através das 3 camadas
4. Gerar agregações finais
5. Validar dados processados

### Passo 4: Explorar os Dados

**Opção A - Verificar dados processados:**
```bash
python src/verify_gold_data.py
```

**Opção B - Notebook Jupyter:**
```bash
jupyter notebook notebooks/01_exploratory_analysis.ipynb
```

**Opção C - Metabase:**
1. Acesse http://localhost:3000
2. Configure conexão com MinIO
3. Explore os dados das camadas Silver e Gold

---

## 📁 Estrutura do Projeto

```
Projeto_Final/
├── airflow/                     # Apache Airflow
│   ├── dags/                    # DAGs do Airflow
│   │   └── mental_health_etl_dag.py
│   ├── logs/                    # Logs de execução
│   └── plugins/                 # Plugins customizados
├── datasets/                    # Dados brutos
│   └── mental_health.csv
├── src/                         # Código-fonte
│   ├── etl.py                   # Pipeline ETL principal
│   └── verify_gold_data.py      # Script de verificação
├── notebooks/                   # Análises exploratórias
│   └── 01_exploratory_analysis.ipynb
├── infra/                       # Infraestrutura
│   ├── docker-compose.yml       # Orquestração (Airflow, MinIO, Metabase, PostgreSQL)
│   └── Dockerfile               # Imagem Python customizada
├── docs/                        # Documentação técnica
│   ├── architecture.md          # Detalhes da arquitetura
│   ├── data_dictionary.md       # Dicionário de dados
│   └── airflow_guide.md         # Guia do Airflow
├── requirements.txt             # Dependências Python
├── .env.example                 # Exemplo de variáveis de ambiente
└── README.md                    # Este arquivo
```

---

## 📊 Descrição dos Dados

### Dataset Original

**Fonte:** Pesquisa sobre saúde mental em trabalhadores de tecnologia  
**Formato:** CSV  
**Tamanho:** ~1200 registros, 27 colunas

### Principais Colunas

| Coluna | Tipo | Descrição | Transformações |
|--------|------|-----------|----------------|
| `Age` | int | Idade do respondente | Filtro: 18-100 anos, preenchimento de nulos com mediana |
| `Gender` | string | Identidade de gênero | Normalização: Male/Female/Other |
| `Country` | string | País de residência | Preenchimento de nulos: "Unknown" |
| `remote_work` | string | Trabalha remotamente (Yes/No) | Preenchimento de nulos: "Unknown" |
| `treatment` | string | Buscou tratamento (Yes/No) | Preenchimento de nulos: "Unknown" |
| `tech_company` | string | Trabalha em empresa tech | Preenchimento de nulos: "Unknown" |

### Agregações Geradas (Gold Layer)

1. **agg_remote_work_treatment.parquet**
   - Cruzamento: trabalho remoto × busca por tratamento
   - Uso: Analisar impacto do trabalho remoto na saúde mental

2. **agg_country_distribution.parquet**
   - Distribuição geográfica dos respondentes
   - Uso: Identificar países com maior participação

---

## 🔧 Decisões Técnicas

### Por que MinIO?

- **Compatibilidade S3**: Facilita migração para AWS/Azure no futuro
- **Open-source**: Sem custos de licença
- **Performance**: Otimizado para object storage
- **Docker-friendly**: Fácil setup local

### Por que Parquet?

- **Compressão**: ~60% menor que CSV
- **Performance**: Leitura colunar eficiente
- **Schema**: Tipagem forte de dados
- **Compatível**: Funciona com Spark, Pandas, DuckDB, etc.

### Por que Metabase?

- **Open-source**: Gratuito e extensível
- **Setup rápido**: Funciona out-of-the-box
- **SQL-friendly**: Queries diretas nos dados
- **Alternativa considerada**: Grafana (mais focado em métricas de infraestrutura)

---

## ⚠️ Limitações e Pontos de Falha

### Limitações Conhecidas

1. **Escalabilidade**: Pandas não é ideal para datasets > 10GB
   - **Mitigação futura**: Migrar para PySpark
   
2. **Resiliência**: ETL falha completamente se um bucket não existir
   - **Mitigação**: Script cria buckets automaticamente
   
3. **Versionamento**: Não há controle de versão dos dados
   - **Mitigação futura**: Implementar Delta Lake

4. **Monitoramento**: Ausência de alertas e métricas
   - **Mitigação futura**: Integrar Prometheus + Grafana

### Pontos de Falha

- **MinIO offline**: ETL falha completamente
- **Arquivo CSV corrompido**: Bronze layer falha
- **Colunas faltantes**: Silver/Gold podem quebrar
- **Memória insuficiente**: Pandas pode travar com datasets grandes

---

## 🧪 Testes e Validação

### Verificar Dados Processados

```bash
python src/verify_gold_data.py
```

Este script valida:
- ✅ Existência dos buckets
- ✅ Presença dos arquivos nas camadas
- ✅ Integridade dos dados Parquet
- ✅ Contagem de registros

---

## 📈 Melhorias Futuras

- [ ] Adicionar Apache Airflow para orquestração
- [ ] Refinar a orquestração com Airflow (ex: adicionar alertas em caso de falha, usar XComs para passar metadados entre tarefas)
- [ ] Implementar testes unitários (pytest)
- [ ] Adicionar Great Expectations para data quality
- [ ] Migrar para PySpark para escalabilidade
- [ ] Implementar Delta Lake para versionamento
- [ ] Adicionar API REST (FastAPI) para servir dados
- [ ] Criar pipeline de ML para predição de risco
- [ ] Implementar CDC (Change Data Capture)

---

## 👥 Equipe

### Responsabilidades Individuais

Cada membro do grupo é responsável por explicar sua área específica durante a apresentação:

| Membro | Área de Responsabilidade | Componentes | O que Explicar na Apresentação |
|--------|--------------------------|-------------|--------------------------------|
| **Natan** | **Arquitetura & Pipeline ETL** | • Data Lake (MinIO)<br>• Pipeline Bronze→Silver→Gold<br>• `src/etl.py` | • Como funciona a arquitetura Medallion<br>• Transformações em cada camada<br>• Por que MinIO e Parquet<br>• Fluxo de dados completo |
| **Leonardo** | **Orquestração & Automação** | • Apache Airflow<br>• DAG (`mental_health_etl_dag.py`)<br>• Agendamento | • Como o Airflow orquestra o pipeline<br>• Tasks e dependências<br>• Agendamento @daily<br>• Monitoramento e logs |
| **Vitor** | **Infraestrutura & DevOps** | • Docker Compose<br>• PostgreSQL<br>• Metabase<br>• Configurações | • Como a infraestrutura funciona<br>• Serviços Docker (6 containers)<br>• Como rodar o projeto do zero<br>• Troubleshooting |
| **Luiz Felipe** | **Análise de Dados & Documentação** | • Jupyter Notebook<br>• Dicionário de dados<br>• Documentação técnica<br>• Validação | • Insights da análise exploratória<br>• Qualidade dos dados<br>• Visualizações e KPIs<br>• Estrutura da documentação |

---

## 📞 Suporte

Em caso de dúvidas ou problemas:

1. Verifique os logs do Docker: `docker-compose logs -f`
2. Consulte a documentação no diretório `docs/`
3. Valide os dados com `verify_gold_data.py`

---

##  Equipe

- Luiz Felipe S. de Souza (6324548)
- Leonardo Frazão Sano (6324073)
- Natan Borges Leme (6324696)
- Vitor Pinheiro Guimarães (6324680)


---

**Última atualização:** Dezembro 2025
