import argparse
import csv
import io
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


def _build_url(country: str, indicator: str, per_page: int) -> str:
    return (
        "https://api.worldbank.org/v2/country/"
        f"{country}/indicator/{indicator}?format=json&per_page={per_page}"
    )


def _to_csv_bytes(records: list[dict]) -> bytes:
    if not records:
        raise ValueError("World Bank API returned no rows for this query.")

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "country_iso2",
            "country_name",
            "indicator_id",
            "indicator_name",
            "date",
            "value",
            "unit",
            "obs_status",
            "decimal",
        ],
    )
    writer.writeheader()
    for row in records:
        writer.writerow(
            {
                "country_iso2": row.get("countryiso3code"),
                "country_name": (row.get("country") or {}).get("value"),
                "indicator_id": (row.get("indicator") or {}).get("id"),
                "indicator_name": (row.get("indicator") or {}).get("value"),
                "date": row.get("date"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "obs_status": row.get("obs_status"),
                "decimal": row.get("decimal"),
            }
        )
    return output.getvalue().encode("utf-8")


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
        description="Download a World Bank indicator and upload CSV to ADLS."
    )
    parser.add_argument("indicator", help="World Bank indicator code")
    parser.add_argument(
        "--country",
        default="IE",
        help="World Bank country code (default: IE)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=20000,
        help="Rows per page (default: 20000)",
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

    url = _build_url(args.country, args.indicator, args.per_page)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("Unexpected World Bank API response format.")

    rows = payload[1] or []
    csv_payload = _to_csv_bytes(rows)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    blob_path = args.blob_path or (
        f"world_bank/{args.indicator}/{args.country}.{stamp}.csv"
    )
    _upload(args.file_system, blob_path, csv_payload)
    print(f"Saved {len(rows)} rows to {args.file_system}/{blob_path}")


if __name__ == "__main__":
    main()
