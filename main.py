import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

from database import (
    clear_database,
    execute_query,
    get_relationships,
    get_schema,
    initialize_database,
    list_tables,
    load_college_preset,
)
from evaluator import BenchmarkEvaluator, EVALUATION_DATASET
from llm import LLMClient
from prompts import build_baseline_prompt, build_proposed_prompt
from schema_linker import SchemaLinker

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ")
    print("=" * 60)


def format_table_output(columns: List[str], rows: List[Any], message: Optional[str] = None) -> str:
    """Formats SQL results into a clean ASCII table or status message."""
    if message and not rows and not columns:
        return f"[Status] {message}"

    if not columns:
        return message or "No columns returned."
    if not rows:
        return (message + "\n" if message else "") + "Query executed successfully (0 rows returned)."

    # Convert all cells to strings
    str_rows = [[str(cell) for cell in row] for row in rows]
    col_widths = [len(col) for col in columns]
    for row in str_rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    header_line = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
    separator_line = "-+-".join("-" * col_widths[i] for i in range(len(columns)))
    
    row_lines = []
    for row in str_rows:
        row_lines.append(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))

    table_str = f"{header_line}\n{separator_line}\n" + "\n".join(row_lines)
    if message:
        table_str = f"[Status] {message}\n\n" + table_str
    return table_str


def get_user_query(default_q: str = "Find students whose attendance is below 75%") -> str:
    """Prompts user for a natural language question or command with a fallback default."""
    print(f"\nEnter your Natural Language instruction or query (or press Enter for default):")
    print(f"Default: '{default_q}'")
    user_input = input(">> ").strip()
    return user_input if user_input else default_q


def run_baseline_mode(
    question: str,
    schema: Dict[str, Dict[str, str]],
    relationships: List[Dict[str, str]],
    llm: LLMClient,
    db_path: str = "college.db",
):
    print_header("Baseline System (Full Schema)")
    print(f"Instruction / Question:\n{question}\n")

    full_col_count = sum(len(cols) for cols in schema.values())
    prompt = build_baseline_prompt(question, schema, relationships)

    print("Generating SQL with Full Schema...")
    llm_res = llm.generate_sql(prompt)
    sql = llm_res["sql"]

    print("\n[Generated SQL]")
    print(sql)

    exec_start = time.time()
    exec_res = execute_query(sql, db_path)
    exec_time = time.time() - exec_start

    print("\n[Execution Status]")
    if exec_res["success"]:
        print("Status: SUCCESS")
        print(f"\n[Result Output]:")
        print(format_table_output(exec_res["columns"], exec_res["rows"], exec_res.get("message")))
    else:
        print(f"Status: FAILED\nReason: {exec_res['error']}")

    print("\n[Metrics]")
    print(f"Active Tables:           {len(schema)}")
    print(f"Full Schema Columns:     {full_col_count}")
    print(f"Prompt Tokens (approx):  {llm_res['input_tokens']}")
    print(f"LLM Latency:             {llm_res['latency']:.4f}s")
    print(f"Execution Latency:       {exec_time:.4f}s")
    print(f"Total Latency:           {(llm_res['latency'] + exec_time):.4f}s")


def run_proposed_mode(
    question: str,
    schema: Dict[str, Dict[str, str]],
    relationships: List[Dict[str, str]],
    linker: SchemaLinker,
    llm: LLMClient,
    db_path: str = "college.db",
):
    print_header("Proposed System (Schema Linking & Reduction)")
    print(f"Instruction / Question:\n{question}\n")

    print("[Schema Linking Phase]")
    link_res = linker.link_schema(question, schema, relationships)
    reduced_schema = link_res["reduced_schema"]

    if link_res["ranked_items"]:
        print("Top Ranked Schema Elements:")
        print(f"{'Table.Column':<25} | {'Score':<6} | {'Lex':<5} | {'Sem':<5} | {'Type':<5} | {'Rel':<5}")
        print("-" * 62)
        for item in link_res["ranked_items"][:8]:
            name = f"{item['table']}.{item['column']}"
            print(
                f"{name:<25} | {item['score']:<6.2f} | {item['lexical']:<5.2f} | "
                f"{item['semantic']:<5.2f} | {item['type']:<5.2f} | {item['relationship']:<5.2f}"
            )

        print("\nSelected Reduced Schema:")
        for tbl, cols in reduced_schema.items():
            print(f"  - {tbl}({', '.join(cols.keys())})")
    else:
        print("(No existing tables to rank. Schema is empty or new table being created.)")

    prompt = build_proposed_prompt(question, reduced_schema, relationships)

    print("\nGenerating SQL with Reduced Schema...")
    llm_res = llm.generate_sql(prompt)
    sql = llm_res["sql"]

    print("\n[Generated SQL]")
    print(sql)

    exec_start = time.time()
    exec_res = execute_query(sql, db_path)
    exec_time = time.time() - exec_start

    print("\n[Execution Status]")
    if exec_res["success"]:
        print("Status: SUCCESS")
        print(f"\n[Result Output]:")
        print(format_table_output(exec_res["columns"], exec_res["rows"], exec_res.get("message")))
    else:
        print(f"Status: FAILED\nReason: {exec_res['error']}")

    red_stats = link_res["schema_reduction"]
    print("\n[Metrics & Schema Reduction]")
    print(f"Full Schema Columns:     {red_stats['full_columns']}")
    print(f"Reduced Schema Columns:  {red_stats['reduced_columns']}")
    print(f"Schema Reduction:        {red_stats['reduction_percentage']:.2f}%")
    print(f"Prompt Tokens (approx):  {llm_res['input_tokens']}")
    print(f"Schema Linking Latency:  {link_res['linking_time_seconds']:.4f}s")
    print(f"LLM Latency:             {llm_res['latency']:.4f}s")
    print(f"Execution Latency:       {exec_time:.4f}s")
    print(f"Total Latency:           {(link_res['linking_time_seconds'] + llm_res['latency'] + exec_time):.4f}s")


def run_compare_mode(
    question: str,
    schema: Dict[str, Dict[str, str]],
    relationships: List[Dict[str, str]],
    linker: SchemaLinker,
    llm: LLMClient,
    db_path: str = "college.db",
):
    print_header("Side-by-Side Comparison (Baseline vs Proposed)")
    print(f"Instruction / Question:\n{question}\n")

    full_col_count = sum(len(cols) for cols in schema.values())

    # Baseline
    base_prompt = build_baseline_prompt(question, schema, relationships)
    base_llm_res = llm.generate_sql(base_prompt)
    base_sql = base_llm_res["sql"]
    base_exec = execute_query(base_sql, db_path)

    # Proposed
    link_res = linker.link_schema(question, schema, relationships)
    reduced_schema = link_res["reduced_schema"]
    prop_prompt = build_proposed_prompt(question, reduced_schema, relationships)
    prop_llm_res = llm.generate_sql(prop_prompt)
    prop_sql = prop_llm_res["sql"]
    prop_exec = execute_query(prop_sql, db_path)

    red_stats = link_res["schema_reduction"]
    base_tokens = base_llm_res["input_tokens"]
    prop_tokens = prop_llm_res["input_tokens"]
    token_red = ((base_tokens - prop_tokens) / base_tokens * 100.0) if base_tokens > 0 else 0.0

    print("=" * 60)
    print("BASELINE (Full Schema):")
    print(f"SQL:    {base_sql}")
    print(f"Status: {'SUCCESS' if base_exec['success'] else 'FAILED'}")
    if base_exec["success"] and base_exec.get("message"):
        print(f"Result: {base_exec['message']}")
    print(f"Tokens: {base_tokens} | Latency: {base_llm_res['latency']:.4f}s")

    print("-" * 60)
    print("PROPOSED (Reduced Schema):")
    print(f"SQL:    {prop_sql}")
    print(f"Status: {'SUCCESS' if prop_exec['success'] else 'FAILED'}")
    if prop_exec["success"] and prop_exec.get("message"):
        print(f"Result: {prop_exec['message']}")
    print(f"Tokens: {prop_tokens} | Latency: {prop_llm_res['latency']:.4f}s | Linking Time: {link_res['linking_time_seconds']:.4f}s")

    print("-" * 60)
    print("COMPARATIVE METRICS:")
    print(f"- Schema Columns:   {full_col_count} -> {red_stats['reduced_columns']} ({red_stats['reduction_percentage']:.2f}% reduction)")
    print(f"- Prompt Tokens:    {base_tokens} -> {prop_tokens} ({token_red:.2f}% reduction)")
    print(f"- Baseline Latency: {base_llm_res['latency']:.4f}s")
    print(f"- Proposed Latency: {link_res['linking_time_seconds'] + prop_llm_res['latency']:.4f}s (incl. linking)")
    print("=" * 60)


def show_current_schema(db_path: str):
    """Displays tables, column structures, and foreign keys in the active database."""
    print_header(f"Active Database Schema: [{db_path}]")
    schema = get_schema(db_path)
    rels = get_relationships(db_path)

    if not schema:
        print("Database is currently empty (0 tables).")
        return

    for table_name, columns in schema.items():
        print(f"\nTable: {table_name}")
        for col, col_type in columns.items():
            print(f"  - {col:<20} ({col_type})")

    if rels:
        print("\nForeign Key Relationships:")
        for r in rels:
            print(f"  - {r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}")
    else:
        print("\nForeign Key Relationships: None")


def main():
    db_path = "college.db"
    initialize_database(db_path, load_preset=False)
    linker = SchemaLinker()
    llm = LLMClient()

    while True:
        current_tables = list_tables(db_path)
        print_header("AI Natural Language -> SQL Query System")
        print(f"Active Database: '{db_path}' | Tables: {len(current_tables)} ({', '.join(current_tables) if current_tables else 'Empty'})")
        print("-" * 60)
        print("1. Natural Language -> SQL (Proposed Mode with Schema Linking)")
        print("2. Natural Language -> SQL (Baseline Mode with Full Schema)")
        print("3. Side-by-Side Comparison (Baseline vs Proposed)")
        print("4. Direct SQL Executor (Execute custom SQL query / DDL)")
        print("5. View Database Schema & Tables")
        print("6. Load Demo College Preset (Student, Course, Enrollment, Faculty)")
        print("7. Clear / Drop All Tables in Active Database")
        print("8. Switch / Change Active SQLite Database File")
        print("9. Run Full Benchmark Evaluation (15 Test Cases)")
        print("10. Run Spider Dataset Benchmark Evaluation")
        print("11. Exit")

        choice = input("\nSelect option (1-11): ").strip()

        schema = get_schema(db_path)
        relationships = get_relationships(db_path)

        if choice == "1":
            q = get_user_query()
            run_proposed_mode(q, schema, relationships, linker, llm, db_path)
        elif choice == "2":
            q = get_user_query()
            run_baseline_mode(q, schema, relationships, llm, db_path)
        elif choice == "3":
            q = get_user_query()
            run_compare_mode(q, schema, relationships, linker, llm, db_path)
        elif choice == "4":
            print_header("Direct SQL Executor")
            print("Enter SQL statement(s) (e.g. CREATE TABLE..., INSERT INTO..., SELECT...):")
            raw_sql = input("SQL>> ").strip()
            if raw_sql:
                res = execute_query(raw_sql, db_path)
                if res["success"]:
                    print(f"\n[Status] Success: {res.get('message', 'Executed successfully.')}")
                    if res["rows"] or res["columns"]:
                        print(format_table_output(res["columns"], res["rows"]))
                else:
                    print(f"\n[Status] Failed: {res['error']}")
        elif choice == "5":
            show_current_schema(db_path)
        elif choice == "6":
            print(f"\nLoading demo college preset into '{db_path}'...")
            load_college_preset(db_path, force_recreate=True)
            print("Done! College preset loaded with 4 tables and sample records.")
        elif choice == "7":
            confirm = input(f"Are you sure you want to drop all tables in '{db_path}'? (y/N): ").strip().lower()
            if confirm == "y":
                clear_database(db_path)
                print(f"All tables dropped in '{db_path}'. Database is now empty.")
        elif choice == "8":
            new_db = input(f"Enter SQLite database path (current: '{db_path}'): ").strip()
            if new_db:
                db_path = new_db
                initialize_database(db_path, load_preset=False)
                print(f"Switched active database to '{db_path}'.")
        elif choice == "9":
            print_header("Running Evaluation Benchmark")
            # Ensure preset is in place for standard benchmark
            if not get_schema(db_path):
                print(f"Active database '{db_path}' is empty. Loading benchmark preset...")
                load_college_preset(db_path, force_recreate=True)
            evaluator = BenchmarkEvaluator(db_path=db_path, llm_client=llm)
            eval_output = evaluator.run_full_evaluation()
            eval_json = os.path.join("evaluation", "results", "evaluation_results.json")
            eval_csv = os.path.join("evaluation", "results", "evaluation_results.csv")
            evaluator.export_results(eval_output, eval_json, eval_csv)
            
            print_header("Evaluation Benchmark Summary")
            summary = eval_output["summary"]
            for k, v in summary.items():
                label = k.replace("_", " ").title()
                print(f"- {label:<40}: {v}")
            print(f"\nSaved detailed results to '{eval_json}' and '{eval_csv}'.")
        elif choice == "10":
            print_header("Spider Dataset Benchmark Evaluation")
            from evaluator_spider import SpiderBenchmarkEvaluator
            spider_db = input("Enter Spider db_id (e.g. concert_singer, flight_2, or 'all') [default: concert_singer]: ").strip()
            spider_db = spider_db or "concert_singer"
            limit_str = input("Enter number of queries to test [default: 10]: ").strip()
            limit_val = int(limit_str) if limit_str.isdigit() else 10
            target_db = None if spider_db.lower() == "all" else spider_db
            spider_eval = SpiderBenchmarkEvaluator(llm_client=llm, linker=linker)
            spider_eval.run_benchmark(db_id=target_db, limit=limit_val)
        elif choice in ("11", "q", "quit", "exit"):
            print("\nExiting. Thank you!")
            sys.exit(0)
        else:
            print("\nInvalid selection. Please choose an option between 1 and 11.")


if __name__ == "__main__":
    main()


