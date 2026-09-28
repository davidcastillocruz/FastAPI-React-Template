"""
In-memory store for translated responses and exceptions.

Loads `language_responses.json` once at app startup and keeps it in a
normalized structure for fast, lock-free lookups at runtime. The store
is built as:

    _DATA[section][entry_id][lang] = payload

where `lang` is always reduced to its base form (e.g. `"es-MX"` becomes
`"es"`). A secondary index maps symbolic names to numeric ids, so callers
can reference entries either by `id` or by `name`.

The JSON is never re-read during runtime. If the file changes on disk,
the process must be restarted (or `load()` called again) for the changes
to take effect.
"""

import json
from pathlib import Path

from src.core.logger import get_logger

logger = get_logger(__name__)

DATA_PATH = Path(__file__).parent.parent.parent / "language_responses.json"

# Keys that are metadata, not languages. They are skipped when building
# the per-language payload map.
META_KEYS = {"id", "name"}

# Module-level state. Both dicts are replaced atomically by `load()`,
# so reads are lock-free and never observe a partially-built state.
_DATA: dict[str, dict[int, dict[str, dict]]] = {}      # {section: {entry_id: {lang: payload}}}
_NAME_INDEX: dict[str, dict[str, int]] = {}     # {section: {name: entry_id}}


def load() -> None:
    """Load and normalize the translations JSON into memory.

    Reads `DATA_PATH`, validates it, and rebuilds both `_DATA` and
    `_NAME_INDEX`. Intended to be called once at app startup (see the
    `lifespan` handler). Can be called again to reload changes without
    restarting the process.

    The JSON is expected to have the shape:

        {
            "section": [
                {
                    "id":   0,
                    "name": "SYMBOLIC_NAME",
                    "en":   { ... payload ... },
                    "es":   { ... payload ... }
                },
                ...
            ]
        }

    Raises:
        ValueError: If an entry is missing a `name`, or if `id` or `name`
            are duplicated within a section.
        FileNotFoundError: If `DATA_PATH` does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    global _DATA, _NAME_INDEX

    with DATA_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    normalized: dict[str, dict[int, dict[str, dict]]] = {}
    name_index: dict[str, dict[str, int]] = {}

    for section, entries in raw.items():
        section_data: dict[int, dict[str, dict]] = {}
        section_names: dict[str, int] = {}

        for entry in entries:
            entry_id = int(entry["id"])

            if entry_id in section_data:
                raise ValueError(
                    f"Duplicate entry_id {entry_id} in section '{section}'"
                )

            name = entry.get("name")
            if not name:
                raise ValueError(
                    f"Entry {entry_id} in section '{section}' is missing a 'name'"
                )
            if name in section_names:
                raise ValueError(
                    f"Duplicate name '{name}' in section '{section}'"
                )

            # Everything that is not metadata is a language key.
            langs = {
                key.split("-")[0].lower(): value
                for key, value in entry.items()
                if key not in META_KEYS
            }
            section_data[entry_id] = langs
            section_names[name] = entry_id

        normalized[section] = section_data
        name_index[section] = section_names

    # Atomic swap: both globals are replaced at once. Readers either see
    # the old state or the new one, never a mix.
    _DATA = normalized
    _NAME_INDEX = name_index

    logger.info(
        "TRANSLATIONS_LOADED",
        path=str(DATA_PATH),
        sections=list(normalized.keys()),
        entries=sum(len(v) for v in normalized.values()),
    )


def get_entry_id_by_name(section: str, name: str) -> int | None:
    """Resolve a symbolic name to its numeric entry id.

    Args:
        section: Section to look in (e.g. `"responses"`, `"exceptions"`).
        name: Symbolic name as declared in the JSON (e.g. `"INVALID_EMAIL"`).

    Returns:
        The numeric id, or `None` if the section or name does not exist.
    """
    section_names = _NAME_INDEX.get(section)
    if section_names is None:
        return None
    return section_names.get(name)


def get_data_raw(section: str, entry_id: int, lang: str) -> dict | None:
    """Look up the payload for a given section, entry, and language.

    Returns the payload as stored in memory. The caller is responsible
    for copying it before mutating (see `language_manager.get_data`).

    Args:
        section: Section to look in (e.g. `"responses"`, `"exceptions"`).
        entry_id: Numeric id of the entry within the section.
        lang: Base language code (e.g. `"es"`, `"en"`).

    Returns:
        The payload dict, or `None` if any of the three keys is missing.
    """
    section_data = _DATA.get(section)
    if section_data is None:
        return None
    translations = section_data.get(entry_id)
    if translations is None:
        return None
    return translations.get(lang)