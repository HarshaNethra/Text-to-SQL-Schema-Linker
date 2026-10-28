import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "college.db")

# Sample records designed for realistic queries
STUDENTS_DATA = [
    (101, "Rahul Sharma", "CSE", 20, 88.5, 92.0),
    (102, "Priya Patel", "CSE", 21, 72.0, 85.5),
    (103, "Amit Verma", "ECE", 22, 65.0, 74.0),
    (104, "Sneha Reddy", "CSE", 20, 94.0, 96.5),
    (105, "Rohan Gupta", "MECH", 21, 78.5, 68.0),
    (106, "Ananya Iyer", "ECE", 20, 91.0, 89.0),
    (107, "Vikram Singh", "CIVIL", 23, 62.5, 58.0),
    (108, "Pooja Nair", "CSE", 21, 84.0, 81.5),
    (109, "Karan Malhotra", "MECH", 22, 70.0, 76.0),
    (110, "Divya Joshi", "CIVIL", 20, 89.0, 88.0),
    (111, "Siddharth Rao", "CSE", 21, 68.0, 79.5),
    (112, "Neha Kapoor", "ECE", 22, 95.5, 94.0),
    (113, "Manish Das", "MECH", 20, 74.0, 71.0),
    (114, "Kavita Menon", "CSE", 21, 80.0, 83.5),
    (115, "Arjun Saxena", "CIVIL", 22, 69.5, 64.0),
]

COURSES_DATA = [
    ("CS101", "Introduction to Programming", 4, "CSE"),
    ("CS201", "Data Structures and Algorithms", 4, "CSE"),
    ("CS301", "Database Management Systems", 4, "CSE"),
    ("CS401", "Artificial Intelligence", 3, "CSE"),
    ("EC101", "Digital Electronics", 3, "ECE"),
    ("EC201", "Signals and Systems", 4, "ECE"),
    ("ME101", "Engineering Thermodynamics", 4, "MECH"),
    ("ME201", "Fluid Mechanics", 3, "MECH"),
    ("CE101", "Structural Analysis", 4, "CIVIL"),
    ("CE201", "Surveying and Geomatics", 3, "CIVIL"),
]

ENROLLMENTS_DATA = [
    (101, "CS101", "A"),
    (101, "CS201", "A"),
    (101, "CS301", "A+"),
    (102, "CS101", "B"),
    (102, "CS301", "B+"),
    (103, "EC101", "B"),
    (103, "EC201", "C"),
    (104, "CS201", "A+"),
    (104, "CS301", "A+"),
    (104, "CS401", "A"),
    (105, "ME101", "B"),
    (105, "ME201", "C+"),
    (106, "EC101", "A"),
    (106, "EC201", "A"),
    (107, "CE101", "C"),
    (108, "CS101", "A"),
    (108, "CS301", "A"),
    (109, "ME101", "B+"),
    (110, "CE101", "A"),
    (110, "CE201", "A"),
    (111, "CS301", "B"),
    (112, "EC101", "A+"),
    (112, "EC201", "A"),
    (113, "ME201", "B"),
    (114, "CS301", "B+"),
]

FACULTY_DATA = [
    (1, "Dr. Arvind Swaminathan", "CSE", 95000.0),
    (2, "Dr. Meenakshi Sundaram", "CSE", 105000.0),
    (3, "Prof. Rajesh Deshmukh", "ECE", 82000.0),
    (4, "Dr. Sunita Kulkarni", "ECE", 88000.0),
    (5, "Prof. Harish Chandra", "MECH", 75000.0),
    (6, "Dr. Rameshwar Pandey", "MECH", 91000.0),
    (7, "Prof. Geeta Bhatnagar", "CIVIL", 78000.0),
    (8, "Dr. Anil Choudhary", "CIVIL", 86000.0),
]


def initialize_database(
    db_path: str = DEFAULT_DB_PATH,
    load_preset: bool = False,
    force_recreate: bool = False
) -> None:
    """Creates the SQLite database. If load_preset is True, populates with college sample data."""
    if os.path.exists(db_path) and not force_recreate:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    if load_preset or force_recreate:
        cursor.executescript("""
            DROP TABLE IF EXISTS Enrollment;
            DROP TABLE IF EXISTS Student;
            DROP TABLE IF EXISTS Course;
            DROP TABLE IF EXISTS Faculty;

            CREATE TABLE Student (
                StudentID INTEGER PRIMARY KEY,
                StudentName TEXT NOT NULL,
                Department TEXT NOT NULL,
                Age INTEGER NOT NULL,
                Attendance REAL NOT NULL,
                Marks REAL NOT NULL
            );

            CREATE TABLE Course (
                CourseID TEXT PRIMARY KEY,
                CourseName TEXT NOT NULL,
                Credits INTEGER NOT NULL,
                Department TEXT NOT NULL
            );

            CREATE TABLE Enrollment (
                StudentID INTEGER NOT NULL,
                CourseID TEXT NOT NULL,
                Grade TEXT NOT NULL,
                PRIMARY KEY (StudentID, CourseID),
                FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE,
                FOREIGN KEY (CourseID) REFERENCES Course(CourseID) ON DELETE CASCADE
            );

            CREATE TABLE Faculty (
                FacultyID INTEGER PRIMARY KEY,
                FacultyName TEXT NOT NULL,
                Department TEXT NOT NULL,
                Salary REAL NOT NULL
            );
        """)

        cursor.executemany(
            "INSERT INTO Student (StudentID, StudentName, Department, Age, Attendance, Marks) VALUES (?, ?, ?, ?, ?, ?)",
            STUDENTS_DATA,
        )
        cursor.executemany(
            "INSERT INTO Course (CourseID, CourseName, Credits, Department) VALUES (?, ?, ?, ?)",
            COURSES_DATA,
        )
        cursor.executemany(
            "INSERT INTO Enrollment (StudentID, CourseID, Grade) VALUES (?, ?, ?)",
            ENROLLMENTS_DATA,
        )
        cursor.executemany(
            "INSERT INTO Faculty (FacultyID, FacultyName, Department, Salary) VALUES (?, ?, ?, ?)",
            FACULTY_DATA,
        )

    conn.commit()
    conn.close()


def load_college_preset(db_path: str = DEFAULT_DB_PATH, force_recreate: bool = True) -> None:
    """Explicitly loads the college preset dataset into the specified database."""
    initialize_database(db_path, load_preset=True, force_recreate=force_recreate)


def clear_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Drops all user tables from the database."""
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
    conn.commit()
    conn.close()


def list_tables(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """Returns a list of all user table names."""
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


_SCHEMA_CACHE: Dict[Tuple[str, float], Dict[str, Dict[str, str]]] = {}
_RELATIONSHIPS_CACHE: Dict[Tuple[str, float], List[Dict[str, str]]] = {}


def get_schema(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Dict[str, str]]:
    """
    Extracts the full database schema with caching based on file modification time.
    Returns:
        {
            "TableName": {
                "ColumnName": "DATA_TYPE",
                ...
            }
        }
    """
    if not os.path.exists(db_path):
        initialize_database(db_path, load_preset=False)

    mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0.0
    cache_key = (os.path.abspath(db_path), mtime)
    if cache_key in _SCHEMA_CACHE:
        # Return a copy to prevent in-place mutation
        return {tbl: dict(cols) for tbl, cols in _SCHEMA_CACHE[cache_key].items()}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    schema: Dict[str, Dict[str, str]] = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        schema[table] = {col[1]: (col[2].upper() if col[2] else "TEXT") for col in columns}

    conn.close()
    _SCHEMA_CACHE[cache_key] = schema
    return {tbl: dict(cols) for tbl, cols in schema.items()}


def get_relationships(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, str]]:
    """
    Extracts foreign key relationships across tables with caching.
    Returns:
        [
            {
                "from_table": "Enrollment",
                "from_column": "StudentID",
                "to_table": "Student",
                "to_column": "StudentID"
            }, ...
        ]
    """
    if not os.path.exists(db_path):
        initialize_database(db_path, load_preset=False)

    mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0.0
    cache_key = (os.path.abspath(db_path), mtime)
    if cache_key in _RELATIONSHIPS_CACHE:
        return [dict(r) for r in _RELATIONSHIPS_CACHE[cache_key]]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    relationships: List[Dict[str, str]] = []
    for table in tables:
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        fks = cursor.fetchall()
        for fk in fks:
            to_table = fk[2]
            from_col = fk[3]
            to_col = fk[4]
            relationships.append({
                "from_table": table,
                "from_column": from_col,
                "to_table": to_table,
                "to_column": to_col,
            })

    conn.close()
    _RELATIONSHIPS_CACHE[cache_key] = relationships
    return [dict(r) for r in relationships]


def validate_sql_safety(
    sql: str,
    allow_modifications: bool = True,
    read_only: bool = False
) -> Tuple[bool, str]:
    """
    Validates SQL safety.
    - If read_only is True: Only allows single SELECT / WITH queries.
    - If allow_modifications is True: Allows CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, REPLACE, SELECT.
    - Always blocks dangerous SQLite system hijacking commands (ATTACH, DETACH, EXEC, PRAGMA).
    """
    cleaned_sql = sql.strip().rstrip(";")
    if not cleaned_sql:
        return False, "Empty SQL query."

    # Remove comments & extra whitespaces
    sanitized = re.sub(r"--.*", "", cleaned_sql)
    sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL).strip()

    # System-level dangerous operations always blocked for security
    hard_forbidden = [
        r"\bATTACH\b",
        r"\bDETACH\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
        r"\bVACUUM\b",
        r"\bPRAGMA\b",
    ]
    for pattern in hard_forbidden:
        if re.search(pattern, sanitized, re.IGNORECASE):
            matched = pattern.replace(r"\b", "")
            return False, f"SQL rejected: forbidden administrative command ({matched})."

    if read_only:
        # Reject data-modifying SQL keywords in read-only mode
        forbidden_keywords = [
            r"\bINSERT\b",
            r"\bUPDATE\b",
            r"\bDELETE\b",
            r"\bDROP\b",
            r"\bALTER\b",
            r"\bCREATE\b",
            r"\bTRUNCATE\b",
            r"\bREPLACE\b",
        ]
        for pattern in forbidden_keywords:
            if re.search(pattern, sanitized, re.IGNORECASE):
                matched = pattern.replace(r"\b", "")
                return False, f"SQL rejected: non-read-only statement ({matched}) in read-only mode."

        if not re.match(r"^(SELECT|WITH)\b", sanitized, re.IGNORECASE):
            return False, "SQL rejected: Only SELECT queries are permitted in read-only mode."

    else:
        # Must start with a recognized valid SQL statement
        allowed_starts = r"^(SELECT|WITH|CREATE|INSERT|UPDATE|DELETE|DROP|ALTER|REPLACE)\b"
        if not re.match(allowed_starts, sanitized, re.IGNORECASE):
            return False, "SQL rejected: Statement must start with SELECT, CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, or REPLACE."

    return True, "OK"


def execute_query(
    sql: str,
    db_path: str = DEFAULT_DB_PATH,
    allow_modifications: bool = True,
    read_only: bool = False
) -> Dict[str, Any]:
    """
    Executes a SQL query safely on the SQLite database.
    Supports SELECT, CREATE, INSERT, UPDATE, DELETE, DROP, ALTER, etc.
    Returns:
        {
            "success": bool,
            "columns": List[str],
            "rows": List[Tuple[Any, ...]],
            "rowcount": int,
            "message": Optional[str],
            "error": Optional[str]
        }
    """
    if not os.path.exists(db_path):
        initialize_database(db_path, load_preset=False)

    is_safe, reason = validate_sql_safety(sql, allow_modifications=allow_modifications, read_only=read_only)
    if not is_safe:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "rowcount": 0,
            "message": None,
            "error": reason,
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Handle potential multi-statement scripts (e.g., multiple INSERTs or table creations)
        statements = [s.strip() for s in sql.split(";") if s.strip()]

        last_columns: List[str] = []
        last_rows: List[Tuple[Any, ...]] = []
        total_rowcount = 0
        statement_type = "QUERY"

        for stmt in statements:
            # Check individual safety
            safe_stmt, stmt_reason = validate_sql_safety(stmt, allow_modifications=allow_modifications, read_only=read_only)
            if not safe_stmt:
                conn.close()
                return {
                    "success": False,
                    "columns": [],
                    "rows": [],
                    "rowcount": 0,
                    "message": None,
                    "error": stmt_reason,
                }

            cursor.execute(stmt)
            if cursor.description:
                # SELECT / WITH statement returning data
                last_columns = [desc[0] for desc in cursor.description]
                last_rows = cursor.fetchall()
                total_rowcount = len(last_rows)
                statement_type = "SELECT"
            else:
                # DDL / DML statement
                total_rowcount += max(0, cursor.rowcount)
                first_word = stmt.strip().split()[0].upper()
                statement_type = first_word

        conn.commit()
        conn.close()

        if statement_type == "SELECT":
            msg = f"{len(last_rows)} row(s) returned."
        elif statement_type == "CREATE":
            msg = "Table created successfully."
        elif statement_type == "INSERT":
            msg = f"Inserted successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "UPDATE":
            msg = f"Updated successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "DELETE":
            msg = f"Deleted successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "DROP":
            msg = "Table dropped successfully."
        else:
            msg = f"Executed statement ({statement_type}) successfully."

        return {
            "success": True,
            "columns": last_columns,
            "rows": last_rows,
            "rowcount": total_rowcount,
            "message": msg,
            "error": None,
        }
    except sqlite3.Error as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "rowcount": 0,
            "message": None,
            "error": f"SQLite execution error: {str(e)}",
        }


def execute_sandboxed_query(
    sql: str,
    db_path: str = DEFAULT_DB_PATH,
    allow_modifications: bool = True,
    read_only: bool = False
) -> Dict[str, Any]:
    """
    Executes a SQL query in an isolated in-memory sandbox cloned from db_path.
    Guarantees no state changes to db_path on disk, ensuring 100% independent testing.
    """
    if not os.path.exists(db_path):
        initialize_database(db_path, load_preset=False)

    is_safe, reason = validate_sql_safety(sql, allow_modifications=allow_modifications, read_only=read_only)
    if not is_safe:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "rowcount": 0,
            "message": None,
            "error": reason,
        }

    try:
        disk_conn = sqlite3.connect(db_path)
        mem_conn = sqlite3.connect(":memory:")
        disk_conn.backup(mem_conn)
        disk_conn.close()

        mem_conn.execute("PRAGMA foreign_keys = ON;")
        cursor = mem_conn.cursor()

        statements = [s.strip() for s in sql.split(";") if s.strip()]
        last_columns: List[str] = []
        last_rows: List[Tuple[Any, ...]] = []
        total_rowcount = 0
        statement_type = "QUERY"

        for stmt in statements:
            safe_stmt, stmt_reason = validate_sql_safety(stmt, allow_modifications=allow_modifications, read_only=read_only)
            if not safe_stmt:
                mem_conn.close()
                return {
                    "success": False,
                    "columns": [],
                    "rows": [],
                    "rowcount": 0,
                    "message": None,
                    "error": stmt_reason,
                }

            cursor.execute(stmt)
            if cursor.description:
                last_columns = [desc[0] for desc in cursor.description]
                last_rows = cursor.fetchall()
                total_rowcount = len(last_rows)
                statement_type = "SELECT"
            else:
                total_rowcount += cursor.rowcount if cursor.rowcount > 0 else 0
                first_word = stmt.strip().split()[0].upper()
                statement_type = first_word

        mem_conn.commit()
        mem_conn.close()

        if statement_type == "SELECT":
            msg = f"{len(last_rows)} row(s) returned."
        elif statement_type == "CREATE":
            msg = "Table created successfully."
        elif statement_type == "INSERT":
            msg = f"Inserted successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "UPDATE":
            msg = f"Updated successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "DELETE":
            msg = f"Deleted successfully. ({total_rowcount} row(s) affected)"
        elif statement_type == "DROP":
            msg = "Table dropped successfully."
        else:
            msg = f"Executed statement ({statement_type}) successfully."

        return {
            "success": True,
            "columns": last_columns,
            "rows": last_rows,
            "rowcount": total_rowcount,
            "message": msg,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "rowcount": 0,
            "message": None,
            "error": f"SQLite execution error: {str(e)}",
        }


if __name__ == "__main__":
    load_college_preset(force_recreate=True)
    schema = get_schema()
    print("Extracted Schema:", schema)
    rels = get_relationships()
    print("Extracted Relationships:", rels)
    res = execute_query("SELECT StudentName, Marks FROM Student WHERE Department='CSE' AND Marks > 80;")
    print("Sample Query Execution:", res)
