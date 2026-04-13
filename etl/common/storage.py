import os

from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient


def get_service_client() -> DataLakeServiceClient:
    account = os.environ["AZURE_STORAGE_ACCOUNT"]
    account_url = f"https://{account}.dfs.core.windows.net"
    credential = DefaultAzureCredential()
    return DataLakeServiceClient(account_url=account_url, credential=credential)


def upload_text(file_system: str, path: str, content: str) -> None:
    svc = get_service_client()
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(path)

    if file_client.exists():
        file_client.delete_file()

    payload = content.encode("utf-8")
    file_client.create_file()
    file_client.append_data(payload, offset=0, length=len(payload))
    file_client.flush_data(len(payload))
