from typing import Any


def clean_nones(value: Any) -> Any:
    if isinstance(value, list):
        return [clean_nones(x) for x in value if x is not None]
    elif isinstance(value, dict):
        return {
            key: clean_nones(val)
            for key, val in value.items()
            if val is not None
        }
    else:
        return value

def str_to_bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    if not value:
        return False
    return value.lower() in ('true', 't', 'yes', 'y', '1', 'on')
