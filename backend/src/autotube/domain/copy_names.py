from __future__ import annotations

COPY_NAME_SUFFIX = " (copy)"


def copy_name(name: str, max_length: int) -> str:
    kept = name.strip()[: max_length - len(COPY_NAME_SUFFIX)].rstrip()
    return f"{kept}{COPY_NAME_SUFFIX}"
