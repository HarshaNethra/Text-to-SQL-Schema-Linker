# PRD — AI-Based Natural Language to SQL Query System
## Final Research-Grade Project PRD

**Status:** Active — implementation and completion  
**Primary objective:** Build and experimentally evaluate an AI-based Natural Language-to-SQL system whose main contribution is intelligent schema linking and schema reduction.

---

# 1. Project Definition

## 1.1 Project Title

**AI-Based Natural Language to SQL Query System**

## 1.2 Core Idea

Normally, a user needs to know SQL to retrieve information from a relational database.

Example:

> "Show all CSE students who scored above 80 marks."

The proposed system allows a user to ask the same question in natural language. An LLM converts the question into SQL, the DBMS executes the generated SQL, and the system displays the result.

The research contribution is **not simply Natural Language → SQL**.

The central research problem is:

> **Can an intelligent schema-linking and schema-reduction mechanism reduce the amount of database schema supplied to an LLM, thereby reducing prompt/token usage, inference latency and API cost while maintaining or improving SQL/result accuracy?**

The system therefore evaluates two pipelines:

```text
BASELINE

Natural Language Question
        ↓
Full Database Schema
        ↓
LLM / Text-to-SQL
        ↓
Generated SQL
        ↓
SQLite Database
        ↓
Query Result
```

```text
PROPOSED SYSTEM

Natural Language Question
        ↓
Schema Linking
        ↓
Relevant Tables + Columns
        ↓
Reduced Schema
        ↓
LLM / Text-to-SQL
        ↓
Generated SQL
        ↓
SQLite Database
        ↓
Query Result
```

The final project must demonstrate the difference between these two systems experimentally.

---

# 2. Research Objective

The project investigates whether schema reduction can improve the efficiency of LLM-based Text-to-SQL generation.

For a user question `q`, instead of giving the LLM the complete schema, the system calculates the relevance of schema elements and supplies only the relevant portion.

The intended relevance model is:

```text
Score(c,q) =
    LexicalSimilarity
    + SemanticSimilarity
    + TypeMatch
    + RelationshipScore
```

The four components are:

1. Lexical similarity
2. Semantic similarity
3. Type matching
4. Relationship score

The system must make these components independently inspectable and configurable.

The research must ultimately evaluate:

- Schema size
- Prompt/token size
- Schema-linking precision
- Schema-linking recall
- Schema-linking/local processing time
- LLM latency
- Total response time
- API cost where measurable
- SQL execution success
- SQL correctness/result correctness
- Baseline vs proposed performance

---

# 3. Non-Negotiable Final Outcome

The final implementation is considered complete only when the following comparison can be demonstrated:

```text
                 SAME QUESTIONS
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
        BASELINE             PROPOSED
             │                   │
       Full Schema         Schema Linking
             │                   │
             ↓                   ↓
       LLM / SQL             Reduced Schema
             │                   │
             ↓                   ↓
       SQL + Result          SQL + Result
             │                   │
             └─────────┬─────────┘
                       ↓
                 COMPARISON
                       ↓
       Accuracy / Tokens / Latency / Cost
```

The project must not stop at "the system generates SQL."

It must produce evidence answering:

> **Does schema reduction actually help, and what accuracy/efficiency trade-off does it introduce?**

---

# 4. Mandatory First Step — Existing Codebase Verification

Before modifying or creating implementation files, **Antigravity must inspect the actual repository/codebase**.

Do not assume that the current code matches this PRD.

Do not recreate modules that already exist.

Do not delete working functionality merely because it differs from the structure suggested in this PRD.

## 4.1 Antigravity Verification Objective

Antigravity must determine:

1. What is already implemented.
2. What is partially implemented.
3. What is implemented incorrectly.
4. What exists but does not satisfy the research requirements.
5. What is completely missing.
6. What tests already exist.
7. What dependencies are already installed.
8. How the current implementation differs from this PRD.
9. Which existing code can be reused.
10. Which code must be modified or replaced.

## 4.2 Required Verification Procedure

Antigravity must:

### Step 1 — Inspect the entire repository

Inspect:

- All source files
- All configuration files
- `requirements.txt`
- `.env.example` / environment configuration
- README
- Tests
- Database files
- Prompt files
- Utility modules
- Existing documentation
- Existing generated/evaluation outputs

Do not limit inspection to filenames.

Read the relevant source code.

### Step 2 — Build an implementation inventory

Produce an internal table:

| Requirement | File(s) | Status | Evidence | Action |
|---|---|---|---|---|
| SQLite database | ... | Complete/Partial/Missing | ... | ... |
| Schema extraction | ... | ... | ... | ... |
| Foreign-key extraction | ... | ... | ... | ... |
| LLM integration | ... | ... | ... | ... |
| Baseline pipeline | ... | ... | ... | ... |
| Lexical similarity | ... | ... | ... | ... |
| Semantic similarity | ... | ... | ... | ... |
| Type matching | ... | ... | ... | ... |
| Relationship scoring | ... | ... | ... | ... |
| Schema ranking | ... | ... | ... | ... |
| Reduced schema generation | ... | ... | ... | ... |
| SQL safety | ... | ... | ... | ... |
| Evaluation | ... | ... | ... | ... |
| Metrics | ... | ... | ... | ... |
| Tests | ... | ... | ... | ... |

### Step 3 — Run the existing project

Run the appropriate project entry point.

Verify:

- Does it start?
- Does database initialization work?
- Can a question be entered?
- Does an LLM request work?
- Is SQL generated?
- Is SQL executed?
- Are results displayed?

Record actual failures rather than guessing.

### Step 4 — Run existing tests

Run every existing automated test.

Record:

- Passing tests
- Failing tests
- Errors
- Missing test coverage

### Step 5 — Inspect implementation quality

Check for:

- Hard-coded values
- Hard-coded schema
- Hard-coded SQL
- Hard-coded API keys
- Unsafe SQL execution
- Incorrect schema extraction
- Broken foreign-key handling
- Incorrect scoring formulas
- Unused dependencies
- Dead code
- Duplicate implementations
- Silent exception handling
- Incorrect latency measurement
- Incorrect token measurement
- Incorrect accuracy claims

### Step 6 — Compare against this PRD

After inspection, classify every requirement as:

```text
COMPLETE
PARTIAL
INCORRECT
MISSING
NOT APPLICABLE
```

### Step 7 — Only then create the implementation plan

The implementation plan must be based on the actual codebase.

**Do not blindly follow the proposed file structure if an existing structure already performs the same responsibility correctly.**

Reuse working code.

Modify only where necessary.

---

# 5. Scope

## 5.1 In Scope

The final system must include:

- Natural-language question input
- Relational SQLite database
- Automatic schema extraction
- Foreign-key relationship extraction
- Baseline full-schema Text-to-SQL
- Schema-linking algorithm
- Lexical similarity
- Semantic similarity
- Type matching
- Relationship scoring
- Schema ranking
- Reduced-schema construction
- Proposed Text-to-SQL
- SQL safety validation
- SQL execution
- Query results
- Baseline/proposed comparison
- Evaluation dataset
- Quantitative metrics
- Automated tests
- Reproducible experiment output
- Documentation

## 5.2 Explicitly Out of Scope

Do not waste implementation time on:

- React
- Vue
- Angular
- HTML/CSS frontend
- Web application
- Dashboard
- Authentication
- User accounts
- WebSockets
- Docker
- Microservices
- Production infrastructure
- LLM training
- Fine-tuning
- RAT-SQL reproduction
- Large external datasets
- Complex deployment
- Unnecessary abstractions

A CLI/research prototype is sufficient.

---

# 6. Technology Stack

Preferred stack:

```text
Python 3.11+
SQLite
LLM API
sentence-transformers
scikit-learn
Python standard library
```

The LLM integration must remain behind a simple interface so the provider/model can be changed without rewriting the system.

API credentials must come from environment variables.

Never hard-code API keys.

---

# 7. Database

Use:

```text
college.db
```

The database must be automatically created if it does not exist.

## 7.1 Student

```text
StudentID
StudentName
Department
Age
Attendance
Marks
```

## 7.2 Course

```text
CourseID
CourseName
Credits
Department
```

## 7.3 Enrollment

```text
StudentID
CourseID
Grade
```

## 7.4 Faculty

```text
FacultyID
FacultyName
Department
Salary
```

Use approximately 10–20 realistic records per table.

## 7.5 Relationships

```text
Enrollment.StudentID → Student.StudentID
Enrollment.CourseID → Course.CourseID
```

The implementation must extract these relationships programmatically rather than relying on hard-coded relationship knowledge.

---

# 8. Database Layer

The database layer must support:

1. Database creation
2. Table creation
3. Sample-data insertion
4. Schema extraction
5. Foreign-key extraction
6. Read-only SQL execution
7. Query-result retrieval

A schema representation should be easy to consume by the schema linker and prompt builder.

Example:

```python
{
    "Student": {
        "StudentID": "INTEGER",
        "StudentName": "TEXT",
        "Department": "TEXT",
        "Age": "INTEGER",
        "Attendance": "REAL",
        "Marks": "REAL"
    }
}
```

Relationships must be separately available.

---

# 9. Baseline System

The baseline represents the conventional approach.

## 9.1 Pipeline

```text
Question
   ↓
Full Database Schema
   ↓
LLM
   ↓
Generated SQL
   ↓
SQL Validation
   ↓
SQLite
   ↓
Result
```

## 9.2 Baseline Prompt

The prompt must contain:

- Natural-language question
- Complete database schema
- Foreign-key relationships where required

The LLM must be instructed to:

1. Generate valid SQLite SQL.
2. Use only supplied schema elements.
3. Return SQL only.
4. Never invent tables or columns.
5. Use joins when necessary.
6. Generate read-only SQL.
7. Never modify the database.

The baseline must remain unchanged during evaluation so that it provides a fair comparison.

---

# 10. Proposed Schema-Linking System

This is the primary research component.

## 10.1 Pipeline

```text
Question
   ↓
Schema Linking
   ↓
Schema Element Scoring
   ↓
Ranking
   ↓
Relevant Tables / Columns
   ↓
Relationship Preservation
   ↓
Reduced Schema
   ↓
LLM
   ↓
Generated SQL
   ↓
SQL Validation
   ↓
SQLite
   ↓
Result
```

## 10.2 Schema Elements

The linker must consider:

- Tables
- Columns
- Data types
- Foreign-key relationships

Where useful, table/column descriptions may also be incorporated.

---

# 11. Relevance Scoring

For each relevant schema element, calculate:

```text
Score(c,q) =
    LexicalSimilarity
    + SemanticSimilarity
    + TypeMatch
    + RelationshipScore
```

The exact implementation may use weighted components:

```text
FinalScore =
    Wl * LexicalSimilarity
  + Ws * SemanticSimilarity
  + Wt * TypeMatch
  + Wr * RelationshipScore
```

Initial recommended weights:

```text
LexicalSimilarity    = 0.40
SemanticSimilarity   = 0.35
TypeMatch             = 0.15
RelationshipScore     = 0.10
```

These weights must be configurable.

The final project must not present these weights as scientifically optimal unless experiments demonstrate that claim.

They are initial parameters.

---

# 12. Lexical Similarity

Compare user-question terms with:

- Table names
- Column names
- Relevant schema text

Possible implementation:

- TF-IDF + cosine similarity
- Robust token-based similarity
- Equivalent lightweight lexical method

Example:

```text
Question:
Find employees whose salary is greater than 80000

Column:
Salary
```

`Salary` should receive a high lexical relevance score.

The implementation should normalize common differences where practical, such as:

```text
employee ↔ employees
name ↔ names
salary ↔ salaries
```

Do not build an unnecessarily complicated NLP pipeline.

---

# 13. Semantic Similarity

Use `sentence-transformers` or an equivalent local embedding approach.

Compare:

```text
User question
```

against:

```text
table name + column name + optional description
```

The implementation must not require model training or fine-tuning.

The semantic model must be loaded once where possible rather than reloaded for every question.

---

# 14. Type Matching

Infer simple semantic requirements from the question.

Examples:

```text
Numeric comparison
→ numeric columns

Name/text search
→ text columns

Date/time references
→ date/time columns

Aggregation
→ appropriate numeric columns
```

This component may be rule-based.

It should not attempt to become a full natural-language parser.

---

# 15. Relationship Scoring

Foreign-key relationships must influence selection.

Example:

```text
Student
   │
   │ StudentID
   ↓
Enrollment
   │
   │ CourseID
   ↓
Course
```

If a question strongly selects `Student` and the requested information requires `Enrollment` and `Course`, related schema elements should receive additional relevance.

The system must avoid selecting disconnected tables merely because individual column names have weak lexical matches.

---

# 16. Schema Selection

The linker must return:

```text
Selected tables
Selected columns
Component scores
Final scores
Relationships required
```

Support configurable:

```text
TOP_K_COLUMNS
TOP_K_TABLES
MIN_RELEVANCE_SCORE
```

However, selection must preserve query executability.

A reduced schema that removes a required join key is not a valid reduction.

For example, if the generated SQL needs:

```text
Student.StudentID
Enrollment.StudentID
Enrollment.CourseID
Course.CourseID
```

the reduced schema must preserve those relationship columns even if their direct lexical score is low.

This is a critical correctness requirement.

---

# 17. Reduced Schema Construction

The reduced schema must contain enough information for the LLM to generate the required SQL.

It must preserve:

- Selected tables
- Selected columns
- Required primary keys
- Required foreign keys
- Required join paths
- Relevant data types
- Relationship information necessary for SQL generation

The project must distinguish between:

```text
Directly relevant columns
```

and:

```text
Structural columns required to connect relevant tables
```

This distinction should be visible in debugging/evaluation output.

---

# 18. Prompt Construction

Provide two separate prompt builders.

## 18.1 Baseline

```text
Question
+
FULL SCHEMA
+
RELATIONSHIPS
```

## 18.2 Proposed

```text
Question
+
REDUCED SCHEMA
+
REQUIRED RELATIONSHIPS
```

Both prompts must use the same core SQL-generation instructions.

The only experimental difference should be the schema supplied to the LLM.

This is necessary for a fair baseline comparison.

---

# 19. LLM Layer

The LLM layer must:

1. Receive a prompt.
2. Send the request.
3. Receive the response.
4. Extract SQL from code fences if present.
5. Return generated SQL.
6. Record latency.
7. Record input/output token counts where the provider exposes them.
8. Preserve raw response for debugging.

Conceptually:

```python
generate_sql(prompt) -> {
    "sql": "...",
    "latency": 1.42,
    "input_tokens": ...,
    "output_tokens": ...,
    "raw_response": "..."
}
```

If token information is unavailable, report that honestly rather than estimating it as an exact provider metric.

---

# 20. SQL Safety

Only read-only SQL may be executed.

Accept:

```text
SELECT
```

Reject:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE
REPLACE
```

Also reject:

- Multiple statements
- Obvious write operations
- Other database-modifying SQL

Unsafe SQL must never reach execution.

Example:

```text
SQL rejected: non-read-only statement.
```

The safety layer must not rely only on an LLM instruction.

Validate the generated SQL locally.

---

# 21. CLI

A simple CLI is sufficient.

Example:

```text
========================================
AI NATURAL LANGUAGE → SQL
========================================

1. Baseline
2. Proposed Schema Linking
3. Compare Both
4. Run Evaluation
5. Exit

Select option:
```

Interactive question:

```text
Enter your question:
> Find students whose attendance is below 75%
```

The proposed mode should display:

```text
[Schema Linking]

Selected Tables:
Student

Selected Columns:
StudentName
Attendance

[Generated SQL]

SELECT StudentName, Attendance
FROM Student
WHERE Attendance < 75;

[Result]

StudentName | Attendance
-------------|-----------
Rahul        | 68
Priya        | 72
```

Also show:

```text
Full schema columns: 18
Reduced schema columns: 2
Schema reduction: 88.89%
```

Where appropriate, display individual relevance scores.

---

# 22. Evaluation Dataset

Create a predefined evaluation set of at least 15 natural-language questions.

The set must include different levels of complexity.

## Simple

Examples:

```text
Find students whose attendance is below 75%.
Find faculty members whose salary is above 80000.
Show courses offered by the CSE department.
```

## Filtering + multiple conditions

```text
Show CSE students who scored above 80.
```

## Aggregation

```text
Find the average marks of CSE students.
Count students in each department.
```

## Joins

```text
Show students and their grades using the enrollment table.
List students enrolled in Database Management Systems.
```

## Multi-table reasoning

```text
Show the names and grades of students enrolled in a specific course.
```

The evaluation set must be fixed before final comparison where possible.

Do not continuously modify questions merely to make the proposed system look better.

---

# 23. Ground Truth

Where possible, every evaluation question must have:

```text
Natural-language question
Ground-truth SQL
Expected result
Relevant tables
Relevant columns
Required relationships
```

This enables evaluation beyond "the SQL executed successfully."

---

# 24. Evaluation Metrics

## 24.1 Schema Reduction

```text
Schema Reduction % =
((FullSchemaSize - ReducedSchemaSize)
 / FullSchemaSize) × 100
```

Define exactly what `SchemaSize` means.

Prefer reporting more than one representation where useful:

- Number of columns
- Number of tables
- Approximate schema tokens

Do not mix these into one unexplained number.

---

## 24.2 Prompt Reduction

```text
Prompt Reduction % =
((BaselineTokens - ProposedTokens)
 / BaselineTokens) × 100
```

Use actual provider token counts where available.

If unavailable, clearly label any tokenizer-based value as an estimate.

---

## 24.3 Latency

Measure separately:

```text
Schema-linking time
LLM latency
SQL execution time
Total response time
```

This matters because the proposed method intentionally adds local processing.

The research question is therefore not:

> "Is schema linking free?"

It is:

> "Does the additional local processing justify the reduction in LLM overhead?"

---

# 25. SQL Execution Success

Measure:

```text
successful executions / total questions
```

Report baseline and proposed separately.

However:

**Successful execution does NOT equal correct SQL.**

A syntactically valid query can return the wrong result.

---

# 26. Result Correctness

Where ground truth is available, compare:

```text
Expected result
vs
Generated-query result
```

This is more meaningful than checking whether SQL merely executes.

At minimum report:

```text
Baseline execution accuracy
Proposed execution accuracy
Baseline result correctness
Proposed result correctness
```

---

# 27. Schema-Linking Evaluation

The proposed linker should be evaluated independently.

For each question, define the expected relevant schema.

Then calculate:

```text
Precision =
Relevant selected elements / Total selected elements
```

```text
Recall =
Relevant selected elements / Total relevant elements
```

Report:

```text
Schema-link precision
Schema-link recall
```

Where relationship columns are included for executability, document whether they are classified as required structural elements.

---

# 28. API Cost

Where the provider exposes reliable token pricing information, estimate:

```text
Baseline cost
Proposed cost
Cost reduction %
```

Do not claim cost savings merely from fewer schema columns.

Cost must be derived from actual token usage and the relevant model pricing assumptions.

If pricing is unavailable, report token reduction instead.

---

# 29. Baseline vs Proposed Experiment

Every evaluation question must be run through both systems using equivalent conditions.

For each question record:

```text
question

baseline_sql
proposed_sql

baseline_schema_size
proposed_schema_size
schema_reduction_percentage

baseline_prompt_tokens
proposed_prompt_tokens
prompt_reduction_percentage

baseline_schema_linking_time
proposed_schema_linking_time

baseline_llm_latency
proposed_llm_latency

baseline_sql_execution_time
proposed_sql_execution_time

baseline_total_time
proposed_total_time

baseline_execution_success
proposed_execution_success

baseline_result_correct
proposed_result_correct

baseline_cost
proposed_cost

schema_link_precision
schema_link_recall
```

---

# 30. Fair Experimental Conditions

For a valid comparison:

- Use the same database.
- Use the same questions.
- Use the same LLM/model.
- Use the same generation settings where applicable.
- Use the same SQL safety layer.
- Use the same execution environment.
- Change only the schema supplied to the LLM.

If the LLM is nondeterministic, document the configuration and consider multiple runs per question.

Do not cherry-pick successful runs.

---

# 31. Important Research Trade-Off

The goal is **not maximum schema reduction at any cost**.

The goal is:

```text
SMALLER SCHEMA
      +
LOWER PROMPT COST
      +
LOWER LLM OVERHEAD
      +
ACCEPTABLE / MAINTAINED ACCURACY
```

An aggressively reduced schema that causes incorrect SQL is a failure, not a success.

The evaluation should therefore investigate the trade-off between:

```text
Schema reduction
        vs
SQL/result correctness
```

Where practical, evaluate multiple selection thresholds or Top-K configurations.

Example:

```text
TOP-K / threshold
       ↓
Schema reduction
       ↓
Accuracy
       ↓
Latency
```

This can reveal an effective operating point.

---

# 32. Error Analysis

For every failed proposed-system case, classify the failure.

Possible categories:

```text
1. Schema-linking failure
2. Missing required table
3. Missing required column
4. Missing join key
5. Incorrect relationship selection
6. LLM SQL-generation failure
7. Invalid SQL
8. SQL safety rejection
9. Database execution failure
10. Result correctness failure
```

Do the same for baseline failures where useful.

The final report must not hide failures.

---

# 33. Required Automated Tests

## Database

Test:

- Database creation
- Tables exist
- Sample data exists
- Schema extraction
- Foreign-key extraction
- Valid SELECT execution
- Invalid SQL rejection

## Schema Linker

Test:

- Salary question ranks Salary highly.
- Attendance question ranks Attendance highly.
- Marks question ranks Marks highly.
- Relevant tables are selected.
- Related tables receive relationship score.
- Required join keys are preserved.
- Top-K selection works.
- Minimum relevance threshold works.

## SQL Safety

Test:

```text
SELECT     → accepted
INSERT     → rejected
UPDATE     → rejected
DELETE     → rejected
DROP       → rejected
ALTER      → rejected
CREATE     → rejected
TRUNCATE   → rejected
REPLACE    → rejected
multi-statement → rejected
```

## LLM

Mock the LLM for unit tests.

Tests must not require a paid API call unless explicitly running integration tests.

## End-to-End

At least three natural-language questions must successfully execute through:

```text
Question
→ schema extraction
→ schema linking
→ reduced schema
→ mocked/real LLM
→ SQL validation
→ SQLite
→ result
```

---

# 34. Project Structure

A clean implementation may use:

```text
text-to-sql/
│
├── main.py
├── database.py
├── schema_linker.py
├── llm.py
├── prompts.py
├── evaluator.py
├── requirements.txt
├── .env.example
├── README.md
├── college.db
│
├── tests/
│   └── test_system.py
│
└── evaluation/
    ├── questions.json
    ├── ground_truth.json
    └── results/
```

**Important:**

This is a logical structure, not a command to duplicate files.

If the existing repository has a better equivalent structure, preserve it.

---

# 35. Configuration

Use environment/configuration values for:

```text
LLM_API_KEY
LLM_MODEL
TOP_K_COLUMNS
TOP_K_TABLES
MIN_RELEVANCE_SCORE
LEXICAL_WEIGHT
SEMANTIC_WEIGHT
TYPE_WEIGHT
RELATIONSHIP_WEIGHT
```

Example:

```text
LLM_API_KEY=...
LLM_MODEL=...
TOP_K_COLUMNS=8
TOP_K_TABLES=4
LEXICAL_WEIGHT=0.40
SEMANTIC_WEIGHT=0.35
TYPE_WEIGHT=0.15
RELATIONSHIP_WEIGHT=0.10
```

Never commit real credentials.

Provide:

```text
.env.example
```

---

# 36. Logging and Debugging

The system should make it possible to inspect:

```text
Question
↓
Schema candidates
↓
Lexical scores
↓
Semantic scores
↓
Type scores
↓
Relationship scores
↓
Final scores
↓
Selected schema
↓
LLM prompt
↓
Generated SQL
↓
Validation
↓
Execution
↓
Result
```

Debug information should be available without making normal CLI output unusably large.

---

# 37. README Requirements

README must explain:

1. Project objective
2. Research question
3. Architecture
4. Baseline system
5. Proposed system
6. Schema-linking algorithm
7. Scoring components
8. Database schema
9. Installation
10. Environment setup
11. How to run
12. Example questions
13. Evaluation procedure
14. Metrics
15. Baseline vs proposed comparison
16. Experimental results
17. Limitations
18. Known failure cases
19. Reproducibility instructions

The README must not claim results that have not actually been measured.

---

# 38. Implementation Order

Do not randomly implement features.

Follow this priority unless the existing codebase verification identifies a better dependency order.

## Phase 0 — Codebase Verification

1. Inspect entire repository.
2. Run existing system.
3. Run tests.
4. Build implementation inventory.
5. Identify complete/partial/missing components.
6. Create concrete completion plan.

## Phase 1 — Core Infrastructure

1. Verify SQLite database.
2. Verify automatic initialization.
3. Verify schema extraction.
4. Verify relationship extraction.
5. Verify SQL execution.
6. Verify SQL safety.
7. Verify LLM integration.

## Phase 2 — Baseline

1. Implement full-schema prompt.
2. Generate SQL.
3. Validate SQL.
4. Execute SQL.
5. Display results.
6. Measure baseline metrics.

## Phase 3 — Schema Linking

1. Lexical similarity.
2. Semantic similarity.
3. Type matching.
4. Relationship scoring.
5. Weighted final scoring.
6. Ranking.
7. Selection.
8. Join-key preservation.
9. Reduced schema generation.

## Phase 4 — Proposed System

1. Reduced-schema prompt.
2. LLM generation.
3. SQL validation.
4. SQL execution.
5. Results.
6. Proposed-system metrics.

## Phase 5 — Evaluation

1. Create at least 15 evaluation questions.
2. Define ground truth.
3. Run baseline.
4. Run proposed system.
5. Collect metrics.
6. Calculate schema-link precision/recall.
7. Compare accuracy.
8. Compare latency.
9. Compare prompt size.
10. Compare cost where possible.

## Phase 6 — Error Analysis

1. Identify failed questions.
2. Classify failures.
3. Fix genuine implementation defects.
4. Re-run evaluation.
5. Do not silently remove difficult questions.

## Phase 7 — Tests and Reproducibility

1. Complete unit tests.
2. Complete integration tests.
3. Complete evaluation runner.
4. Ensure results can be regenerated.

## Phase 8 — Documentation

1. README.
2. Architecture.
3. Algorithm explanation.
4. Evaluation methodology.
5. Results.
6. Limitations.
7. Viva/presentation explanation.

---

# 39. Antigravity Final Verification

Before declaring the project complete, Antigravity must perform a second full repository audit.

## 39.1 Functional Verification

Confirm:

```text
[ ] python main.py starts
[ ] Database initializes automatically
[ ] Natural-language question is accepted
[ ] Full schema can be extracted
[ ] Relationships can be extracted
[ ] Baseline mode works
[ ] Schema linker works
[ ] Reduced schema is generated
[ ] Required join keys are preserved
[ ] Proposed mode works
[ ] LLM generates SQL
[ ] Unsafe SQL is rejected
[ ] Valid SQL executes
[ ] Results are displayed
[ ] Baseline/proposed comparison works
[ ] Evaluation set runs
[ ] Metrics are generated
```

## 39.2 Research Verification

Confirm:

```text
[ ] Baseline uses full schema
[ ] Proposed system uses reduced schema
[ ] Same questions are used for both
[ ] Same model/settings are used where applicable
[ ] Lexical similarity exists
[ ] Semantic similarity exists
[ ] Type matching exists
[ ] Relationship scoring exists
[ ] Configurable weights exist
[ ] Schema reduction is measurable
[ ] Prompt reduction is measurable
[ ] LLM latency is measurable
[ ] Local schema-linking time is measurable
[ ] SQL execution time is measurable
[ ] Execution success is measured
[ ] Result correctness is measured where ground truth exists
[ ] Schema-link precision is measured
[ ] Schema-link recall is measured
[ ] API cost is measured where reliably possible
```

## 39.3 Safety Verification

Confirm:

```text
[ ] API keys are not committed
[ ] Only read-only SQL executes
[ ] Multiple statements are rejected
[ ] Database modification statements are rejected
[ ] LLM output is validated locally
[ ] Exceptions are not silently swallowed
```

## 39.4 Code Quality Verification

Check:

```text
[ ] No duplicate modules
[ ] No dead critical code
[ ] No hard-coded API keys
[ ] No unnecessary dependencies
[ ] No unnecessary abstractions
[ ] No fake metrics
[ ] No hard-coded evaluation results
[ ] No misleading accuracy claims
[ ] Existing functionality was preserved unless intentionally replaced
```

---

# 40. Final Antigravity Completion Report

After implementation, Antigravity must produce a final report containing:

## A. What existed before implementation

List the actual files/components discovered during Phase 0.

## B. What was implemented

List every modified/created component.

## C. What was already correct

Do not rewrite or replace components unnecessarily.

## D. What was fixed

Explain bugs or incomplete functionality.

## E. What remains incomplete

Be explicit.

## F. Test results

Report:

```text
Tests passed:
Tests failed:
Integration tests:
Evaluation questions:
```

## G. Final research metrics

Report actual measured values:

```text
Schema reduction:
Prompt reduction:
Baseline latency:
Proposed latency:
Schema-linking overhead:
Baseline execution accuracy:
Proposed execution accuracy:
Baseline result correctness:
Proposed result correctness:
Schema-link precision:
Schema-link recall:
Cost reduction:
```

Use `N/A` when a metric cannot legitimately be measured.

## H. Final conclusion

Answer:

> Does the proposed schema-linking/reduction approach provide a measurable benefit over the full-schema baseline?

The answer must be based on measured results, not assumptions.

---

# 41. Definition of Done

The project is complete only when:

- The CLI starts successfully.
- SQLite initializes automatically.
- The user can enter an English question.
- The system extracts the actual database schema.
- The system extracts relationships.
- Baseline full-schema Text-to-SQL works.
- Proposed schema-linking Text-to-SQL works.
- Schema elements receive relevance scores.
- Relevant tables and columns are selected.
- Required join keys are preserved.
- Reduced schema is supplied to the LLM.
- Generated SQL is locally validated as read-only.
- SQL executes against SQLite.
- Results are displayed.
- At least 15 evaluation questions can be executed.
- Baseline and proposed systems are compared using the same evaluation set.
- Schema reduction is measured.
- Prompt/token reduction is measured where possible.
- Latency is measured.
- Execution success is measured.
- Result correctness is evaluated where ground truth exists.
- Schema-link precision/recall is measured.
- API cost is measured where reliably possible.
- Automated tests pass.
- Failure cases are documented.
- README explains reproduction.
- Final experimental results are recorded.
- Antigravity has completed the final codebase verification.
- No unsupported performance claims are made.

---

# 42. Core Principle

Do not lose sight of the actual project.

The project is **not**:

```text
Build a chatbot that generates SQL.
```

It is:

```text
FULL SCHEMA
     ↓
BASELINE TEXT-TO-SQL
     ↓
COMPARE
     ↑
SCHEMA LINKING
     ↓
REDUCED SCHEMA
     ↓
PROPOSED TEXT-TO-SQL
```

The research question is:

> **Can intelligent schema reduction reduce LLM input and inference overhead while maintaining acceptable SQL/result accuracy?**

Everything implemented should support answering that question.

Anything that does not contribute meaningfully to that objective should be treated as secondary.

---

# 43. Final Instruction to Antigravity

**Do not assume this PRD describes the current state of the codebase.**

First inspect the actual repository.

Then determine what already exists.

Then implement only what is missing or incorrect.

Do not throw away working code simply to match a proposed folder structure.

Do not fabricate completed functionality.

Do not fabricate metrics.

Do not claim an optimization works until it has been measured.

Do not optimize for visual polish.

Optimize for:

```text
CORRECTNESS
+
RESEARCH VALIDITY
+
MEASURABILITY
+
REPRODUCIBILITY
+
EXPLAINABILITY
```

The final system must be simple enough that every major component can be explained clearly during a project presentation/viva, while being rigorous enough to support a legitimate baseline-vs-proposed experimental comparison.
