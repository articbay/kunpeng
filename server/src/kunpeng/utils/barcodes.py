"""Wildberries product barcode normalization helpers."""

import re
from collections.abc import Iterable
from typing import Any, Optional, Tuple

_ORIGINAL_BARCODE_RE = re.compile(r"^\d{13}$")
_HAND_BARCODE_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]+$")


def split_wb_barcodes(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Split one WB barcode or a barcode list into original and manual values.

    Original barcodes are exactly 13 digits. Manual barcodes contain both letters
    and digits and may use ``-`` or ``_`` separators. When a response contains
    several values of the same kind, the first non-empty value is used; the full
    platform response remains available in the ODS ``row_data`` column.
    """

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        values = value
    else:
        values = (value,)

    barcode_ori: Optional[str] = None
    barcode_hand: Optional[str] = None
    for item in values:
        if item is None:
            continue
        normalized = str(item).strip()
        if not normalized:
            continue
        if barcode_ori is None and _ORIGINAL_BARCODE_RE.fullmatch(normalized):
            barcode_ori = normalized
        elif barcode_hand is None and _HAND_BARCODE_RE.fullmatch(normalized):
            barcode_hand = normalized

    return barcode_ori, barcode_hand
