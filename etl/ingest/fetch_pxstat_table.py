import argparse
import os
from datetime import datetime, timezone

import requests
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient


def build_url(table_id: str, fmt: str) -> str:
    return (
        "https://ws.cso.ie/public/api.restful/"
        f"PxStat.Data.Cube_API.ReadDataset/{table_id}/{fmt}/1.0/"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download CSO PxStat table and upload to ADLS."
    )
    parser.add_argument("table_id", help="PxStat table id, e.g. PEA08 or RIQ02")
    parser.add_argument(
        "--format",
        default="CSV",
        help="Output format in endpoint URL (default: CSV)",
    )
    parser.add_argument(
        "--file-system",
        default=os.getenv("RAW_FILE_SYSTEM", "raw"),
        help="ADLS file system/container to write into (default: raw)",
    )
    parser.add_argument(
        "--blob-path",
        default=None,
        help=(
            "Optional ADLS path. Default: pxstat/<TABLE>/<TABLE>.<UTCSTAMP>.<ext>"
        ),
    )
    args = parser.parse_args()

    url = build_url(args.table_id, args.format.upper())
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    ext = args.format.lower()
    blob_path = args.blob_path or f"pxstat/{args.table_id}/{args.table_id}.{stamp}.{ext}"

    account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not account:
        raise ValueError("AZURE_STORAGE_ACCOUNT env var not set")

    svc = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    fs = svc.get_file_system_client(args.file_system)
    file_client = fs.get_file_client(blob_path)
    payload = response.content

    if file_client.exists():
        file_client.delete_file()
    file_client.create_file()
    file_client.append_data(data=payload, offset=0, length=len(payload))
    file_client.flush_data(len(payload))
    print(f"Saved {args.table_id} to {args.file_system}/{blob_path}")


if __name__ == "__main__":
    main()
