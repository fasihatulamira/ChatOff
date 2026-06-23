"""Helpers to parse JSON arrays from local LLM output."""
import json
import re


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _extract_json_array(text: str) -> str | None:
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    return match.group(0) if match else None


def _fix_trailing_commas(text: str) -> str:
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r",\s*}", "}", text)
    return text


def parse_json_array(text: str) -> list:
    """Parse a JSON array from raw model output, with light repair for common LLM mistakes."""
    if not text or not text.strip():
        raise ValueError("Ollama returned an empty response. Check if Ollama is running.")

    candidates = [_strip_markdown_fences(text)]
    extracted = _extract_json_array(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    last_error = None
    for candidate in candidates:
        if not candidate:
            continue
        for attempt in (_fix_trailing_commas(candidate), candidate):
            try:
                result = json.loads(attempt)
                if isinstance(result, list):
                    return result
                raise ValueError("AI did not return a JSON array.")
            except json.JSONDecodeError as e:
                last_error = e

    preview = text.strip()[:250]
    raise ValueError(
        f"AI response was not valid JSON.\nRaw output (first 250 chars): {preview}"
    ) from last_error
