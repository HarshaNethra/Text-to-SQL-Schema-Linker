import os
import sys
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluator_spider import SpiderBenchmarkEvaluator
from llm import LLMClient
from schema_linker import SchemaLinker
from spider_adapter import SpiderAdapter


class TestSpiderAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SpiderAdapter()

    def test_tables_metadata_loaded(self):
        meta = self.adapter.get_tables_metadata()
        self.assertIn("concert_singer", meta)
        cs_meta = meta["concert_singer"]
        self.assertIn("table_names_original", cs_meta)
        self.assertIn("column_names_original", cs_meta)
        self.assertIn("singer", cs_meta["table_names_original"])

    def test_list_available_databases(self):
        dbs = self.adapter.list_available_databases()
        self.assertGreater(len(dbs), 100)
        db_names = [d["db_id"] for d in dbs]
        self.assertIn("concert_singer", db_names)
        self.assertIn("flight_2", db_names)

    def test_get_db_path(self):
        path = self.adapter.get_db_path("concert_singer")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("concert_singer.sqlite"))

    def test_load_dev_queries(self):
        queries = self.adapter.load_dev_queries(db_id="concert_singer", limit=5)
        self.assertEqual(len(queries), 5)
        for q in queries:
            self.assertEqual(q["db_id"], "concert_singer")
            self.assertIn("question", q)
            self.assertIn("query", q)

    def test_extract_ground_truth_elements(self):
        sample_q = {
            "db_id": "concert_singer",
            "query": "SELECT name ,  country ,  age FROM singer ORDER BY age DESC",
            "sql": {
                "from": {"table_units": [["table_unit", 1]], "conds": []},
                "select": [False, [[0, [0, [0, 9, False], None]], [0, [0, [0, 10, False], None]], [0, [0, [0, 13, False], None]]]],
                "where": [],
                "groupBy": [],
                "having": [],
                "orderBy": ["desc", [[0, [0, 13, False], None]]],
                "limit": None,
                "intersect": None,
                "union": None,
                "except": None,
            },
        }
        tables, cols = self.adapter.extract_ground_truth_elements(sample_q)
        self.assertEqual(tables, ["singer"])
        self.assertIn("singer.Name", cols)
        self.assertIn("singer.Country", cols)
        self.assertIn("singer.Age", cols)

    def test_format_as_evaluation_item(self):
        sample_q = self.adapter.load_dev_queries(db_id="concert_singer", limit=1)[0]
        item = self.adapter.format_as_evaluation_item(sample_q, 1)
        self.assertEqual(item["id"], 1)
        self.assertEqual(item["db_id"], "concert_singer")
        self.assertTrue(os.path.exists(item["db_path"]))
        self.assertIn("direct_tables", item)
        self.assertIn("direct_columns", item)


class TestSpiderBenchmarkEvaluator(unittest.TestCase):
    def setUp(self):
        self.llm = LLMClient()
        self.linker = SchemaLinker()
        self.evaluator = SpiderBenchmarkEvaluator(llm_client=self.llm, linker=self.linker)

    def test_evaluate_concert_singer_single_query(self):
        adapter = SpiderAdapter()
        q = adapter.load_dev_queries(db_id="concert_singer", limit=1)[0]
        item = adapter.format_as_evaluation_item(q, 1)
        res = self.evaluator.evaluate_item(item)
        self.assertEqual(res["db_id"], "concert_singer")
        self.assertIn("schema_reduction_pct", res)
        self.assertIn("schema_metrics", res)
        self.assertTrue(res["baseline"]["exec_success"])
        self.assertTrue(res["proposed"]["exec_success"])

    def test_run_small_benchmark(self):
        output = self.evaluator.run_benchmark(db_id="concert_singer", limit=3, export=False)
        self.assertIn("summary", output)
        self.assertIn("results", output)
        self.assertEqual(output["summary"]["total_queries"], 3)
        self.assertGreaterEqual(output["summary"]["avg_schema_reduction_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
