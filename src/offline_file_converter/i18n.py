import json
from importlib.resources import files
from typing import TypeAlias, cast

Strings: TypeAlias = dict[str, str]


def load_strings(locale: str = "ru") -> Strings:
    resource = files("offline_file_converter.resources.i18n").joinpath(f"{locale}.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
    ):
        raise ValueError(f"Invalid translation file: {resource}")
    return cast(Strings, payload)
