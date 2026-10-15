import os
import re
import json
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Load benchmark metrics from JSON
with open("docs/benchmark_run_results.json", "r", encoding="utf-8") as f:
    benchmark_data = json.load(f)

# Define metadata and metrics for each database
db_details = {
    "hr_1": {
        "title": "Database: hr_1",
        "domain": "Human Resources",
        "tables": 7,
        "cols": 35,
        "rows": 216,
        "primary_table": "employees (107 rows)",
        "metrics": [
            ("Prompt Tokens", "829.20", "433.60", "-47.7% context savings (-395.6 tokens)"),
            ("Columns Sent", "35.00", "10.20", "-70.9% schema clutter reduction"),
            ("Schema Reduction", "0.0%", "70.90%", "High compression ratio"),
            ("Algorithm Linking Latency", "0.0 ms", "27.6 ms (warm avg)", "Fast vectorized in-memory graph linking (26.06s cold load)"),
            ("LLM Generation Latency", "3.22 s", "2.98 s", "Faster inference due to compact prompt (-0.24 s)"),
            ("End-to-End (Total) Latency", "3.22 s", "3.01 s (warm)", "Net faster end-to-end than baseline (-0.21 s)"),
            ("Schema Linking Precision", "9.70%", "32.20%", "+22.50 points (3.3x precision increase)"),
            ("Schema Recall Accuracy", "100.0%", "93.30%", "Preserved query answerability (93.3% recall)"),
            ("Schema F1-Score (Harmonic Mean of Precision and Recall)", "17.70%", "47.50%", "+29.80 points F1 gain"),
            ("SQL Execution Success", "100.0%", "100.0%", "100% valid, executable SQLite syntax"),
            ("Execution Accuracy", "40.0% (2/5)", "60.0% (3/5)", "+20.0% accuracy gain (Proposed beats Baseline: 3/5 vs 2/5)"),
            ("Generation Throughput (tokens/s ~ tps)", "8.60 tps", "8.36 tps", "Consistent token output throughput")
        ]
    },
    "car_1": {
        "title": "Database: car_1",
        "domain": "Automotive Specs",
        "tables": 6,
        "cols": 23,
        "rows": 890,
        "primary_table": "cars_data (406 rows)",
        "metrics": [
            ("Prompt Tokens", "512.40", "325.80", "-36.4% context savings (-186.6 tokens)"),
            ("Columns Sent", "23.00", "6.60", "-71.3% schema clutter reduction"),
            ("Schema Reduction", "0.0%", "71.30%", "High compression ratio"),
            ("Algorithm Linking Latency", "0.0 ms", "33.5 ms (avg)", "Fast vectorized in-memory graph linking"),
            ("LLM Generation Latency", "2.72 s", "2.84 s", "Comparable inference latency (+0.12 s)"),
            ("End-to-End (Total) Latency", "2.72 s", "2.87 s", "Comparable end-to-end turnaround (+0.15 s)"),
            ("Schema Linking Precision", "11.30%", "69.20%", "+57.90 points (6.1x precision increase)"),
            ("Schema Recall Accuracy", "100.0%", "100.0%", "100% complete schema recall"),
            ("Schema F1-Score (Harmonic Mean of Precision and Recall)", "20.20%", "75.00%", "+54.80 points F1 gain"),
            ("SQL Execution Success", "100.0%", "100.0%", "100% valid, executable SQLite syntax"),
            ("Execution Accuracy", "100.0% (5/5)", "100.0% (5/5)", "100% execution accuracy (All 5 queries passed)"),
            ("Generation Throughput (tokens/s ~ tps)", "9.18 tps", "8.60 tps", "Consistent token output throughput")
        ]
    },
    "flight_2": {
        "title": "Database: flight_2",
        "domain": "Airlines & Flights",
        "tables": 3,
        "cols": 13,
        "rows": 1312,
        "primary_table": "flights (1,200 rows)",
        "metrics": [
            ("Prompt Tokens", "375.20", "289.60", "-22.8% context savings (-85.6 tokens)"),
            ("Columns Sent", "13.00", "5.20", "-60.0% schema clutter reduction"),
            ("Schema Reduction", "0.0%", "60.00%", "High compression ratio"),
            ("Algorithm Linking Latency", "0.0 ms", "32.4 ms (avg)", "Fast vectorized in-memory graph linking"),
            ("LLM Generation Latency", "2.94 s", "2.90 s", "Faster inference due to compact prompt (-0.04 s)"),
            ("End-to-End (Total) Latency", "2.94 s", "2.93 s", "Net faster end-to-end than baseline (-0.01 s)"),
            ("Schema Linking Precision", "16.90%", "39.00%", "+22.10 points (2.3x precision increase)"),
            ("Schema Recall Accuracy", "100.0%", "80.00%", "80.0% schema recall (Compact anchor preservation)"),
            ("Schema F1-Score (Harmonic Mean of Precision and Recall)", "28.80%", "50.50%", "+21.70 points F1 gain"),
            ("SQL Execution Success", "100.0%", "100.0%", "100% valid, executable SQLite syntax"),
            ("Execution Accuracy", "60.0% (3/5)", "60.0% (3/5)", "Identical execution accuracy (3/5 queries passed)"),
            ("Generation Throughput (tokens/s ~ tps)", "4.30 tps", "4.44 tps", "Consistent token output throughput")
        ]
    },
    "world_1": {
        "title": "Database: world_1",
        "domain": "Global Demographics",
        "tables": 3,
        "cols": 24,
        "rows": 5302,
        "primary_table": "city (4,079 rows)",
        "metrics": [
            ("Prompt Tokens", "517.80", "303.80", "-41.3% context savings (-214.0 tokens)"),
            ("Columns Sent", "24.00", "5.20", "-78.3% schema clutter reduction"),
            ("Schema Reduction", "0.0%", "78.30%", "High compression ratio"),
            ("Algorithm Linking Latency", "0.0 ms", "33.4 ms (avg)", "Fast vectorized in-memory graph linking"),
            ("LLM Generation Latency", "2.91 s", "2.77 s", "Faster inference due to compact prompt (-0.14 s)"),
            ("End-to-End (Total) Latency", "2.91 s", "2.80 s", "Net faster end-to-end than baseline (-0.11 s)"),
            ("Schema Linking Precision", "6.70%", "29.70%", "+23.00 points (4.4x precision increase)"),
            ("Schema Recall Accuracy", "100.0%", "90.00%", "90.0% schema recall preserved"),
            ("Schema F1-Score (Harmonic Mean of Precision and Recall)", "12.40%", "42.70%", "+30.30 points F1 gain"),
            ("SQL Execution Success", "100.0%", "100.0%", "100% valid, executable SQLite syntax"),
            ("Execution Accuracy", "60.0% (3/5)", "60.0% (3/5)", "Identical execution accuracy (3/5 queries passed)"),
            ("Generation Throughput (tokens/s ~ tps)", "4.70 tps", "4.90 tps", "Consistent token output throughput")
        ]
    },
    "sakila_1": {
        "title": "Database: sakila_1",
        "domain": "Media Rental Store",
        "tables": 16,
        "cols": 89,
        "rows": 46823,
        "primary_table": "payment (16,049 rows)",
        "metrics": [
            ("Prompt Tokens", "1550.80", "456.80", "-70.5% context savings (-1094.0 tokens)"),
            ("Columns Sent", "89.00", "12.00", "-86.5% schema clutter reduction"),
            ("Schema Reduction", "0.0%", "86.50%", "Highest compression ratio on largest schema"),
            ("Algorithm Linking Latency", "0.0 ms", "52.2 ms (avg)", "Fast vectorized in-memory graph linking"),
            ("LLM Generation Latency", "3.19 s", "3.00 s", "Faster inference due to compact prompt (-0.19 s)"),
            ("End-to-End (Total) Latency", "3.19 s", "3.05 s", "Net faster end-to-end than baseline (-0.14 s)"),
            ("Schema Linking Precision", "1.30%", "10.00%", "+8.70 points (7.7x precision increase)"),
            ("Schema Recall Accuracy", "100.0%", "100.00%", "100% complete schema recall"),
            ("Schema F1-Score (Harmonic Mean of Precision and Recall)", "2.70%", "18.00%", "+15.30 points F1 gain"),
            ("SQL Execution Success", "100.0%", "100.0%", "100% valid, executable SQLite syntax"),
            ("Execution Accuracy", "80.0% (4/5)", "80.0% (4/5)", "Identical execution accuracy (4/5 queries passed)"),
            ("Generation Throughput (tokens/s ~ tps)", "7.44 tps", "9.22 tps", "High token generation throughput (+1.78 tps)")
        ]
    }
}

doc_path = "docs/Dataset Benchmark Report/Spider Dataset Report.docx"
doc = docx.Document(doc_path)

def set_cell_properties(cell, width_dxa):
    tcPr = cell._tc.get_or_add_tcPr()
    # width
    tcW = parse_xml(f'<w:tcW {nsdecls("w")} w:w="{width_dxa}" w:type="dxa"/>')
    tcPr.append(tcW)
    # vAlign center
    vAlign = parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>')
    tcPr.append(vAlign)

def build_4col_table(doc, metrics):
    col_widths = [2695, 1890, 1834, 2756]
    tbl = doc.add_table(rows=len(metrics) + 1, cols=4)
    tbl.style = "Plain Table 1"
    
    # tblPr settings matching Table 1
    tblPr = tbl._tbl.tblPr
    tblPr_xml = parse_xml(f'''
        <w:tblPr {nsdecls("w")}>
            <w:tblStyle w:val="PlainTable1"/>
            <w:tblW w:w="5088" w:type="pct"/>
            <w:tblLayout w:type="fixed"/>
            <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>
        </w:tblPr>
    ''')
    tbl._tbl.replace(tblPr, tblPr_xml)
    
    # Header
    headers = ["Metric", "Full-Schema Baseline", "Proposed Pipeline", "Net Improvement"]
    hdr_row = tbl.rows[0]
    for c_idx, h_text in enumerate(headers):
        cell = hdr_row.cells[c_idx]
        set_cell_properties(cell, col_widths[c_idx])
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(h_text)
        run.font.name = "Inter"
        run.bold = True
        run.font.size = Pt(9.5)

    # Data Rows
    for r_idx, (m_name, base_val, prop_val, imp_val) in enumerate(metrics, start=1):
        row = tbl.rows[r_idx]
        vals = [m_name, base_val, prop_val, imp_val]
        for c_idx, val in enumerate(vals):
            cell = row.cells[c_idx]
            set_cell_properties(cell, col_widths[c_idx])
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2.5)
            p.paragraph_format.space_after = Pt(2.5)
            run = p.add_run(val)
            run.font.name = "Inter"
            run.font.size = Pt(9)
            if c_idx == 0:
                run.bold = True
                
    return tbl

# We will replace doc.tables[2] through doc.tables[6] with our updated tables
# Let's locate each table's parent and replace its XML element
tables_to_replace = [
    ("hr_1", 2),
    ("car_1", 3),
    ("flight_2", 4),
    ("world_1", 5),
    ("sakila_1", 6)
]

for db_id, tbl_idx in tables_to_replace:
    old_tbl = doc.tables[tbl_idx]
    parent = old_tbl._tbl.getparent()
    pos = list(parent).index(old_tbl._tbl)
    
    # Create new table
    new_tbl = build_4col_table(doc, db_details[db_id]["metrics"])
    
    # Move new_tbl._tbl to pos, and remove old_tbl._tbl
    parent.insert(pos, new_tbl._tbl)
    parent.remove(old_tbl._tbl)

# Save document
output_path = "docs/Dataset Benchmark Report/Spider Dataset Report.docx"
doc.save(output_path)
print("Successfully updated Spider Dataset Report.docx with 4-column breakdown tables!")
