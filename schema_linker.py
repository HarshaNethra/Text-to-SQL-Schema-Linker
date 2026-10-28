import os
import re
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# Lazy load sentence-transformers or scikit-learn
_TRANSFORMER_MODEL = None
_TRANSFORMER_LOADED = False

def get_sentence_transformer(model_name: str = "all-MiniLM-L6-v2"):
    """Loads SentenceTransformer model locally with fallback handling."""
    global _TRANSFORMER_MODEL, _TRANSFORMER_LOADED
    if _TRANSFORMER_LOADED:
        return _TRANSFORMER_MODEL

    try:
        from sentence_transformers import SentenceTransformer
        
        # Check if local model directory exists
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_dir = os.path.join(base_dir, "models", model_name)
        
        if os.path.isdir(local_dir):
            _TRANSFORMER_MODEL = SentenceTransformer(local_dir)
        else:
            # Download and persist locally for fast offline access
            _TRANSFORMER_MODEL = SentenceTransformer(model_name)
            try:
                os.makedirs(os.path.join(base_dir, "models"), exist_ok=True)
                _TRANSFORMER_MODEL.save(local_dir)
            except Exception:
                pass
        _TRANSFORMER_LOADED = True
    except Exception as e:
        print(f"[Warning] SentenceTransformer could not be loaded: {e}. Falling back to lexical embedding approximation.")
        _TRANSFORMER_MODEL = None
        _TRANSFORMER_LOADED = True

    return _TRANSFORMER_MODEL


def split_identifier(ident: str) -> List[str]:
    """Splits camelCase, PascalCase, or snake_case identifiers into lowercase words."""
    # Split on underscores or transitions between lowercase and uppercase
    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', ident)
    return [w.lower() for w in words] if words else [ident.lower()]


def get_stem(w: str) -> str:
    """Strips common English inflectional and derivational suffixes for resilient matching."""
    w = w.lower()
    for suff in ["ment", "ments", "ing", "ed", "es", "s"]:
        if w.endswith(suff) and len(w) - len(suff) >= 4:
            return w[:-len(suff)]
    return w


DOMAIN_SYNONYMS: Dict[str, Set[str]] = {
    "marks": {"score", "scores", "scored", "mark", "grade", "points", "cgpa", "gpa"},
    "score": {"mark", "marks", "grade", "points"},
    "department": {"cse", "ece", "mech", "civil", "dept", "branch", "major", "division"},
    "major": {"cse", "ece", "mech", "civil", "dept", "department", "branch"},
    "faculty": {"professor", "teacher", "instructor", "lecturer"},
    "course": {"class", "subject"},
}


def compute_lexical_similarity(question: str, table_name: str, col_name: str) -> float:
    """
    Computes lexical similarity between user query tokens and table/column tokens.
    Combines exact match, token overlap, and substring matching.
    """
    q_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', question.lower()))
    col_tokens = set(split_identifier(col_name))
    table_tokens = set(split_identifier(table_name))
    
    combined_tokens = col_tokens.union(table_tokens)
    if not q_tokens or not combined_tokens:
        return 0.0

    # Direct word overlap (Jaccard / containment)
    overlap = q_tokens.intersection(combined_tokens)
    col_overlap = q_tokens.intersection(col_tokens)
    
    score = 0.0
    if col_overlap:
        # High reward if column name itself is mentioned
        score += 0.6 * (len(col_overlap) / len(col_tokens))
    if overlap:
        score += 0.4 * (len(overlap) / len(combined_tokens))

    QUERY_ACTION_VERBS = {"return", "show", "list", "display", "find", "give", "tell", "select", "get"}
    q_stems = {get_stem(qt) for qt in q_tokens}

    # Substring / partial match checks (excluding generic query verbs)
    for ct in col_tokens:
        ct_stem = get_stem(ct)
        if (ct in q_tokens or ct_stem in q_stems) and ct not in QUERY_ACTION_VERBS:
            score = max(score, 0.85)
        elif len(ct) >= 4 and any(ct in qt or (len(qt) >= 4 and qt in ct) for qt in q_tokens if qt not in QUERY_ACTION_VERBS):
            score = max(score, 0.65)

    # Domain synonym matching
    for ct in col_tokens:
        syns = DOMAIN_SYNONYMS.get(ct, set())
        if syns and (syns.intersection(q_tokens) or any(any(s in qt for s in syns if len(s) >= 3) for qt in q_tokens)):
            score = max(score, 0.85)

    return min(1.0, score)




def infer_type_match(question: str, col_type: str, col_name: str) -> float:
    """
    Infers data type intent from question keywords and checks compatibility.
    """
    q_lower = question.lower()
    numeric_types = {"INTEGER", "REAL", "NUMERIC", "FLOAT", "DOUBLE", "INT"}
    text_types = {"TEXT", "VARCHAR", "CHAR", "STRING"}

    is_col_numeric = any(nt in col_type.upper() for nt in numeric_types)
    is_col_text = any(tt in col_type.upper() for tt in text_types)

    numeric_cues = [
        "above", "below", "greater", "less", "highest", "lowest", "maximum", "minimum",
        "average", "avg", "sum", "total", "count", "marks", "salary", "age", "credits",
        "attendance", "percentage", "%", ">", "<", "=", "more than", "older", "younger",
        "score", "earned", "cost"
    ]
    has_numeric_cue = any(cue in q_lower for cue in numeric_cues) or bool(re.search(r'\d+', q_lower))

    text_cues = [
        "named", "called", "name", "who", "which department", "department", "department of",
        "cse", "ece", "mech", "civil", "grade", "course name", "faculty name", "student name"
    ]
    has_text_cue = any(cue in q_lower for cue in text_cues)

    if has_numeric_cue and is_col_numeric:
        return 0.9
    if has_text_cue and is_col_text:
        return 0.85
    if not has_numeric_cue and is_col_text:
        return 0.6
    if not has_text_cue and is_col_numeric:
        return 0.5
    return 0.4


class SchemaLinker:
    """
    Core Schema Linking & Reduction Engine.
    Combines Lexical, Semantic, Type Match, and Relationship Graph scores with:
    - Column-driven anchor table selection
    - Separation of content columns and structural columns
    - Foreign-key graph shortest path join-path completion
    - Reduced-schema validation and deterministic repair
    - Graph proximity duplicate-column disambiguation
    """

    def __init__(
        self,
        lexical_weight: float = 0.40,
        semantic_weight: float = 0.35,
        type_weight: float = 0.15,
        relationship_weight: float = 0.10,
        top_k_tables: Optional[int] = None,
        top_k_columns: Optional[int] = None,
        min_relevance_score: Optional[float] = None,
        anchor_margin: Optional[float] = None,
        disambiguation_proximity_weight: Optional[float] = None,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.lexical_weight = lexical_weight if lexical_weight != 0.40 else float(os.getenv("LEXICAL_WEIGHT", 0.40))
        self.semantic_weight = semantic_weight if semantic_weight != 0.35 else float(os.getenv("SEMANTIC_WEIGHT", 0.35))
        self.type_weight = type_weight if type_weight != 0.15 else float(os.getenv("TYPE_WEIGHT", 0.15))
        self.relationship_weight = relationship_weight if relationship_weight != 0.10 else float(os.getenv("RELATIONSHIP_WEIGHT", 0.10))
        self.default_top_k_tables = top_k_tables or int(os.getenv("TOP_K_TABLES", 4))
        self.default_top_k_columns = top_k_columns or int(os.getenv("TOP_K_COLUMNS", 8))
        self.default_min_relevance_score = min_relevance_score if min_relevance_score is not None else float(os.getenv("MIN_RELEVANCE_SCORE", 0.15))
        self.anchor_margin = anchor_margin if anchor_margin is not None else float(os.getenv("ANCHOR_MARGIN", 0.15))
        self.disambiguation_proximity_weight = (
            disambiguation_proximity_weight
            if disambiguation_proximity_weight is not None
            else float(os.getenv("DISAMBIGUATION_PROXIMITY_WEIGHT", 0.15))
        )
        self.model_name = os.getenv("EMBEDDING_MODEL", model_name)
        self.model = None
        self._schema_cache: Dict[Any, Tuple[List[Tuple[str, str]], np.ndarray]] = {}

    def _ensure_model(self):
        if self.model is None:
            self.model = get_sentence_transformer(self.model_name)

    def _get_schema_embeddings(self, schema: Dict[str, Dict[str, str]]) -> Tuple[List[Tuple[str, str]], np.ndarray]:
        """
        Returns cached normalized column embeddings for the given schema.
        Computed once per unique schema structure.
        """
        schema_key = tuple(sorted((t, tuple(sorted(cols.items()))) for t, cols in schema.items()))
        if schema_key in self._schema_cache:
            return self._schema_cache[schema_key]

        self._ensure_model()
        cols_list: List[Tuple[str, str]] = []
        texts: List[str] = []
        for table, columns in sorted(schema.items()):
            for col, col_type in sorted(columns.items()):
                cols_list.append((table, col))
                col_words = " ".join(split_identifier(col))
                texts.append(f"Table {table} column {col} representing {col_words} of type {col_type}")

        if self.model is not None and texts:
            try:
                embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            except Exception:
                embeddings = np.zeros((len(texts), 384), dtype=np.float32)
        else:
            embeddings = np.zeros((len(texts), 384), dtype=np.float32)

        self._schema_cache[schema_key] = (cols_list, embeddings)
        return cols_list, embeddings

    @staticmethod
    def _build_fk_graph(relationships: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Builds an undirected adjacency list from foreign key relationships.
        Each edge contains {neighbor, from_col, to_col}.
        """
        graph: Dict[str, List[Dict[str, str]]] = {}
        for rel in relationships:
            f_t, f_c = rel.get("from_table"), rel.get("from_column")
            t_t, t_c = rel.get("to_table"), rel.get("to_column")
            if not f_t or not t_t:
                continue
            if f_t not in graph:
                graph[f_t] = []
            if t_t not in graph:
                graph[t_t] = []
            graph[f_t].append({"neighbor": t_t, "from_col": f_c, "to_col": t_c})
            graph[t_t].append({"neighbor": f_t, "from_col": t_c, "to_col": f_c})
        return graph

    @staticmethod
    def _find_shortest_path(
        graph: Dict[str, List[Dict[str, str]]],
        start: str,
        goal: str
    ) -> Optional[List[Dict[str, str]]]:
        """
        Finds shortest path between start and goal table using BFS.
        Returns a list of edge dicts:
        [{'from_table': ..., 'from_column': ..., 'to_table': ..., 'to_column': ...}]
        or None if no path exists.
        """
        if start == goal:
            return []
        if start not in graph or goal not in graph:
            return None

        queue = deque([(start, [])])
        visited = {start}

        while queue:
            curr_table, path = queue.popleft()
            if curr_table == goal:
                return path

            for edge in graph.get(curr_table, []):
                neighbor = edge["neighbor"]
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_edge = {
                        "from_table": curr_table,
                        "from_column": edge["from_col"],
                        "to_table": neighbor,
                        "to_column": edge["to_col"]
                    }
                    queue.append((neighbor, path + [new_edge]))

        return None

    def _connect_anchor_tables(
        self,
        graph: Dict[str, List[Dict[str, str]]],
        anchor_tables: List[str],
        schema: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Connects multiple anchor tables using shortest paths across foreign keys.
        Avoids adding unrelated neighbors that do not contribute to connecting paths.
        """
        if len(anchor_tables) <= 1:
            return {
                "intermediate_tables": set(),
                "connecting_edges": [],
                "structural_columns": {t: set() for t in anchor_tables},
                "disconnected_anchors": []
            }

        connected_component: Set[str] = {anchor_tables[0]}
        unconnected: Set[str] = set(anchor_tables[1:])
        chosen_edges: List[Dict[str, str]] = []
        intermediate_tables: Set[str] = set()
        structural_columns: Dict[str, Set[str]] = {t: set() for t in schema}
        disconnected_anchors: List[str] = []

        while unconnected:
            best_path = None
            best_target = None

            for target in unconnected:
                for source in list(connected_component):
                    path = self._find_shortest_path(graph, source, target)
                    if path is not None:
                        if best_path is None or len(path) < len(best_path):
                            best_path = path
                            best_target = target

            if best_path is None or best_target is None:
                disconnected_anchors.extend(list(unconnected))
                break

            unconnected.remove(best_target)
            for edge in best_path:
                u = edge["from_table"]
                v = edge["to_table"]
                connected_component.add(u)
                connected_component.add(v)
                if u not in anchor_tables:
                    intermediate_tables.add(u)
                if v not in anchor_tables:
                    intermediate_tables.add(v)

                already_in_chosen = any(
                    (e["from_table"] == u and e["to_table"] == v and e["from_column"] == edge["from_column"] and e["to_column"] == edge["to_column"]) or
                    (e["from_table"] == v and e["to_table"] == u and e["from_column"] == edge["to_column"] and e["to_column"] == edge["from_column"])
                    for e in chosen_edges
                )
                if not already_in_chosen:
                    chosen_edges.append(edge)

                structural_columns[u].add(edge["from_column"])
                structural_columns[v].add(edge["to_column"])

        return {
            "intermediate_tables": intermediate_tables,
            "connecting_edges": chosen_edges,
            "structural_columns": {t: cols for t, cols in structural_columns.items() if cols},
            "disconnected_anchors": disconnected_anchors
        }

    def _disambiguate_duplicate_columns(
        self,
        ranked_list: List[Dict[str, Any]],
        graph: Dict[str, List[Dict[str, str]]],
        candidate_anchor_tables: Set[str],
        schema: Dict[str, Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Improves ranking for duplicate column names across multiple tables.
        Uses question relevance combined with normalized graph proximity to other anchor tables.
        """
        col_to_tables: Dict[str, List[str]] = {}
        for tbl, cols in schema.items():
            for c in cols.keys():
                col_to_tables.setdefault(c.lower(), []).append(tbl)

        for item in ranked_list:
            c_lower = item["column"].lower()
            matching_tables = col_to_tables.get(c_lower, [])
            if len(matching_tables) > 1:
                tbl = item["table"]
                if tbl in candidate_anchor_tables:
                    # Anchor table itself has distance 0 to anchor
                    min_dist = 0
                elif candidate_anchor_tables and tbl in graph:
                    min_dist = float('inf')
                    for target in candidate_anchor_tables:
                        path = self._find_shortest_path(graph, tbl, target)
                        if path is not None:
                            min_dist = min(min_dist, len(path))
                else:
                    min_dist = float('inf')

                if min_dist < float('inf'):
                    proximity_score = 1.0 / (1.0 + min_dist)
                    bonus = round(self.disambiguation_proximity_weight * proximity_score, 4)
                    item["score"] = round(item["score"] + bonus, 4)
                    item["disambiguation_bonus"] = bonus
                    item["graph_distance_to_anchors"] = min_dist

        ranked_list.sort(key=lambda x: x["score"], reverse=True)
        return ranked_list

    def _validate_and_repair_schema(
        self,
        schema: Dict[str, Dict[str, str]],
        reduced_schema: Dict[str, Dict[str, str]],
        essential_columns: List[Dict[str, Any]],
        connecting_edges: List[Dict[str, str]],
        intermediate_tables: Set[str],
        disconnected_anchors: List[str]
    ) -> Dict[str, Any]:
        """
        Validates reduced schema against integrity invariants and performs bounded deterministic repairs.
        """
        errors: List[str] = []
        warnings: List[str] = []
        repaired = False

        # Check 1: Every selected column belongs to a selected table and exists in schema
        for tbl, cols in list(reduced_schema.items()):
            if tbl not in schema:
                errors.append(f"Selected table '{tbl}' does not exist in database schema.")
                del reduced_schema[tbl]
                repaired = True
                continue
            for col in list(cols.keys()):
                if col not in schema[tbl]:
                    errors.append(f"Column '{tbl}.{col}' does not exist in table '{tbl}'.")
                    del reduced_schema[tbl][col]
                    repaired = True

        # Check 2: Every essential content column is present
        for ess in essential_columns:
            e_tbl, e_col = ess["table"], ess["column"]
            if e_tbl not in reduced_schema:
                if e_tbl in schema:
                    reduced_schema[e_tbl] = {e_col: schema[e_tbl].get(e_col, "TEXT")}
                    warnings.append(f"Repaired missing essential table '{e_tbl}' for column '{e_col}'.")
                    repaired = True
                else:
                    errors.append(f"Essential column '{e_tbl}.{e_col}' belongs to nonexistent table '{e_tbl}'.")
            elif e_col not in reduced_schema[e_tbl]:
                if e_tbl in schema and e_col in schema[e_tbl]:
                    reduced_schema[e_tbl][e_col] = schema[e_tbl][e_col]
                    warnings.append(f"Repaired missing essential column '{e_tbl}.{e_col}'.")
                    repaired = True
                else:
                    errors.append(f"Essential column '{e_col}' does not exist in '{e_tbl}'.")

        # Check 3: Every intermediate table on connecting paths is present
        for itbl in intermediate_tables:
            if itbl not in reduced_schema:
                if itbl in schema:
                    reduced_schema[itbl] = {}
                    warnings.append(f"Repaired missing intermediate join table '{itbl}'.")
                    repaired = True
                else:
                    errors.append(f"Intermediate join table '{itbl}' not in schema.")

        # Check 4: Every required join key is retained
        for edge in connecting_edges:
            f_tbl, f_col = edge["from_table"], edge["from_column"]
            t_tbl, t_col = edge["to_table"], edge["to_column"]
            if f_tbl in reduced_schema and f_col not in reduced_schema[f_tbl]:
                if f_tbl in schema and f_col in schema[f_tbl]:
                    reduced_schema[f_tbl][f_col] = schema[f_tbl][f_col]
                    warnings.append(f"Repaired missing join key '{f_tbl}.{f_col}'.")
                    repaired = True
                else:
                    errors.append(f"Join key '{f_tbl}.{f_col}' not found in database schema.")

            if t_tbl in reduced_schema and t_col not in reduced_schema[t_tbl]:
                if t_tbl in schema and t_col in schema[t_tbl]:
                    reduced_schema[t_tbl][t_col] = schema[t_tbl][t_col]
                    warnings.append(f"Repaired missing join key '{t_tbl}.{t_col}'.")
                    repaired = True
                else:
                    errors.append(f"Join key '{t_tbl}.{t_col}' not found in database schema.")

        # Check 5: Disconnected anchors
        if disconnected_anchors:
            warnings.append(f"Anchor tables disconnected in foreign key graph: {', '.join(disconnected_anchors)}.")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "repaired": repaired,
            "fallback_used": False,
            "errors": errors,
            "warnings": warnings,
            "join_paths": connecting_edges,
            "disconnected_anchors": disconnected_anchors,
        }

    def link_schema(
        self,
        question: str,
        schema: Dict[str, Dict[str, str]],
        relationships: Optional[List[Dict[str, str]]] = None,
        top_k_tables: Optional[int] = None,
        top_k_columns: Optional[int] = None,
        min_relevance_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates relevance scores for all tables and columns, and generates a reduced schema.
        Returns:
            {
                "reduced_schema": Dict[str, Dict[str, str]],
                "ranked_items": List[Dict[str, Any]],
                "selected_tables": List[str],
                "selected_columns": Dict[str, List[str]],
                "content_columns": Dict[str, List[str]],
                "structural_columns": Dict[str, List[str]],
                "validation": Dict[str, Any],
                "schema_reduction": {
                    "full_columns": int,
                    "reduced_columns": int,
                    "reduction_percentage": float
                },
                "linking_time_seconds": float
            }
        """
        k_tables = top_k_tables if top_k_tables is not None else self.default_top_k_tables
        k_columns = top_k_columns if top_k_columns is not None else self.default_top_k_columns
        min_score = min_relevance_score if min_relevance_score is not None else self.default_min_relevance_score
        start_time = time.time()
        self._ensure_model()

        if relationships is None:
            relationships = []

        total_full_columns = sum(len(cols) for cols in schema.values())

        if not schema or total_full_columns == 0:
            return {
                "reduced_schema": {},
                "ranked_items": [],
                "selected_tables": [],
                "selected_columns": {},
                "content_columns": {},
                "structural_columns": {},
                "validation": {
                    "is_valid": True,
                    "repaired": False,
                    "fallback_used": False,
                    "errors": [],
                    "warnings": [],
                    "join_paths": [],
                    "disconnected_anchors": []
                },
                "schema_reduction": {
                    "full_columns": 0,
                    "reduced_columns": 0,
                    "reduction_percentage": 0.0,
                },
                "linking_time_seconds": round(time.time() - start_time, 4),
            }

        # Step 1: Base scoring (Lexical + Semantic + Type Match) for all columns
        cols_list, col_embeddings = self._get_schema_embeddings(schema)
        q_emb = None
        if self.model is not None:
            try:
                q_emb = self.model.encode(question, normalize_embeddings=True, show_progress_bar=False)
            except Exception:
                q_emb = None

        if q_emb is not None and col_embeddings.shape[0] == len(cols_list):
            sims = np.dot(col_embeddings, q_emb)
            sem_scores_array = np.clip((sims + 1.0) / 2.0, 0.0, 1.0)
            sem_map = {cols_list[i]: float(sem_scores_array[i]) for i in range(len(cols_list))}
        else:
            sem_map = {}

        base_scores: Dict[Tuple[str, str], Dict[str, float]] = {}
        for table, columns in schema.items():
            for col, col_type in columns.items():
                lex_score = compute_lexical_similarity(question, table, col)
                sem_score = sem_map.get((table, col), 0.3)
                type_score = infer_type_match(question, col_type, col)

                raw_score = (
                    self.lexical_weight * lex_score
                    + self.semantic_weight * sem_score
                    + self.type_weight * type_score
                )

                base_scores[(table, col)] = {
                    "lexical": lex_score,
                    "semantic": sem_score,
                    "type": type_score,
                    "raw": raw_score,
                    "relationship": 0.0,
                    "final": raw_score,
                }

        # Step 2: Build foreign key graph
        graph = self._build_fk_graph(relationships)

        # Step 3: Compute ranked list of columns
        ranked_list: List[Dict[str, Any]] = []
        for (table, col), scores in base_scores.items():
            ranked_list.append({
                "table": table,
                "column": col,
                "data_type": schema[table][col],
                "score": round(scores["final"], 4),
                "lexical": round(scores["lexical"], 4),
                "semantic": round(scores["semantic"], 4),
                "type": round(scores["type"], 4),
                "relationship": round(scores["relationship"], 4),
            })

        # Sort all columns by score descending
        ranked_list.sort(key=lambda x: x["score"], reverse=True)

        # Step 3.1: Duplicate-Column Analysis and Anchor Disambiguation
        col_to_tables: Dict[str, List[str]] = {}
        for tbl, cols in schema.items():
            for c in cols.keys():
                col_to_tables.setdefault(c.lower(), []).append(tbl)

        q_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', question.lower()))
        q_stems = {get_stem(qt) for qt in q_tokens}
        top_col_score = ranked_list[0]["score"] if ranked_list else 1.0
        QUERY_ACTION_VERBS = {"return", "show", "list", "display", "find", "give", "tell", "select", "get"}
        GENERIC_ATTRIBUTE_WORDS = {
            "name", "names", "id", "ids", "code", "codes", "number", "numbers", 
            "no", "date", "dates", "time", "times", "year", "years", "type", "types", 
            "status", "value", "values", "total", "count", "amount", "record", "records",
            "description", "desc", "comment", "comments", "text", "info"
        }

        # Identify foreign key source/pointer columns
        fk_from_columns: Set[Tuple[str, str]] = set()
        fk_join_columns: Set[Tuple[str, str]] = set()
        for r in relationships:
            f_t, f_c = r.get("from_table"), r.get("from_column")
            t_t, t_c = r.get("to_table"), r.get("to_column")
            if f_t and f_c:
                fk_from_columns.add((f_t, f_c))
                fk_join_columns.add((f_t, f_c))
            if t_t and t_c:
                fk_join_columns.add((t_t, t_c))

        # Identify unambiguous anchor candidates:
        # 1. Tables whose name or name stem matches an explicit token in the question
        unambiguous_anchors: Set[str] = set()
        for tbl in schema.keys():
            tbl_tokens = set(split_identifier(tbl))
            for tt in tbl_tokens:
                tt_stem = get_stem(tt)
                if (tt in q_tokens or f"{tt}s" in q_tokens or f"{tt}es" in q_tokens or tt_stem in q_stems) and tt not in QUERY_ACTION_VERBS:
                    unambiguous_anchors.add(tbl)

        # 2. Tables containing unique columns with domain-specific lexical evidence
        for item in ranked_list:
            c_lower = item["column"].lower()
            t = item["table"]
            # Foreign key pointers referencing other tables do not make their parent an entity anchor
            if (t, item["column"]) in fk_from_columns:
                continue

            if len(col_to_tables.get(c_lower, [])) == 1:
                c_subtokens = set(split_identifier(c_lower)) - QUERY_ACTION_VERBS
                matched_c = {st for st in c_subtokens if st in q_tokens or get_stem(st) in q_stems}
                domain_matched = matched_c - GENERIC_ATTRIBUTE_WORDS
                has_domain_lex = bool(domain_matched)

                # If the only matching sub-token is generic (e.g. 'name' or 'id') and the table wasn't directly mentioned, skip
                if matched_c and not domain_matched and t not in unambiguous_anchors:
                    continue

                if has_domain_lex and item["score"] >= min_score:
                    unambiguous_anchors.add(t)

        # Disambiguate duplicate columns using graph proximity to unambiguous anchors
        ranked_list = self._disambiguate_duplicate_columns(ranked_list, graph, unambiguous_anchors, schema)

        # Step 3.2: Select essential content columns and anchor tables
        essential_columns: List[Dict[str, Any]] = []
        anchor_tables: Set[str] = set()
        resolved_duplicate_cols: Set[str] = set()

        # Seed anchor tables with verified unambiguous entity anchors
        for ua in unambiguous_anchors:
            anchor_tables.add(ua)

        for item in ranked_list:
            t, c, sc = item["table"], item["column"], item["score"]
            c_lower = c.lower()
            is_dup = len(col_to_tables.get(c_lower, [])) > 1

            if is_dup and c_lower in resolved_duplicate_cols and t not in anchor_tables:
                continue

            c_subtokens = set(split_identifier(c_lower)) - QUERY_ACTION_VERBS
            matched_c = {st for st in c_subtokens if st in q_tokens or get_stem(st) in q_stems}
            domain_matched = matched_c - GENERIC_ATTRIBUTE_WORDS
            has_domain_lex = bool(domain_matched)
            has_generic_lex = bool(matched_c)
            is_near_top = sc >= max(min_score, top_col_score - self.anchor_margin)

            # If table is already an anchor, admit columns matching generic or domain lexical cues
            if t in anchor_tables:
                if has_generic_lex or (is_near_top and sc >= min_score):
                    essential_columns.append(item)
                    if is_dup:
                        resolved_duplicate_cols.add(c_lower)
            elif has_domain_lex and sc >= min_score:
                # Table is not yet an anchor: only promote it if column has strong domain-specific lexical evidence
                # and is NOT merely a foreign key reference column
                if (t, c) not in fk_from_columns:
                    essential_columns.append(item)
                    anchor_tables.add(t)
                    if is_dup:
                        resolved_duplicate_cols.add(c_lower)

        if not anchor_tables and ranked_list:
            top_item = ranked_list[0]
            essential_columns.append(top_item)
            anchor_tables.add(top_item["table"])

        # Step 3.3: Table-Level Gating (direct evidence only, avoiding blind FK pollution)
        table_gating_scores: Dict[str, float] = {}

        for tbl in schema.keys():
            tbl_tokens = set(split_identifier(tbl))
            tbl_overlap = q_tokens.intersection(tbl_tokens)
            direct_tbl_score = (len(tbl_overlap) / len(tbl_tokens)) if tbl_overlap else 0.0

            for tt in tbl_tokens:
                tt_stem = get_stem(tt)
                if tt in q_tokens or f"{tt}s" in q_tokens or f"{tt}es" in q_tokens or tt_stem in q_stems:
                    direct_tbl_score = max(direct_tbl_score, 0.9)

            col_scores = [scores["final"] for (t, c), scores in base_scores.items() if t == tbl]
            max_col_sc = max(col_scores) if col_scores else 0.0
            top2_col_sc = (sum(sorted(col_scores, reverse=True)[:2]) / min(2, len(col_scores))) if col_scores else 0.0

            table_score = 0.40 * direct_tbl_score + 0.35 * max_col_sc + 0.25 * top2_col_sc
            table_gating_scores[tbl] = round(table_score, 4)

        max_table_score = max(table_gating_scores.values()) if table_gating_scores else 1.0
        gating_margin = float(os.getenv("TABLE_GATING_MARGIN", 0.25))
        gated_tables: Set[str] = set()

        for tbl, t_score in table_gating_scores.items():
            if t_score >= max(0.40, max_table_score - gating_margin):
                gated_tables.add(tbl)

        # Invariant: Anchor tables are unconditionally protected and admitted
        candidate_tables: Set[str] = set(anchor_tables).union(gated_tables)

        if not candidate_tables and table_gating_scores:
            best_tbl = max(table_gating_scores, key=table_gating_scores.get)
            candidate_tables.add(best_tbl)

        # Step 4: Content Column Selection (subject to top_k_columns budget)
        fk_join_columns: Set[Tuple[str, str]] = set()
        for r in relationships:
            f_t, f_c = r.get("from_table"), r.get("from_column")
            t_t, t_c = r.get("to_table"), r.get("to_column")
            if f_t and f_c:
                fk_join_columns.add((f_t, f_c))
            if t_t and t_c:
                fk_join_columns.add((t_t, t_c))

        content_columns_by_table: Dict[str, List[str]] = {}
        chosen_tables: Set[str] = set(anchor_tables)
        total_content_cols = 0

        # Compute max column score per candidate table for adaptive column pruning
        table_top_col_score: Dict[str, float] = {}
        for item in ranked_list:
            t, sc = item["table"], item["score"]
            if t in candidate_tables:
                table_top_col_score[t] = max(table_top_col_score.get(t, 0.0), sc)

        col_margin = float(os.getenv("COLUMN_GATING_MARGIN", 0.25))

        for item in ranked_list:
            t, c, sc = item["table"], item["column"], item["score"]

            if t not in candidate_tables:
                continue

            top_sc_in_t = table_top_col_score.get(t, 1.0)
            col_threshold = max(0.40, top_sc_in_t - col_margin)

            current_cols_for_t = len(content_columns_by_table.get(t, []))
            is_anchor = t in anchor_tables
            is_small_table = len(schema.get(t, {})) <= 5
            has_high_sem = item.get("semantic", 0.0) >= 0.70

            if sc < col_threshold and current_cols_for_t >= 2:
                if not (is_anchor and (is_small_table or has_high_sem) and total_content_cols < k_columns):
                    continue

            # Check if this column is explicitly mentioned or a join key
            c_tokens = set(split_identifier(c))
            is_explicit_mention = bool(c_tokens.intersection(q_tokens) or any(get_stem(ct) in q_stems for ct in c_tokens))
            is_join_key = (t, c) in fk_join_columns

            # Non-anchor tables are only admitted if column score is genuinely strong and relevant
            if t not in chosen_tables:
                if len(chosen_tables) >= k_tables:
                    continue
                if sc < max(0.50, top_col_score - self.anchor_margin) and not is_explicit_mention:
                    continue

            if is_join_key and not is_explicit_mention:
                continue

            if total_content_cols >= k_columns:
                continue

            chosen_tables.add(t)
            if t not in content_columns_by_table:
                content_columns_by_table[t] = []
            if c not in content_columns_by_table[t]:
                content_columns_by_table[t].append(c)
                total_content_cols += 1

        # Fallback to anchor tables if none selected
        if not chosen_tables:
            chosen_tables = set(anchor_tables)

        # Key descriptor column retention for entities (within content budget)
        has_entity_cue = bool(re.search(r'\b(named|called|of|for|who|is|where|in)\b', question, re.IGNORECASE)) or any(w[0].isupper() for w in question.split() if len(w) > 1)
        if has_entity_cue:
            for t in chosen_tables:
                if t in schema:
                    for col in schema[t]:
                        col_l = col.lower()
                        if "name" in col_l or "title" in col_l:
                            if t not in content_columns_by_table and total_content_cols < k_columns:
                                content_columns_by_table[t] = [col]
                                total_content_cols += 1
                            elif t in content_columns_by_table and col not in content_columns_by_table[t] and total_content_cols < k_columns:
                                content_columns_by_table[t].append(col)
                                total_content_cols += 1

        # Step 5: Join-Path Completion (Connect anchor tables using shortest path)
        # Structural columns do not consume the content column budget!
        target_anchors = list(anchor_tables) if anchor_tables else list(chosen_tables)
        connection_res = self._connect_anchor_tables(graph, target_anchors, schema)
        intermediate_tables = connection_res["intermediate_tables"]
        connecting_edges = connection_res["connecting_edges"]
        structural_columns_by_table: Dict[str, List[str]] = {
            t: sorted(list(cols)) for t, cols in connection_res["structural_columns"].items()
        }

        # Add intermediate tables to chosen tables
        chosen_tables.update(intermediate_tables)

        # Step 6: Construct Reduced Schema representation
        selected_columns_by_table: Dict[str, List[str]] = {}
        reduced_schema: Dict[str, Dict[str, str]] = {}

        for t in chosen_tables:
            if t not in schema:
                continue
            cols_set = set(content_columns_by_table.get(t, [])).union(set(structural_columns_by_table.get(t, [])))
            if not cols_set:
                cols_set = set(schema[t].keys())

            ordered_cols = [c for c in schema[t].keys() if c in cols_set]
            selected_columns_by_table[t] = ordered_cols
            reduced_schema[t] = {c: schema[t][c] for c in ordered_cols}

        # Step 7: Reduced-Schema Validation & Deterministic Repair
        validation_info = self._validate_and_repair_schema(
            schema=schema,
            reduced_schema=reduced_schema,
            essential_columns=essential_columns,
            connecting_edges=connecting_edges,
            intermediate_tables=intermediate_tables,
            disconnected_anchors=connection_res["disconnected_anchors"]
        )

        # Synchronize selected_columns_by_table with repaired reduced_schema
        for t, col_map in reduced_schema.items():
            selected_columns_by_table[t] = list(col_map.keys())

        # Fallback safeguard: if reduced schema is empty, take highest-scoring table's columns
        if not reduced_schema and ranked_list:
            top_t = ranked_list[0]["table"]
            reduced_schema[top_t] = schema[top_t]
            selected_columns_by_table[top_t] = list(schema[top_t].keys())
            validation_info["fallback_used"] = True
            validation_info["is_valid"] = True
            validation_info["warnings"].append("Fallback activated: took entire schema of highest scoring table.")

        reduced_col_count = sum(len(cols) for cols in reduced_schema.values())
        reduction_pct = (
            ((total_full_columns - reduced_col_count) / total_full_columns) * 100.0
            if total_full_columns > 0
            else 0.0
        )

        linking_time = time.time() - start_time
        linking_throughput = round(total_full_columns / max(0.0001, linking_time), 1)

        return {
            "reduced_schema": reduced_schema,
            "ranked_items": ranked_list,
            "selected_tables": list(reduced_schema.keys()),
            "selected_columns": selected_columns_by_table,
            "content_columns": content_columns_by_table,
            "structural_columns": structural_columns_by_table,
            "validation": validation_info,
            "schema_reduction": {
                "full_columns": total_full_columns,
                "reduced_columns": reduced_col_count,
                "reduction_percentage": round(reduction_pct, 2),
                "linking_throughput_cps": linking_throughput,
            },
            "linking_time_seconds": round(linking_time, 4),
            "linking_throughput_cps": linking_throughput,
        }
