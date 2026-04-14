import argparse
import os
from datetime import datetime, timezone

import requests
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient


def _service_client() -> DataLakeServiceClient:
    account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not account:
        raise ValueError("AZURE_STORAGE_ACCOUNT env var not set")
    return DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def _upload(file_system: str, blob_path: str, payload: bytes) -> None:
    svc = _service_client()
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(blob_path)
    if file_client.exists():
        file_client.delete_file()
    file_client.create_file()
    file_client.append_data(payload, offset=0, length=len(payload))
    file_client.flush_data(len(payload))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a Central Bank dataset URL and upload the raw payload to ADLS."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Central Bank Open Data URL returning CSV or JSON payload.",
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Stable dataset identifier used in ADLS path.",
    )
    parser.add_argument(
        "--format",
        default="csv",
        choices=["csv", "json"],
        help="Payload extension used for storage path.",
    )
    parser.add_argument(
        "--file-system",
        default=os.getenv("RAW_FILE_SYSTEM", "raw"),
        help="ADLS file system/container name",
    )
    parser.add_argument(
        "--blob-path",
        default=None,
        help="Optional destination path inside ADLS",
    )
    args = parser.parse_args()

    response = requests.get(args.url, timeout=120)
    response.raise_for_status()
    payload = response.content

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    blob_path = args.blob_path or (
        f"central_bank/{args.dataset_id}/{args.dataset_id}.{stamp}.{args.format}"
    )
    _upload(args.file_system, blob_path, payload)
    print(f"Saved {args.dataset_id} to {args.file_system}/{blob_path}")


if __name__ == "__main__":
    main()
