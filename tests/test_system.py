import os
import sqlite3
import sys
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import execute_query, get_relationships, get_schema, initialize_database, validate_sql_safety
from evaluator import (
    BenchmarkEvaluator,
    classify_pipeline_outcome,
    compute_schema_linking_metrics,
    load_evaluation_dataset,
)
from llm import LLMClient
from prompts import build_baseline_prompt, build_proposed_prompt
from schema_linker import SchemaLinker


class TestDatabaseModule(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_college.db"
        initialize_database(self.test_db, load_preset=True, force_recreate=True)

    def tearDown(self):
        import gc
        gc.collect()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

    def test_database_initialization(self):
        self.assertTrue(os.path.exists(self.test_db))
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = set(row[0] for row in cursor.fetchall())
        conn.close()
        expected_tables = {"Student", "Course", "Enrollment", "Faculty"}
        self.assertTrue(expected_tables.issubset(tables))

    def test_schema_extraction(self):
        schema = get_schema(self.test_db)
        self.assertIn("Student", schema)
        self.assertIn("StudentID", schema["Student"])
        self.assertIn("StudentName", schema["Student"])
        self.assertIn("Attendance", schema["Student"])
        self.assertIn("Marks", schema["Student"])
        self.assertIn("Faculty", schema)
        self.assertIn("Salary", schema["Faculty"])

    def test_relationship_extraction(self):
        relationships = get_relationships(self.test_db)
        self.assertTrue(len(relationships) >= 2)
        from_tables = [r["from_table"] for r in relationships]
        self.assertIn("Enrollment", from_tables)

    def test_sql_execution(self):
        res = execute_query("SELECT StudentName, Marks FROM Student WHERE Department = 'CSE';", self.test_db)
        self.assertTrue(res["success"])
        self.assertGreater(len(res["rows"]), 0)
        self.assertEqual(res["columns"], ["StudentName", "Marks"])

    def test_custom_table_creation_and_insert(self):
        create_res = execute_query("CREATE TABLE Products (id INTEGER PRIMARY KEY, name TEXT, price REAL);", self.test_db)
        self.assertTrue(create_res["success"])
        insert_res = execute_query("INSERT INTO Products (id, name, price) VALUES (1, 'Laptop', 1200.0);", self.test_db)
        self.assertTrue(insert_res["success"])
        select_res = execute_query("SELECT name, price FROM Products WHERE id = 1;", self.test_db)
        self.assertTrue(select_res["success"])
        self.assertEqual(len(select_res["rows"]), 1)
        self.assertEqual(select_res["rows"][0][0], "Laptop")


class TestSQLSafety(unittest.TestCase):
    def test_safe_select(self):
        safe, _ = validate_sql_safety("SELECT * FROM Student WHERE Attendance < 75;")
        self.assertTrue(safe)

    def test_safe_with_cte(self):
        safe, _ = validate_sql_safety("WITH TopStudents AS (SELECT * FROM Student) SELECT * FROM TopStudents;")
        self.assertTrue(safe)

    def test_allow_create_and_insert_in_default_mode(self):
        safe_create, _ = validate_sql_safety("CREATE TABLE Books (id INT, title TEXT);", allow_modifications=True)
        self.assertTrue(safe_create)
        safe_insert, _ = validate_sql_safety("INSERT INTO Books VALUES (1, 'Database Systems');", allow_modifications=True)
        self.assertTrue(safe_insert)

    def test_reject_insert_in_read_only_mode(self):
        safe, reason = validate_sql_safety("INSERT INTO Student (StudentID) VALUES (999);", read_only=True)
        self.assertFalse(safe)
        self.assertIn("rejected", reason.lower())

    def test_reject_drop_in_read_only_mode(self):
        safe, reason = validate_sql_safety("DROP TABLE Student;", read_only=True)
        self.assertFalse(safe)
        self.assertIn("rejected", reason.lower())

    def test_reject_hard_forbidden_pragma_and_attach(self):
        safe1, reason1 = validate_sql_safety("ATTACH DATABASE 'malicious.db' AS mal;")
        self.assertFalse(safe1)
        safe2, reason2 = validate_sql_safety("PRAGMA table_info(Student);")
        self.assertFalse(safe2)


class TestSchemaLinker(unittest.TestCase):
    def setUp(self):
        self.linker = SchemaLinker()
        self.schema = {
            "Student": {
                "StudentID": "INTEGER",
                "StudentName": "TEXT",
                "Department": "TEXT",
                "Age": "INTEGER",
                "Attendance": "REAL",
                "Marks": "REAL",
            },
            "Course": {
                "CourseID": "TEXT",
                "CourseName": "TEXT",
                "Credits": "INTEGER",
                "Department": "TEXT",
            },
            "Enrollment": {
                "StudentID": "INTEGER",
                "CourseID": "TEXT",
                "Grade": "TEXT",
            },
            "Faculty": {
                "FacultyID": "INTEGER",
                "FacultyName": "TEXT",
                "Department": "TEXT",
                "Salary": "REAL",
            },
        }
        self.relationships = [
            {"from_table": "Enrollment", "from_column": "StudentID", "to_table": "Student", "to_column": "StudentID"},
            {"from_table": "Enrollment", "from_column": "CourseID", "to_table": "Course", "to_column": "CourseID"},
        ]

    def test_salary_query_ranking(self):
        res = self.linker.link_schema("Find faculty whose salary is above 80000", self.schema, self.relationships)
        top_item = res["ranked_items"][0]
        self.assertEqual(top_item["table"], "Faculty")
        self.assertIn("Salary", [item["column"] for item in res["ranked_items"][:3]])
        self.assertIn("Faculty", res["reduced_schema"])

    def test_attendance_query_ranking(self):
        res = self.linker.link_schema("Find students whose attendance is below 75%", self.schema, self.relationships)
        ranked_cols = [item["column"] for item in res["ranked_items"][:3]]
        self.assertIn("Attendance", ranked_cols)
        self.assertIn("Student", res["reduced_schema"])

    def test_schema_reduction_metrics(self):
        res = self.linker.link_schema("Show CSE students who scored above 80", self.schema, self.relationships)
        self.assertIn("schema_reduction", res)
        red = res["schema_reduction"]
        self.assertGreater(red["reduction_percentage"], 0.0)
        self.assertLessEqual(red["reduced_columns"], red["full_columns"])


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_college.db"
        initialize_database(self.test_db, load_preset=True, force_recreate=True)
        self.schema = get_schema(self.test_db)
        self.relationships = get_relationships(self.test_db)
        self.linker = SchemaLinker()
        self.llm = LLMClient()

    def tearDown(self):
        import gc
        gc.collect()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except OSError:
                pass

    def test_e2e_attendance_question(self):
        q = "Find students whose attendance is below 75%"
        link_res = self.linker.link_schema(q, self.schema, self.relationships)
        prompt = build_proposed_prompt(q, link_res["reduced_schema"], self.relationships)
        llm_res = self.llm.generate_sql(prompt)
        exec_res = execute_query(llm_res["sql"], self.test_db)
        self.assertTrue(exec_res["success"])
        self.assertGreater(exec_res["rowcount"], 0)

    def test_e2e_salary_question(self):
        q = "Find faculty members whose salary is above 80000"
        link_res = self.linker.link_schema(q, self.schema, self.relationships)
        prompt = build_proposed_prompt(q, link_res["reduced_schema"], self.relationships)
        llm_res = self.llm.generate_sql(prompt)
        exec_res = execute_query(llm_res["sql"], self.test_db)
        self.assertTrue(exec_res["success"])
        self.assertGreater(exec_res["rowcount"], 0)

    def test_e2e_join_question(self):
        q = "List students enrolled in Database Management Systems"
        link_res = self.linker.link_schema(q, self.schema, self.relationships)
        prompt = build_proposed_prompt(q, link_res["reduced_schema"], self.relationships)
        llm_res = self.llm.generate_sql(prompt)
        exec_res = execute_query(llm_res["sql"], self.test_db)
        self.assertTrue(exec_res["success"])


class TestEvaluatorModule(unittest.TestCase):
    def test_load_dataset(self):
        dataset = load_evaluation_dataset()
        self.assertEqual(len(dataset), 15)
        item1 = dataset[0]
        self.assertEqual(item1["id"], 1)
        self.assertIn("direct_columns", item1)
        self.assertIn("ground_truth_sql", item1)

    def test_compute_schema_linking_metrics(self):
        gt_item = {
            "direct_tables": ["Student"],
            "direct_columns": ["Student.StudentName", "Student.Attendance"],
            "structural_tables": [],
            "structural_columns": [],
            "all_required_tables": ["Student"],
            "all_required_columns": ["Student.StudentName", "Student.Attendance"],
        }
        # Exact match
        reduced_schema_exact = {
            "Student": {"StudentName": "TEXT", "Attendance": "REAL"}
        }
        metrics = compute_schema_linking_metrics(reduced_schema_exact, gt_item)
        self.assertEqual(metrics["direct_col_precision"], 1.0)
        self.assertEqual(metrics["direct_col_recall"], 1.0)
        self.assertEqual(metrics["table_precision"], 1.0)
        self.assertEqual(metrics["table_recall"], 1.0)

        # Oversized selection (lower precision, high recall)
        reduced_schema_broad = {
            "Student": {"StudentName": "TEXT", "Attendance": "REAL", "Marks": "REAL", "Age": "INTEGER"}
        }
        metrics_broad = compute_schema_linking_metrics(reduced_schema_broad, gt_item)
        self.assertEqual(metrics_broad["direct_col_precision"], 0.5)
        self.assertEqual(metrics_broad["direct_col_recall"], 1.0)

    def test_structural_column_distinction(self):
        gt_item = {
            "direct_tables": ["Student", "Course"],
            "direct_columns": ["Student.StudentName", "Course.CourseName"],
            "structural_tables": ["Enrollment"],
            "structural_columns": ["Student.StudentID", "Enrollment.StudentID", "Enrollment.CourseID", "Course.CourseID"],
            "all_required_tables": ["Student", "Enrollment", "Course"],
            "all_required_columns": [
                "Student.StudentName", "Course.CourseName",
                "Student.StudentID", "Enrollment.StudentID", "Enrollment.CourseID", "Course.CourseID"
            ],
        }
        reduced_schema = {
            "Student": {"StudentName": "TEXT", "StudentID": "INTEGER"},
            "Course": {"CourseName": "TEXT", "CourseID": "TEXT"},
            "Enrollment": {"StudentID": "INTEGER", "CourseID": "TEXT"},
        }
        metrics = compute_schema_linking_metrics(reduced_schema, gt_item)
        self.assertEqual(metrics["executable_col_recall"], 1.0)
        self.assertEqual(metrics["table_recall"], 1.0)
        # Direct precision is 2/6 = 0.3333, but executable precision is 6/6 = 1.0
        self.assertAlmostEqual(metrics["direct_col_precision"], 0.3333, places=2)
        self.assertEqual(metrics["executable_col_precision"], 1.0)

    def test_failure_classification(self):
        # 1. Safe success
        c1 = classify_pipeline_outcome({"success": True}, True, None)
        self.assertEqual(c1, "SUCCESS")

        # 2. Safety rejection
        c2 = classify_pipeline_outcome({"success": False, "error": "SQL rejected: non-read-only"}, False)
        self.assertEqual(c2, "SQL_SAFETY_REJECTED")

        # 3. Missing table in proposed mode
        schema_m = {"table_recall": 0.5, "executable_col_recall": 0.5}
        c3 = classify_pipeline_outcome({"success": True}, False, schema_m, is_proposed=True)
        self.assertEqual(c3, "SCHEMA_LINK_MISSING_TABLE")

        # 4. Result mismatch
        c4 = classify_pipeline_outcome({"success": True}, False, {"table_recall": 1.0, "executable_col_recall": 1.0}, is_proposed=True)
        self.assertEqual(c4, "RESULT_CORRECTNESS_MISMATCH")


if __name__ == "__main__":
    unittest.main()

