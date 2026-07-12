# Enhanced Banking Multi-Agent RAG System

A production-grade AI banking analysis platform built on **Microsoft Semantic Kernel** that coordinates six specialised agents in a sequential workflow. The system integrates Azure AI Foundry (GPT-4.1 reasoning + text-embedding-3-small for RAG), Azure SQL Database, and ChromaDB to deliver comprehensive banking analyses covering fraud detection, loan evaluation, risk assessment, and customer support.

---

## Architecture Overview

```
User Query
    │
    ▼
EnhancedBankingSequentialOrchestration (main_starter.py)
    │
    ├── DataConnector          ── Azure SQL Database (transactions table)
    ├── BlobStorageConnector   ── Local file simulator / Azure Blob Storage
    ├── ChromaDBManager        ── Vector store (6 banking policy collections)
    ├── SharedState            ── Thread-safe cross-agent state
    │
    └── SequentialOrchestration (Semantic Kernel)
            │
            ├── 1. Enhanced_Data_Gatherer       ← customer financial profiling
            ├── 2. Enhanced_Fraud_Analyst        ← transaction anomaly detection
            ├── 3. Enhanced_Loan_Analyst         ← credit risk & loan eligibility
            ├── 4. Enhanced_Support_Specialist   ← CX optimisation & retention
            ├── 5. Enhanced_Risk_Analyst         ← enterprise risk & compliance
            └── 6. Enhanced_Synthesis_Coordinator ← executive report generation
```

Each agent builds on the previous agent's output, producing a progressively richer analysis that culminates in an `EnhancedBankingReport`.

---

## Project Structure

```
starter/
├── main_starter.py        # Main orchestration — fully implemented
├── blob_connector.py      # Local blob storage simulator (provided)
├── chroma_manager.py      # ChromaDB vector store manager (provided)
├── rag_utils.py           # Policy extraction & RAG utilities (provided)
├── shared_state.py        # Thread-safe multi-agent state (provided)
├── create.sql             # Azure SQL schema (transactions table)
├── insert.sql             # Sample customer transaction data
├── query.sql              # Sample query
├── .env.template          # Environment variable template
└── README.md              # This file
```

---

## Azure Services Required

| Service | Purpose | SKU |
|---------|---------|-----|
| Azure AI Foundry (Cognitive Services) | GPT-4.1 reasoning + text-embedding-3-small | S0 |
| Azure SQL Database | Customer transaction storage | Basic |
| Azure Blob Storage *(optional)* | Banking policy document storage | Standard LRS |

---

## Setup Instructions

### 1. Clone and prepare environment

```bash
cd starter/
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install semantic-kernel pyodbc python-dotenv chromadb
```

### 2. Create Azure resources

#### Azure AI Foundry
1. Go to [Azure Portal](https://portal.azure.com) → Create resource → **Azure AI Foundry**
2. Deploy two models:
   - `gpt-4.1` (or `gpt-4`) — Chat Completion
   - `text-embedding-3-small` (or `text-embedding-ada-002`) — Embeddings
3. Note the endpoint URL and API key.

#### Azure SQL Database
```bash
# Create SQL Server
az sql server create \
  --resource-group <your-rg> \
  --name banking-sql-rag1 \
  --location westus \
  --admin-user sqladmin

# Create database
az sql db create \
  --resource-group <your-rg> \
  --server banking-sql-rag1 \
  --name banking-db \
  --service-objective Basic

# Allow Azure services
az sql server firewall-rule create \
  --resource-group <your-rg> --server banking-sql-rag1 \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

#### Load schema and sample data
Connect to your database via Azure Portal Query Editor or SSMS and run:
```sql
-- Run create.sql first, then insert.sql
```

### 3. Configure environment variables

Copy `.env.template` to `.env` and fill in your values:

```bash
cp .env.template .env
```

```dotenv
# Azure AI Foundry
AZURE_TEXTGENERATOR_DEPLOYMENT_ENDPOINT="https://your-resource.cognitiveservices.azure.com/"
AZURE_TEXTGENERATOR_DEPLOYMENT_KEY="your_api_key_here"
AZURE_TEXTGENERATOR_DEPLOYMENT_NAME="gpt-4.1"

# Azure Embeddings (optional)
AZURE_TEXTEMBEDDING_DEPLOYMENT_ENDPOINT="https://your-resource.cognitiveservices.azure.com/"
AZURE_TEXTEMBEDDING_DEPLOYMENT_KEY="your_api_key_here"
AZURE_TEXTEMBEDDING_DEPLOYMENT_NAME="text-embedding-3-small"

# Azure SQL
AZURE_SQL_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=tcp:banking-sql-rag1.database.windows.net,1433;Database=banking-db;Uid=sqladmin;Pwd=<your-password>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# Azure Blob Storage (optional)
BLOB_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net"
```

---

## Running the System

```bash
cd starter/

# Default — runs 3 demo scenarios (financial planning, loan, fraud)
python main_starter.py

# Quick single-scenario smoke test
python main_starter.py --demo

# Full 5-scenario validation suite with pass/fail assertions
python main_starter.py --test

# Demo + full test suite
python main_starter.py --all
```

### Expected output (--test)
```
BANKING MULTI-AGENT RAG SYSTEM — TEST MODE
================================================================================
[TEST] financial_planning | Customer: 12345
       [PASS] risk=0.250 (low), findings=8, agents=6, time=42.3s
[TEST] loan_application | Customer: 67890
       [PASS] risk=0.470 (medium), findings=7, agents=6, time=38.1s
...
TEST RESULTS: 5 passed, 0 failed out of 5 tests
```

---

## Implementation Details

### DataConnector (Azure SQL)
- Loads `AZURE_SQL_CONNECTION_STRING` from environment on init
- Tests connectivity with `SELECT 1` at startup; raises on failure
- `fetch_income(customer_id)` — queries latest income row per customer
- `fetch_transactions(customer_id)` — returns all transactions as list of dicts
- `get_db_connection()` — `@contextmanager` ensuring clean connection lifecycle
- Falls back to sample data when SQL is unavailable (graceful degradation)

### Pydantic Models
**`CustomerProfile`** — 9 fields with two computed properties:
- `tenure_years` — float years since `customer_since`
- `total_monthly_obligations` — sum of debit transactions

**`EnhancedBankingReport`** — 13 fields including `risk_score`, `agent_contributions` dict, and `processing_metrics` dict with per-agent timing breakdowns.

### Risk Scoring Algorithm (`_calculate_enhanced_risk_score`)
Multi-factor score in [0.0, 1.0] — lower is safer:

| Factor | Adjustment |
|--------|-----------|
| Income ≥ $100k | −0.15 |
| Income ≥ $60k | −0.10 |
| Credit score ≥ 750 | −0.15 |
| Credit score ≥ 680 | −0.08 |
| Tenure ≥ 5 years | −0.05 |
| Products ≥ 4 | −0.05 |
| High RAG relevance | −0.03 |
| Income < $20k | +0.10 |
| Credit score < 580 | +0.15 |

### Six Specialised Agents

| Agent | Domain | Output |
|-------|--------|--------|
| Enhanced_Data_Gatherer | Financial profiling & data quality | Structured customer summary |
| Enhanced_Fraud_Analyst | Anomaly detection & risk rating | LOW/MEDIUM/HIGH/CRITICAL rating |
| Enhanced_Loan_Analyst | Credit risk & eligibility | ELIGIBLE/CONDITIONAL/NOT ELIGIBLE |
| Enhanced_Support_Specialist | CX optimisation & retention | Resolution plan + retention offers |
| Enhanced_Risk_Analyst | Enterprise risk & compliance | Risk score 0–1, compliance status |
| Enhanced_Synthesis_Coordinator | Executive synthesis | Final report + ranked action plan |

### RAG Pipeline
1. Blob connector uploads 5 banking policy markdown files on first run
2. `load_enhanced_documents()` chunks and indexes them into 6 ChromaDB collections
3. `hybrid_search()` combines semantic similarity + keyword boosting
4. Top-6 results are injected into the orchestration task as grounded context

---

## Database Schema

```sql
CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id    VARCHAR(50) NOT NULL,
    income         DECIMAL(18,2),
    amount         DECIMAL(18,2) NOT NULL,
    ts             DATETIME2 NOT NULL,
    description    NVARCHAR(500)
);
```

Sample data includes 3 customers (IDs: 12345, 67890, 11111) with 4 transactions each.

---

## Logging

Each run creates a timestamped log file under `./logs/`:
```
logs/banking_analysis_20260712_143022.log
```

All agent callbacks, SQL queries, ChromaDB operations, and errors are logged at INFO/ERROR level.

---

## Graceful Degradation

| Service | Fallback behaviour |
|---------|-------------------|
| Azure SQL unreachable | Uses hardcoded sample profiles (3 customers) |
| ChromaDB empty | Runs analysis with empty policy context |
| Azure AI Foundry timeout | 300s timeout then raises; outer try/catch logs error |
| Blob Storage empty | Uploads 5 sample policy documents automatically |
