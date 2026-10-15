import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import execute_query, get_relationships, get_schema
from evaluator import compute_schema_linking_metrics
from llm import LLMClient
from prompts import build_baseline_prompt, build_proposed_prompt
from schema_linker import SchemaLinker
from spider_adapter import SpiderAdapter

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation", "results")


class SpiderBenchmarkEvaluator:
    """
    Runs automated schema linking & Text-to-SQL benchmark evaluation on the Spider dataset.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        linker: Optional[SchemaLinker] = None,
    ):
        self.adapter = SpiderAdapter()
        self.linker = linker or SchemaLinker()
        self.llm = llm_client or LLMClient()
        self._schema_cache: Dict[str, Tuple[Dict[str, Dict[str, str]], List[Dict[str, str]]]] = {}

    def get_db_schema_and_rels(self, db_path: str):
        if db_path not in self._schema_cache:
            schema = get_schema(db_path)
            rels = get_relationships(db_path)
            self._schema_cache[db_path] = (schema, rels)
        return self._schema_cache[db_path]

    def evaluate_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs Baseline and Proposed pipelines on a single Spider test item.
        """
        db_path = item["db_path"]
        q = item["question"]
        gt_sql = item["ground_truth_sql"]

        schema, relationships = self.get_db_schema_and_rels(db_path)
        full_col_count = sum(len(cols) for cols in schema.values())

        # Ground truth execution
        gt_exec_start = time.time()
        gt_exec = execute_query(gt_sql, db_path)
        gt_exec_time = time.time() - gt_exec_start

        # ----------------- 1. BASELINE PIPELINE -----------------
        base_prompt = build_baseline_prompt(q, schema, relationships)
        base_llm_res = self.llm.generate_sql(base_prompt)
        base_sql = base_llm_res["sql"]

        base_exec_start = time.time()
        base_exec = execute_query(base_sql, db_path)
        base_exec_time = time.time() - base_exec_start

        # ----------------- 2. PROPOSED PIPELINE -----------------
        link_res = self.linker.link_schema(q, schema, relationships)
        reduced_schema = link_res["reduced_schema"]
        linking_time = link_res["linking_time_seconds"]

        # Schema precision/recall
        schema_metrics = compute_schema_linking_metrics(reduced_schema, item)

        prop_prompt = build_proposed_prompt(q, reduced_schema, relationships)
        prop_llm_res = self.llm.generate_sql(prop_prompt)
        prop_sql = prop_llm_res["sql"]

        prop_exec_start = time.time()
        prop_exec = execute_query(prop_sql, db_path)
        prop_exec_time = time.time() - prop_exec_start

        reduced_col_count = sum(len(cols) for cols in reduced_schema.values())
        schema_red_pct = (
            ((full_col_count - reduced_col_count) / full_col_count) * 100.0
            if full_col_count > 0 else 0.0
        )
        token_red_pct = (
            ((base_llm_res["input_tokens"] - prop_llm_res["input_tokens"]) / max(1, base_llm_res["input_tokens"])) * 100.0
        )

        # Result correctness check against ground-truth
        base_correct = False
        prop_correct = False
        if gt_exec.get("success"):
            gt_rows = sorted([str(r) for r in gt_exec.get("rows", [])])
            if base_exec.get("success"):
                b_rows = sorted([str(r) for r in base_exec.get("rows", [])])
                base_correct = (gt_rows == b_rows)
            if prop_exec.get("success"):
                p_rows = sorted([str(r) for r in prop_exec.get("rows", [])])
                prop_correct = (gt_rows == p_rows)

        return {
            "id": item["id"],
            "db_id": item["db_id"],
            "question": q,
            "ground_truth_sql": gt_sql,
            "full_columns": full_col_count,
            "reduced_columns": reduced_col_count,
            "schema_reduction_pct": round(schema_red_pct, 2),
            "token_reduction_pct": round(token_red_pct, 2),
            "linking_time": round(linking_time, 4),
            "baseline": {
                "sql": base_sql,
                "input_tokens": base_llm_res["input_tokens"],
                "llm_latency": base_llm_res["latency"],
                "exec_latency": round(base_exec_time, 4),
                "total_latency": round(base_llm_res["latency"] + base_exec_time, 4),
                "exec_success": base_exec.get("success", False),
                "result_correct": base_correct,
                "error": base_exec.get("error"),
            },
            "proposed": {
                "sql": prop_sql,
                "input_tokens": prop_llm_res["input_tokens"],
                "llm_latency": prop_llm_res["latency"],
                "exec_latency": round(prop_exec_time, 4),
                "total_latency": round(linking_time + prop_llm_res["latency"] + prop_exec_time, 4),
                "exec_success": prop_exec.get("success", False),
                "result_correct": prop_correct,
                "error": prop_exec.get("error"),
                "reduced_schema": reduced_schema,
                "content_columns": link_res.get("content_columns", {}),
                "structural_columns": link_res.get("structural_columns", {}),
                "validation_passed": link_res.get("validation", {}).get("is_valid", True),
                "fallback_used": link_res.get("validation", {}).get("fallback_used", False),
                "join_paths": link_res.get("validation", {}).get("join_paths", []),
            },
            "schema_metrics": schema_metrics,
        }

    def run_benchmark(
        self,
        db_id: Optional[str] = None,
        limit: Optional[int] = 10,
        offset: int = 0,
        export: bool = True
    ) -> Dict[str, Any]:
        """
        Runs benchmark across Spider dev queries and returns aggregate results.
        """
        raw_queries = self.adapter.load_dev_queries(db_id=db_id, limit=limit, offset=offset)
        print(f"\n============================================================")
        print(f" SPIDER TEXT-TO-SQL BENCHMARK RUNNER ")
        print(f" Target Database: {db_id or 'ALL'}")
        print(f" Total Queries to Evaluate: {len(raw_queries)}")
        print(f" LLM Provider: {self.llm.provider} ({self.llm.model_name})")
        print(f"============================================================\n")

        results = []
        for idx, raw_q in enumerate(raw_queries, start=1):
            try:
                item = self.adapter.format_as_evaluation_item(raw_q, idx)
                res = self.evaluate_item(item)
                results.append(res)
                b_ok = "PASS" if res["baseline"]["exec_success"] else "FAIL"
                p_ok = "PASS" if res["proposed"]["exec_success"] else "FAIL"
                print(f"[{idx}/{len(raw_queries)}] DB: {res['db_id']:<15} | Base: {b_ok} | Prop: {p_ok} | Red: {res['schema_reduction_pct']}% | Q: {res['question'][:45]}...")
            except Exception as e:
                print(f"[{idx}/{len(raw_queries)}] Error on query: {e}")

        # Compute Aggregates
        n = max(1, len(results))
        avg_schema_red = sum(r["schema_reduction_pct"] for r in results) / n
        avg_token_red = sum(r["token_reduction_pct"] for r in results) / n
        base_exec_acc = (sum(1 for r in results if r["baseline"]["exec_success"]) / n) * 100.0
        prop_exec_acc = (sum(1 for r in results if r["proposed"]["exec_success"]) / n) * 100.0
        base_result_acc = (sum(1 for r in results if r["baseline"]["result_correct"]) / n) * 100.0
        prop_result_acc = (sum(1 for r in results if r["proposed"]["result_correct"]) / n) * 100.0
        avg_table_recall = (sum(r["schema_metrics"]["table_recall"] for r in results) / n) * 100.0
        avg_col_recall = (sum(r["schema_metrics"]["direct_col_recall"] for r in results) / n) * 100.0

        summary = {
            "total_queries": len(results),
            "target_db": db_id or "ALL",
            "llm_provider": self.llm.provider,
            "avg_schema_reduction_pct": round(avg_schema_red, 2),
            "avg_token_reduction_pct": round(avg_token_red, 2),
            "baseline_execution_accuracy_pct": round(base_exec_acc, 2),
            "proposed_execution_accuracy_pct": round(prop_exec_acc, 2),
            "baseline_result_correctness_pct": round(base_result_acc, 2),
            "proposed_result_correctness_pct": round(prop_result_acc, 2),
            "avg_table_recall_pct": round(avg_table_recall, 2),
            "avg_direct_column_recall_pct": round(avg_col_recall, 2),
        }

        print("\n" + "=" * 60)
        print(" SPIDER BENCHMARK SUMMARY RESULTS ")
        print("=" * 60)
        print(f" Total Evaluated Queries:           {summary['total_queries']}")
        print(f" Avg Schema Reduction:              {summary['avg_schema_reduction_pct']}%")
        print(f" Avg Prompt Token Reduction:        {summary['avg_token_reduction_pct']}%")
        print(f" Baseline SQL Execution Accuracy:   {summary['baseline_execution_accuracy_pct']}%")
        print(f" Proposed SQL Execution Accuracy:   {summary['proposed_execution_accuracy_pct']}%")
        print(f" Proposed Table Recall:             {summary['avg_table_recall_pct']}%")
        print(f" Proposed Direct Column Recall:     {summary['avg_direct_column_recall_pct']}%")
        print(f" Result Match Accuracy (Baseline):  {summary['baseline_result_correctness_pct']}%")
        print(f" Result Match Accuracy (Proposed):  {summary['proposed_result_correctness_pct']}%")
        print("=" * 60)

        if export and results:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_tag = db_id or "all"
            json_path = os.path.join(RESULTS_DIR, f"spider_{db_tag}_{timestamp}.json")
            csv_path = os.path.join(RESULTS_DIR, f"spider_{db_tag}_{timestamp}.csv")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"summary": summary, "results": results}, f, indent=2)

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "DB_ID", "Question", "Full_Cols", "Reduced_Cols",
                    "Schema_Red_Pct", "Token_Red_Pct", "Base_Exec", "Prop_Exec",
                    "Base_Correct", "Prop_Correct", "Table_Recall", "Col_Recall"
                ])
                for r in results:
                    writer.writerow([
                        r["id"], r["db_id"], r["question"], r["full_columns"],
                        r["reduced_columns"], r["schema_reduction_pct"],
                        r["token_reduction_pct"], r["baseline"]["exec_success"],
                        r["proposed"]["exec_success"], r["baseline"]["result_correct"],
                        r["proposed"]["result_correct"], r["schema_metrics"]["table_recall"],
                        r["schema_metrics"]["direct_col_recall"]
                    ])
            print(f"\nSaved benchmark outputs to:")
            print(f"  • JSON: {json_path}")
            print(f"  • CSV:  {csv_path}\n")

        return {"summary": summary, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Evaluate Schema Linking on Spider Benchmark Dataset")
    parser.add_argument("--db", type=str, default="concert_singer", help="Specific Spider db_id (e.g. concert_singer, flight_2) or 'all'")
    parser.add_argument("--limit", type=int, default=10, help="Number of queries to evaluate (default 10)")
    parser.add_argument("--offset", type=int, default=0, help="Query offset (default 0)")
    parser.add_argument("--model", type=str, default=None, help="Gemini model name (default from .env)")
    parser.add_argument("--k-tables", type=int, default=4, help="Max tables to link (default 4)")
    parser.add_argument("--k-columns", type=int, default=8, help="Max columns to link (default 8)")
    args = parser.parse_args()

    target_db = None if args.db.lower() == "all" else args.db
    llm_client = LLMClient(model_name=args.model)
    linker = SchemaLinker(top_k_tables=args.k_tables, top_k_columns=args.k_columns)

    evaluator = SpiderBenchmarkEvaluator(llm_client=llm_client, linker=linker)
    evaluator.run_benchmark(db_id=target_db, limit=args.limit, offset=args.offset)


if __name__ == "__main__":
    main()
