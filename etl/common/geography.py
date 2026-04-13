from typing import Dict


def normalize_area_name(name: str) -> str:
    return " ".join(str(name).strip().split())


def apply_name_map(name: str, aliases: Dict[str, str]) -> str:
    normalized = normalize_area_name(name)
    return aliases.get(normalized, normalized)
