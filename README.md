# AI-Based Natural Language to SQL Query System
### Intelligent Schema Linking & Schema Reduction for LLM-Powered Text-to-SQL

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LLM](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)](https://ai.google.dev/)
[![Embeddings](https://img.shields.io/badge/Embeddings-SentenceTransformers-green.svg)](https://sbert.net/)
[![Benchmark](https://img.shields.io/badge/Benchmark-Spider%20Dataset-purple.svg)](https://yale-lily.github.io/spider)

---

## 1. Project Overview

Traditional Text-to-SQL systems feed the entire database schema into the LLM prompt. In large relational databases (or academic benchmarks like Yale's Spider dataset), this causes:
1. **Excessive prompt token consumption** and high API costs.
2. **Elevated inference latency**.
3. **LLM hallucinations and distractions** caused by irrelevant tables and columns.

### The Research Question
> **Can an intelligent schema-linking and schema-reduction mechanism prune the database schema supplied to an LLM, reducing token usage, API cost, and inference latency while maintaining or improving SQL execution accuracy?**

This project implements and experimentally benchmarks a **4-Factor Schema Linking & Reduction Engine** that selectively identifies relevant content columns, resolves necessary foreign-key join paths, and passes a compact, pruned schema to **Google Gemini**.

```
BASELINE PIPELINE:
  Natural Language Question
             │
             ▼
    [Full Database Schema] (100% of tables & columns)
             │
             ▼
     LLM (Gemini 3.5 Flash Lite)
             │
             ▼
       Generated SQL
             │
             ▼
   SQLite Execution (Sandbox) ──► Query Result

──────────────────────────────────────────────────────────

PROPOSED PIPELINE:
  Natural Language Question
             │
             ▼
  [4-Factor Schema Linker]
  ├── 1. Lexical Similarity (token overlap & stemming)
  ├── 2. Dense Semantic Embeddings (SentenceTransformers)
  ├── 3. Data Type Intent Matching
  └── 4. FK Graph Join-Path Resolution (Shortest BFS)
             │
             ▼
    [Pruned Reduced Schema] (typically 50% - 80% smaller)
             │
             ▼
     LLM (Gemini 3.5 Flash Lite)
             │
             ▼
       Generated SQL
             │
             ▼
      SQLite Execution ────────► Query Result
```

---

## 2. Key Features

- **4-Factor Schema Relevance Engine:**
  $$\text{Score}(c, q) = w_{\text{lex}} \cdot \text{Lexical} + w_{\text{sem}} \cdot \text{Semantic} + w_{\text{type}} \cdot \text{TypeMatch} + w_{\text{rel}} \cdot \text{Relationship}$$
- **Foreign-Key Graph Join Completion:** Automatically performs BFS on the foreign-key relational graph to pull in intermediate junction tables and structural keys required for multi-table `JOIN` queries.
- **Dual-Execution Comparison Dashboard:** Interactive web interface (`server.py`) that executes both the Baseline and Proposed pipelines side-by-side, comparing:
  - Generated SQL syntax
  - Actual table execution results
  - Input/Output token savings
  - Component and end-to-end latency
  - Precision, Recall, and F1 metrics against Ground Truth
  - Automated execution verdict (`BOTH_CORRECT`, `PROPOSED_CORRECT`, `BASELINE_CORRECT`, `NEITHER_CORRECT`)
- **Spider Benchmark Suite:** Built-in adapter for 100+ Spider databases (`spider_data/`), with a dedicated background runner for the Top-5 Spider schemas (`hr_1`, `car_1`, `flight_2`, `world_1`, `sakila_1`).
- **Zero-Setup Cross-Platform Compatibility:**
  - Auto-initializes the default `college.db` database with sample data if missing.
  - Automatically unzips `dataset/spider_data.zip` if uncompressed files are absent.
  - Automatically downloads SentenceTransformer model weights (`all-MiniLM-L6-v2`) if local weights are not present.
  - Works seamlessly on Windows, macOS, and Linux without OS-specific path assumptions.

---

## 3. Prerequisites

- **Python:** Version 3.10, 3.11, 3.12, or 3.13.
- **Google Gemini API Key:** Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).
- **Git** (with Git LFS recommended for tracking model weights, though the application will automatically fetch weights from Hugging Face if Git LFS was not used).

---

## 4. Installation & Quick Start

### Step 1: Clone the Repository
```bash
git clone https://github.com/HarshaNethra/Text-to-SQL-Schema-Linker.git
cd Text-to-SQL-Schema-Linker
```

### Step 2: Create a Virtual Environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (Command Prompt):
python -m venv venv
venv\Scripts\activate.bat

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Your Environment (.env)
Copy the example environment file and add your Gemini API key:
```bash
# On Linux / macOS:
cp .env.example .env

# On Windows:
copy .env.example .env
```

Open `.env` in any text editor and set your key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## 5. Running the Application

### Option A: Web Dashboard (Recommended)
Start the multi-threaded HTTP server and open the web dashboard:
```bash
python server.py
```
Open your browser at: **`http://localhost:5000`**

From the UI, you can:
1. Run natural language queries against `college.db` or switch to any Spider database.
2. View dual Baseline vs. Proposed execution, token savings, and execution verdicts.
3. Explore database tables and raw data.
4. Adjust schema linking factor weights in real time.
5. Launch the automated Top-5 Spider Benchmark with live event streaming and charts.

### Option B: Interactive CLI
To query databases directly from the command terminal:
```bash
python main.py
```
Options available in the interactive menu:
- `1`: Run a natural language query with dual pipeline comparison.
- `2`: Run benchmark on the College dataset.
- `3`: Run Spider dataset benchmark.
- `4`: View active database schema & foreign keys.
- `5`: Reset database to preset records.

### Option C: Standalone Top-5 Spider Benchmark
To execute an automated dual-pipeline evaluation across 5 standard Spider databases:
```bash
python benchmark_spider_top5.py
```
This saves benchmark metrics and summary tables to `docs/benchmark_run_results.json`.

---

## 6. Running Tests

Run the complete test suite with `pytest`:
```bash
pytest tests/
```
All 42 test cases cover:
- Foreign-key graph construction and BFS join-path resolution.
- 4-Factor relevance scoring and duplicate column disambiguation.
- Spider benchmark query loading and ground-truth mapping.
- End-to-end LLM SQL generation and sandboxed SQLite execution.

---

## 7. Project Structure

```text
Text-to-SQL-Schema-Linker/
├── college.db                     # SQLite sample database (Student, Course, Enrollment, Faculty)
├── database.py                    # Database layer: schema introspection, execution sandbox, presets
├── schema_linker.py               # Core 4-factor scoring, graph join-path completion, schema pruning
├── llm.py                         # Google Gemini API integration (gemini-3.5-flash-lite) & SQL cleanup
├── prompts.py                     # Baseline (full schema) & Proposed (reduced schema) prompt builders
├── server.py                      # Multi-threaded HTTP server & REST APIs for web frontend
├── main.py                        # Interactive command-line interface (CLI)
├── spider_adapter.py              # Adapter for Spider benchmark databases & ground-truth queries
├── benchmark_spider_top5.py       # Standalone Top-5 Spider benchmark script
├── evaluator.py                   # Academic evaluation harness and metric calculations
├── evaluator_spider.py            # Spider evaluation runner used by CLI & tests
│
├── static/                        # Frontend Web Application
│   ├── index.html                 # Single-page dashboard HTML
│   ├── app.js                     # Frontend logic, charts, and API event streaming
│   └── index.css                  # UI styling & responsive layout
│
├── dataset/
│   ├── spider_data.zip            # Spider benchmark archive
│   └── spider_data/               # Extracted Spider databases and JSON ground truths
│
├── evaluation/
│   ├── questions.json             # Evaluation natural language questions
│   ├── ground_truth.json          # Ground-truth SQL and required schema elements
│   └── results/                   # Benchmark output logs
│
├── models/
│   └── all-MiniLM-L6-v2/          # Local SentenceTransformers dense embedding model
│
├── docs/
│   ├── PRD.md                     # Full Product Requirements Document & Research Design
│   ├── benchmark_run_results.json # Cached empirical Top-5 Spider benchmark metrics
│   ├── Dataset Benchmark Report/  # Academic benchmark analysis report
│   └── Planning and Final Report/ # System architecture diagram and final project report
│
├── tests/
│   ├── test_schema_linker_advanced.py # Unit tests for 4-factor scoring & disambiguation
│   ├── test_spider.py                 # Tests for Spider adapter & evaluation
│   └── test_system.py                 # End-to-end integration tests
│
├── .env.example                   # Template configuration file
├── requirements.txt               # Python package dependencies
└── README.md                      # Project documentation
```

---

## 8. Configuration Reference (.env)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(Required)* | Google Gemini API key from AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model name |
| `PORT` | `5000` | Port for the web application server |
| `LEXICAL_WEIGHT` | `0.40` | Weight for token overlap & stemming |
| `SEMANTIC_WEIGHT` | `0.35` | Weight for SentenceTransformer vector similarity |
| `TYPE_WEIGHT` | `0.15` | Weight for datatype intent heuristics |
| `RELATIONSHIP_WEIGHT` | `0.10` | Weight for foreign-key proximity |
| `TOP_K_TABLES` | `4` | Maximum candidate tables admitted before graph completion |
| `TOP_K_COLUMNS` | `8` | Maximum candidate content columns per table |
| `MIN_RELEVANCE_SCORE` | `0.15` | Minimum score threshold to admit a column |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model identifier |

---