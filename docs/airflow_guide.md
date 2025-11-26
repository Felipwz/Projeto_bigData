# Guia de Uso do Apache Airflow - Tech Minds Analytics

## 📋 Visão Geral

O Apache Airflow orquestra o pipeline ETL automaticamente, executando as camadas Bronze → Silver → Gold de forma sequencial e monitorada.

---

## 🚀 Primeiro Acesso

### 1. Acessar a Interface Web

```
URL: http://localhost:8080
Usuário: admin
Senha: admin
```

### 2. Localizar a DAG

Na página principal, procure por:
```
DAG Name: mental_health_etl_pipeline
Tags: etl, mental-health, data-lake
```

### 3. Ativar a DAG

- Clique no toggle à esquerda do nome da DAG para ativá-la
- Status mudará de **OFF** para **ON**

---

## 🔄 Executar o Pipeline

### Execução Manual (Trigger)

1. Clique no nome da DAG `mental_health_etl_pipeline`
2. No canto superior direito, clique no botão **▶ Trigger DAG**
3. (Opcional) Adicione configurações customizadas
4. Clique em **Trigger**

### Execução Agendada

A DAG está configurada para executar automaticamente **diariamente** (`@daily`).

Para alterar o schedule:
```python
# Em airflow/dags/mental_health_etl_dag.py
schedule_interval='@daily'  # Opções: @hourly, @weekly, @monthly, cron expression
```

---

## 📊 Monitorar Execução

### Visualizar o Graph

1. Acesse a DAG
2. Clique na aba **Graph**
3. Veja o fluxo visual das tasks:

```
initialize_minio → bronze_layer → silver_layer → gold_layer → validate_pipeline → notify_completion
```

**Cores das Tasks:**
- 🟢 Verde escuro: Sucesso
- 🔴 Vermelho: Falha
- 🟡 Amarelo: Em execução
- ⚪ Cinza: Aguardando

### Visualizar Logs

1. Clique em qualquer task no graph
2. Selecione **Log**
3. Veja a saída detalhada da execução

**Exemplo de log esperado:**
```
[2025-11-26 10:00:00] INFO - 🔧 Inicializando MinIO...
[2025-11-26 10:00:01] INFO - ✅ Bucket 'bronze' criado com sucesso
[2025-11-26 10:00:01] INFO - ✅ MinIO inicializado com sucesso!
```

---

## 🎯 Estrutura da DAG

### Tasks Implementadas

| Task ID | Descrição | Tempo Estimado |
|---------|-----------|----------------|
| `initialize_minio` | Cria buckets no MinIO | ~2s |
| `bronze_layer` | Ingere dados brutos | ~5s |
| `silver_layer` | Limpa e padroniza dados | ~10s |
| `gold_layer` | Gera agregações | ~5s |
| `validate_pipeline` | Valida dados processados | ~3s |
| `notify_completion` | Notifica conclusão | ~1s |

**Tempo Total:** ~26 segundos

### Dependências (Order)

```python
initialize_minio >> bronze_layer >> silver_layer >> gold_layer >> validate_pipeline >> notify_completion
```

---

## ⚙️ Configurações Avançadas

### Alterar Schedule

```python
# @daily - Todo dia à meia-noite
# @hourly - A cada hora
# @weekly - Toda segunda-feira à meia-noite
# @monthly - Todo dia 1º do mês
# Cron: '0 9 * * *' - Todo dia às 9h
```

### Configurar Retries

```python
default_args = {
    'retries': 2,              # Número de tentativas
    'retry_delay': timedelta(minutes=5),  # Intervalo entre tentativas
}
```

### Notificações por Email

```python
default_args = {
    'email_on_failure': True,
    'email_on_retry': True,
    'email': ['seu-email@example.com'],
}
```

(Requer configuração de SMTP no Airflow)

---

## 🛠️ Troubleshooting

### DAG não aparece na interface

**Problema:** DAG não está sendo detectada

**Solução:**
```bash
# 1. Verifique se o arquivo está no diretório correto
ls airflow/dags/

# 2. Restart do Airflow Scheduler
docker-compose restart airflow-scheduler

# 3. Verifique logs de erros
docker-compose logs airflow-scheduler | grep ERROR
```

### Task falhando repetidamente

**Problema:** Uma task específica está falhando

**Passos:**
1. Clique na task no Graph
2. Selecione **Log**
3. Identifique a mensagem de erro
4. Verifique:
   - MinIO está rodando?
   - Arquivo CSV existe em `datasets/`?
   - Variáveis de ambiente estão corretas?

**Comandos úteis:**
```bash
# Verificar status dos containers
docker-compose ps

# Logs do MinIO
docker-compose logs minio

# Logs do Airflow Scheduler
docker-compose logs -f airflow-scheduler
```

### Limpar histórico de execuções

```bash
# Via UI do Airflow:
# 1. Vá em Admin → DAGs
# 2. Selecione a DAG
# 3. Actions → Delete

# Via CLI (dentro do container):
docker exec -it tech-minds-airflow-scheduler airflow dags delete mental_health_etl_pipeline
```

---

## 📈 Boas Práticas

### 1. Teste Local Primeiro

Antes de executar via Airflow, teste o ETL standalone:
```bash
python src/etl.py
```

### 2. Use Logs Detalhados

Todas as funções do ETL já têm logging integrado. Consulte os logs no Airflow UI.

### 3. Valide Dados Regularmente

A task `validate_pipeline` verifica automaticamente:
- ✅ Buckets existem
- ✅ Arquivos foram criados
- ✅ Dados estão corretos

### 4. Monitore Execuções

- Acesse regularmente a UI do Airflow
- Verifique o histórico na aba **Tree**
- Configure alertas para falhas

---

## 🔄 Fluxo Completo Recomendado

```bash
# 1. Subir infraestrutura
cd infra
docker-compose up -d

# 2. Aguardar inicialização (2-3 minutos)
docker-compose logs -f airflow-init

# 3. Acessar Airflow UI
# Navegador: http://localhost:8080
# Login: admin / admin

# 4. Ativar a DAG
# Toggle ON na interface

# 5. Executar (trigger manual ou aguardar schedule)
# Botão "Trigger DAG"

# 6. Monitorar execução
# Aba "Graph" → Acompanhar tasks

# 7. Validar resultados
# MinIO Console: http://localhost:9001
# Verificar buckets: bronze, silver, gold

# 8. Visualizar dados
# Metabase: http://localhost:3000
# Jupyter: jupyter notebook notebooks/01_exploratory_analysis.ipynb
```

---

## 📚 Recursos Adicionais

### Documentação Oficial
- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [Airflow DAGs](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html)

### Comandos Úteis

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (reset completo)
docker-compose down -v

# Ver logs em tempo real
docker-compose logs -f

# Restart de um serviço específico
docker-compose restart airflow-webserver

# Acessar shell do Airflow
docker exec -it tech-minds-airflow-webserver bash
```

---

**Última atualização:** Novembro 2025
