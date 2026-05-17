"""File processing service for translation file import/export.

Handles CSV/JSON parsing, validation, and file generation.
"""
import csv
import io
import json
from typing import List, Dict, Any, Tuple
from config import settings
from utils.logger import get_logger

logger = get_logger("file_service")

REQUIRED_COLUMNS = {"type", "key", "en"}


def parse_csv_file(file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse CSV file into list of dicts.
    
    Args:
        file_content: CSV file content as bytes
        
    Returns:
        Tuple of (rows, columns) where rows is list of dicts and columns is list of column names
        
    Raises:
        ValueError: If required columns are missing
    """
    try:
        content_str = file_content.decode('utf-8')
        
        # Detect delimiter by counting occurrences in first line
        sample = content_str.split('\n')[0]
        semicolon_count = sample.count(';')
        comma_count = sample.count(',')
        delimiter = ';' if semicolon_count >= comma_count else ','
        
        reader = csv.DictReader(io.StringIO(content_str), delimiter=delimiter)
        rows = list(reader)
        columns = reader.fieldnames or []
        
        # Clean column names (strip whitespace, remove empty columns, strip trailing delimiters and commas)
        columns = [col.strip().rstrip(delimiter).rstrip(',').strip() for col in columns if col.strip()]
        
        if not rows:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        missing_columns = REQUIRED_COLUMNS - set(columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}. Found columns: {columns}")
        
        logger.info("csv_parsed", rows=len(rows), columns=columns, delimiter=delimiter)
        logger.debug("csv_first_row", first_row=rows[0] if rows else None)
        return rows, columns
        
    except UnicodeDecodeError:
        raise ValueError("CSV file must be UTF-8 encoded")
    except Exception as exc:
        logger.exception("csv_parse_error", error=str(exc))
        raise ValueError(f"Failed to parse CSV: {str(exc)}")


def parse_json_file(file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse JSON file into list of dicts.
    
    Args:
        file_content: JSON file content as bytes
        
    Returns:
        Tuple of (rows, columns) where rows is list of dicts and columns is list of column names
        
    Raises:
        ValueError: If required columns are missing or JSON is invalid
    """
    try:
        content_str = file_content.decode('utf-8')
        data = json.loads(content_str)
        
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON file is empty")
        
        rows = data
        columns = list(rows[0].keys()) if rows else []
        
        # Clean column names (strip whitespace, remove empty columns, strip trailing delimiters and commas)
        columns = [col.strip().rstrip(',').rstrip(';').strip() for col in columns if col.strip()]
        
        # Validate required columns
        missing_columns = REQUIRED_COLUMNS - set(columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logger.info("json_parsed", rows=len(rows), columns=columns)
        return rows, columns
        
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {str(exc)}")
    except UnicodeDecodeError:
        raise ValueError("JSON file must be UTF-8 encoded")
    except Exception as exc:
        logger.exception("json_parse_error", error=str(exc))
        raise ValueError(f"Failed to parse JSON: {str(exc)}")


def validate_locale_columns(columns: List[str], valid_locales: List[str]) -> Dict[str, Any]:
    """Check all non-required columns are valid Pepsi locales.
    
    Args:
        columns: All column names from file
        valid_locales: List of valid locale codes from pepsi_languages table
        
    Returns:
        Dict with:
            - valid: bool
            - invalid_locales: List[str] of invalid locale columns
            - valid_locales: List[str] of valid locale columns (excluding required)
    """
    required_columns = {"type", "key", "en"}
    locale_columns = [col for col in columns if col not in required_columns]
    
    # Clean locale columns (strip trailing delimiters and commas)
    locale_columns = [col.strip().rstrip(',').rstrip(';').strip() for col in locale_columns]
    
    invalid_locales = [col for col in locale_columns if col not in valid_locales]
    valid_locale_cols = [col for col in locale_columns if col in valid_locales]
    
    result = {
        "valid": len(invalid_locales) == 0,
        "invalid_locales": invalid_locales,
        "valid_locales": valid_locale_cols,
    }
    
    logger.info("locale_validation", result=result)
    return result


def prepare_translation_items(
    rows: List[Dict[str, Any]], 
    locale_columns: List[str],
    skip_ai_if_exists: bool = True
) -> Dict[str, Any]:
    """Split rows into existing translations (upsert) and missing translations (need AI).
    
    Args:
        rows: Parsed file rows
        locale_columns: List of locale columns (excluding type, key, en)
        skip_ai_if_exists: If True, skip AI translation for filled cells
        
    Returns:
        Dict with:
            - existing: List of dicts for create_translation (filled locales)
            - missing: List of dicts for ai_translate (empty locales)
            - keys: Set of all keys in file
    """
    existing = []
    missing = []
    keys = set()
    
    # Clean locale columns (strip trailing delimiters and commas)
    locale_columns = [col.strip().rstrip(',').rstrip(';').strip() for col in locale_columns]
    
    logger.info("prepare_translation_items.start", rows_count=len(rows), locale_columns=locale_columns)
    
    for row in rows:
        # Clean row keys as well to match cleaned column names
        cleaned_row = {k.strip().rstrip(',').rstrip(';').strip(): v for k, v in row.items()}
        
        key = cleaned_row.get("key")
        type_ = cleaned_row.get("type")
        source_text = cleaned_row.get("en")
        
        logger.info("processing_row", key=key, type=type_, source_text=source_text, row_keys=list(cleaned_row.keys()), cleaned_row=cleaned_row)
        
        if not key or not source_text:
            continue
        
        keys.add(key)
        
        # Add source language (en) translation to existing if not empty
        if source_text and source_text.strip():
            existing.append({
                "label": key,
                "language_code": "en",
                "translation": source_text,
                "type": type_,
            })
        
        for locale in locale_columns:
            translation = cleaned_row.get(locale)
            
            if translation and translation.strip():
                # Filled cell - upsert directly
                existing.append({
                    "label": key,
                    "language_code": locale,
                    "translation": translation,
                    "type": type_,
                })
            else:
                # Empty cell - needs AI translation
                missing.append({
                    "label": key,
                    "source_text": source_text,
                    "target_language_codes": [locale],
                    "type": type_,
                })
    
    result = {
        "existing": existing,
        "missing": missing,
        "keys": list(keys),
    }
    
    logger.info("translation_items_prepared", existing=len(existing), missing=len(missing), keys=len(keys))
    return result


def generate_output_file(
    translations: List[Dict[str, Any]], 
    format: str, 
    locale_columns: List[str]
) -> bytes:
    """Generate output file with all translations filled.
    
    Args:
        translations: List of translation dicts from database
        format: Output format ("csv" or "json")
        locale_columns: List of locale columns to include
        
    Returns:
        File content as bytes
    """
    if format == "csv":
        return generate_csv_file(translations, locale_columns)
    elif format == "json":
        return generate_json_file(translations, locale_columns)
    else:
        raise ValueError(f"Unsupported format: {format}")


def generate_csv_file(translations: List[Dict[str, Any]], locale_columns: List[str]) -> bytes:
    """Generate CSV file from translations.
    
    Args:
        translations: List of translation dicts
        locale_columns: List of locale columns
        
    Returns:
        CSV file as bytes
    """
    output = io.StringIO()
    
    # Group translations by key
    by_key: Dict[str, Dict[str, Any]] = {}
    for t in translations:
        key = t["label"]
        if key not in by_key:
            by_key[key] = {"type": t.get("type", ""), "key": key, "en": ""}
        by_key[key][t["language_code"]] = t["translation"]
        if t["language_code"] == settings.SOURCE_LANGUAGE:
            by_key[key]["en"] = t["translation"]
    
    # Prepare rows
    fieldnames = ["type", "key", "en"] + locale_columns
    rows = []
    for key in sorted(by_key.keys()):
        row = by_key[key]
        # Ensure all locale columns exist
        for locale in locale_columns:
            if locale not in row:
                row[locale] = ""
        rows.append(row)
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(rows)
    
    content = output.getvalue()
    logger.info("csv_generated", rows=len(rows))
    return content.encode('utf-8')


def generate_json_file(translations: List[Dict[str, Any]], locale_columns: List[str]) -> bytes:
    """Generate JSON file from translations.
    
    Args:
        translations: List of translation dicts
        locale_columns: List of locale columns
        
    Returns:
        JSON file as bytes
    """
    # Group translations by key
    by_key: Dict[str, Dict[str, Any]] = {}
    for t in translations:
        key = t["label"]
        if key not in by_key:
            by_key[key] = {"type": t.get("type", ""), "key": key, "en": ""}
        by_key[key][t["language_code"]] = t["translation"]
        if t["language_code"] == settings.SOURCE_LANGUAGE:
            by_key[key]["en"] = t["translation"]
    
    # Prepare rows
    rows = []
    for key in sorted(by_key.keys()):
        row = by_key[key]
        # Ensure all locale columns exist
        for locale in locale_columns:
            if locale not in row:
                row[locale] = ""
        rows.append(row)
    
    content = json.dumps(rows, ensure_ascii=False, indent=2)
    logger.info("json_generated", rows=len(rows))
    return content.encode('utf-8')
