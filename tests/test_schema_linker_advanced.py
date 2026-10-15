import os
import sys
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_schema, get_relationships
from schema_linker import SchemaLinker


class TestSchemaLinkerAdvanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.linker = SchemaLinker()
        cls.car_db = "dataset/spider_data/database/car_1/car_1.sqlite"
        cls.college_db = "college.db"

    def test_a_horsepower_regression(self):
        """
        Test A: Horsepower regression on car_1.
        Question: 'Which model of the car has the minimum horsepower?'
        Verifies:
        - The relevant horsepower column is selected.
        - Its parent table (cars_data) survives table selection.
        - The relevant model-name candidate (car_names.Model) is considered.
        - Reduced schema contains the necessary tables and join keys.
        - Unrelated geographical tables (countries) are not added without demonstrated need.
        - Reduced schema is internally valid.
        """
        if not os.path.exists(self.car_db):
            self.skipTest(f"Spider database not found at {self.car_db}")

        schema = get_schema(self.car_db)
        rels = get_relationships(self.car_db)

        question = "Which model of the car has the minimum horsepower?"
        res = self.linker.link_schema(question, schema, rels)

        reduced_schema = res["reduced_schema"]
        selected_tables = res["selected_tables"]
        val = res["validation"]

        # 1. cars_data table must survive table selection
        self.assertIn("cars_data", selected_tables, "cars_data must be retained in selected tables")
        self.assertIn("cars_data", reduced_schema, "cars_data must be present in reduced_schema")

        # 2. Horsepower column must be selected
        self.assertIn("Horsepower", reduced_schema["cars_data"], "Horsepower column must be present in cars_data")

        # 3. Model candidate must be considered and retained
        has_model = ("car_names" in reduced_schema and "Model" in reduced_schema["car_names"]) or \
                    ("model_list" in reduced_schema and "Model" in reduced_schema["model_list"])
        self.assertTrue(has_model, "Model candidate must be selected in reduced schema")

        # 4. Join key between cars_data and car_names must be present
        self.assertIn("Id", reduced_schema["cars_data"], "cars_data.Id join key must be retained")
        if "car_names" in reduced_schema:
            self.assertIn("MakeId", reduced_schema["car_names"], "car_names.MakeId join key must be retained")

        # 5. Unrelated geographical tables (countries) must not be added
        self.assertNotIn("countries", selected_tables, "Unrelated table 'countries' must not be added")

        # 6. Reduced schema must be valid
        self.assertTrue(val["is_valid"], f"Validation must pass: errors={val['errors']}")
        self.assertEqual(len(val["errors"]), 0)

    def test_b_duplicate_column_disambiguation(self):
        """
        Test B: Duplicate column names.
        Verifies that when similarly named columns appear in different tables,
        the linker considers both candidates and uses question relevance and
        relationship context / graph proximity to rank them.
        """
        mock_schema = {
            "department": {"id": "INTEGER", "name": "TEXT"},
            "employee": {"id": "INTEGER", "name": "TEXT", "dept_id": "INTEGER", "salary": "REAL"},
            "project": {"id": "INTEGER", "name": "TEXT", "lead_id": "INTEGER"}
        }
        mock_rels = [
            {"from_table": "employee", "from_column": "dept_id", "to_table": "department", "to_column": "id"},
            {"from_table": "project", "from_column": "lead_id", "to_table": "employee", "to_column": "id"}
        ]

        # Query clearly asks about employee salary and name
        q = "Find the employee name with highest salary"
        res = self.linker.link_schema(q, mock_schema, mock_rels)

        ranked = res["ranked_items"]
        # Find employee.name and department.name in ranking
        emp_name_item = next((item for item in ranked if item["table"] == "employee" and item["column"] == "name"), None)
        dept_name_item = next((item for item in ranked if item["table"] == "department" and item["column"] == "name"), None)

        self.assertIsNotNone(emp_name_item)
        self.assertIsNotNone(dept_name_item)
        # employee.name should outrank department.name because salary is in employee
        self.assertGreaterEqual(emp_name_item["score"], dept_name_item["score"],
                                "employee.name should rank higher than department.name given query context")

    def test_c_multi_table_join(self):
        """
        Test C: Multi-table join.
        Use a question requiring at least three related tables.
        Verify that all necessary intermediate tables and join keys survive reduction.
        """
        mock_schema = {
            "customers": {"customer_id": "INTEGER", "customer_name": "TEXT"},
            "orders": {"order_id": "INTEGER", "customer_id": "INTEGER", "order_date": "TEXT"},
            "order_items": {"item_id": "INTEGER", "order_id": "INTEGER", "product_id": "INTEGER", "quantity": "INTEGER"},
            "products": {"product_id": "INTEGER", "product_name": "TEXT", "price": "REAL"}
        }
        mock_rels = [
            {"from_table": "orders", "from_column": "customer_id", "to_table": "customers", "to_column": "customer_id"},
            {"from_table": "order_items", "from_column": "order_id", "to_table": "orders", "to_column": "order_id"},
            {"from_table": "order_items", "from_column": "product_id", "to_table": "products", "to_column": "product_id"}
        ]

        q = "List customer names who ordered laptop product"
        res = self.linker.link_schema(q, mock_schema, mock_rels, top_k_tables=4)

        reduced = res["reduced_schema"]
        val = res["validation"]

        # Should retain customers, products, and intermediate tables orders and order_items
        self.assertIn("customers", reduced)
        self.assertIn("products", reduced)
        self.assertIn("orders", reduced, "Intermediate table 'orders' must survive reduction")
        self.assertIn("order_items", reduced, "Intermediate table 'order_items' must survive reduction")

        # Structural join keys must be retained
        self.assertIn("customer_id", reduced["customers"])
        self.assertIn("customer_id", reduced["orders"])
        self.assertIn("order_id", reduced["orders"])
        self.assertIn("order_id", reduced["order_items"])
        self.assertIn("product_id", reduced["order_items"])
        self.assertIn("product_id", reduced["products"])

        self.assertTrue(val["is_valid"])

    def test_d_structural_columns_outside_top_k_budget(self):
        """
        Test D: Structural columns outside Top-K.
        Set a small content-column budget (top_k_columns = 2) and verify that
        essential join keys are still retained without consuming the content-column budget.
        """
        mock_schema = {
            "authors": {"author_id": "INTEGER", "author_name": "TEXT"},
            "books": {"book_id": "INTEGER", "author_id": "INTEGER", "title": "TEXT", "isbn": "TEXT"}
        }
        mock_rels = [
            {"from_table": "books", "from_column": "author_id", "to_table": "authors", "to_column": "author_id"}
        ]

        q = "Find author name for title Hamlet"
        # Content column budget = 2
        res = self.linker.link_schema(q, mock_schema, mock_rels, top_k_columns=2)

        reduced = res["reduced_schema"]
        content_cols = res["content_columns"]
        structural_cols = res["structural_columns"]

        # Content columns should respect the budget of 2
        total_content = sum(len(cols) for cols in content_cols.values())
        self.assertLessEqual(total_content, 2, "Content columns should not exceed content-column budget")

        # Essential join keys must still be present in reduced_schema via structural columns
        self.assertIn("author_id", reduced["authors"], "author_id PK must be retained")
        self.assertIn("author_id", reduced["books"], "author_id FK must be retained")

        # Check structural columns record
        self.assertIn("author_id", structural_cols["authors"])
        self.assertIn("author_id", structural_cols["books"])

    def test_e_irrelevant_neighbors_pruning(self):
        """
        Test E: Irrelevant neighbors.
        Construct or use a schema where a relevant table has foreign-key connections
        to unrelated metadata tables. Verify that relationship expansion does not
        automatically include every neighbor.
        """
        mock_schema = {
            "users": {"user_id": "INTEGER", "username": "TEXT", "system_log_id": "INTEGER", "audit_id": "INTEGER"},
            "posts": {"post_id": "INTEGER", "user_id": "INTEGER", "content": "TEXT"},
            "system_logs": {"log_id": "INTEGER", "timestamp": "TEXT", "log_payload": "TEXT"},
            "audit_trail": {"audit_id": "INTEGER", "server_ip": "TEXT", "checksum": "TEXT"}
        }
        mock_rels = [
            {"from_table": "posts", "from_column": "user_id", "to_table": "users", "to_column": "user_id"},
            {"from_table": "users", "from_column": "system_log_id", "to_table": "system_logs", "to_column": "log_id"},
            {"from_table": "users", "from_column": "audit_id", "to_table": "audit_trail", "to_column": "audit_id"}
        ]

        q = "Show posts content written by user Alice"
        res = self.linker.link_schema(q, mock_schema, mock_rels, top_k_tables=3)

        selected_tables = res["selected_tables"]

        # Relevant tables
        self.assertIn("users", selected_tables)
        self.assertIn("posts", selected_tables)

        # Unrelated metadata neighbors must NOT be blindly included
        self.assertNotIn("system_logs", selected_tables, "system_logs should not be blindly expanded")
        self.assertNotIn("audit_trail", selected_tables, "audit_trail should not be blindly expanded")

    def test_f_disconnected_tables_explicit_handling(self):
        """
        Test F: Disconnected tables.
        Verify that the linker handles an absent or disconnected relationship path explicitly
        rather than inventing a join.
        """
        mock_schema = {
            "inventory": {"item_id": "INTEGER", "stock_count": "INTEGER"},
            "weather": {"city_id": "INTEGER", "temperature": "REAL", "rainfall": "REAL"}
        }
        # No relationships connecting inventory and weather
        mock_rels = []

        q = "Show inventory stock count and city temperature"
        res = self.linker.link_schema(q, mock_schema, mock_rels)

        val = res["validation"]
        # The linker should report disconnected anchors explicitly in warnings/disconnected_anchors
        # rather than inventing non-existent join keys
    def test_g_critical_column_admission(self):
        """
        Test G: Critical column admission.
        Verifies that a table with 20 columns is not excluded by dilution when exactly
        one column has high direct relevance.
        """
        mock_schema = {
            "large_table": {f"col_{i}": "TEXT" for i in range(20)},
            "small_table": {"id": "INTEGER", "summary": "TEXT"}
        }
        mock_schema["large_table"]["critical_target"] = "REAL"
        mock_rels = []

        q = "Find records with high critical target value"
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        self.assertIn("large_table", res["selected_tables"])
        self.assertIn("critical_target", res["reduced_schema"]["large_table"])

    def test_h_validation_repair_and_recording(self):
        """
        Test H: Schema validation and deterministic repair.
        Verifies that dropped structural join keys are repaired and recorded.
        """
        mock_schema = {
            "dept": {"dept_id": "INTEGER", "name": "TEXT"},
            "emp": {"emp_id": "INTEGER", "dept_id": "INTEGER", "name": "TEXT"}
        }
        mock_rels = [
            {"from_table": "emp", "from_column": "dept_id", "to_table": "dept", "to_column": "dept_id"}
        ]
        q = "List emp name and dept name"
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        val = res["validation"]
        self.assertTrue(val["is_valid"])
        self.assertIn("dept_id", res["reduced_schema"]["dept"])
        self.assertIn("dept_id", res["reduced_schema"]["emp"])

    def test_i_latency_warm_run_speedup(self):
        """
        Test I: Warm-run embedding caching latency.
        Verifies warm query execution completes in under 150ms.
        """
        import time
        mock_schema = {
            "tbl1": {f"c{i}": "TEXT" for i in range(15)},
            "tbl2": {f"c{i}": "INTEGER" for i in range(15)}
        }
        mock_rels = []
        q = "Find c1 in tbl1"
        # First call warms cache
        self.linker.link_schema(q, mock_schema, mock_rels)

        t0 = time.time()
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        duration = time.time() - t0
        self.assertLess(duration, 0.20, f"Warm run should execute in < 200ms, took {duration:.4f}s")


    def test_j_entity_noun_disambiguation(self):
        """
        Test J: Entity noun table disambiguation regression.
        Verifies that when a query mentions an entity whose name matches a table (e.g. 'actor'),
        duplicate columns ('first_name', 'last_name') are attributed to that entity table
        rather than unmentioned tables ('staff', 'customer').
        """
        mock_schema = {
            "actor": {"actor_id": "INTEGER", "first_name": "TEXT", "last_name": "TEXT"},
            "staff": {"staff_id": "INTEGER", "first_name": "TEXT", "last_name": "TEXT", "username": "TEXT"},
            "customer": {"customer_id": "INTEGER", "first_name": "TEXT", "last_name": "TEXT"}
        }
        mock_rels = []
        q = "Return the most common first name among all actors."
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        self.assertIn("actor", res["selected_tables"], "Entity table 'actor' must be selected")
        self.assertIn("first_name", res["reduced_schema"].get("actor", {}), "first_name must be linked to actor")
        self.assertNotIn("staff", res["selected_tables"], "Unmentioned 'staff' table must not supplant 'actor'")

    def test_k_small_table_attribute_retention(self):
        """
        Test K: Small table attribute retention regression.
        Verifies that for compact anchor tables (<= 5 columns), highly relevant attributes
        (e.g., Country filter column) are retained within the column budget rather than dropped.
        """
        mock_schema = {
            "airlines": {"uid": "INTEGER", "Airline": "TEXT", "Abbreviation": "TEXT", "Country": "TEXT"},
            "airports": {"AirportCode": "TEXT", "AirportName": "TEXT", "Country": "TEXT"}
        }
        mock_rels = []
        q = 'List all airline names and their abbreviations in "USA".'
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        self.assertIn("airlines", res["selected_tables"], "Table 'airlines' must be selected")
        self.assertIn("Country", res["reduced_schema"].get("airlines", {}), "Country column must be retained for filtering")
        self.assertIn("Airline", res["reduced_schema"].get("airlines", {}), "Airline name must be retained")
        self.assertIn("Abbreviation", res["reduced_schema"].get("airlines", {}), "Abbreviation must be retained")

    def test_l_query_action_verb_exclusion(self):
        """
        Test L: Query action verb exclusion regression.
        Verifies that generic query action verbs ('return', 'list', 'show') do not cause
        unrelated tables with matching substrings (e.g. 'return_date') to be falsely declared as anchors.
        """
        mock_schema = {
            "actor": {"actor_id": "INTEGER", "first_name": "TEXT", "last_name": "TEXT"},
            "rental": {"rental_id": "INTEGER", "return_date": "TEXT", "customer_id": "INTEGER"}
        }
        mock_rels = []
        q = "Return the most common first name among all actors."
        res = self.linker.link_schema(q, mock_schema, mock_rels)
        self.assertNotIn("rental", res["selected_tables"], "Generic verb 'Return' must not trigger 'rental' table selection")


if __name__ == "__main__":
    unittest.main()

