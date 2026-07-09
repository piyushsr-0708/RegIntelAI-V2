import sqlite3
import os
from pathlib import Path
import sys

def bytes_to_mb(b):
    return f"{b / (1024 * 1024):.2f} MB"

def get_db_path():
    # Attempt to locate regintel.db
    possible_paths = [
        Path("d:/SuRaksha-v2/regintel.db"),
        Path("d:/SuRaksha-v2/backend/database/regintel.db"),
        Path.cwd() / "regintel.db"
    ]
    for p in possible_paths:
        if p.exists():
            return p
    return None

def main():
    db_path = get_db_path()
    if not db_path:
        print("Could not locate regintel.db")
        sys.exit(1)
        
    db_size = db_path.stat().st_size
    
    # Connect in read-only mode if uri is supported
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except Exception:
        conn = sqlite3.connect(db_path)
    
    cursor = conn.cursor()
    
    # DATABASE SUMMARY
    cursor.execute("SELECT sqlite_version()")
    sqlite_version = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA freelist_count")
    freelist_count = cursor.fetchone()[0]
    
    print("="*60)
    print(" DATABASE SUMMARY")
    print("="*60)
    print(f"Database path:  {db_path}")
    print(f"Database size:  {bytes_to_mb(db_size)} ({db_size} bytes)")
    print(f"SQLite version: {sqlite_version}")
    print(f"Page size:      {page_size} bytes")
    print(f"Page count:     {page_count}")
    print(f"Free pages:     {freelist_count} (Wasted space: {bytes_to_mb(freelist_count * page_size)})")
    print("\n")
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]
    
    table_stats = {}
    largest_columns = []
    
    print("="*60)
    print(" TABLE ANALYSIS")
    print("="*60)
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Calculate estimated size of table by summing avg length of columns
        avg_row_size = 0
        text_cols = []
        for col in columns:
            col_name = col[1]
            col_type = col[2].upper()
            
            if 'TEXT' in col_type or 'VARCHAR' in col_type or 'JSON' in col_type:
                text_cols.append(col_name)
                
            cursor.execute(f"SELECT AVG(LENGTH(CAST({col_name} AS TEXT))), MAX(LENGTH(CAST({col_name} AS TEXT))) FROM {table}")
            avg_len, max_len = cursor.fetchone()
            avg_len = avg_len or 0
            max_len = max_len or 0
            avg_row_size += avg_len
            
            if max_len > 1000:
                largest_columns.append({"table": table, "column": col_name, "max_length": max_len, "avg_length": avg_len})
                
        estimated_table_size = row_count * avg_row_size
        table_stats[table] = {
            "rows": row_count,
            "avg_row_size": avg_row_size,
            "estimated_size": estimated_table_size,
            "text_cols": text_cols
        }
        
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        
        print(f"Table: {table}")
        print(f"  Rows: {row_count}")
        print(f"  Estimated Size: {bytes_to_mb(estimated_table_size)}")
        print(f"  Avg Row Size: {avg_row_size:.2f} bytes")
        print(f"  Indexes: {len(indexes)}")
        print("-" * 30)

    print("\n")
    print("="*60)
    print(" COLUMN ANALYSIS & DUPLICATES")
    print("="*60)
    
    duplicate_warnings = []
    
    # Sort largest columns
    largest_columns.sort(key=lambda x: x['max_length'], reverse=True)
    print("Largest Text/JSON Columns (Max Length > 1000 bytes):")
    for lc in largest_columns[:10]:
        print(f"  {lc['table']}.{lc['column']} -> Max: {lc['max_length']} bytes, Avg: {lc['avg_length']:.2f} bytes")
        
        # Check for duplicates in these large columns
        if lc['table'] != 'audit_logs': # Skip checking audit log uniqueness as they might be similar
            try:
                cursor.execute(f"SELECT COUNT(*), COUNT(DISTINCT {lc['column']}) FROM {lc['table']} WHERE {lc['column']} IS NOT NULL")
                total_val, distinct_val = cursor.fetchone()
                if total_val > 0 and (total_val - distinct_val) > 0:
                    dup_pct = ((total_val - distinct_val) / total_val) * 100
                    if dup_pct > 5:
                        duplicate_warnings.append(f"{lc['table']}.{lc['column']} has {dup_pct:.1f}% duplicate values (Total: {total_val}, Unique: {distinct_val})")
            except Exception as e:
                pass

    print("\nDuplicate Data Warnings:")
    for warn in duplicate_warnings:
        print(f"  [WARNING] {warn}")

    print("\n")
    print("="*60)
    print(" TOP 20 LARGEST ROWS ACROSS DATABASE")
    print("="*60)
    
    # For a quick heuristic, we will just query the sum of lengths for rows in tables that have large average row sizes
    largest_rows = []
    for table, stats in table_stats.items():
        if stats['rows'] > 0 and stats['text_cols']:
            length_expr = " + ".join([f"COALESCE(LENGTH(CAST({c} AS TEXT)), 0)" for c in stats['text_cols']])
            query = f"SELECT id, {length_expr} as total_len FROM {table} ORDER BY total_len DESC LIMIT 5"
            try:
                cursor.execute(query)
                for row_id, total_len in cursor.fetchall():
                    largest_rows.append({"table": table, "id": row_id, "size": total_len})
            except Exception:
                pass
                
    largest_rows.sort(key=lambda x: x['size'], reverse=True)
    for i, lr in enumerate(largest_rows[:20]):
        print(f"{i+1}. Table: {lr['table']} | ID: {lr['id']} | Size: {lr['size']} bytes")

    print("\n")
    print("="*60)
    print(" NORMALIZATION REVIEW")
    print("="*60)
    issues = []
    if any("requirement_provenance" in w for w in duplicate_warnings):
        issues.append("Provenance JSON (blocks, nodes) appears heavily duplicated. Consider separating Block/Node dictionaries.")
    if any("compliance_controls" in w and "description" in w for w in duplicate_warnings):
        issues.append("Control descriptions are duplicated. Controls may have been created per requirement instead of reused via mapping.")
    if not issues:
        print("No glaring normalization issues detected via heuristics.")
    else:
        for iss in issues:
            print(f"- {iss}")

    print("\n")
    print("="*60)
    print(" PERFORMANCE REVIEW")
    print("="*60)
    perf_issues = []
    # Check for missing foreign key indexes
    for table in tables:
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        index_names = [idx[1] for idx in indexes]
        
        indexed_cols = []
        for idx_name in index_names:
            cursor.execute(f"PRAGMA index_info({idx_name})")
            idx_cols = cursor.fetchall()
            if len(idx_cols) == 1:
                indexed_cols.append(idx_cols[0][2])
                
        for fk in fks:
            fk_col = fk[3]
            if fk_col not in indexed_cols:
                perf_issues.append(f"Missing Index: Foreign key {table}.{fk_col} is not indexed. This will cause full table scans on cascading deletes or joins.")
                
    if not perf_issues:
        print("Indexes appear healthy. Foreign keys are indexed.")
    else:
        for pi in perf_issues[:10]:
            print(f"- {pi}")
        if len(perf_issues) > 10:
            print(f"... and {len(perf_issues) - 10} more missing indexes.")

    print("\n")
    print("="*60)
    print(" OVERALL ASSESSMENT")
    print("="*60)
    
    score = 10
    if len(duplicate_warnings) > 2: score -= 2
    if len(perf_issues) > 0: score -= 1
    if db_size > 100 * 1024 * 1024: score -= 2
    
    print(f"Database Health Score: {score} / 10")
    print("\nMajor Problems:")
    if db_size > 50 * 1024 * 1024 and table_stats.get('documents', {}).get('rows', 0) < 500:
        print("- Database footprint is unusually large for the document count. High likelihood of aggressive text duplication or massive JSON provenance blobs.")
    for warn in duplicate_warnings[:3]:
        print(f"- {warn}")
        
    print("\nRecommended Fixes:")
    print("1. Implement strict deduplication logic during the `PipelineIngestionService` run to reuse ComplianceControl objects instead of creating new ones per requirement.")
    print("2. Normalize `RequirementProvenance` by storing the massive arrays of block IDs and text off-database, or compressing the JSON payload.")
    print("3. Ensure SQLAlchemy models specify `index=True` on all ForeignKey columns to prevent table scan locks.")
    print("4. Run `VACUUM;` to reclaim unused pages and reduce file size.")
    
    conn.close()

if __name__ == "__main__":
    main()
