# Compare two Snowflake databases (DEV vs PROD/QA) across schemas and store results

from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import datetime, timedelta

session = get_active_session()

# ============================================================
# PARAMETERS - Change these for different environment comparisons
# ============================================================
SOURCE_DB = "CICD_AUTOMATION_DEV"          
TARGET_DB = "CICD_AUTOMATION_PROD"         
SCHEMAS = "PATIENTS,HOSPITALS,UTILITIES"  
RESULTS_TABLE = "CICD_AUTOMATION_DEV.VALIDATION.DB_COMPARE_RESULTS"
RETENTION_DAYS = 7   # Auto-purge results older than this
# ============================================================


def q(sql: str):
    try:
        return [r.as_dict() for r in session.sql(sql).collect()]
    except Exception as e:
        print(f"  Warning: {e}")
        return []


def normalize_def(text, source_db, target_db):
    if not text:
        return ""
    return text.upper().replace(source_db.upper(), "__DB__").replace(target_db.upper(), "__DB__").strip()


def run_comparison(source_db, target_db, schemas):
    schema_list = [s.strip().upper() for s in schemas.split(",") if s.strip()]
    results = []

    def add(schema, obj_type, obj_name, detail, prop, src_val, tgt_val, status):
        results.append({
            "SCHEMA": schema,
            "OBJECT_TYPE": obj_type,
            "OBJECT_NAME": obj_name,
            "DETAIL_TYPE": detail,
            "PROPERTY": prop,
            "SOURCE_VALUE": str(src_val),
            "TARGET_VALUE": str(tgt_val),
            "STATUS": status,
        })

    def compare_existence(schema, obj_type, src_set, tgt_set):
        for name in src_set & tgt_set:
            add(schema, obj_type, name, "OBJECT", "EXISTS", "YES", "YES", "PRESENT")
        for name in src_set - tgt_set:
            add(schema, obj_type, name, "OBJECT", "EXISTS", "YES", "NO", f"MISSING IN {target_db}")
        for name in tgt_set - src_set:
            add(schema, obj_type, name, "OBJECT", "EXISTS", "NO", "YES", f"MISSING IN {source_db}")
        return src_set & tgt_set

    for SCHEMA_NAME in schema_list:
        print(f"\n=== Schema: {SCHEMA_NAME} ===")

        # --- TABLES ---
        print("  Comparing TABLES...")
        src_tables = set(r["TABLE_NAME"] for r in q(f"""
            SELECT TABLE_NAME FROM {source_db}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_TYPE = 'BASE TABLE'
        """))
        tgt_tables = set(r["TABLE_NAME"] for r in q(f"""
            SELECT TABLE_NAME FROM {target_db}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_TYPE = 'BASE TABLE'
        """))
        common_tables = compare_existence(SCHEMA_NAME, "TABLE", src_tables, tgt_tables)

        for t in common_tables:
            src_cols = {r["COLUMN_NAME"]: r for r in q(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION
                FROM {source_db}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_NAME = '{t}'
            """)}
            tgt_cols = {r["COLUMN_NAME"]: r for r in q(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION
                FROM {target_db}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_NAME = '{t}'
            """)}
            for col in set(src_cols) - set(tgt_cols):
                add(SCHEMA_NAME, "TABLE", t, "COLUMN", col, "EXISTS", "MISSING", f"COLUMN MISSING IN {target_db}")
            for col in set(tgt_cols) - set(src_cols):
                add(SCHEMA_NAME, "TABLE", t, "COLUMN", col, "MISSING", "EXISTS", f"COLUMN MISSING IN {source_db}")
            for col in set(src_cols) & set(tgt_cols):
                for prop in ["DATA_TYPE", "IS_NULLABLE", "COLUMN_DEFAULT", "CHARACTER_MAXIMUM_LENGTH", "NUMERIC_PRECISION"]:
                    sv = src_cols[col].get(prop)
                    tv = tgt_cols[col].get(prop)
                    if str(sv) != str(tv):
                        add(SCHEMA_NAME, "TABLE", t, "COLUMN", f"{col}.{prop}", str(sv), str(tv), "DIFFERENT")

            # Constraints
            src_c = {r["CONSTRAINT_NAME"]: r["CONSTRAINT_TYPE"] for r in q(f"""
                SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE FROM {source_db}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_NAME = '{t}'
            """)}
            tgt_c = {r["CONSTRAINT_NAME"]: r["CONSTRAINT_TYPE"] for r in q(f"""
                SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE FROM {target_db}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}' AND TABLE_NAME = '{t}'
            """)}
            for c in set(src_c) - set(tgt_c):
                add(SCHEMA_NAME, "TABLE", t, "CONSTRAINT", c, src_c[c], "MISSING", f"MISSING IN {target_db}")
            for c in set(tgt_c) - set(src_c):
                add(SCHEMA_NAME, "TABLE", t, "CONSTRAINT", c, "MISSING", tgt_c[c], f"MISSING IN {source_db}")

        # --- VIEWS ---
        print("  Comparing VIEWS...")
        src_views = {r["TABLE_NAME"]: r.get("VIEW_DEFINITION", "") for r in q(f"""
            SELECT TABLE_NAME, VIEW_DEFINITION FROM {source_db}.INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = '{SCHEMA_NAME}'
        """)}
        tgt_views = {r["TABLE_NAME"]: r.get("VIEW_DEFINITION", "") for r in q(f"""
            SELECT TABLE_NAME, VIEW_DEFINITION FROM {target_db}.INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = '{SCHEMA_NAME}'
        """)}
        common_views = compare_existence(SCHEMA_NAME, "VIEW", set(src_views), set(tgt_views))
        for v in common_views:
            src_def = normalize_def(src_views.get(v), source_db, target_db)
            tgt_def = normalize_def(tgt_views.get(v), source_db, target_db)
            if src_def != tgt_def:
                add(SCHEMA_NAME, "VIEW", v, "DEFINITION", "VIEW_DEFINITION", src_views[v][:200], tgt_views[v][:200], "DIFFERENT")

        # --- STAGES ---
        print("  Comparing STAGES...")
        src_stages = {r["name"]: r for r in q(f"SHOW STAGES IN {source_db}.{SCHEMA_NAME}")}
        tgt_stages = {r["name"]: r for r in q(f"SHOW STAGES IN {target_db}.{SCHEMA_NAME}")}
        common_stages = compare_existence(SCHEMA_NAME, "STAGE", set(src_stages), set(tgt_stages))
        for s in common_stages:
            for prop in ["type", "url", "cloud", "has_credentials", "has_encryption_key", "owner", "comment", "directory_enabled"]:
                sv = str(src_stages[s].get(prop, "")).strip()
                tv = str(tgt_stages[s].get(prop, "")).strip()
                if sv != tv:
                    add(SCHEMA_NAME, "STAGE", s, "PROPERTY", prop.upper(), sv, tv, "DIFFERENT")

        # --- FILE FORMATS ---
        print("  Comparing FILE FORMATS...")
        src_ffs = {r["name"]: r for r in q(f"SHOW FILE FORMATS IN {source_db}.{SCHEMA_NAME}")}
        tgt_ffs = {r["name"]: r for r in q(f"SHOW FILE FORMATS IN {target_db}.{SCHEMA_NAME}")}
        common_ffs = compare_existence(SCHEMA_NAME, "FILE FORMAT", set(src_ffs), set(tgt_ffs))
        for ff in common_ffs:
            src_desc = {r["property"]: r.get("property_value", "") for r in q(f"DESCRIBE FILE FORMAT {source_db}.{SCHEMA_NAME}.{ff}")}
            tgt_desc = {r["property"]: r.get("property_value", "") for r in q(f"DESCRIBE FILE FORMAT {target_db}.{SCHEMA_NAME}.{ff}")}
            for prop in sorted(set(src_desc) | set(tgt_desc)):
                sv = str(src_desc.get(prop, "N/A")).strip()
                tv = str(tgt_desc.get(prop, "N/A")).strip()
                if sv != tv:
                    add(SCHEMA_NAME, "FILE FORMAT", ff, "PROPERTY", prop, sv, tv, "DIFFERENT")

        # --- TASKS ---
        print("  Comparing TASKS...")
        src_tasks = {r["name"]: r for r in q(f"SHOW TASKS IN {source_db}.{SCHEMA_NAME}")}
        tgt_tasks = {r["name"]: r for r in q(f"SHOW TASKS IN {target_db}.{SCHEMA_NAME}")}
        common_tasks = compare_existence(SCHEMA_NAME, "TASK", set(src_tasks), set(tgt_tasks))
        for t in common_tasks:
            for prop in ["schedule", "state", "warehouse", "condition"]:
                sv = str(src_tasks[t].get(prop, "")).strip()
                tv = str(tgt_tasks[t].get(prop, "")).strip()
                if sv != tv:
                    add(SCHEMA_NAME, "TASK", t, "PROPERTY", prop.upper(), sv, tv, "DIFFERENT")
            src_def = normalize_def(src_tasks[t].get("definition", ""), source_db, target_db)
            tgt_def = normalize_def(tgt_tasks[t].get("definition", ""), source_db, target_db)
            if src_def != tgt_def:
                add(SCHEMA_NAME, "TASK", t, "DEFINITION", "DEFINITION", src_tasks[t].get("definition", "")[:200], tgt_tasks[t].get("definition", "")[:200], "DIFFERENT")

        # --- STREAMS ---
        print("  Comparing STREAMS...")
        src_streams = {r["name"]: r for r in q(f"SHOW STREAMS IN {source_db}.{SCHEMA_NAME}")}
        tgt_streams = {r["name"]: r for r in q(f"SHOW STREAMS IN {target_db}.{SCHEMA_NAME}")}
        common_streams = compare_existence(SCHEMA_NAME, "STREAM", set(src_streams), set(tgt_streams))
        for s in common_streams:
            for prop in ["table_name", "type", "mode"]:
                sv = str(src_streams[s].get(prop, ""))
                tv = str(tgt_streams[s].get(prop, ""))
                if sv != tv:
                    add(SCHEMA_NAME, "STREAM", s, "PROPERTY", prop.upper(), sv, tv, "DIFFERENT")

        # --- PIPES ---
        print("  Comparing PIPES...")
        src_pipes = {r["name"]: r for r in q(f"SHOW PIPES IN {source_db}.{SCHEMA_NAME}")}
        tgt_pipes = {r["name"]: r for r in q(f"SHOW PIPES IN {target_db}.{SCHEMA_NAME}")}
        common_pipes = compare_existence(SCHEMA_NAME, "PIPE", set(src_pipes), set(tgt_pipes))
        for p in common_pipes:
            src_def = normalize_def(src_pipes[p].get("definition", ""), source_db, target_db)
            tgt_def = normalize_def(tgt_pipes[p].get("definition", ""), source_db, target_db)
            if src_def != tgt_def:
                add(SCHEMA_NAME, "PIPE", p, "DEFINITION", "DEFINITION", src_pipes[p].get("definition", "")[:200], tgt_pipes[p].get("definition", "")[:200], "DIFFERENT")

        # --- SEQUENCES ---
        print("  Comparing SEQUENCES...")
        src_seqs = {r["name"]: r for r in q(f"SHOW SEQUENCES IN {source_db}.{SCHEMA_NAME}")}
        tgt_seqs = {r["name"]: r for r in q(f"SHOW SEQUENCES IN {target_db}.{SCHEMA_NAME}")}
        common_seqs = compare_existence(SCHEMA_NAME, "SEQUENCE", set(src_seqs), set(tgt_seqs))
        for s in common_seqs:
            for prop in ["interval", "ordered"]:
                sv = str(src_seqs[s].get(prop, ""))
                tv = str(tgt_seqs[s].get(prop, ""))
                if sv != tv:
                    add(SCHEMA_NAME, "SEQUENCE", s, "PROPERTY", prop.upper(), sv, tv, "DIFFERENT")

        # --- PROCEDURES ---
        print("  Comparing PROCEDURES...")

        def is_valid_proc(name):
            if not name:
                return False
            n = name.strip().upper()
            return not (
                n.startswith("SYSTEM$") or
                n.startswith("SNOWFLAKE.") or
                n.startswith("INFORMATION_SCHEMA.") or
                n.startswith("GET_") or
                n.startswith("APP_")
            )

            src_procs = {
                r["name"] + "(" + r.get("arguments", "") + ")": r
                for r in q(f"SHOW PROCEDURES IN {SOURCE_DB}.{SCHEMA_NAME}")
                if is_valid_proc(r["name"])
            }
            
            tgt_procs = {
                r["name"] + "(" + r.get("arguments", "") + ")": r
                for r in q(f"SHOW PROCEDURES IN {TARGET_DB}.{SCHEMA_NAME}")
                if is_valid_proc(r["name"])
            }
            
            common_procs = compare_existence(
                SCHEMA_NAME,
                "PROCEDURE",
                set(src_procs),
                set(tgt_procs)
            )
            
            for p in common_procs:
                for prop in ["language", "is_secure"]:
                    sv = str(src_procs[p].get(prop, ""))
                    tv = str(tgt_procs[p].get(prop, ""))
                    if sv != tv:
                        add(
                            SCHEMA_NAME,
                            "PROCEDURE",
                            p,
                            "PROPERTY",
                            prop.upper(),
                            sv,
                            tv,
                            "DIFFERENT"
                        )
            
        
        # --- FUNCTIONS ---
        print("  Comparing FUNCTIONS...")
        src_funcs = {r["name"] + "(" + r.get("arguments", "") + ")": r for r in q(f"SHOW USER FUNCTIONS IN {source_db}.{SCHEMA_NAME}")}
        tgt_funcs = {r["name"] + "(" + r.get("arguments", "") + ")": r for r in q(f"SHOW USER FUNCTIONS IN {target_db}.{SCHEMA_NAME}")}
        common_funcs = compare_existence(SCHEMA_NAME, "FUNCTION", set(src_funcs), set(tgt_funcs))
        for f in common_funcs:
            for prop in ["language", "is_secure"]:
                sv = str(src_funcs[f].get(prop, ""))
                tv = str(tgt_funcs[f].get(prop, ""))
                if sv != tv:
                    add(SCHEMA_NAME, "FUNCTION", f, "PROPERTY", prop.upper(), sv, tv, "DIFFERENT")

    return results


# --- Run comparison ---
print(f"Comparing {SOURCE_DB} vs {TARGET_DB}")
print(f"Schemas: {SCHEMAS}")
print("=" * 60)

results = run_comparison(SOURCE_DB, TARGET_DB, SCHEMAS)
df = pd.DataFrame(results)

print(f"\n{'=' * 60}")
print(f"Total differences/objects found: {len(df)}")
if not df.empty:
    print(f"\nBreakdown by status:")
    print(df["STATUS"].value_counts().to_string())

# --- Store results ---
session.sql(f"""
    CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
        RUN_DATETIME    TIMESTAMP_NTZ,
        SOURCE_DB       STRING,
        TARGET_DB       STRING,
        SCHEMA          STRING,
        OBJECT_TYPE     STRING,
        OBJECT_NAME     STRING,
        DETAIL_TYPE     STRING,
        PROPERTY        STRING,
        SOURCE_VALUE    STRING,
        TARGET_VALUE    STRING,
        STATUS          STRING
    )
""").collect()

# Insert results
run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
insert_count = 0
for _, row in df.iterrows():
    vals = [
        run_ts,
        SOURCE_DB.replace("'", "''"),
        TARGET_DB.replace("'", "''"),
        row["SCHEMA"].replace("'", "''"),
        row["OBJECT_TYPE"].replace("'", "''"),
        row["OBJECT_NAME"].replace("'", "''"),
        row["DETAIL_TYPE"].replace("'", "''"),
        row["PROPERTY"].replace("'", "''"),
        str(row["SOURCE_VALUE"]).replace("'", "''")[:500],
        str(row["TARGET_VALUE"]).replace("'", "''")[:500],
        row["STATUS"].replace("'", "''"),
    ]
    session.sql(f"""
        INSERT INTO {RESULTS_TABLE} VALUES (
            '{vals[0]}', '{vals[1]}', '{vals[2]}', '{vals[3]}',
            '{vals[4]}', '{vals[5]}', '{vals[6]}', '{vals[7]}',
            '{vals[8]}', '{vals[9]}', '{vals[10]}'
        )
    """).collect()
    insert_count += 1

print(f"\nInserted {insert_count} rows into {RESULTS_TABLE}")

# Purge old results
cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
session.sql(f"""
    DELETE FROM {RESULTS_TABLE}
    WHERE RUN_DATETIME < '{cutoff}'::TIMESTAMP_NTZ
""").collect()
print(f"Purged rows older than {RETENTION_DAYS} days")
