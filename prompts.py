from typing import Any, Dict, List, Optional


def format_schema_for_prompt(
    schema: Dict[str, Dict[str, str]],
    relationships: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Formats the schema dictionary into a clean string representation for the LLM.
    Example:
    Table: Student
      - StudentID (INTEGER)
      - StudentName (TEXT)
      - Marks (REAL)
    Relationships:
      - Enrollment.StudentID -> Student.StudentID
    """
    lines: List[str] = []
    if not schema:
        lines.append("(Database currently has no tables. User may create tables using CREATE TABLE statements.)")
    else:
        for table_name, columns in schema.items():
            lines.append(f"Table: {table_name}")
            for col_name, col_type in columns.items():
                lines.append(f"  - {col_name} ({col_type})")
            lines.append("")

    if relationships:
        # Filter relationships to only include tables present in this schema
        active_tables = set(schema.keys())
        active_rels = [
            rel for rel in relationships
            if rel.get("from_table") in active_tables and rel.get("to_table") in active_tables
        ]
        if active_rels:
            lines.append("Relationships (Foreign Keys):")
            for rel in active_rels:
                lines.append(f"  - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
            lines.append("")

    return "\n".join(lines).strip()


def build_baseline_prompt(
    question: str,
    full_schema: Dict[str, Dict[str, str]],
    relationships: Optional[List[Dict[str, str]]] = None,
    read_only: bool = False,
) -> str:
    """
    Constructs the prompt for the Baseline system sending the FULL database schema.
    """
    schema_str = format_schema_for_prompt(full_schema, relationships)
    
    rules = [
        "1. Return ONLY the raw SQL query. Do not wrap in explanation or markdown commentary.",
        "2. Use valid SQLite syntax and data types (INTEGER, REAL, TEXT, BLOB, NULL).",
        "3. When querying existing tables, use only tables and columns from the Schema below.",
        "4. If the user asks to CREATE a table, generate a valid CREATE TABLE statement.",
        "5. If the user asks to INSERT, UPDATE, or DELETE data, generate valid DML statements.",
        "6. If the user asks to query/search data, generate a valid SELECT query with proper JOINs where needed.",
        "7. When comparing against percentage, rate, or score attributes (e.g., Attendance, Marks, Salary), use whole number values (e.g. 75 instead of 0.75) unless decimals are explicitly requested.",
    ]
    if read_only:
        rules.append("8. READ-ONLY MODE: Only SELECT queries are permitted.")

    rules_str = "\n".join(rules)

    prompt = f"""You are an expert SQLite Database & SQL system.

Convert the user's natural-language instruction or question into executable SQLite SQL statement(s).

Rules:
{rules_str}

DATABASE SCHEMA:
{schema_str}

User Instruction/Question:
{question}

SQL Statement:"""
    return prompt.strip()


def build_proposed_prompt(
    question: str,
    reduced_schema: Dict[str, Dict[str, str]],
    relationships: Optional[List[Dict[str, str]]] = None,
    read_only: bool = False,
) -> str:
    """
    Constructs the prompt for the Proposed system sending ONLY the REDUCED database schema.
    """
    schema_str = format_schema_for_prompt(reduced_schema, relationships)
    
    rules = [
        "1. Return ONLY the raw SQL query. Do not wrap in explanation or markdown commentary.",
        "2. Use valid SQLite syntax and data types (INTEGER, REAL, TEXT, BLOB, NULL).",
        "3. When querying existing tables, use only tables and columns from the REDUCED Schema below.",
        "4. If the user asks to CREATE a table, generate a valid CREATE TABLE statement.",
        "5. If the user asks to INSERT, UPDATE, or DELETE data, generate valid DML statements.",
        "6. If the user asks to query/search data, generate a valid SELECT query with proper JOINs where needed.",
        "7. When comparing against percentage, rate, or score attributes (e.g., Attendance, Marks, Salary), use whole number values (e.g. 75 instead of 0.75) unless decimals are explicitly requested.",
    ]
    if read_only:
        rules.append("8. READ-ONLY MODE: Only SELECT queries are permitted.")

    rules_str = "\n".join(rules)

    prompt = f"""You are an expert SQLite Database & SQL system.

Convert the user's natural-language instruction or question into executable SQLite SQL statement(s).

Rules:
{rules_str}

REDUCED DATABASE SCHEMA:
{schema_str}

User Instruction/Question:
{question}

SQL Statement:"""
    return prompt.strip()
