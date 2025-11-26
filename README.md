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

_[Preencher com os nomes e responsabilidades de cada membro do grupo]_

| Nome | Responsabilidade |
|------|------------------|
| _Membro 1_ | Arquitetura e ETL |
| _Membro 2_ | Análise exploratória e notebooks |
| _Membro 3_ | Infraestrutura Docker |
| _Membro 4_ | Dashboards e visualizações |
| _Membro 5_ | Documentação e testes |

---

## 📞 Suporte

Em caso de dúvidas ou problemas:

1. Verifique os logs do Docker: `docker-compose logs -f`
2. Consulte a documentação no diretório `docs/`
3. Valide os dados com `verify_gold_data.py`

---

## 📄 Licença

Este projeto é parte de um trabalho acadêmico para a disciplina de Big Data e Ciência de Dados.

---

**Última atualização:** Novembro 2025
