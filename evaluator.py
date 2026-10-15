import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from database import execute_query, get_relationships, get_schema, initialize_database
from llm import LLMClient
from prompts import build_baseline_prompt, build_proposed_prompt
from schema_linker import SchemaLinker

# Default dataset path references
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "evaluation", "questions.json")
GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "evaluation", "ground_truth.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "evaluation", "results")

# Fallback in-memory dataset to ensure independence and backward compatibility
FALLBACK_DATASET: List[Dict[str, Any]] = [
    {
        "id": 1,
        "question": "Find students whose attendance is below 75%.",
        "category": "Single Table Filter",
        "ground_truth_sql": "SELECT StudentName, Attendance FROM Student WHERE Attendance < 75;",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.StudentName", "Student.Attendance"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.StudentName", "Student.Attendance"],
        "required_relationships": [],
    },
    {
        "id": 2,
        "question": "Show CSE students who scored above 80.",
        "category": "Multi-Condition Filter",
        "ground_truth_sql": "SELECT StudentName, Marks FROM Student WHERE Department = 'CSE' AND Marks > 80;",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.StudentName", "Student.Department", "Student.Marks"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.StudentName", "Student.Department", "Student.Marks"],
        "required_relationships": [],
    },
    {
        "id": 3,
        "question": "List students enrolled in Database Management Systems.",
        "category": "3-Table Join",
        "ground_truth_sql": """SELECT Student.StudentName
FROM Student
JOIN Enrollment ON Student.StudentID = Enrollment.StudentID
JOIN Course ON Enrollment.CourseID = Course.CourseID
WHERE Course.CourseName = 'Database Management Systems';""",
        "direct_tables": ["Student", "Course"],
        "direct_columns": ["Student.StudentName", "Course.CourseName"],
        "structural_tables": ["Enrollment"],
        "structural_columns": ["Student.StudentID", "Enrollment.StudentID", "Enrollment.CourseID", "Course.CourseID"],
        "all_required_tables": ["Student", "Enrollment", "Course"],
        "all_required_columns": [
            "Student.StudentName",
            "Course.CourseName",
            "Student.StudentID",
            "Enrollment.StudentID",
            "Enrollment.CourseID",
            "Course.CourseID",
        ],
        "required_relationships": [
            {"from_table": "Enrollment", "from_column": "StudentID", "to_table": "Student", "to_column": "StudentID"},
            {"from_table": "Enrollment", "from_column": "CourseID", "to_table": "Course", "to_column": "CourseID"},
        ],
    },
    {
        "id": 4,
        "question": "Find the average marks of CSE students.",
        "category": "Aggregation",
        "ground_truth_sql": "SELECT AVG(Marks) AS AverageMarks FROM Student WHERE Department = 'CSE';",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.Marks", "Student.Department"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.Marks", "Student.Department"],
        "required_relationships": [],
    },
    {
        "id": 5,
        "question": "Show the names and grades of students enrolled in each course.",
        "category": "3-Table Join",
        "ground_truth_sql": """SELECT Student.StudentName, Enrollment.Grade, Course.CourseName
FROM Student
JOIN Enrollment ON Student.StudentID = Enrollment.StudentID
JOIN Course ON Enrollment.CourseID = Course.CourseID;""",
        "direct_tables": ["Student", "Enrollment", "Course"],
        "direct_columns": ["Student.StudentName", "Enrollment.Grade", "Course.CourseName"],
        "structural_tables": [],
        "structural_columns": ["Student.StudentID", "Enrollment.StudentID", "Enrollment.CourseID", "Course.CourseID"],
        "all_required_tables": ["Student", "Enrollment", "Course"],
        "all_required_columns": [
            "Student.StudentName",
            "Enrollment.Grade",
            "Course.CourseName",
            "Student.StudentID",
            "Enrollment.StudentID",
            "Enrollment.CourseID",
            "Course.CourseID",
        ],
        "required_relationships": [
            {"from_table": "Enrollment", "from_column": "StudentID", "to_table": "Student", "to_column": "StudentID"},
            {"from_table": "Enrollment", "from_column": "CourseID", "to_table": "Course", "to_column": "CourseID"},
        ],
    },
    {
        "id": 6,
        "question": "Find faculty members whose salary is above 80000.",
        "category": "Single Table Filter",
        "ground_truth_sql": "SELECT FacultyName, Salary FROM Faculty WHERE Salary > 80000;",
        "direct_tables": ["Faculty"],
        "direct_columns": ["Faculty.FacultyName", "Faculty.Salary"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Faculty"],
        "all_required_columns": ["Faculty.FacultyName", "Faculty.Salary"],
        "required_relationships": [],
    },
    {
        "id": 7,
        "question": "Count students in each department.",
        "category": "Group By & Aggregation",
        "ground_truth_sql": "SELECT Department, COUNT(*) AS StudentCount FROM Student GROUP BY Department;",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.Department", "Student.StudentID"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.Department", "Student.StudentID"],
        "required_relationships": [],
    },
    {
        "id": 8,
        "question": "Show courses offered by the CSE department.",
        "category": "Single Table Filter",
        "ground_truth_sql": "SELECT CourseID, CourseName, Credits FROM Course WHERE Department = 'CSE';",
        "direct_tables": ["Course"],
        "direct_columns": ["Course.CourseID", "Course.CourseName", "Course.Credits", "Course.Department"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Course"],
        "all_required_columns": ["Course.CourseID", "Course.CourseName", "Course.Credits", "Course.Department"],
        "required_relationships": [],
    },
    {
        "id": 9,
        "question": "Find the student with the highest marks.",
        "category": "Order By & Limit",
        "ground_truth_sql": "SELECT StudentName, Marks FROM Student ORDER BY Marks DESC LIMIT 1;",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.StudentName", "Student.Marks"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.StudentName", "Student.Marks"],
        "required_relationships": [],
    },
    {
        "id": 10,
        "question": "Show students and their grades using the enrollment table.",
        "category": "Single Table Select",
        "ground_truth_sql": "SELECT StudentID, CourseID, Grade FROM Enrollment;",
        "direct_tables": ["Enrollment"],
        "direct_columns": ["Enrollment.StudentID", "Enrollment.CourseID", "Enrollment.Grade"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Enrollment"],
        "all_required_columns": ["Enrollment.StudentID", "Enrollment.CourseID", "Enrollment.Grade"],
        "required_relationships": [],
    },
    {
        "id": 11,
        "question": "Find all faculty in the ECE department.",
        "category": "Single Table Filter",
        "ground_truth_sql": "SELECT FacultyName, Department FROM Faculty WHERE Department = 'ECE';",
        "direct_tables": ["Faculty"],
        "direct_columns": ["Faculty.FacultyName", "Faculty.Department"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Faculty"],
        "all_required_columns": ["Faculty.FacultyName", "Faculty.Department"],
        "required_relationships": [],
    },
    {
        "id": 12,
        "question": "List courses that offer 4 credits.",
        "category": "Numeric Filter",
        "ground_truth_sql": "SELECT CourseID, CourseName FROM Course WHERE Credits = 4;",
        "direct_tables": ["Course"],
        "direct_columns": ["Course.CourseID", "Course.CourseName", "Course.Credits"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Course"],
        "all_required_columns": ["Course.CourseID", "Course.CourseName", "Course.Credits"],
        "required_relationships": [],
    },
    {
        "id": 13,
        "question": "Find the minimum attendance among all students.",
        "category": "Aggregation",
        "ground_truth_sql": "SELECT MIN(Attendance) AS MinAttendance FROM Student;",
        "direct_tables": ["Student"],
        "direct_columns": ["Student.Attendance"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Student"],
        "all_required_columns": ["Student.Attendance"],
        "required_relationships": [],
    },
    {
        "id": 14,
        "question": "Show all students enrolled in course CS101.",
        "category": "2-Table Join",
        "ground_truth_sql": """SELECT Student.StudentName, Enrollment.Grade
FROM Student
JOIN Enrollment ON Student.StudentID = Enrollment.StudentID
WHERE Enrollment.CourseID = 'CS101';""",
        "direct_tables": ["Student", "Enrollment"],
        "direct_columns": ["Student.StudentName", "Enrollment.CourseID", "Enrollment.Grade"],
        "structural_tables": [],
        "structural_columns": ["Student.StudentID", "Enrollment.StudentID"],
        "all_required_tables": ["Student", "Enrollment"],
        "all_required_columns": [
            "Student.StudentName",
            "Enrollment.CourseID",
            "Enrollment.Grade",
            "Student.StudentID",
            "Enrollment.StudentID",
        ],
        "required_relationships": [
            {"from_table": "Enrollment", "from_column": "StudentID", "to_table": "Student", "to_column": "StudentID"}
        ],
    },
    {
        "id": 15,
        "question": "Find the total salary expenditure for the MECH faculty.",
        "category": "Aggregation & Filter",
        "ground_truth_sql": "SELECT SUM(Salary) AS TotalSalary FROM Faculty WHERE Department = 'MECH';",
        "direct_tables": ["Faculty"],
        "direct_columns": ["Faculty.Salary", "Faculty.Department"],
        "structural_tables": [],
        "structural_columns": [],
        "all_required_tables": ["Faculty"],
        "all_required_columns": ["Faculty.Salary", "Faculty.Department"],
        "required_relationships": [],
    },
]

# Aliased global for backward compatibility
EVALUATION_DATASET = FALLBACK_DATASET


def load_evaluation_dataset() -> List[Dict[str, Any]]:
    """
    Loads benchmark questions and ground-truth metadata from JSON files if present,
    falling back to in-memory dataset.
    """
    if os.path.exists(QUESTIONS_FILE) and os.path.exists(GROUND_TRUTH_FILE):
        try:
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as qf:
                questions = json.load(qf)
            with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as gtf:
                ground_truth = json.load(gtf)

            gt_by_id = {item["id"]: item for item in ground_truth}
            merged_dataset = []
            for q in questions:
                qid = q["id"]
                gt = gt_by_id.get(qid, {})
                combined = {**q, **gt}
                merged_dataset.append(combined)
            return merged_dataset
        except Exception as e:
            print(f"[Warning] Failed loading dataset files ({e}). Using embedded dataset.")

    return FALLBACK_DATASET


def compare_query_results(rows1: List[Any], rows2: List[Any]) -> bool:
    """Compares two query results agnostic to slight row ordering differences."""
    if len(rows1) != len(rows2):
        return False
    try:
        set1 = set(tuple(str(x) for x in r) for r in rows1)
        set2 = set(tuple(str(x) for x in r) for r in rows2)
        return set1 == set2
    except Exception:
        return rows1 == rows2


def compute_schema_linking_metrics(
    reduced_schema: Dict[str, Dict[str, str]],
    gt_item: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes precise schema-linking precision and recall for columns and tables,
    distinguishing directly relevant columns from structural columns required for joins.
    """
    # Build selected column set: e.g., {'Student.StudentName', 'Student.Attendance'}
    selected_cols: Set[str] = set()
    for tbl, cols in reduced_schema.items():
        for col in cols:
            selected_cols.add(f"{tbl}.{col}")

    selected_tables = set(reduced_schema.keys())

    direct_cols = set(gt_item.get("direct_columns", []))
    direct_tables = set(gt_item.get("direct_tables", []))
    structural_cols = set(gt_item.get("structural_columns", []))
    structural_tables = set(gt_item.get("structural_tables", []))
    all_required_cols = set(gt_item.get("all_required_columns", [])) or (direct_cols | structural_cols)
    all_required_tables = set(gt_item.get("all_required_tables", [])) or (direct_tables | structural_tables)

    # Column metrics
    num_selected = len(selected_cols)
    direct_intersect = selected_cols & direct_cols
    all_intersect = selected_cols & all_required_cols

    direct_col_precision = (len(direct_intersect) / num_selected) if num_selected > 0 else 0.0
    direct_col_recall = (len(direct_intersect) / len(direct_cols)) if direct_cols else 1.0

    executable_col_precision = (len(all_intersect) / num_selected) if num_selected > 0 else 0.0
    executable_col_recall = (len(all_intersect) / len(all_required_cols)) if all_required_cols else 1.0

    # Table metrics
    num_sel_tables = len(selected_tables)
    table_intersect = selected_tables & all_required_tables
    table_precision = (len(table_intersect) / num_sel_tables) if num_sel_tables > 0 else 0.0
    table_recall = (len(table_intersect) / len(all_required_tables)) if all_required_tables else 1.0

    # Missing elements (useful for error diagnosis)
    missing_direct_cols = list(direct_cols - selected_cols)
    missing_structural_cols = list(structural_cols - selected_cols)
    missing_tables = list(all_required_tables - selected_tables)

    return {
        "selected_columns_count": num_selected,
        "direct_columns_count": len(direct_cols),
        "structural_columns_count": len(structural_cols),
        "all_required_columns_count": len(all_required_cols),
        "direct_col_precision": round(direct_col_precision, 4),
        "direct_col_recall": round(direct_col_recall, 4),
        "executable_col_precision": round(executable_col_precision, 4),
        "executable_col_recall": round(executable_col_recall, 4),
        "table_precision": round(table_precision, 4),
        "table_recall": round(table_recall, 4),
        "missing_direct_cols": missing_direct_cols,
        "missing_structural_cols": missing_structural_cols,
        "missing_tables": missing_tables,
    }


def classify_pipeline_outcome(
    exec_res: Dict[str, Any],
    is_result_correct: bool,
    schema_metrics: Optional[Dict[str, Any]] = None,
    is_proposed: bool = False,
) -> str:
    """
    Classifies the outcome or failure category of query generation/execution.
    Categories:
      - SUCCESS
      - SQL_SAFETY_REJECTED
      - SQL_EXECUTION_SYNTAX_ERROR
      - SCHEMA_LINK_MISSING_TABLE
      - SCHEMA_LINK_MISSING_COLUMN
      - RESULT_CORRECTNESS_MISMATCH
    """
    if not exec_res["success"]:
        err = str(exec_res.get("error", "")).lower()
        if "rejected" in err or "safety" in err or "read-only" in err or "multiple statements" in err:
            return "SQL_SAFETY_REJECTED"
        return "SQL_EXECUTION_SYNTAX_ERROR"

    if not is_result_correct:
        if is_proposed and schema_metrics:
            if schema_metrics.get("table_recall", 1.0) < 1.0:
                return "SCHEMA_LINK_MISSING_TABLE"
            if schema_metrics.get("executable_col_recall", 1.0) < 1.0:
                return "SCHEMA_LINK_MISSING_COLUMN"
        return "RESULT_CORRECTNESS_MISMATCH"

    return "SUCCESS"


class BenchmarkEvaluator:
    """
    Evaluator that executes the test suite against Baseline and Proposed approaches
    and calculates rigorous research metrics including precision/recall and failure taxonomy.
    """

    def __init__(
        self,
        db_path: str = "college.db",
        llm_client: Optional[LLMClient] = None,
        linker: Optional[SchemaLinker] = None,
    ):
        self.db_path = db_path
        if not os.path.exists(self.db_path) or not get_schema(self.db_path):
            initialize_database(self.db_path, load_preset=True)
        self.full_schema = get_schema(self.db_path)
        self.relationships = get_relationships(self.db_path)
        self.linker = linker or SchemaLinker()
        self.llm = llm_client or LLMClient()
        self.dataset = load_evaluation_dataset()

    def evaluate_question(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Runs baseline and proposed pipelines on a single test item with full metrics."""
        q = item["question"]
        gt_sql = item.get("ground_truth_sql")

        # Ground truth execution
        gt_exec = execute_query(gt_sql, self.db_path) if gt_sql else None

        # ----------------- BASELINE PIPELINE -----------------
        base_prompt = build_baseline_prompt(q, self.full_schema, self.relationships)
        base_llm_res = self.llm.generate_sql(base_prompt)
        base_sql = base_llm_res["sql"]
        base_exec_start = time.time()
        base_exec = execute_query(base_sql, self.db_path)
        base_exec_time = time.time() - base_exec_start

        full_col_count = sum(len(cols) for cols in self.full_schema.values())

        # ----------------- PROPOSED PIPELINE -----------------
        link_res = self.linker.link_schema(q, self.full_schema, self.relationships)
        reduced_schema = link_res["reduced_schema"]
        linking_time = link_res["linking_time_seconds"]

        # Calculate schema linking precision/recall
        schema_metrics = compute_schema_linking_metrics(reduced_schema, item)

        prop_prompt = build_proposed_prompt(q, reduced_schema, self.relationships)
        prop_llm_res = self.llm.generate_sql(prop_prompt)
        prop_sql = prop_llm_res["sql"]
        prop_exec_start = time.time()
        prop_exec = execute_query(prop_sql, self.db_path)
        prop_exec_time = time.time() - prop_exec_start

        reduced_col_count = sum(len(cols) for cols in reduced_schema.values())
        schema_reduction_pct = (
            ((full_col_count - reduced_col_count) / full_col_count) * 100.0
            if full_col_count > 0
            else 0.0
        )

        base_tokens = base_llm_res["input_tokens"]
        prop_tokens = prop_llm_res["input_tokens"]
        prompt_reduction_pct = (
            ((base_tokens - prop_tokens) / base_tokens) * 100.0
            if base_tokens > 0
            else 0.0
        )

        # Result correctness check against ground truth
        base_correct = False
        prop_correct = False
        if gt_exec and gt_exec["success"]:
            if base_exec["success"]:
                base_correct = compare_query_results(base_exec["rows"], gt_exec["rows"])
            if prop_exec["success"]:
                prop_correct = compare_query_results(prop_exec["rows"], gt_exec["rows"])

        # Failure classification
        base_outcome = classify_pipeline_outcome(base_exec, base_correct, None, is_proposed=False)
        prop_outcome = classify_pipeline_outcome(prop_exec, prop_correct, schema_metrics, is_proposed=True)

        return {
            "id": item["id"],
            "question": q,
            "category": item.get("category", "General"),
            "complexity": item.get("complexity", "Medium"),
            # Schema & Prompt Reduction
            "baseline_schema_columns": full_col_count,
            "proposed_schema_columns": reduced_col_count,
            "schema_reduction_pct": round(schema_reduction_pct, 2),
            "baseline_prompt_tokens": base_tokens,
            "proposed_prompt_tokens": prop_tokens,
            "prompt_reduction_pct": round(prompt_reduction_pct, 2),
            # Latency Breakdown
            "baseline_llm_latency": base_llm_res["latency"],
            "baseline_sql_exec_time": round(base_exec_time, 4),
            "baseline_total_latency": round(base_llm_res["latency"] + base_exec_time, 4),
            "proposed_schema_linking_time": linking_time,
            "proposed_llm_latency": prop_llm_res["latency"],
            "proposed_sql_exec_time": round(prop_exec_time, 4),
            "proposed_total_latency": round(linking_time + prop_llm_res["latency"] + prop_exec_time, 4),
            # Schema Linking Precision & Recall
            "direct_col_precision": schema_metrics["direct_col_precision"],
            "direct_col_recall": schema_metrics["direct_col_recall"],
            "executable_col_precision": schema_metrics["executable_col_precision"],
            "executable_col_recall": schema_metrics["executable_col_recall"],
            "table_precision": schema_metrics["table_precision"],
            "table_recall": schema_metrics["table_recall"],
            "missing_direct_cols": schema_metrics["missing_direct_cols"],
            "missing_structural_cols": schema_metrics["missing_structural_cols"],
            "missing_tables": schema_metrics["missing_tables"],
            # SQL Outputs
            "baseline_sql": base_sql,
            "proposed_sql": prop_sql,
            "ground_truth_sql": gt_sql,
            # Execution and Correctness
            "baseline_execution_success": base_exec["success"],
            "proposed_execution_success": prop_exec["success"],
            "baseline_error": base_exec.get("error"),
            "proposed_error": prop_exec.get("error"),
            "baseline_result_match": base_correct,
            "proposed_result_match": prop_correct,
            # Failure Classification
            "baseline_outcome": base_outcome,
            "proposed_outcome": prop_outcome,
            # Debug & Validation Context
            "selected_tables": link_res["selected_tables"],
            "content_columns": link_res.get("content_columns", {}),
            "structural_columns": link_res.get("structural_columns", {}),
            "validation_passed": link_res.get("validation", {}).get("is_valid", True),
            "fallback_used": link_res.get("validation", {}).get("fallback_used", False),
            "join_paths": link_res.get("validation", {}).get("join_paths", []),
            "ranked_schema": link_res["ranked_items"][:5],
        }

    def run_full_evaluation(self, dataset: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs benchmark across all dataset questions and aggregates statistics."""
        data = dataset or self.dataset
        results = []

        print(f"Running evaluation on {len(data)} test cases...\n")
        for item in data:
            print(f"[{item['id']}/{len(data)}] Evaluating: {item['question']}")
            res = self.evaluate_question(item)
            results.append(res)

        total_q = len(results)
        avg_schema_red = sum(r["schema_reduction_pct"] for r in results) / total_q
        avg_prompt_red = sum(r["prompt_reduction_pct"] for r in results) / total_q
        avg_base_lat = sum(r["baseline_total_latency"] for r in results) / total_q
        avg_prop_lat = sum(r["proposed_total_latency"] for r in results) / total_q
        avg_link_time = sum(r["proposed_schema_linking_time"] for r in results) / total_q

        base_exec_rate = (sum(1 for r in results if r["baseline_execution_success"]) / total_q) * 100.0
        prop_exec_rate = (sum(1 for r in results if r["proposed_execution_success"]) / total_q) * 100.0

        base_acc_rate = (sum(1 for r in results if r["baseline_result_match"]) / total_q) * 100.0
        prop_acc_rate = (sum(1 for r in results if r["proposed_result_match"]) / total_q) * 100.0

        avg_direct_col_prec = sum(r["direct_col_precision"] for r in results) / total_q
        avg_direct_col_rec = sum(r["direct_col_recall"] for r in results) / total_q
        avg_exec_col_prec = sum(r["executable_col_precision"] for r in results) / total_q
        avg_exec_col_rec = sum(r["executable_col_recall"] for r in results) / total_q
        avg_tbl_prec = sum(r["table_precision"] for r in results) / total_q
        avg_tbl_rec = sum(r["table_recall"] for r in results) / total_q

        # Error distribution counts
        base_outcomes: Dict[str, int] = {}
        prop_outcomes: Dict[str, int] = {}
        for r in results:
            base_outcomes[r["baseline_outcome"]] = base_outcomes.get(r["baseline_outcome"], 0) + 1
            prop_outcomes[r["proposed_outcome"]] = prop_outcomes.get(r["proposed_outcome"], 0) + 1

        base_qps = round(1.0 / max(0.001, avg_base_lat), 2)
        prop_qps = round(1.0 / max(0.001, avg_prop_lat), 2)
        throughput_speedup = round(((prop_qps - base_qps) / max(0.01, base_qps)) * 100.0, 2)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": total_q,
            "avg_schema_reduction_pct": round(avg_schema_red, 2),
            "avg_prompt_reduction_pct": round(avg_prompt_red, 2),
            "avg_baseline_latency_sec": round(avg_base_lat, 4),
            "avg_proposed_latency_sec": round(avg_prop_lat, 4),
            "avg_schema_linking_time_sec": round(avg_link_time, 4),
            "baseline_throughput_qps": base_qps,
            "proposed_throughput_qps": prop_qps,
            "throughput_speedup_pct": throughput_speedup,
            "baseline_sql_execution_success_rate": round(base_exec_rate, 2),
            "proposed_sql_execution_success_rate": round(prop_exec_rate, 2),
            "baseline_result_correctness_rate": round(base_acc_rate, 2),
            "proposed_result_correctness_rate": round(prop_acc_rate, 2),
            # Schema-Linking Precision & Recall Summaries
            "avg_direct_column_precision": round(avg_direct_col_prec, 4),
            "avg_direct_column_recall": round(avg_direct_col_rec, 4),
            "avg_executable_column_precision": round(avg_exec_col_prec, 4),
            "avg_executable_column_recall": round(avg_exec_col_rec, 4),
            "avg_table_precision": round(avg_tbl_prec, 4),
            "avg_table_recall": round(avg_tbl_rec, 4),
            "baseline_outcome_distribution": base_outcomes,
            "proposed_outcome_distribution": prop_outcomes,
        }

        return {
            "summary": summary,
            "results": results,
        }

    def export_results(
        self,
        eval_output: Dict[str, Any],
        json_path: str = "evaluation_results.json",
        csv_path: str = "evaluation_results.csv",
        archive: bool = True,
    ) -> None:
        """Exports evaluation results to root files and timestamped archive in evaluation/results/."""
        # Ensure results dir exists
        os.makedirs(RESULTS_DIR, exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(eval_output, f, indent=2)

        results = eval_output.get("results", [])
        if results:
            fieldnames = [
                "id",
                "question",
                "category",
                "complexity",
                "baseline_schema_columns",
                "proposed_schema_columns",
                "schema_reduction_pct",
                "baseline_prompt_tokens",
                "proposed_prompt_tokens",
                "prompt_reduction_pct",
                "baseline_total_latency",
                "proposed_total_latency",
                "proposed_schema_linking_time",
                "direct_col_precision",
                "direct_col_recall",
                "executable_col_precision",
                "executable_col_recall",
                "table_precision",
                "table_recall",
                "baseline_execution_success",
                "proposed_execution_success",
                "baseline_result_match",
                "proposed_result_match",
                "baseline_outcome",
                "proposed_outcome",
                "baseline_sql",
                "proposed_sql",
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for r in results:
                    writer.writerow(r)

        if archive:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived_json = os.path.join(RESULTS_DIR, f"eval_results_{ts}.json")
            with open(archived_json, "w", encoding="utf-8") as af:
                json.dump(eval_output, af, indent=2)


if __name__ == "__main__":
    evaluator = BenchmarkEvaluator()
    eval_res = evaluator.run_full_evaluation()
    evaluator.export_results(eval_res)
    print("\nSummary Metrics:")
    print(json.dumps(eval_res["summary"], indent=2))
