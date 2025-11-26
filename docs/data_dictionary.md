# Dicionário de Dados - Tech Minds Analytics

Este documento descreve o schema e o significado de cada campo nos datasets processados.

---

## Dataset Original (Bronze Layer)

**Arquivo:** `bronze/raw_mental_health.csv`  
**Formato:** CSV  
**Registros:** ~1200  
**Fonte:** Pesquisa sobre saúde mental em trabalhadores de tecnologia

### Colunas Principais

| Coluna | Tipo | Descrição | Valores Possíveis | Nulos |
|--------|------|-----------|-------------------|-------|
| `Timestamp` | string | Data/hora da resposta | ISO 8601 format | Não |
| `Age` | integer | Idade do respondente | 1-999 (outliers comuns) | Sim |
| `Gender` | string | Identidade de gênero | Texto livre (não padronizado) | Sim |
| `Country` | string | País de residência | Nome do país | Sim |
| `state` | string | Estado/província (EUA principalmente) | Sigla ou nome | Sim |
| `self_employed` | string | Autônomo | "Yes", "No" | Sim |
| `family_history` | string | Histórico familiar de doença mental | "Yes", "No" | Sim |
| `treatment` | string | Buscou tratamento para saúde mental | "Yes", "No" | Sim |
| `work_interfere` | string | Trabalho interfere na saúde mental | "Never", "Rarely", "Sometimes", "Often" | Sim |
| `no_employees` | string | Tamanho da empresa | Faixas: "1-5", "6-25", "26-100", etc. | Sim |
| `remote_work` | string | Trabalha remotamente | "Yes", "No" | Sim |
| `tech_company` | string | Trabalha em empresa de tecnologia | "Yes", "No" | Sim |
| `benefits` | string | Empresa oferece benefícios de saúde mental | "Yes", "No", "Don't know" | Sim |
| `care_options` | string | Conhece opções de cuidado | "Yes", "No", "Not sure" | Sim |
| `wellness_program` | string | Empresa tem programa de bem-estar | "Yes", "No", "Don't know" | Sim |
| `seek_help` | string | Empresa fornece recursos para buscar ajuda | "Yes", "No", "Don't know" | Sim |
| `anonymity` | string | Anonimato é protegido | "Yes", "No", "Don't know" | Sim |
| `leave` | string | Facilidade para tirar licença médica | Scale: "Very easy" a "Very difficult" | Sim |
| `mental_health_consequence` | string | Discutir saúde mental traz consequências | "Yes", "No", "Maybe" | Sim |
| `phys_health_consequence` | string | Discutir saúde física traz consequências | "Yes", "No", "Maybe" | Sim |
| `coworkers` | string | Conversaria com colegas | "Yes", "No", "Some of them" | Sim |
| `supervisor` | string | Conversaria com supervisor | "Yes", "No", "Some of them" | Sim |
| `mental_health_interview` | string | Discutiria em entrevista de emprego | "Yes", "No", "Maybe" | Sim |
| `phys_health_interview` | string | Discutiria saúde física em entrevista | "Yes", "No", "Maybe" | Sim |
| `mental_vs_physical` | string | Empregador leva saúde mental a sério | "Yes", "No", "Don't know" | Sim |
| `obs_consequence` | string | Observou consequências negativas | "Yes", "No" | Sim |
| `comments` | string | Comentários adicionais | Texto livre | Sim |

---

## Dataset Limpo (Silver Layer)

**Arquivo:** `silver/mental_health_clean.parquet`  
**Formato:** Parquet (compressão snappy)  
**Schema:** Tipado

### Transformações Aplicadas

#### 1. Campo: `Age`

**Original:**
- Tipo: integer/float
- Range: 1-999
- Nulos: Sim
- Problemas: Outliers extremos (ex: -1, 999)

**Transformado:**
- Tipo: integer
- Range: 18-100
- Nulos: Preenchidos com mediana
- Regra: `18 <= Age <= 100`

**Lógica:**
```python
# Preenche nulos com mediana
df['Age'].fillna(df['Age'].median(), inplace=True)

# Remove outliers
df = df[(df['Age'] >= 18) & (df['Age'] <= 100)]
```

---

#### 2. Campo: `Gender`

**Original:**
- Tipo: string
- Valores: 49 valores únicos (ex: "Male", "male", "M", "m", "Man", "cis male", "Cis Male", "Female", "female", "F", "Woman", "Trans woman", "Agender", "Genderqueer", etc.)
- Nulos: Sim
- Problema: Inconsistência total

**Transformado:**
- Tipo: string (categorical)
- Valores: "Male", "Female", "Other"
- Nulos: Classificados como "Other"

**Mapeamento:**

| Valor Normalizado | Valores Originais (exemplos) |
|-------------------|------------------------------|
| `Male` | "Male", "male", "M", "m", "Man", "man", "cis male", "Cis Male", "Male (CIS)", "mail", "maile", "mal" |
| `Female` | "Female", "female", "F", "f", "Woman", "woman", "Cis Female", "cis-female/femme", "Female (cis)", "femail", "femake" |
| `Other` | "Trans woman", "Trans man", "Genderqueer", "Androgyne", "Agender", "Non-binary", "Enby", "Fluid", "Genderflux", nulos, outros |

**Lógica:**
```python
def normalize_gender(gender):
    if pd.isna(gender):
        return 'Other'
    
    gender_str = str(gender).lower().strip()
    
    male_variants = ['male', 'man', 'm', 'cis male', ...]
    if any(v in gender_str for v in male_variants) and 'female' not in gender_str:
        return 'Male'
    
    female_variants = ['female', 'woman', 'f', 'cis female', ...]
    if any(v in gender_str for v in female_variants):
        return 'Female'
    
    return 'Other'
```

---

#### 3. Campos de Texto (Geral)

**Campos afetados:** `Country`, `state`, `remote_work`, `treatment`, etc.

**Transformação:**
- Nulos: Preenchidos com `"Unknown"`
- Tipo: string

**Lógica:**
```python
for col in df.columns:
    if df[col].dtype == 'object':
        df[col].fillna('Unknown', inplace=True)
```

---

## Datasets Agregados (Gold Layer)

### 1. Tratamento por Trabalho Remoto

**Arquivo:** `gold/agg_remote_work_treatment.parquet`

**Schema:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `remote_work` | string | "Yes", "No", "Unknown" |
| `No` | integer | Contagem de respondentes que NÃO buscaram tratamento |
| `Yes` | integer | Contagem de respondentes que buscaram tratamento |

**SQL Equivalente:**
```sql
SELECT 
    remote_work,
    SUM(CASE WHEN treatment = 'No' THEN 1 ELSE 0 END) as No,
    SUM(CASE WHEN treatment = 'Yes' THEN 1 ELSE 0 END) as Yes
FROM mental_health_clean
GROUP BY remote_work
```

**Exemplo de Dados:**

| remote_work | No | Yes |
|-------------|----|-----|
| Yes | 120 | 180 |
| No | 250 | 450 |
| Unknown | 30 | 50 |

---

### 2. Distribuição por País

**Arquivo:** `gold/agg_country_distribution.parquet`

**Schema:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `Country` | string | Nome do país |
| `Count` | integer | Número de respondentes |

**SQL Equivalente:**
```sql
SELECT 
    Country,
    COUNT(*) as Count
FROM mental_health_clean
GROUP BY Country
ORDER BY Count DESC
```

**Exemplo de Dados:**

| Country | Count |
|---------|-------|
| United States | 700 |
| United Kingdom | 150 |
| Canada | 80 |
| Germany | 50 |
| ... | ... |

---

## Convenções e Padrões

### Nomenclatura de Arquivos

```
Padrão: {tipo}_{descrição}.{extensão}

Exemplos:
- raw_mental_health.csv       (dados brutos)
- mental_health_clean.parquet  (dados limpos)
- agg_remote_work_treatment.parquet (agregação)
```

### Tipos de Dados

| Tipo Python | Tipo Parquet | Uso |
|-------------|--------------|-----|
| `int64` | `INT64` | Age, contagens |
| `float64` | `DOUBLE` | Métricas calculadas |
| `object` | `STRING` | Texto, categorias |
| `bool` | `BOOLEAN` | Flags binários |
| `datetime64` | `TIMESTAMP` | Timestamps |

### Tratamento de Valores Ausentes

| Tipo de Coluna | Estratégia | Valor Padrão |
|----------------|------------|--------------|
| Numérica (Age) | Mediana | Mediana calculada |
| Categórica (texto) | Constante | "Unknown" |
| Booleana | Remoção | - |
| Timestamp | Remoção | - |

---

## Validações de Qualidade

### Regras Implementadas

1. **Age:** Deve estar entre 18 e 100
2. **Gender:** Deve ser Male, Female ou Other
3. **Campos obrigatórios:** Não podem ser completamente nulos
4. **Duplicatas:** Não verificado (timestamps únicos assumidos)

### Métricas de Qualidade

```python
# Completude
completeness = (df.count() / len(df)) * 100

# Validade (Age)
valid_age = ((df['Age'] >= 18) & (df['Age'] <= 100)).sum() / len(df)

# Consistência (Gender)
valid_gender = df['Gender'].isin(['Male', 'Female', 'Other']).sum() / len(df)
```

---

## Changelog

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | Nov 2025 | Schema inicial |

---

**Última atualização:** Novembro 2025
