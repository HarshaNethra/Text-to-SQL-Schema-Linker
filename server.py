import json
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from database import (
    DEFAULT_DB_PATH,
    clear_database,
    execute_query,
    execute_sandboxed_query,
    get_relationships,
    get_schema,
    initialize_database,
    list_tables,
    load_college_preset,
)
from llm import LLMClient
from prompts import build_baseline_prompt, build_proposed_prompt
from schema_linker import SchemaLinker

ACTIVE_DB_PATH = DEFAULT_DB_PATH
ACTIVE_DB_ID = "college"
initialize_database(ACTIVE_DB_PATH, load_preset=False)

linker = SchemaLinker()
llm = LLMClient()

# ---------------------------------------------------------------------------
# SPIDER TOP-5 BENCHMARK STATE & BACKGROUND RUNNER
# ---------------------------------------------------------------------------
BENCHMARK_STATE = {
    "status": "idle",  # "idle" | "running" | "completed" | "error" | "cancelled"
    "progress": 0.0,
    "current_db": None,
    "current_query_index": 0,
    "total_queries": 0,
    "current_question": "",
    "logs": [],
    "recent_records": [],
    "results": None,
    "error": None,
    "started_at": None,
    "finished_at": None,
}
BENCHMARK_CANCEL_FLAG = False
BENCHMARK_LOCK = threading.Lock()


from benchmark_spider_top5 import run_top5_benchmark, TARGET_DBS


def run_benchmark_background(queries_per_db: int = 1, target_dbs: Optional[List[str]] = None):
    global BENCHMARK_STATE, BENCHMARK_CANCEL_FLAG

    dbs = target_dbs if target_dbs else TARGET_DBS
    total = len(dbs) * queries_per_db

    with BENCHMARK_LOCK:
        BENCHMARK_CANCEL_FLAG = False
        BENCHMARK_STATE["status"] = "running"
        BENCHMARK_STATE["progress"] = 0.0
        BENCHMARK_STATE["current_db"] = dbs[0] if dbs else None
        BENCHMARK_STATE["current_query_index"] = 0
        BENCHMARK_STATE["total_queries"] = total
        BENCHMARK_STATE["current_question"] = ""
        BENCHMARK_STATE["logs"] = [f"[START] Commencing 5-Spider DB Benchmark ({len(dbs)} DBs x {queries_per_db} query/db = {total} dual runs)..."]
        BENCHMARK_STATE["recent_records"] = []
        BENCHMARK_STATE["error"] = None
        BENCHMARK_STATE["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        BENCHMARK_STATE["finished_at"] = None

    def progress_callback(data):
        with BENCHMARK_LOCK:
            evt = data.get("event")
            if evt == "query_starting":
                BENCHMARK_STATE["current_db"] = data.get("db_id")
                BENCHMARK_STATE["current_query_index"] = data.get("overall_query_index")
                BENCHMARK_STATE["current_question"] = data.get("question", "")
                BENCHMARK_STATE["progress"] = data.get("progress_pct", 0.0)
                msg = data.get("message", "")
                if msg:
                    BENCHMARK_STATE["logs"].append(msg)
                    if len(BENCHMARK_STATE["logs"]) > 50:
                        BENCHMARK_STATE["logs"] = BENCHMARK_STATE["logs"][-50:]
            elif evt == "query_completed":
                BENCHMARK_STATE["progress"] = data.get("progress_pct", 100.0)
                rec = data.get("record")
                if rec:
                    BENCHMARK_STATE["recent_records"].append(rec)
                    if len(BENCHMARK_STATE["recent_records"]) > 30:
                        BENCHMARK_STATE["recent_records"] = BENCHMARK_STATE["recent_records"][-30:]
                msg = data.get("message", "")
                if msg:
                    BENCHMARK_STATE["logs"].append(msg)
                    if len(BENCHMARK_STATE["logs"]) > 50:
                        BENCHMARK_STATE["logs"] = BENCHMARK_STATE["logs"][-50:]

    def cancel_check():
        return BENCHMARK_CANCEL_FLAG

    try:
        output = run_top5_benchmark(
            queries_per_db=queries_per_db,
            target_dbs=dbs,
            progress_fn=progress_callback,
            cancel_fn=cancel_check,
        )
        with BENCHMARK_LOCK:
            if BENCHMARK_CANCEL_FLAG:
                BENCHMARK_STATE["status"] = "cancelled"
                BENCHMARK_STATE["logs"].append("[CANCEL] Benchmark execution was terminated by user.")
            else:
                BENCHMARK_STATE["status"] = "completed"
                BENCHMARK_STATE["progress"] = 100.0
                BENCHMARK_STATE["logs"].append(f"[SUCCESS] Top-5 Spider Benchmark finished successfully ({len(output.get('results', []))} queries evaluated)!")
            BENCHMARK_STATE["results"] = output
            BENCHMARK_STATE["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        with BENCHMARK_LOCK:
            BENCHMARK_STATE["status"] = "error"
            BENCHMARK_STATE["error"] = str(e)
            BENCHMARK_STATE["logs"].append(f"[ERROR] Benchmark failed: {str(e)}")
            BENCHMARK_STATE["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def extract_required_columns_from_sql(sql_str: str, schema: Dict[str, Dict[str, str]]) -> Tuple[List[str], List[str]]:
    """
    Extracts referenced tables and columns (format 'Table.Column') from an SQL string
    against the known schema by matching explicit aliases, qualified names, and standalone column tokens.
    """
    if not sql_str:
        return [], []
    sql_lower = sql_str.lower()
    used_tables = set()
    used_cols = set()

    for tbl in schema.keys():
        if re.search(r'\b' + re.escape(tbl.lower()) + r'\b', sql_lower):
            used_tables.add(tbl)

    alias_map = {}
    alias_matches = re.findall(r'\b(?:from|join)\s+([a-zA-Z0-9_]+)(?:\s+(?:as\s+)?([a-zA-Z0-9_]+))?', sql_lower)
    for tbl_cand, alias_cand in alias_matches:
        for tbl in schema.keys():
            if tbl.lower() == tbl_cand:
                used_tables.add(tbl)
                if alias_cand and alias_cand not in ("on", "where", "join", "inner", "left", "cross", "as", "group", "order", "limit"):
                    alias_map[alias_cand] = tbl

    for tbl, cols in schema.items():
        for col in cols.keys():
            if re.search(r'\b' + re.escape(tbl.lower()) + r'\.' + re.escape(col.lower()) + r'\b', sql_lower):
                used_tables.add(tbl)
                used_cols.add(f"{tbl}.{col}")
                continue

            found_alias = False
            for alias, tgt_tbl in alias_map.items():
                if tgt_tbl == tbl and re.search(r'\b' + re.escape(alias) + r'\.' + re.escape(col.lower()) + r'\b', sql_lower):
                    used_tables.add(tbl)
                    used_cols.add(f"{tbl}.{col}")
                    found_alias = True
                    break
            if found_alias:
                continue

            if tbl in used_tables or len(schema) == 1:
                if re.search(r'\b' + re.escape(col.lower()) + r'\b', sql_lower):
                    used_cols.add(f"{tbl}.{col}")

    return sorted(list(used_tables)), sorted(list(used_cols))


class AppRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/status":
            tables = list_tables(ACTIVE_DB_PATH)
            schema = get_schema(ACTIVE_DB_PATH)
            relationships = get_relationships(ACTIVE_DB_PATH)
            return self._send_json({
                "db_path": ACTIVE_DB_PATH,
                "active_db_id": ACTIVE_DB_ID,
                "active_db_name": ACTIVE_DB_ID if ACTIVE_DB_ID != "college" else "College Preset (college.db)",
                "is_spider": ACTIVE_DB_ID != "college",
                "provider": llm.provider,
                "model_name": llm.model_name,
                "tables": tables,
                "schema": schema,
                "relationships": relationships,
                "total_columns": sum(len(c) for c in schema.values()),
            })

        if path == "/api/spider/databases":
            from spider_adapter import SpiderAdapter
            adapter = SpiderAdapter()
            return self._send_json({
                "active_db_id": ACTIVE_DB_ID,
                "databases": adapter.list_available_databases()
            })

        if path == "/api/sample-queries":
            target_db = query_params.get("db_id", [ACTIVE_DB_ID])[0]
            target_table = query_params.get("table", [None])[0]
            limit_str = query_params.get("limit", ["8"])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 8

            sample_queries = []
            if target_db == "college":
                from evaluator import load_evaluation_dataset
                try:
                    dataset = load_evaluation_dataset()
                    for item in dataset:
                        req_tables = item.get("all_required_tables", [])
                        if target_table:
                            if not any(t.lower() == target_table.lower() for t in req_tables):
                                continue
                        sample_queries.append({
                            "question": item.get("question", ""),
                            "sql": item.get("ground_truth_sql", ""),
                            "tables": req_tables,
                            "db_id": "college"
                        })
                        if len(sample_queries) >= limit:
                            break
                except Exception as e:
                    print(f"Notice loading college dataset queries: {e}")
            else:
                try:
                    from spider_adapter import SpiderAdapter
                    adapter = SpiderAdapter()
                    sample_queries = adapter.get_sample_queries(target_db, table_name=target_table, limit=limit)
                except Exception as e:
                    print(f"Notice loading Spider queries for {target_db}: {e}")

            return self._send_json({
                "db_id": target_db,
                "table": target_table,
                "queries": sample_queries,
            })

        if path == "/api/benchmark/top5":
            with BENCHMARK_LOCK:
                results_data = BENCHMARK_STATE.get("results")
                if not results_data:
                    json_path = os.path.join(os.path.dirname(__file__), "docs", "benchmark_run_results.json")
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                results_data = json.load(f)
                        except Exception as e:
                            print(f"[BENCHMARK] Error loading saved benchmark: {e}")
                            results_data = None

                return self._send_json({
                    "status": BENCHMARK_STATE["status"],
                    "progress": BENCHMARK_STATE["progress"],
                    "current_db": BENCHMARK_STATE["current_db"],
                    "current_query_index": BENCHMARK_STATE["current_query_index"],
                    "total_queries": BENCHMARK_STATE["total_queries"],
                    "current_question": BENCHMARK_STATE["current_question"],
                    "logs": list(BENCHMARK_STATE["logs"][-30:]),
                    "recent_records": list(BENCHMARK_STATE["recent_records"]),
                    "error": BENCHMARK_STATE["error"],
                    "started_at": BENCHMARK_STATE["started_at"],
                    "finished_at": BENCHMARK_STATE["finished_at"],
                    "results": results_data,
                    "target_dbs": ["hr_1", "car_1", "flight_2", "world_1", "sakila_1"]
                })

        if path.startswith("/api/table/"):
            table_name = urllib.parse.unquote(path[len("/api/table/"):].strip())
            # Safely query table contents
            schema = get_schema(ACTIVE_DB_PATH)
            if table_name not in schema:
                return self._send_json({"error": f"Table '{table_name}' not found."}, status=404)

            res = execute_query(f'SELECT * FROM "{table_name}" LIMIT 200;', ACTIVE_DB_PATH)
            return self._send_json({
                "table_name": table_name,
                "columns": res["columns"],
                "rows": res["rows"],
                "rowcount": res["rowcount"],
                "schema": schema.get(table_name, {}),
            })

        # Serve static files from static/ directory
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        req_file = path.lstrip("/")
        if not req_file or req_file == "":
            req_file = "index.html"

        file_path = os.path.join(static_dir, req_file)
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, f"File not found: {path}")

    def do_POST(self):
        global ACTIVE_DB_PATH, ACTIVE_DB_ID
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_json_body()

        if path == "/api/query":
            question = body.get("question", "").strip()
            if not question:
                return self._send_json({"error": "Question / prompt cannot be empty."}, status=400)

            # Snapshot schema and relationships before either pipeline executes
            initial_schema = get_schema(ACTIVE_DB_PATH)
            initial_relationships = get_relationships(ACTIVE_DB_PATH)
            full_col_count = sum(len(c) for c in initial_schema.values())

            under_the_hood = []

            # -----------------------------------------------------------------
            # 1. BASELINE PIPELINE (Full Database Schema -> LLM)
            # -----------------------------------------------------------------
            under_the_hood.append({
                "step": 1,
                "phase": "Baseline Initiation",
                "message": f"Building baseline prompt with full schema ({full_col_count} columns across {len(initial_schema)} table(s))..."
            })
            base_start = time.time()
            base_prompt = build_baseline_prompt(question, initial_schema, initial_relationships)
            base_llm_res = llm.generate_sql(base_prompt)
            
            # Execute Baseline in isolated sandbox to prevent mutating disk DB before proposed runs
            base_exec = execute_sandboxed_query(base_llm_res["sql"], ACTIVE_DB_PATH)
            base_exec_time = time.time() - base_start
            base_gen_tps = round(base_llm_res["output_tokens"] / max(0.001, base_llm_res["latency"]), 1)
            base_e2e_qps = round(1.0 / max(0.001, base_exec_time), 2)

            under_the_hood.append({
                "step": 2,
                "phase": "Baseline Complete",
                "message": f"Baseline generated SQL in {base_llm_res['latency']:.2f}s ({base_llm_res['input_tokens']} input tokens). Sandboxed execution: {'SUCCESS' if base_exec['success'] else 'FAILED'}."
            })

            # -----------------------------------------------------------------
            # 2. PROPOSED PIPELINE (4-Factor Schema Linking -> Reduced LLM)
            # -----------------------------------------------------------------
            under_the_hood.append({
                "step": 3,
                "phase": "Proposed Schema Linking",
                "message": f"Computing 4-Factor relevance scores (Lexical, Semantic, Type Match, FK Graph)..."
            })
            link_start = time.time()
            link_res = linker.link_schema(question, initial_schema, initial_relationships)
            prop_prompt = build_proposed_prompt(question, link_res["reduced_schema"], initial_relationships)
            prop_llm_res = llm.generate_sql(prop_prompt)

            # Execute Proposed SQL on active DB
            prop_exec = execute_query(prop_llm_res["sql"], ACTIVE_DB_PATH)
            prop_total_time = time.time() - link_start
            prop_gen_tps = round(prop_llm_res["output_tokens"] / max(0.001, prop_llm_res["latency"]), 1)
            prop_e2e_qps = round(1.0 / max(0.001, prop_total_time), 2)

            under_the_hood.append({
                "step": 4,
                "phase": "Proposed Complete",
                "message": f"Schema reduced to {link_res['schema_reduction']['reduced_columns']} cols (-{link_res['schema_reduction']['reduction_percentage']}%). Generated SQL in {prop_llm_res['latency']:.2f}s ({prop_llm_res['input_tokens']} tokens). Execution: {'SUCCESS' if prop_exec['success'] else 'FAILED'}."
            })

            # -----------------------------------------------------------------
            # 3. GROUND TRUTH IDENTIFICATION & REQUIRED COLUMNS RESOLUTION
            # -----------------------------------------------------------------
            expected_sql = body.get("expected_sql", "").strip()
            gt_cols = []
            gt_tables = []
            matched_gt_item = None

            def _clean_q(t: str) -> str:
                return re.sub(r'[^a-zA-Z0-9]', '', t or '').lower()

            norm_question = _clean_q(question)

            if not expected_sql:
                if ACTIVE_DB_ID and ACTIVE_DB_ID != "college":
                    try:
                        from spider_adapter import SpiderAdapter
                        sp_adapter = SpiderAdapter()
                        db_queries = sp_adapter.load_all_queries_for_db(ACTIVE_DB_ID)
                        for item in db_queries:
                            if norm_question == _clean_q(item.get("question", "")):
                                expected_sql = item.get("query", "").strip()
                                matched_gt_item = item
                                gt_tables, gt_cols = sp_adapter.extract_ground_truth_elements(item)
                                break
                    except Exception as e:
                        print(f"[EVAL] Notice loading Spider queries for evaluation: {e}")
                else:
                    try:
                        from evaluator import load_evaluation_dataset
                        eval_ds = load_evaluation_dataset()
                        for item in eval_ds:
                            if norm_question == _clean_q(item.get("question", "")):
                                expected_sql = item.get("ground_truth_sql", "").strip()
                                matched_gt_item = item
                                gt_cols = item.get("all_required_columns") or (item.get("direct_columns", []) + item.get("structural_columns", []))
                                gt_tables = item.get("all_required_tables") or (item.get("direct_tables", []) + item.get("structural_tables", []))
                                break
                    except Exception as e:
                        print(f"[EVAL] Notice loading College dataset for evaluation: {e}")

            if expected_sql and not gt_cols:
                gt_tables, gt_cols = extract_required_columns_from_sql(expected_sql, initial_schema)

            # Ground truth required columns
            required_cols_set = {c.lower() for c in gt_cols}

            # Columns sent by Baseline
            base_sent_cols = {f"{t}.{c}".lower() for t, cols in initial_schema.items() for c in cols}
            base_cols_sent_count = len(base_sent_cols)

            # Columns sent by Proposed
            prop_sent_cols = {f"{t}.{c}".lower() for t, cols in link_res.get("reduced_schema", {}).items() for c in cols}
            prop_cols_sent_count = len(prop_sent_cols)

            if required_cols_set:
                # 1. Schema Linking Precision (% of sent columns that were actually required)
                base_match = base_sent_cols & required_cols_set
                base_precision = round((len(base_match) / max(1, len(base_sent_cols))) * 100.0, 1)

                prop_match = prop_sent_cols & required_cols_set
                prop_precision = round((len(prop_match) / max(1, len(prop_sent_cols))) * 100.0, 1)

                # 2. Schema Recall Accuracy (% of required columns that were sent)
                base_recall = round((len(base_match) / max(1, len(required_cols_set))) * 100.0, 1)
                prop_recall = round((len(prop_match) / max(1, len(required_cols_set))) * 100.0, 1)

                # 3. Schema F1-Score
                base_f1 = round((2 * base_precision * base_recall) / max(0.01, base_precision + base_recall), 1)
                prop_f1 = round((2 * prop_precision * prop_recall) / max(0.01, prop_precision + prop_recall), 1)

                # 4. Check if algo sent >= all the required columns to generate a successful SQL query
                base_has_all = required_cols_set.issubset(base_sent_cols)
                prop_has_all = required_cols_set.issubset(prop_sent_cols)

                base_sufficiency = {
                    "has_all_required": base_has_all,
                    "required_count": len(required_cols_set),
                    "sent_required_count": len(base_match),
                    "coverage_pct": base_recall,
                    "missing_columns": sorted(list(required_cols_set - base_sent_cols)),
                    "is_custom": False,
                }
                prop_sufficiency = {
                    "has_all_required": prop_has_all,
                    "required_count": len(required_cols_set),
                    "sent_required_count": len(prop_match),
                    "coverage_pct": prop_recall,
                    "missing_columns": sorted(list(required_cols_set - prop_sent_cols)),
                    "is_custom": False,
                }
            else:
                # Fallback for custom prompt without gold benchmark SQL
                base_tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', base_llm_res["sql"].lower()))
                prop_tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', prop_llm_res["sql"].lower()))
                base_used = set()
                for tbl, cols in initial_schema.items():
                    for col in cols.keys():
                        if col.lower() in base_tokens or f"{tbl.lower()}.{col.lower()}" in base_llm_res["sql"].lower():
                            base_used.add((tbl, col))
                base_precision = min(100.0, round((max(1, len(base_used)) / max(1, full_col_count)) * 100.0, 1))
                base_recall = 100.0
                base_f1 = base_precision

                prop_used = set()
                for tbl, cols in link_res.get("reduced_schema", {}).items():
                    for col in cols:
                        if col.lower() in prop_tokens or f"{tbl.lower()}.{col.lower()}" in prop_llm_res["sql"].lower():
                            prop_used.add((tbl, col))
                prop_precision = min(100.0, round((max(1, len(prop_used)) / max(1, prop_cols_sent_count)) * 100.0, 1))
                prop_recall = 100.0
                prop_f1 = prop_precision

                base_sufficiency = {"has_all_required": True, "required_count": 0, "sent_required_count": 0, "coverage_pct": 100.0, "missing_columns": [], "is_custom": True}
                prop_sufficiency = {"has_all_required": True, "required_count": 0, "sent_required_count": 0, "coverage_pct": 100.0, "missing_columns": [], "is_custom": True}

            # -----------------------------------------------------------------
            # 4. COMPARISON & THROUGHPUT METRICS
            # -----------------------------------------------------------------
            throughput_gain_pct = round(
                ((prop_e2e_qps - base_e2e_qps) / max(0.01, base_e2e_qps)) * 100.0, 1
            )
            token_red_pct = round(
                ((base_llm_res["input_tokens"] - prop_llm_res["input_tokens"]) / max(1, base_llm_res["input_tokens"])) * 100.0, 2
            )

            # -----------------------------------------------------------------
            # 5. EXECUTION & LOGIC VERIFICATION
            # -----------------------------------------------------------------
            gt_exec = None
            base_correct = None
            prop_correct = None
            verdict = "NO_GROUND_TRUTH"
            verdict_label = "CUSTOM QUERY"
            verdict_detail = "Custom ad-hoc prompt (no benchmark ground-truth label)."

            if expected_sql:
                gt_exec = execute_sandboxed_query(expected_sql, ACTIVE_DB_PATH)

                def _norm_cell(val):
                    if val is None:
                        return "NULL"
                    if isinstance(val, float):
                        return str(round(val, 4))
                    return str(val).strip()

                def _norm_row(row):
                    return tuple(_norm_cell(c) for c in row)

                if gt_exec.get("success"):
                    gt_rows = sorted([_norm_row(r) for r in gt_exec.get("rows", [])])

                    if base_exec.get("success"):
                        b_rows = sorted([_norm_row(r) for r in base_exec.get("rows", [])])
                        base_correct = (gt_rows == b_rows)
                    else:
                        base_correct = False

                    if prop_exec.get("success"):
                        p_rows = sorted([_norm_row(r) for r in prop_exec.get("rows", [])])
                        prop_correct = (gt_rows == p_rows)
                    else:
                        prop_correct = False

                    if base_correct and prop_correct:
                        verdict = "BOTH_CORRECT"
                        verdict_label = "BOTH QUERIES ARE CORRECT"
                        verdict_detail = f"Both Baseline and Proposed produced the exact expected output of the Spider benchmark ({len(gt_rows)} row(s))."
                    elif prop_correct and not base_correct:
                        verdict = "PROPOSED_CORRECT"
                        verdict_label = "PROPOSED QUERY IS CORRECT"
                        b_row_cnt = len(base_exec.get('rows', [])) if base_exec.get('success') else 'Failed'
                        verdict_detail = f"Proposed query produced the exact expected Spider benchmark output ({len(gt_rows)} row(s)). Baseline produced a mismatch ({b_row_cnt} row(s))."
                    elif base_correct and not prop_correct:
                        verdict = "BASELINE_CORRECT"
                        verdict_label = "BASELINE QUERY IS CORRECT"
                        p_row_cnt = len(prop_exec.get('rows', [])) if prop_exec.get('success') else 'Failed'
                        verdict_detail = f"Baseline query produced the exact expected Spider benchmark output ({len(gt_rows)} row(s)). Proposed produced a mismatch ({p_row_cnt} row(s) vs {len(gt_rows)} expected)."
                    else:
                        verdict = "NEITHER_CORRECT"
                        verdict_label = "NEITHER QUERY MATCHES GROUND TRUTH"
                        verdict_detail = f"Neither generated query matched the expected Spider benchmark output ({len(gt_rows)} row(s))."
                else:
                    verdict = "GT_EXECUTION_FAILED"
                    verdict_label = "GROUND TRUTH EXECUTION ERROR"
                    verdict_detail = f"Ground truth query failed to execute: {gt_exec.get('error')}"

                under_the_hood.append({
                    "step": 5,
                    "phase": "Ground Truth Verification",
                    "message": f"Spider Benchmark Logic Check: [{verdict_label}] - {verdict_detail}"
                })

            is_exec_match = False
            if base_exec.get("success") and prop_exec.get("success"):
                try:
                    b_check = sorted([str(r) for r in base_exec.get("rows", [])])
                    p_check = sorted([str(r) for r in prop_exec.get("rows", [])])
                    is_exec_match = (b_check == p_check)
                except Exception:
                    is_exec_match = (base_exec.get("rows") == prop_exec.get("rows"))

            return self._send_json({
                "mode": "compare",
                "question": question,
                "under_the_hood": under_the_hood,
                "ground_truth": {
                    "has_ground_truth": bool(expected_sql),
                    "sql": expected_sql,
                    "required_columns": list(required_cols_set),
                    "execution": gt_exec,
                    "baseline_correct": base_correct,
                    "proposed_correct": prop_correct,
                    "verdict": verdict,
                    "verdict_label": verdict_label,
                    "verdict_detail": verdict_detail,
                },
                "baseline": {
                    "prompt": base_prompt,
                    "sql": base_llm_res["sql"],
                    "llm_latency": base_llm_res["latency"],
                    "total_latency": round(base_exec_time, 4),
                    "input_tokens": base_llm_res["input_tokens"],
                    "output_tokens": base_llm_res["output_tokens"],
                    "columns_sent": base_cols_sent_count,
                    "precision": base_precision,
                    "recall": base_recall,
                    "f1": base_f1,
                    "sufficiency": base_sufficiency,
                    "accuracy": 100.0 if base_exec.get("success") else 0.0,
                    "throughput": {
                        "generation_tps": base_gen_tps,
                        "e2e_qps": base_e2e_qps,
                    },
                    "execution": base_exec,
                },
                "proposed": {
                    "prompt": prop_prompt,
                    "sql": prop_llm_res["sql"],
                    "schema_linking": link_res,
                    "llm_latency": prop_llm_res["latency"],
                    "total_latency": round(prop_total_time, 4),
                    "input_tokens": prop_llm_res["input_tokens"],
                    "output_tokens": prop_llm_res["output_tokens"],
                    "columns_sent": prop_cols_sent_count,
                    "precision": prop_precision,
                    "recall": prop_recall,
                    "f1": prop_f1,
                    "sufficiency": prop_sufficiency,
                    "accuracy": 100.0 if prop_exec.get("success") else 0.0,
                    "throughput": {
                        "generation_tps": prop_gen_tps,
                        "e2e_qps": prop_e2e_qps,
                        "linking_cps": link_res.get("linking_throughput_cps", 0.0),
                    },
                    "execution": prop_exec,
                },
                "comparison": {
                    "schema_columns_full": base_cols_sent_count,
                    "schema_columns_reduced": prop_cols_sent_count,
                    "schema_reduction_pct": link_res["schema_reduction"]["reduction_percentage"],
                    "token_reduction_pct": token_red_pct,
                    "throughput_gain_pct": throughput_gain_pct,
                    "baseline_qps": base_e2e_qps,
                    "proposed_qps": prop_e2e_qps,
                    "baseline_precision": base_precision,
                    "proposed_precision": prop_precision,
                    "baseline_recall": base_recall,
                    "proposed_recall": prop_recall,
                    "baseline_f1": base_f1,
                    "proposed_f1": prop_f1,
                    "base_sufficiency": base_sufficiency,
                    "prop_sufficiency": prop_sufficiency,
                    "required_columns": sorted(list(required_cols_set)),
                    "execution_match": is_exec_match,
                }
            })

        elif path == "/api/execute-sql":
            sql = body.get("sql", "").strip()
            if not sql:
                return self._send_json({"error": "SQL statement cannot be empty."}, status=400)
            exec_start = time.time()
            res = execute_query(sql, ACTIVE_DB_PATH)
            exec_time = time.time() - exec_start
            res["execution_time_sec"] = round(exec_time, 4)
            return self._send_json(res)

        elif path == "/api/preset":
            ACTIVE_DB_ID = "college"
            ACTIVE_DB_PATH = DEFAULT_DB_PATH
            load_college_preset(ACTIVE_DB_PATH, force_recreate=True)
            schema = get_schema(ACTIVE_DB_PATH)
            return self._send_json({
                "message": "College dataset preset loaded successfully.",
                "active_db_id": ACTIVE_DB_ID,
                "active_db_name": "College Preset (college.db)",
                "is_spider": False,
                "db_path": ACTIVE_DB_PATH,
                "tables": list_tables(ACTIVE_DB_PATH),
                "schema": schema,
                "relationships": get_relationships(ACTIVE_DB_PATH),
            })

        elif path == "/api/clear":
            if ACTIVE_DB_ID != "college":
                return self._send_json({
                    "error": f"Cannot drop tables from Spider benchmark database '{ACTIVE_DB_ID}'. Spider datasets are read-only benchmarks.",
                }, status=400)
            clear_database(ACTIVE_DB_PATH)
            return self._send_json({
                "message": "All tables dropped. Database is now empty.",
                "tables": [],
                "schema": {},
                "relationships": [],
            })

        elif path == "/api/spider/switch":
            from spider_adapter import SpiderAdapter
            db_id = body.get("db_id", "").strip()
            if db_id:
                if db_id == "college":
                    ACTIVE_DB_ID = "college"
                    ACTIVE_DB_PATH = DEFAULT_DB_PATH
                    # If college.db is missing or has 0 tables, force create/populate preset
                    if not list_tables(ACTIVE_DB_PATH):
                        load_college_preset(ACTIVE_DB_PATH, force_recreate=True)
                    else:
                        load_college_preset(ACTIVE_DB_PATH, force_recreate=False)
                else:
                    adapter = SpiderAdapter()
                    ACTIVE_DB_PATH = adapter.get_db_path(db_id)
                    ACTIVE_DB_ID = db_id
            return self._send_json({
                "message": f"Active database switched to '{ACTIVE_DB_ID}'.",
                "active_db_id": ACTIVE_DB_ID,
                "active_db_name": ACTIVE_DB_ID if ACTIVE_DB_ID != "college" else "College Preset (college.db)",
                "is_spider": ACTIVE_DB_ID != "college",
                "db_path": ACTIVE_DB_PATH,
                "tables": list_tables(ACTIVE_DB_PATH),
                "schema": get_schema(ACTIVE_DB_PATH),
                "relationships": get_relationships(ACTIVE_DB_PATH),
            })

        elif path == "/api/benchmark/top5/run":
            with BENCHMARK_LOCK:
                if BENCHMARK_STATE["status"] == "running":
                    return self._send_json({
                        "error": "A benchmark run is already in progress.",
                        "status": "running"
                    }, status=409)

            queries_per_db = int(body.get("queries_per_db", 1))
            queries_per_db = max(1, min(5, queries_per_db))
            target_dbs = body.get("target_dbs", None)

            t = threading.Thread(
                target=run_benchmark_background,
                kwargs={"queries_per_db": queries_per_db, "target_dbs": target_dbs},
                daemon=True
            )
            t.start()

            return self._send_json({
                "message": f"Spider Top-5 benchmark started ({queries_per_db} query/db).",
                "status": "running",
                "queries_per_db": queries_per_db
            })

        elif path == "/api/benchmark/top5/stop":
            global BENCHMARK_CANCEL_FLAG
            BENCHMARK_CANCEL_FLAG = True
            with BENCHMARK_LOCK:
                BENCHMARK_STATE["logs"].append("[NOTICE] Stop requested by user. Halting gracefully...")
            return self._send_json({"message": "Cancellation requested. Benchmark will stop at next safe step."})

        else:
            self.send_error(404, f"API endpoint not found: {path}")

    def log_message(self, format, *args):
        # Clean logging format
        print(f"[HTTP] {self.address_string()} - {args[0]} {args[1]}")


def warmup_system():
    """Warms up local sentence embeddings, schema cache, and the Gemini LLM API."""
    print("[WARMUP] Starting system warm-up sequence...")
    t0 = time.time()

    # 1. Warm up schema & table list
    schema = get_schema(ACTIVE_DB_PATH)
    relationships = get_relationships(ACTIVE_DB_PATH)
    tables = list_tables(ACTIVE_DB_PATH)
    print(f"[WARMUP] Schema cache: {len(tables)} table(s) indexed.")

    # 2. Warm up Sentence Transformer embeddings model
    try:
        sample_schema = schema if schema else {"sample_table": {"id": "INTEGER", "name": "TEXT"}}
        link_res = linker.link_schema("test query warmup", sample_schema, relationships, top_k_tables=2)
        print("[WARMUP] SentenceTransformer: Loaded locally & embeddings cached.")
    except Exception as e:
        print(f"[WARMUP] SentenceTransformer notice: {e}")

    # 3. Warm up Gemini API with a test prompt
    warmup_prompt = "Find all records in the active database"
    print(f"[WARMUP] Sending test prompt to Gemini API ('{warmup_prompt}')...")
    try:
        t_llm = time.time()
        effective_schema = schema if schema else {"sample_table": {"id": "INTEGER", "name": "TEXT"}}
        prop_prompt = build_proposed_prompt(warmup_prompt, effective_schema, relationships)
        res = llm.generate_sql(prop_prompt)
        llm_duration = time.time() - t_llm
        sql_preview = res.get("sql", "").replace("\n", " ").strip()[:50]
        print(f"[WARMUP] Gemini API response received in {llm_duration:.2f}s (SQL: {sql_preview}...).")
        print(f"[WARMUP] Warm-up complete in {time.time() - t0:.2f}s. System is ready.\n")
    except Exception as e:
        print(f"[WARMUP] Gemini API warm-up notice: {e}\n")


def start_server(port: int = 5000):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, AppRequestHandler)
    print(f"\n============================================================")
    print(f" NL TO SQL OPTIMIZER // CMD WEB APPLICATION ")
    print(f"============================================================")
    print(f" Local URL: http://localhost:{port}")
    print(f" Active Database: {ACTIVE_DB_PATH}")
    print(f" LLM Provider: {llm.provider} (Model: {llm.model_name})")
    print(f" Press Ctrl+C to stop the server.\n")

    # Run warm-up sequence asynchronously so server accepts requests immediately
    import threading
    threading.Thread(target=warmup_system, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    start_server(port)
