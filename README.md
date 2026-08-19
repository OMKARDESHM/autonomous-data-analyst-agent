<div align="center">

# 🤖 Autonomous Data Analyst Agent

### AI-Powered Business Intelligence · Natural Language → SQL → Insights

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-FF6B35?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-1.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

<br/>

> Ask a business question in plain English.  
> Get back validated SQL, interactive charts, and executive-grade insights — automatically.

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#️-tech-stack)
- [Architecture](#️-architecture)
- [LangGraph Pipeline](#-langgraph-pipeline)
- [Project Structure](#-project-structure)
- [Database Schema](#️-database-schema)
- [Agent Details](#-agent-details)
- [SQL Safety & Guardrails](#️-sql-safety--guardrails)
- [Visualization Engine](#-visualization-engine)
- [Quickstart (No PostgreSQL)](#-quickstart-no-postgresql-required)
- [Full Installation](#-full-installation)
- [Environment Variables](#-environment-variables)
- [Running the App](#️-running-the-app)
- [Running Tests](#-running-tests)
- [Docker Deployment](#-docker-deployment)
- [Example Walkthrough](#-example-walkthrough)
- [Design Decisions](#-design-decisions)
- [Future Roadmap](#-future-roadmap)
- [Author](#-author)

---

## 🌟 Overview

The **Autonomous Data Analyst Agent** is a production-grade, AI-powered Business Intelligence assistant that bridges the gap between business users and raw databases. It accepts questions written in plain English, intelligently generates safe SQL, executes queries, creates interactive visualizations, and delivers executive-level insights — all through a premium Streamlit interface.

The system is built on a **real LangGraph `StateGraph`** with seven specialized agent nodes that communicate through a shared typed `GraphState`. This architecture makes the pipeline modular, inspectable, and easy to extend.

### What makes it different?

| Capability | Traditional BI | This Agent |
|---|---|---|
| Query interface | SQL editor | Plain English |
| Schema awareness | Manual | Auto-reflected |
| SQL safety | None | Multi-layer guardrail |
| Insights | Manual analysis | LLM-generated |
| LLM provider | Single | NVIDIA NIM → OpenAI → Heuristic |
| Works without a DB | ❌ | ✅ (upload CSV/SQLite) |

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| 💬 **Natural Language Queries** | Ask questions like *"Show monthly revenue by region"* |
| 🧠 **AI Planner Agent** | Decides execution steps, SQL need, and chart type |
| 📝 **SQL Specialist Agent** | Generates schema-aware PostgreSQL/SQLite SELECT queries |
| 🛡️ **SQL Guardrail** | Blocks all destructive SQL (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE) |
| 🔎 **Schema Reflection** | Auto-inspects DB schema at runtime — no hardcoded table names |
| 🗄️ **Multi-DB Support** | PostgreSQL (primary), SQLite, uploaded CSV/Parquet/SQL dumps |
| 📊 **Smart Visualizations** | Auto-selects bar, line, scatter, histogram, box, or time-series charts |
| 💡 **Executive Insights** | LLM-generated bullet-point summaries with trends and recommendations |
| 🔄 **Real LangGraph Workflow** | Typed `StateGraph` with 7 nodes and conditional routing |
| 🌐 **Premium Streamlit UI** | Dark glassmorphism theme, tabbed results, pipeline badges, query history |
| 📁 **File Upload** | Upload `.db`, `.sqlite`, `.csv`, `.parquet`, or `.sql` files instantly |
| 🔐 **Auth Support** | Optional JWT login form or simple token-based access |
| 🐳 **Docker Ready** | Production `docker-compose.prod.yml` included |

---

## ⚙️ Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Language** | Python | 3.10+ |
| **AI Orchestration** | LangGraph | 1.2.11 |
| **LLM Framework** | LangChain | 1.3.15 |
| **Primary LLM** | NVIDIA NIM (`ChatNVIDIA`) | via `langchain-nvidia-ai-endpoints` |
| **Fallback LLM** | OpenAI (`ChatOpenAI`) | via `langchain-openai` |
| **Database** | PostgreSQL / SQLite | 15+ / 3.x |
| **ORM** | SQLAlchemy | 2.0+ |
| **Data Processing** | Pandas + NumPy | 3.x / 2.x |
| **Visualization** | Plotly | 6.9 |
| **Frontend** | Streamlit | 1.x |
| **SQL Validation** | sqlparse | 0.6 |
| **Auth** | PyJWT | 2.13 |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT FRONTEND                           │
│   ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │
│   │  Sidebar │  │ Auth (JWT /  │  │   File Upload (.db/.csv/     │ │
│   │  Query   │  │   Token)     │  │   .parquet/.sql)             │ │
│   └──────────┘  └──────────────┘  └──────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ run_workflow()
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH STATEGRAPH                            │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐   │
│  │ schema_node │───▶│ planner_node│───▶│     sql_node         │   │
│  │             │    │             │    │ (LLM / heuristic)    │   │
│  │ SQLAlchemy  │    │ LLM decides │    └──────────┬───────────┘   │
│  │ reflection  │    │ sql/viz/    │               │               │
│  └─────────────┘    │ steps       │               ▼               │
│                     └─────────────┘    ┌──────────────────────┐   │
│                                        │   guardrail_node     │   │
│                                        │   (sqlparse + regex) │   │
│                                        └──────┬───────┬───────┘   │
│                                    (blocked)  │       │  (clean)  │
│                                               ▼       ▼           │
│                              ┌──────────────┐  ┌─────────────┐   │
│                              │visualization │  │executor_node│   │
│                              │    _node     │◀─│(SQLAlchemy) │   │
│                              └──────┬───────┘  └─────────────┘   │
│                                     │                             │
│                                     ▼                             │
│                              ┌─────────────┐                     │
│                              │insights_node│                     │
│                              │(LLM/stats)  │                     │
│                              └──────┬──────┘                     │
└─────────────────────────────────────┼───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     STREAMLIT RESULTS DASHBOARD                     │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │  📝 SQL  │ │ 📋 Data  │ │ 📊 Charts│ │ 💡 Insight│ │🗺️ Plan │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 LangGraph Pipeline

The workflow is a compiled `StateGraph` with typed `GraphState` shared across all nodes.

```
schema_node → planner_node → sql_node → guardrail_node
                                              │
                              ┌───────────────┴──────────────┐
                              │ (validation_error?)           │
                         Yes  ▼                    No  ▼
                     (skip executor)          executor_node
                              │                     │
                              └──────────┬──────────┘
                                         ▼
                                visualization_node
                                         │
                                         ▼
                                  insights_node
                                         │
                                        END
```

### Node Responsibilities

| Node | Input | Output | LLM? |
|---|---|---|---|
| `schema_node` | `engine_override` | `database_schema` (string) | ❌ |
| `planner_node` | `user_query`, `database_schema` | `plan`, `planned_steps` | ✅ optional |
| `sql_node` | `user_query`, `database_schema` | `generated_sql` | ✅ optional |
| `guardrail_node` | `generated_sql` | `sql` (clean) or `validation_error` | ❌ |
| `executor_node` | `sql` | `dataframe`, `rows_returned` | ❌ |
| `visualization_node` | `dataframe` | `figure`, `figures`, `chart_types` | ❌ |
| `insights_node` | `dataframe` | `insights`, `final_response` | ✅ optional |

### LLM Provider Fallback Chain

```
NVIDIA_API_KEY set?
    ├── YES → ChatNVIDIA (meta/llama-3.1-8b-instruct by default)
    └── NO  → OPENAI_API_KEY set?
                  ├── YES → ChatOpenAI (gpt-3.5-turbo by default)
                  └── NO  → Heuristic SQL + Statistical Insights (no API needed)
```

---

## 📁 Project Structure

```
autonomous-data-analyst-agent/
│
├── 📄 app.py                      # Streamlit application — premium dark UI
├── 📄 graph.py                    # LangGraph StateGraph — 7-node workflow
├── 📄 agents.py                   # All agent implementations (planner, SQL,
│                                  #   executor, visualization, insights)
├── 📄 config.py                   # LLM + DB configuration, get_llm() factory
├── 📄 schema.py                   # GraphState TypedDict definition
├── 📄 state.py                    # initial_state() factory function
├── 📄 guardrails.py               # SQL validation (sqlparse + regex)
├── 📄 uploads.py                  # File upload handler (CSV/Parquet/SQLite/SQL)
├── 📄 logging_config.py           # Centralized logging setup
│
├── 📁 prompts/
│   ├── 📄 planner_prompt.txt      # Planner agent LLM prompt
│   ├── 📄 sql_prompt.txt          # SQL specialist LLM prompt
│   └── 📄 insights_prompt.txt     # Insights agent LLM prompt
│
├── 📁 database/
│   ├── 📄 __init__.py             # Package init
│   ├── 📄 schema.sql              # PostgreSQL DDL (products, regions,
│   │                              #   time_periods, sales tables)
│   ├── 📄 sample_data.sql         # Indian cities/products sample data
│   ├── 📄 reflection.py           # reflect_schema() + demo SQLite engine
│   ├── 📄 seed_sqlite.py          # CLI script to seed demo.db
│   └── 📄 demo.db                 # Pre-built SQLite demo database ✅
│
├── 📁 tests/                      # Original test suite (25 tests)
│   ├── 📄 test_executor.py
│   ├── 📄 test_guardrails.py
│   ├── 📄 test_guardrails_fuzz.py
│   ├── 📄 test_insights.py
│   ├── 📄 test_planner.py
│   ├── 📄 test_sql_generation_schema_driven.py
│   ├── 📄 test_sql_identifier_quoting.py
│   ├── 📄 test_sql_specialist.py
│   ├── 📄 test_uploads.py
│   └── 📄 test_visualization.py
│
├── 📄 planner_test.py             # Planner agent tests (10 tests)
├── 📄 sql_test.py                 # SQL generation + guardrail tests (17 tests)
├── 📄 executor_test.py            # SQL executor tests (11 tests)
├── 📄 visualization_test.py       # Visualization agent tests (12 tests)
├── 📄 graph_test.py               # End-to-end workflow tests (14 tests)
│
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env.example                # Environment variable template
├── 📄 Dockerfile                  # Docker image definition
├── 📄 docker-compose.yml          # Development compose
├── 📄 docker-compose.prod.yml     # Production compose
└── 📄 README.md                   # This file
```

---

## 🗄️ Database Schema

The default schema models a retail sales operation across Indian cities.

```sql
┌─────────────────┐        ┌──────────────────┐
│    products     │        │     regions      │
├─────────────────┤        ├──────────────────┤
│ product_id  PK  │        │ region_id    PK  │
│ product_name    │        │ region_name      │
│ category        │        │ state            │
│ unit_price      │        │ country          │
└────────┬────────┘        └────────┬─────────┘
         │                          │
         │    ┌─────────────────┐   │
         │    │      sales      │   │
         │    ├─────────────────┤   │
         └───▶│ sale_id     PK  │◀──┘
              │ product_id  FK  │
              │ region_id   FK  │
              │ time_id     FK  │
              │ quantity        │
              │ revenue         │
              │ profit          │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   time_periods  │
              ├─────────────────┤
              │ time_id     PK  │
              │ sale_date       │
              │ month           │
              │ quarter         │
              │ year            │
              └─────────────────┘
```

**Sample data includes:**  
Products: Laptop, Mouse, Keyboard, Desk, Chair  
Regions: Nagpur, Mumbai, Delhi, Bangalore, Hyderabad  
Time: Jan–May 2025

---

## 🤖 Agent Details

### 1. Schema Agent
Uses `sqlalchemy.inspect()` to dynamically reflect all tables, columns (with types), and sample rows. Output is a structured text block fed to all LLM agents as context.

### 2. Planner Agent
Reads the user query + schema and returns a JSON execution plan:
```json
{
  "sql_required": true,
  "visualization_required": true,
  "suggested_chart_type": "bar",
  "steps": ["Inspect schema", "Generate SQL", "Execute query", "Create bar chart", "Generate insights"]
}
```
Falls back to keyword heuristics when no LLM is configured.

### 3. SQL Specialist Agent
Generates a single `SELECT` statement grounded in the reflected schema. Uses chain-of-thought prompting to pick correct tables, join conditions, aggregations, and aliases. Falls back to a deterministic heuristic generator for common query patterns.

### 4. SQL Guardrail
Multi-layer validation using `sqlparse`:
- Parses the SQL AST to verify the first DML token is `SELECT`
- Blocks all forbidden keywords: `INSERT UPDATE DELETE DROP ALTER TRUNCATE CREATE REPLACE GRANT REVOKE SHUTDOWN MERGE`
- Detects obfuscated attempts like `D R O P` or `d·r·o·p`
- Rejects multi-statement inputs and inline comments

### 5. SQL Executor
Executes validated SQL in a transaction with:
- Auto-`LIMIT` injection when missing
- PostgreSQL `statement_timeout` for query timeout protection
- Automatic rollback on failure
- Returns a typed Pandas `DataFrame`

### 6. Visualization Agent
Rule-based chart selection (no extra LLM call):

| Data Shape | Chart Type(s) |
|---|---|
| Category + 1 numeric | Bar chart |
| Category + 2+ numerics | Bar + Line |
| Datetime + numerics | Time-series line |
| 2 numerics only | Line + Scatter |
| 1 numeric only | Histogram + Box plot |

All charts use the `plotly_dark` template for visual consistency.

### 7. Insights Agent
Generates 4–8 executive bullet points covering:
- Headline summary
- Top numeric trend or performer
- Unexpected patterns or anomalies
- One actionable business recommendation

Falls back to statistical summaries (min/max/mean/median/mode) when no LLM is configured.

---

## 🛡️ SQL Safety & Guardrails

The guardrail layer runs **before** any SQL touches the database.

```
User SQL Input
      │
      ▼
┌─────────────────────────────────────┐
│ 1. Strip comments (sqlparse)        │
│ 2. Parse into AST                   │
│ 3. Count statements → must be 1    │
│ 4. Check first DML token = SELECT  │
│ 5. Scan for forbidden keywords      │
│ 6. Detect obfuscated keywords       │
│    (spaced letters: D R O P)        │
│ 7. Reject semicolons                │
│ 8. Reject inline comments (-- /*) │
└─────────────────────────────────────┘
      │
      ├─ PASS → executor_node
      └─ FAIL → validation_error in GraphState, skip to visualization_node
```

**Blocked operations:** `INSERT · UPDATE · DELETE · DROP · ALTER · TRUNCATE · CREATE · REPLACE · GRANT · REVOKE · SHUTDOWN · MERGE`

---

## 📊 Visualization Engine

Charts are created deterministically based on DataFrame column types — no LLM call needed.

```python
# Pseudocode for chart selection
if category_cols and numeric_cols:
    → Bar chart  (+ Line if 2+ numeric cols)
elif datetime_cols and numeric_cols:
    → Time-series line chart
elif len(numeric_cols) >= 2:
    → Line chart + Scatter plot
elif len(numeric_cols) == 1:
    → Histogram + Box plot
```

All figures use **Plotly dark theme** and are rendered with `use_container_width=True` for responsive display.

---

## ⚡ Quickstart (No PostgreSQL Required)

The fastest way to run the app using the pre-built SQLite demo database:

```bash
# 1. Clone the repository
git clone https://github.com/OMKARDESHM/autonomous-data-analyst-agent.git
cd autonomous-data-analyst-agent

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set your LLM API key in .env
cp .env.example .env
# Edit .env → add NVIDIA_API_KEY or OPENAI_API_KEY

# 5. Run the app
streamlit run app.py
```

In the sidebar:
1. Click **Upload a database or dataset**
2. Select `database/demo.db`
3. Type: *"Show total sales by region"*
4. Click **▶ Run Analysis**

> **No API key needed.** The app uses heuristic SQL generation and statistical insights when no LLM is configured.

---

## 🔧 Full Installation

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| pip | 23+ |
| PostgreSQL *(optional)* | 13+ |
| Git | Any recent |

### Steps

```bash
# Clone
git clone https://github.com/OMKARDESHM/autonomous-data-analyst-agent.git
cd autonomous-data-analyst-agent

# Virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# Install all dependencies
pip install -r requirements.txt

# (Optional) Seed a fresh demo SQLite database
python database/seed_sqlite.py

# Configure environment
cp .env.example .env
# Edit .env with your keys and database URL

# Launch
streamlit run app.py
```

### PostgreSQL Setup (Optional)

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE salesdb;"

# Run the schema and seed data
psql -U postgres -d salesdb -f database/schema.sql
psql -U postgres -d salesdb -f database/sample_data.sql
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# ── NVIDIA NIM (Primary LLM) ─────────────────────────────────────────
NVIDIA_API_KEY=nvapi-your-key-here
MODEL_NAME=meta/llama-3.1-8b-instruct

# ── OpenAI (Optional Fallback LLM) ───────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# ── Database ──────────────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/salesdb

# ── Streamlit Auth ────────────────────────────────────────────────────
# Option A – Simple token
STREAMLIT_AUTH_TOKEN=your_secret_token

# Option B – JWT login form
JWT_SECRET=your_jwt_secret
AUTH_USER=admin
AUTH_PASS=password

# ── Upload Storage ────────────────────────────────────────────────────
UPLOADS_DIR=./uploads
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | ✅ for NIM | — | NVIDIA NIM API key |
| `MODEL_NAME` | No | `meta/llama-3.1-8b-instruct` | NVIDIA NIM model name |
| `OPENAI_API_KEY` | ✅ for OpenAI | — | OpenAI API key (fallback) |
| `OPENAI_MODEL` | No | `gpt-3.5-turbo` | OpenAI model name |
| `DATABASE_URL` | No | `postgresql://postgres:postgres@localhost:5432/salesdb` | SQLAlchemy DB URL |
| `STREAMLIT_AUTH_TOKEN` | No | — | Simple token auth |
| `JWT_SECRET` | No | — | Enables JWT login form |
| `UPLOADS_DIR` | No | system temp | Folder for uploaded files |

---

## ▶️ Running the App

### Development

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### Production (Docker)

```bash
# Build and start
docker compose -f docker-compose.prod.yml up --build -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

The service exposes **port 8501**. Set `NVIDIA_API_KEY` (or `OPENAI_API_KEY`) and `DATABASE_URL` via environment or `.env`.

---

## 🧪 Running Tests

The project includes **64 unit and integration tests** across 5 test files.

```bash
# Run all new tests
pytest planner_test.py sql_test.py executor_test.py visualization_test.py graph_test.py -v

# Run original test suite
pytest tests/ -v

# Run everything
pytest -v

# With coverage
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
```

### Test Coverage

| Test File | Tests | Coverage Area |
|---|---|---|
| `planner_test.py` | 10 | Planner agent, heuristic fallback, plan keys |
| `sql_test.py` | 17 | Schema inspection, SQL generation, guardrail (all 9 block cases) |
| `executor_test.py` | 11 | SELECT, WHERE, GROUP BY, ORDER BY, auto-LIMIT, error handling |
| `visualization_test.py` | 12 | Bar, line, scatter, histogram, box, time-series, empty inputs |
| `graph_test.py` | 14 | Full workflow, guardrail routing, manual SQL, elapsed time |
| `tests/` | 25 | Guardrails (including fuzz), uploads, insights, SQL identifier quoting |

All tests use an **in-memory SQLite engine** — no database server required.

---

## 📊 Example Walkthrough

### Input

```
Show total revenue by region
```

### Step 1 — Schema Node
```
Table: sales
  - sale_id (INTEGER)
  - revenue (REAL)
  - region_id (INTEGER)
Table: regions
  - region_id (INTEGER)
  - region_name (TEXT)
```

### Step 2 — Planner Node
```json
{
  "sql_required": true,
  "visualization_required": true,
  "suggested_chart_type": "bar",
  "steps": ["Generate SQL", "Execute query", "Create bar chart", "Generate insights"]
}
```

### Step 3 — SQL Specialist
```sql
SELECT r.region_name, SUM(s.revenue) AS total_revenue
FROM sales s
JOIN regions r ON s.region_id = r.region_id
GROUP BY r.region_name
ORDER BY total_revenue DESC
LIMIT 100
```

### Step 4 — Guardrail
```
✅ Validated — SELECT only, no forbidden keywords, single statement
```

### Step 5 — Executor
```
DataFrame: 5 rows × 2 columns
region_name | total_revenue
Mumbai      | 19000.00
Nagpur      | 15850.00
Delhi       | 7500.00
Bangalore   | 8100.00
Hyderabad   | 4320.00
```

### Step 6 — Visualization
```
→ Bar chart: Total Revenue by Region (Plotly dark theme)
```

### Step 7 — Insights
```
- Mumbai and Nagpur together account for over 60% of total regional revenue.
- Hyderabad recorded the lowest revenue at ₹4,320 — significantly below the regional average.
- Revenue is concentrated in Maharashtra (Mumbai + Nagpur), suggesting a geographic dependency risk.
- Recommendation: Invest in demand generation campaigns in Hyderabad and Bangalore to diversify revenue.
```

---

## 💡 Design Decisions

### Why LangGraph `StateGraph`?

A `StateGraph` provides clean separation of concerns: each node is a pure function that reads from `GraphState` and writes back into it. This makes the pipeline:
- **Inspectable** — every node's input/output is visible
- **Testable** — nodes can be unit-tested independently
- **Extensible** — add a new node without rewriting the pipeline

### Why Dynamic Schema Reflection?

`sqlalchemy.inspect()` queries the live database at runtime. If tables or columns change, the SQL agent automatically receives the updated schema — no prompt re-engineering needed.

### Why Rule-Based Visualization?

Deterministic chart selection (based on column dtypes) is:
- **Faster** — no extra LLM call
- **Cheaper** — no API token consumption
- **Predictable** — same data shape always produces the same chart type
- **Reliable** — works without any API key

### Why Three LLM Tiers?

The heuristic fallback ensures the app is **always functional** — even in air-gapped environments or during API outages. NVIDIA NIM is preferred for its speed and cost efficiency at scale.

### Why `GraphState` as Shared Memory?

All 7 nodes communicate through a single typed `TypedDict`. This eliminates argument passing between agents, makes state inspection trivial, and allows LangGraph's checkpointing to save and resume state.

---

## 🔮 Future Roadmap

| Feature | Priority |
|---|---|
| Self-correction loop (retry SQL on execution error) | 🔴 High |
| Schema-aware guardrail (validate table/column names) | 🔴 High |
| Persistent conversation memory (`LangGraph MemorySaver`) | 🟡 Medium |
| Query result caching (Redis / SQLite) | 🟡 Medium |
| Multi-turn chat interface | 🟡 Medium |
| Export visualizations as PNG/PDF | 🟢 Low |
| Scheduled report generation | 🟢 Low |
| Role-based access control (RBAC) | 🟢 Low |
| Kubernetes deployment manifests | 🟢 Low |

---

## 👨‍💻 Author

<div align="center">

**Omkar Deshmukh**

*AI Engineer · Machine Learning · Generative AI · Agentic Systems*

[![GitHub](https://img.shields.io/badge/GitHub-OMKARDESHM-181717?style=for-the-badge&logo=github)](https://github.com/OMKARDESHM)

</div>

---

<div align="center">

**If this project helped you, please consider giving it a ⭐**

*Built with LangGraph · LangChain · NVIDIA NIM · Streamlit · PostgreSQL*

</div>
