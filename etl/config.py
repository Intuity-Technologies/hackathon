import os

PIPELINE_DATA_MODE = os.getenv("PIPELINE_DATA_MODE", "auto")
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")

RAW_FS = os.getenv("RAW_FILE_SYSTEM", "raw")
CURATED_FS = os.getenv("CURATED_FILE_SYSTEM", "curated")
SIGNALS_FS = os.getenv("SIGNALS_FILE_SYSTEM", "signals")
DEMO_FS = os.getenv("DEMO_ARTIFACTS_FILE_SYSTEM", "demo")

AREA_LEVEL = os.getenv("AREA_LEVEL", "county")
