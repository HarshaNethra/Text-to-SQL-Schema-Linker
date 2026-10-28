import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

SPIDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset", "spider_data")
TABLES_FILE = os.path.join(SPIDER_DIR, "tables.json")
DEV_FILE = os.path.join(SPIDER_DIR, "dev.json")
TRAIN_FILE = os.path.join(SPIDER_DIR, "train_spider.json")
DATABASE_DIR = os.path.join(SPIDER_DIR, "database")


class SpiderAdapter:
    """
    Adapter for the Spider Text-to-SQL Benchmark dataset.
    Loads database schemas, relationships, ground-truth queries, and ground-truth column/table usages.
    """

    def __init__(self, spider_dir: str = SPIDER_DIR):
        self.spider_dir = spider_dir
        self.database_dir = os.path.join(spider_dir, "database")
        self.tables_file = os.path.join(spider_dir, "tables.json")
        self.dev_file = os.path.join(spider_dir, "dev.json")
        self.train_file = os.path.join(spider_dir, "train_spider.json")

        # Auto-extract zip if tables_file or database_dir is missing but spider_data.zip exists
        zip_path = os.path.join(os.path.dirname(spider_dir), "spider_data.zip")
        if (not os.path.exists(self.tables_file) or not os.path.exists(self.database_dir)) and os.path.exists(zip_path):
            try:
                import zipfile
                if zipfile.is_zipfile(zip_path):
                    print(f"[SpiderAdapter] Extracting Spider dataset from {zip_path}...")
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        zf.extractall(os.path.dirname(spider_dir))
                    print("[SpiderAdapter] Extraction completed successfully.")
            except Exception as e:
                print(f"[SpiderAdapter] Notice: Could not auto-extract {zip_path}: {e}")

        self._tables_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._dev_cache: Optional[List[Dict[str, Any]]] = None

    def get_tables_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads tables.json and indexes schemas by db_id.
        Returns:
            {
                "db_id": {
                    "table_names": [...],
                    "table_names_original": [...],
                    "column_names": [[table_idx, col_name], ...],
                    "column_names_original": [[table_idx, col_name], ...],
                    "column_types": [...],
                    "primary_keys": [...],
                    "foreign_keys": [...]
                }
            }
        """
        if self._tables_cache is not None:
            return self._tables_cache

        if not os.path.exists(self.tables_file):
            raise FileNotFoundError(f"Spider tables.json not found at {self.tables_file}")

        with open(self.tables_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        indexed: Dict[str, Dict[str, Any]] = {}
        for entry in raw_data:
            db_id = entry.get("db_id")
            if db_id:
                indexed[db_id] = entry

        self._tables_cache = indexed
        return indexed

    def list_available_databases(self) -> List[Dict[str, Any]]:
        """
        Lists all Spider databases with path, table count, and existence check.
        """
        if not os.path.exists(self.database_dir):
            return []

        tables_meta = self.get_tables_metadata()
        results = []
        for folder_name in sorted(os.listdir(self.database_dir)):
            folder_path = os.path.join(self.database_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            sqlite_path = os.path.join(folder_path, f"{folder_name}.sqlite")
            meta = tables_meta.get(folder_name, {})
            table_names = meta.get("table_names_original", [])

            results.append({
                "db_id": folder_name,
                "sqlite_path": sqlite_path,
                "exists": os.path.exists(sqlite_path),
                "table_count": len(table_names),
                "tables": table_names,
            })
        return results

    def get_db_path(self, db_id: str) -> str:
        """Returns the absolute path to a Spider SQLite database."""
        sqlite_path = os.path.join(self.database_dir, db_id, f"{db_id}.sqlite")
        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"Spider SQLite database not found for '{db_id}' at {sqlite_path}")
        return sqlite_path

    def load_dev_queries(
        self,
        db_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Loads queries from dev.json, optionally filtered by db_id.
        """
        if self._dev_cache is None:
            if not os.path.exists(self.dev_file):
                raise FileNotFoundError(f"Spider dev.json not found at {self.dev_file}")
            with open(self.dev_file, "r", encoding="utf-8") as f:
                self._dev_cache = json.load(f)

        queries = self._dev_cache
        if db_id:
            queries = [q for q in queries if q.get("db_id") == db_id]

        if offset > 0:
            queries = queries[offset:]
        if limit is not None:
            queries = queries[:limit]

        return queries

    def load_all_queries_for_db(self, db_id: str) -> List[Dict[str, Any]]:
        """
        Loads queries for a database from dev.json first, and augments with train_spider.json if available.
        """
        dev_qs = self.load_dev_queries(db_id=db_id)
        if dev_qs:
            return dev_qs

        if getattr(self, "_train_cache", None) is None:
            if os.path.exists(self.train_file):
                with open(self.train_file, "r", encoding="utf-8") as f:
                    self._train_cache = json.load(f)
            else:
                self._train_cache = []

        return [q for q in self._train_cache if q.get("db_id") == db_id]

    def get_sample_queries(
        self,
        db_id: str,
        table_name: Optional[str] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Returns natural language sample queries for a Spider database,
        optionally filtered by table relevance.
        """
        all_qs = self.load_all_queries_for_db(db_id)
        if not all_qs:
            return []

        results: List[Dict[str, Any]] = []
        seen_questions: Set[str] = set()

        for item in all_qs:
            question = item.get("question", "").strip()
            if not question or question in seen_questions:
                continue

            query_sql = item.get("query", "").strip()
            used_tables, used_cols = self.extract_ground_truth_elements(item)

            if table_name:
                t_lower = table_name.lower()
                matches_table = (
                    any(t.lower() == t_lower for t in used_tables)
                    or re.search(r'\b' + re.escape(t_lower) + r'\b', query_sql.lower()) is not None
                )
                if not matches_table:
                    continue

            seen_questions.add(question)
            results.append({
                "question": question,
                "sql": query_sql,
                "tables": used_tables,
                "columns": used_cols,
                "db_id": db_id,
            })

            if len(results) >= limit:
                break

        # Fallback to general DB queries if table-specific yielded none
        if not results and table_name:
            return self.get_sample_queries(db_id, table_name=None, limit=limit)

        return results

    def extract_ground_truth_elements(
        self,
        spider_item: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """
        Extracts ground-truth tables and columns utilized in a Spider query.
        Traverses Spider AST format (from, select, where, groupBy, orderBy, having).
        Returns:
            (direct_tables: List[str], direct_columns: List[str])
            Example: (["singer"], ["singer.Singer_ID", "singer.Name"])
        """
        db_id = spider_item.get("db_id", "")
        tables_meta = self.get_tables_metadata().get(db_id)
        if not tables_meta:
            return [], []

        table_names = tables_meta.get("table_names_original", [])
        col_names = tables_meta.get("column_names_original", [])

        used_tables: Set[str] = set()
        used_cols: Set[str] = set()

        sql_ast = spider_item.get("sql")
        if isinstance(sql_ast, dict):
            def walk(node: Any):
                if isinstance(node, list):
                    # Check for table_unit: ['table_unit', tbl_idx]
                    if len(node) == 2 and node[0] == "table_unit" and isinstance(node[1], int):
                        tbl_idx = node[1]
                        if 0 <= tbl_idx < len(table_names):
                            used_tables.add(table_names[tbl_idx])
                    # Check for col_unit: [agg_id, col_idx, isDistinct]
                    elif len(node) == 3 and isinstance(node[0], int) and isinstance(node[1], int) and isinstance(node[2], bool):
                        col_idx = node[1]
                        if 0 <= col_idx < len(col_names):
                            t_idx, c_name = col_names[col_idx]
                            if c_name != "*" and 0 <= t_idx < len(table_names):
                                tbl_name = table_names[t_idx]
                                used_tables.add(tbl_name)
                                used_cols.add(f"{tbl_name}.{c_name}")
                    for item in node:
                        walk(item)
                elif isinstance(node, dict):
                    for v in node.values():
                        walk(v)

            walk(sql_ast)

        # Fallback if AST extraction produced nothing
        if not used_tables and not used_cols:
            gt_query = spider_item.get("query", "")
            tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', gt_query.lower()))
            for t_name in table_names:
                if t_name.lower() in tokens:
                    used_tables.add(t_name)
            for t_idx, c_name in col_names:
                if c_name == "*" or t_idx < 0 or t_idx >= len(table_names):
                    continue
                t_name = table_names[t_idx]
                if t_name in used_tables and (c_name.lower() in tokens or f"{t_name.lower()}.{c_name.lower()}" in gt_query.lower()):
                    used_cols.add(f"{t_name}.{c_name}")

        return sorted(list(used_tables)), sorted(list(used_cols))

    def format_as_evaluation_item(
        self,
        spider_item: Dict[str, Any],
        item_id: int
    ) -> Dict[str, Any]:
        """
        Converts a raw Spider dev.json entry into standard evaluation format compatible with evaluator.py.
        """
        db_id = spider_item["db_id"]
        db_path = self.get_db_path(db_id)
        gt_tables, gt_cols = self.extract_ground_truth_elements(spider_item)

        return {
            "id": item_id,
            "db_id": db_id,
            "db_path": db_path,
            "question": spider_item.get("question", ""),
            "ground_truth_sql": spider_item.get("query", ""),
            "category": f"Spider ({db_id})",
            "direct_tables": gt_tables,
            "direct_columns": gt_cols,
            "structural_tables": [],
            "structural_columns": [],
            "all_required_tables": gt_tables,
            "all_required_columns": gt_cols,
            "required_relationships": [],
        }
