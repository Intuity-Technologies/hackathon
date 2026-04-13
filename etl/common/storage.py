from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.filedatalake import DataLakeServiceClient
except ImportError:  # pragma: no cover - local-only runtime without Azure extras
    DefaultAzureCredential = None
    DataLakeServiceClient = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class StorageBackend:
    data_mode: str

    def read_csv(self, file_system: str, path: str) -> pd.DataFrame:
        raise NotImplementedError

    def read_parquet(self, file_system: str, path: str) -> pd.DataFrame:
        raise NotImplementedError

    def read_text(self, file_system: str, path: str) -> str:
        raise NotImplementedError

    def write_bytes(self, file_system: str, path: str, payload: bytes) -> None:
        raise NotImplementedError

    def exists(self, file_system: str, path: str) -> bool:
        raise NotImplementedError

    def write_json(self, file_system: str, path: str, payload: Any) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        self.write_text(file_system, path, content)

    def write_parquet(self, file_system: str, path: str, df: pd.DataFrame) -> None:
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        self.write_bytes(file_system, path, buffer.getvalue())

    def write_text(self, file_system: str, path: str, content: str) -> None:
        self.write_bytes(file_system, path, content.encode("utf-8"))


@dataclass(slots=True)
class LocalStorageBackend(StorageBackend):
    root: Path

    def _resolve_path(self, file_system: str, path: str) -> Path:
        raw = Path(path)
        if raw.is_absolute():
            return raw
        if file_system:
            return self.root / file_system / raw
        return self.root / raw

    def read_csv(self, file_system: str, path: str) -> pd.DataFrame:
        return pd.read_csv(self._resolve_path(file_system, path))

    def read_parquet(self, file_system: str, path: str) -> pd.DataFrame:
        return pd.read_parquet(self._resolve_path(file_system, path))

    def read_text(self, file_system: str, path: str) -> str:
        return self._resolve_path(file_system, path).read_text(encoding="utf-8")

    def write_bytes(self, file_system: str, path: str, payload: bytes) -> None:
        target = self._resolve_path(file_system, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def exists(self, file_system: str, path: str) -> bool:
        return self._resolve_path(file_system, path).exists()


@dataclass(slots=True)
class AdlsStorageBackend(StorageBackend):
    account: str
    _service_client: Any = field(init=False)

    def __post_init__(self) -> None:
        if DataLakeServiceClient is None or DefaultAzureCredential is None:
            raise ImportError("Azure storage dependencies are required for ADLS mode")
        self._service_client = DataLakeServiceClient(
            account_url=f"https://{self.account}.dfs.core.windows.net",
            credential=DefaultAzureCredential(),
        )

    def _file_client(self, file_system: str, path: str):
        fs = self._service_client.get_file_system_client(file_system)
        return fs.get_file_client(path)

    def read_csv(self, file_system: str, path: str) -> pd.DataFrame:
        payload = self._file_client(file_system, path).download_file().readall()
        return pd.read_csv(io.BytesIO(payload))

    def read_parquet(self, file_system: str, path: str) -> pd.DataFrame:
        payload = self._file_client(file_system, path).download_file().readall()
        return pd.read_parquet(io.BytesIO(payload))

    def read_text(self, file_system: str, path: str) -> str:
        payload = self._file_client(file_system, path).download_file().readall()
        return payload.decode("utf-8")

    def write_bytes(self, file_system: str, path: str, payload: bytes) -> None:
        file_client = self._file_client(file_system, path)
        if file_client.exists():
            file_client.delete_file()
        file_client.create_file()
        file_client.append_data(payload, offset=0, length=len(payload))
        file_client.flush_data(len(payload))

    def exists(self, file_system: str, path: str) -> bool:
        return self._file_client(file_system, path).exists()


def get_service_client() -> DataLakeServiceClient:
    if DataLakeServiceClient is None or DefaultAzureCredential is None:
        raise ImportError("Azure storage dependencies are required for ADLS access")
    account = os.environ["AZURE_STORAGE_ACCOUNT"]
    account_url = f"https://{account}.dfs.core.windows.net"
    credential = DefaultAzureCredential()
    return DataLakeServiceClient(account_url=account_url, credential=credential)


def build_storage_backend(mode: str | None = None) -> StorageBackend:
    resolved_mode = (mode or os.getenv("PIPELINE_DATA_MODE", "auto")).strip().lower()
    account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()

    if resolved_mode == "auto":
        resolved_mode = "adls" if account else "local"

    if resolved_mode == "adls":
        if not account:
            raise ValueError("AZURE_STORAGE_ACCOUNT env var not set for ADLS mode")
        return AdlsStorageBackend(data_mode="adls", account=account)

    if resolved_mode != "local":
        raise ValueError(f"Unsupported PIPELINE_DATA_MODE: {resolved_mode}")

    root = Path(os.getenv("LOCAL_DATA_ROOT", _repo_root() / "data"))
    return LocalStorageBackend(data_mode="local", root=root)


def upload_text(file_system: str, path: str, content: str) -> None:
    storage = build_storage_backend("adls")
    storage.write_text(file_system, path, content)
