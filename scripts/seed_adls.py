import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from etl.common.storage import build_storage_backend, get_service_client
from service.housing_data import write_demo_artifacts, _load_signals_dataframe

def main():
    print("Setting up Azure Data Lake Storage containers...")
    service_client = get_service_client()
    
    # Ensure containers exist
    for fs_name in ["signals", "demo"]:
        try:
            service_client.create_file_system(file_system=fs_name)
            print(f" [+] Created file system (container): '{fs_name}'")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e) or "ResourceExistsError" in str(e) or "ErrorCode:ContainerAlreadyExists" in str(e):
                print(f" [=] File system '{fs_name}' already exists.")
            else:
                print(f" [!] Warning creating '{fs_name}': {e}")

    # Upload the base signals parquet file manually using our AdlsStorageBackend
    adls_backend = build_storage_backend("adls")
    storage_path = "housing_pressure/area_level=county/part-000.parquet"
    local_path = Path("data/signals/housing_pressure/area_level=county/part-000.parquet")
    
    if local_path.exists():
        print(f"\nUploading local signals data from '{local_path}' to ADLS 'signals/{storage_path}'...")
        payload = local_path.read_bytes()
        adls_backend.write_bytes("signals", storage_path, payload)
        print(" [+] Upload successful.")
    else:
        print(f" [!] Could not find local file '{local_path}'. Is your data folder intact?")
        return

    # Use the pipeline script to generate and upload the demo artifacts to ADLS
    print("\nGenerating Demo Artifacts and pushing them directly to ADLS 'demo' container...")
    # Because we're in ADLS mode, `write_demo_artifacts` will automatically push outputs to Azure
    bundle = write_demo_artifacts()
    
    print("\nAll done! Your Azure Storage account is now fully seeded with Data Lake files.")
    print("You can now safely run 'python web.py'")

if __name__ == "__main__":
    main()
