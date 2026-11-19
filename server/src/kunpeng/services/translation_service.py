"""Shared translation helpers for marketplace search and DWD content."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
import uuid
from typing import Optional

import httpx
import structlog

from kunpeng.config import settings

logger = structlog.get_logger(__name__)

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_HAS_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_PASSTHROUGH_TOKEN_RE = re.compile(r"^[\d\s.,+/%×xX-]+$")
_SIZE_TOKEN_RE = re.compile(
    r"^(?:X{0,4}[SLM]|S/M|M/L|L/XL|ONE\s+SIZE|\d{1,3}(?:[-/]\d{1,3})?)$",
    re.IGNORECASE,
)
_TECHNICAL_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
_BAIDU_REQUEST_LOCK = asyncio.Lock()
_BAIDU_LAST_REQUEST_AT = 0.0
_BAIDU_ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"
_BAIDU_MAX_ATTEMPTS = 3
_BAIDU_RETRYABLE_ERROR_CODES = {"52001", "52002", "54003"}


def contains_cyrillic(text: Optional[str]) -> bool:
    """Return whether a value contains Cyrillic characters."""
    return bool(text and _CYRILLIC_RE.search(text))


def contains_chinese(text: Optional[str]) -> bool:
    """Return whether a value already contains Chinese characters."""
    return bool(text and _HAS_CHINESE_RE.search(text))


def _looks_like_russian(text: str) -> bool:
    """Treat mostly-Cyrillic text as Russian search input."""
    if not text:
        return False
    cyrillic = len(_CYRILLIC_RE.findall(text))
    letters = len(re.findall(r"[A-Za-z\u0400-\u04FF]", text))
    return cyrillic > 0 and (letters == 0 or cyrillic / letters >= 0.5)


def _cache_get(target_language: str, text: str) -> Optional[str]:
    return _TRANSLATION_CACHE.get((target_language, text))


def _cache_set(target_language: str, text: str, translated: str) -> None:
    if len(_TRANSLATION_CACHE) >= 10_000:
        _TRANSLATION_CACHE.pop(next(iter(_TRANSLATION_CACHE)))
    _TRANSLATION_CACHE[(target_language, text)] = translated


async def translate_to_chinese(
    text: Optional[str], *, timeout: float = 15.0
) -> Optional[str]:
    """Translate Russian DWD content to Chinese through Baidu Translate.

    Non-Russian values and failures return ``None`` so translation never blocks
    the original DWD reconciliation flow.
    """
    cleaned = (text or "").strip()
    if not cleaned or not contains_cyrillic(cleaned):
        return None

    cached = _cache_get("zh", cleaned)
    if cached:
        return cached

    translated = await _translate_via_baidu(cleaned, timeout=timeout)
    if not translated or translated == cleaned:
        return None

    _cache_set("zh", cleaned, translated)
    return translated


async def translate_dwd_value_to_chinese(
    text: Optional[str],
    *,
    fixed_mapping: Optional[dict[str, str]] = None,
    timeout: float = 15.0,
) -> Optional[str]:
    """Populate a DWD Chinese companion value using safe layered rules.

    Business codes use deterministic mappings, existing Chinese and neutral
    tokens (sizes, model codes, numbers) pass through, Russian uses the normal
    translation path, and other prose uses Baidu automatic language detection.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    mapping = fixed_mapping or {}
    mapped = mapping.get(cleaned) or mapping.get(cleaned.upper())
    if mapped:
        return mapped
    if contains_chinese(cleaned):
        return cleaned
    if contains_cyrillic(cleaned):
        return await translate_to_chinese(cleaned, timeout=timeout)
    if _PASSTHROUGH_TOKEN_RE.fullmatch(cleaned) or _SIZE_TOKEN_RE.fullmatch(cleaned):
        return cleaned

    translation_input = (
        cleaned.replace("_", " ").lower()
        if _TECHNICAL_CODE_RE.fullmatch(cleaned)
        else cleaned
    )
    cached = _cache_get("zh:auto", cleaned)
    if cached:
        return cached
    translated = await _translate_via_baidu(
        translation_input, timeout=timeout, source_language="auto"
    )
    if not translated or translated == cleaned:
        return None
    _cache_set("zh:auto", cleaned, translated)
    return translated


async def _translate_via_baidu(
    text: str, *, timeout: float, source_language: str = "ru"
) -> Optional[str]:
    app_id = settings.baidu_translate_app_id
    secret_key = settings.baidu_translate_secret_key
    if not app_id or not secret_key:
        logger.warning("Baidu translation is not configured")
        return None

    for attempt in range(1, _BAIDU_MAX_ATTEMPTS + 1):
        try:
            if source_language == "ru":
                data = await _request_baidu_translation(text, timeout=timeout)
            else:
                data = await _request_baidu_translation(
                    text,
                    timeout=timeout,
                    source_language=source_language,
                )
        except Exception as exc:  # noqa: BLE001
            retryable = _is_retryable_http_error(exc)
            logger.warning(
                "Baidu translation request failed",
                error=str(exc),
                attempt=attempt,
                retryable=retryable,
            )
            if retryable and attempt < _BAIDU_MAX_ATTEMPTS:
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            return None

        error_code = str(data.get("error_code") or "")
        if error_code:
            retryable = error_code in _BAIDU_RETRYABLE_ERROR_CODES
            logger.warning(
                "Baidu translation rejected request",
                error_code=error_code,
                error_message=str(data.get("error_msg") or ""),
                attempt=attempt,
                retryable=retryable,
            )
            if retryable and attempt < _BAIDU_MAX_ATTEMPTS:
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            return None

        results = data.get("trans_result") or []
        translated = "\n".join(
            str(item.get("dst") or "").strip() for item in results if item.get("dst")
        ).strip()
        if translated and translated != text:
            return translated
        logger.warning(
            "Baidu translation returned no usable translation",
            attempt=attempt,
        )
        if attempt < _BAIDU_MAX_ATTEMPTS:
            await asyncio.sleep(2 ** (attempt - 1))
            continue
        return None

    return None


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError, ValueError))


async def _request_baidu_translation(
    text: str, *, timeout: float, source_language: str = "ru"
) -> dict:
    app_id = settings.baidu_translate_app_id
    secret_key = settings.baidu_translate_secret_key
    salt = uuid.uuid4().hex
    sign_source = f"{app_id}{text}{salt}{secret_key}".encode("utf-8")
    sign = hashlib.md5(sign_source).hexdigest()  # noqa: S324 - Baidu API contract

    global _BAIDU_LAST_REQUEST_AT
    min_interval = 1 / max(settings.baidu_translate_qps, 1)
    async with _BAIDU_REQUEST_LOCK:
        wait_seconds = min_interval - (time.monotonic() - _BAIDU_LAST_REQUEST_AT)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _BAIDU_ENDPOINT,
                data={
                    "q": text,
                    "from": source_language,
                    "to": "zh",
                    "appid": app_id,
                    "salt": salt,
                    "sign": sign,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        _BAIDU_LAST_REQUEST_AT = time.monotonic()
    response.raise_for_status()
    return response.json()


async def translate_to_russian(text: str, *, timeout: float = 8.0) -> str:
    """Translate a marketplace search keyword to Russian."""
    cleaned = (text or "").strip()
    if not cleaned or _looks_like_russian(cleaned):
        return cleaned

    cached = _cache_get("ru", cleaned)
    if cached:
        return cached

    translated = await _translate_via_azure(cleaned, timeout=timeout)
    if not translated:
        translated = await _translate_via_mymemory(cleaned, timeout=timeout)
    if not translated:
        logger.warning("Search keyword translation failed")
        return cleaned

    _cache_set("ru", cleaned, translated)
    return translated


async def _translate_via_azure(text: str, *, timeout: float) -> Optional[str]:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not (api_key and endpoint and deployment):
        return None

    url = (
        f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/"
        f"chat/completions?api-version={api_version}"
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Translate e-commerce search keywords into natural Russian. "
                    "Return the translation only."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": 64,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        return _extract_translation(response.json())
    except Exception as exc:  # noqa: BLE001
        logger.debug("Azure search translation failed", error=str(exc))
        return None


async def _translate_via_mymemory(text: str, *, timeout: float) -> Optional[str]:
    source_lang = "zh-CN" if _HAS_CHINESE_RE.search(text) else "en"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text, "langpair": f"{source_lang}|ru"},
            )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("MyMemory search translation failed", error=str(exc))
        return None

    translated = (data.get("responseData") or {}).get("translatedText") or ""
    translated = re.sub(r"<[^>]+>", " ", translated).strip()
    return translated or None


def _extract_translation(data: dict) -> Optional[str]:
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return None
    line = content.strip().splitlines()[0] if content.strip() else ""
    return line.strip().strip('"').strip("'").strip("«»") or None
