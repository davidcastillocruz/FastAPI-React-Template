import json
import logging
from pathlib import Path

from src.core.settings import BASE_DIR, SRC_DIR, settings

logger = logging.getLogger(__name__)


# Shape of the loaded translations: response name -> language -> text key -> text
type Translations = dict[str, dict[str, dict[str, str]]]

# Values that fill the %s of each text of a response: {"detail": ("email",)}
type TextArgs = dict[str, tuple[object, ...]]

# Every *_translations.json inside src/: core/translations has the shared ones, mail/templates/<email>/translations
# the texts of the emails, modules/<module>/translations the ones of each module
LANGUAGE_DATA: Translations = {}


# json.load keeps only the last of two equal keys without saying anything: a repeated response
# or text inside the same file would silently replace the other one -> stop startup
def _reject_repeated_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"Repeated keys: {repeated}")
    return dict(pairs)


# Reads one translations file, stops startup if it can't be read or isn't a JSON object
def _read_translations_file(file: Path) -> dict[str, object]:
    path = file.relative_to(BASE_DIR).as_posix()

    try:
        # utf-8-sig also reads the files that some editors save with a BOM at the start
        with file.open("r", encoding="utf-8-sig") as f:
            data = json.load(f, object_pairs_hook=_reject_repeated_keys)

    except json.JSONDecodeError as exc:
        logger.critical(
            "Invalid JSON in translations file: %s",
            exc.msg,
            extra={"path": path, "line": exc.lineno, "column": exc.colno},
        )
        raise

    except UnicodeDecodeError:
        logger.critical("Translations file is not valid UTF-8", extra={"path": path})
        raise

    # After the two above: JSONDecodeError and UnicodeDecodeError are ValueErrors too
    except ValueError as exc:
        logger.critical("Repeated key in translations file: %s", exc, extra={"path": path})
        raise

    except OSError:
        # Permission denied, file is a directory, disk errors...
        logger.exception("Could not read translations file", extra={"path": path})
        raise

    if not isinstance(data, dict):
        logger.critical(
            "Translations file must contain a JSON object",
            extra={"path": path, "type": type(data).__name__},
        )
        raise TypeError(f"Expected a dict in {path}, got {type(data).__name__}")

    return data


# Loads every translations file into LANGUAGE_DATA on startup. A file that can't be served in every language
# stops the app here, instead of failing later with a 500 for the users of one language
def setup_language_system() -> None:
    global LANGUAGE_DATA

    files = sorted(SRC_DIR.rglob("translations/*_translations.json"))
    if not files:
        logger.critical("No translations files found", extra={"path": SRC_DIR.relative_to(BASE_DIR).as_posix()})
        raise FileNotFoundError(f"No translations/*_translations.json files in {SRC_DIR}")

    available = set(settings.AVAILABLE_LANGUAGES)
    data: Translations = {}
    # File of each response, to report where a repeated name is
    sources: dict[str, str] = {}

    for file in files:
        path = file.relative_to(BASE_DIR).as_posix()

        for name, languages in _read_translations_file(file).items():
            # Same name in two files: one would silently replace the other -> stop startup
            if name in sources:
                logger.critical(
                    "Response defined in two translations files",
                    extra={"entry": name, "files": [sources[name], path]},
                )
                raise ValueError(f"Response '{name}' is in {sources[name]} and {path}")

            if not isinstance(languages, dict):
                logger.critical(
                    "Invalid response entry, languages must be an object",
                    extra={"path": path, "entry": name, "type": type(languages).__name__},
                )
                raise TypeError(f"Expected a dict in {path} [{name}], got {type(languages).__name__}")

            # AVAILABLE_LANGUAGES is read in lowercase: a "pt-BR" key would never match "pt-br"
            uppercase = sorted(language for language in languages if language != language.lower())
            if uppercase:
                logger.critical(
                    "Language codes must be lowercase",
                    extra={"path": path, "entry": name, "languages": uppercase},
                )
                raise ValueError(f"Response '{name}' in {path} has language codes not in lowercase: {uppercase}")

            # Missing languages: the response can't be served -> stop startup
            missing = available - set(languages)
            if missing:
                logger.critical(
                    "Response is missing available languages",
                    extra={"path": path, "entry": name, "missing": sorted(missing)},
                )
                raise ValueError(f"Response '{name}' in {path} is missing languages: {sorted(missing)}")

            for language, texts in languages.items():
                # Extra languages: harmless, just never used
                if language not in available:
                    logger.warning(
                        "Response has a language not in AVAILABLE_LANGUAGES, it will be ignored",
                        extra={"path": path, "entry": name, "language": language},
                    )
                    continue

                if not isinstance(texts, dict):
                    logger.critical(
                        "Invalid translation, texts must be an object",
                        extra={"path": path, "entry": name, "language": language, "type": type(texts).__name__},
                    )
                    raise TypeError(f"Expected a dict in {path} [{name}][{language}], got {type(texts).__name__}")

                # Every text is a string, a number or a list would reach the client as it is
                for key, text in texts.items():
                    if not isinstance(text, str):
                        logger.critical(
                            "Invalid translation, every text must be a string",
                            extra={"path": path, "entry": name, "language": language, "text": key},
                        )
                        raise TypeError(
                            f"Expected a string in {path} [{name}][{language}][{key}], got {type(text).__name__}",
                        )

            # Same texts in every language (detail, message...), or asking for one of them would fail later
            texts_by_language = {language: sorted(languages[language]) for language in sorted(available)}
            if len({tuple(texts) for texts in texts_by_language.values()}) > 1:
                logger.critical(
                    "Response has different texts in each language",
                    extra={"path": path, "entry": name, "texts": texts_by_language},
                )
                raise ValueError(
                    f"Response '{name}' in {path} has different texts in each language: {texts_by_language}",
                )

            # Same number of %s in every language, or filling the text would fail in one of them
            # (a 500 only for the users of that language). %% is a literal %, not a placeholder
            for key in languages[settings.MAIN_LANGUAGE]:
                placeholders = {
                    language: languages[language][key].replace("%%", "").count("%s") for language in sorted(available)
                }
                if len(set(placeholders.values())) > 1:
                    logger.critical(
                        "Response has a different number of %s in each language",
                        extra={"path": path, "entry": name, "text": key, "placeholders": placeholders},
                    )
                    raise ValueError(
                        f"Response '{name}' in {path} [{key}] has a different number of %s in each language: "
                        f"{placeholders}",
                    )

                # A text with %s must be fillable: a literal % next to a %s has to be written %%
                # ("50% off for %s" would fail when filled, "50%% off for %s" works)
                count = placeholders[settings.MAIN_LANGUAGE]
                for language in sorted(available) if count else []:
                    try:
                        _ = languages[language][key] % (("x",) * count)
                    except (TypeError, ValueError):
                        logger.critical(
                            "Response can't be filled, write a literal % as %%",
                            extra={"path": path, "entry": name, "language": language, "text": key},
                        )
                        raise ValueError(
                            f"Response '{name}' in {path} [{language}][{key}] can't be filled, "
                            "write a literal % as %%",
                        ) from None

            # Only the available languages, the extra ones were not validated
            data[name] = {language: languages[language] for language in available}
            sources[name] = path

    LANGUAGE_DATA = data
    logger.info(
        "Language system loaded",
        extra={"files": len(files), "responses": len(LANGUAGE_DATA), "languages": sorted(available)},
    )


# Texts of a response in the given language
# args fills the %s of each text: {"detail": ("email",)}. Texts without args are returned as they are,
# so a literal % only needs to be written %% in texts that take args
def get_response(name: str, language: str, args: TextArgs | None = None) -> dict[str, str]:
    args = args or {}

    try:
        texts = LANGUAGE_DATA[name][language]
        return {key: text % args[key] if key in args else text for key, text in texts.items()}

    except KeyError:
        logger.error("Response not found", extra={"entry": name, "language": language})
        raise

    except (TypeError, ValueError):
        # Wrong number/type of placeholder args. Only how many were given: the values may be personal data
        logger.error(
            "Invalid arguments for response",
            extra={
                "entry": name,
                "language": language,
                "args_given": {key: len(values) for key, values in args.items()},
            },
        )
        raise


# The "detail" text of an error response, fails if the entry has no "detail"
def get_error_detail(name: str, language: str, args: TextArgs | None = None) -> str:
    return get_response(name, language, args)["detail"]
