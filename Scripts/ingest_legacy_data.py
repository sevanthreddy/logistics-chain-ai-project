from pathlib import Path
import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# __file__ is 'experiment/phase-0/ingest_legacy_data.py'
script_dir = Path(__file__).resolve().parent # points to experiment/phase-0
project_root = script_dir.parents[0] # climbs up 1 levels to project root

load_dotenv(project_root / ".env")

data_path = project_root / "Data" / "Raw" / "dynamic_supply_chain_logistics_dataset.csv"
db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_port = os.getenv("SQL_SERVER_PORT", "1434")
db_name = os.getenv("SQL_DATABASE_NAME", "cold_chain")
db_user = os.getenv("SQL_ADMIN_USER")
db_password = os.getenv("SQL_ADMIN_PASSWORD")

# 1. Load the raw dataset
print(f"Loading CSV from {data_path}...")
df = pd.read_csv(data_path)

# 2. Map clean columns to a messy 2000s legacy enterprise schema
legacy_mapping = {
    'timestamp': 'TS_UTC',
    'vehicle_gps_latitude': 'V_LAT',
    'vehicle_gps_longitude': 'V_LON',
    'iot_temperature': 'IOT_TEMP_VAL_C',
    'cargo_condition_status': 'CGO_COND_CD',
    'risk_classification': 'RISK_CLS_TXT',
    'delay_probability': 'DELAY_PROB_DEC',
    'port_congestion_level': 'PRT_CNG_LVL',
    'route_risk_level': 'RT_RSK_IDX'
}

# Keep only the columns we mapped for this demo and rename them
df_legacy = df[list(legacy_mapping.keys())].rename(columns=legacy_mapping)

# 3. Connect to Docker MSSQL Server
print("Connecting to legacy MSSQL Database...")

try:
    import pymssql  # noqa: F401
    pymssql_available = True
except Exception:
    pymssql_available = False

if pymssql_available:
    connection_string = (
        f"mssql+pymssql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
    )
else:
    # Fallback for systems that have the SQL Server ODBC driver installed.
    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={db_host},{db_port};"
        f"DATABASE={db_name};"
        f"UID={db_user};"
        f"PWD={db_password};"
        f"Encrypt=no;"
        f"TrustServerCertificate=yes;"
    )
    params = quote_plus(connection_string)
    connection_string = f"mssql+pyodbc:///?odbc_connect={params}"

engine = create_engine(connection_string)

# 4. Ingest data into the messy table name
table_name = 'TBL_SC_FLEET_HIST_RAW'
print(f"Ingesting into {table_name}. This may take a minute...")
df_legacy.to_sql(
    table_name,
    engine,
    if_exists='append',
    index=False,
    schema='dbo'
)

print("✅ Legacy data ingestion complete!")