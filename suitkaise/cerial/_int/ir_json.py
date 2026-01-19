"""
JSON conversion helpers for cerial intermediate representations (IR).
"""

from __future__ import annotations

import base64
import datetime
import decimal
import fractions
import json
import pathlib
import uuid
from collections import ChainMap, Counter, OrderedDict, defaultdict, deque
from typing import Any

JSON_MARKER = "__cerial_json__"


def ir_to_jsonable(ir: Any) -> Any:
    """
    Convert a cerial IR into a JSON-serializable structure.
    
    This does NOT guarantee round-trip back to IR. It is for inspection,
    logging, or debugging.
    """
    if ir is None or isinstance(ir, (bool, int, float, str)):
        return ir
    if isinstance(ir, bytes):
        return {JSON_MARKER: "bytes", "base64": _b64(ir)}
    if isinstance(ir, bytearray):
        return {JSON_MARKER: "bytearray", "base64": _b64(bytes(ir))}
    if isinstance(ir, complex):
        return {JSON_MARKER: "complex", "real": ir.real, "imag": ir.imag}
    if isinstance(ir, list):
        return [ir_to_jsonable(item) for item in ir]
    if isinstance(ir, tuple):
        return {JSON_MARKER: "tuple", "items": [ir_to_jsonable(item) for item in ir]}
    if isinstance(ir, set):
        return {JSON_MARKER: "set", "items": [ir_to_jsonable(item) for item in ir]}
    if isinstance(ir, frozenset):
        return {JSON_MARKER: "frozenset", "items": [ir_to_jsonable(item) for item in ir]}
    if isinstance(ir, dict):
        if all(isinstance(key, str) for key in ir.keys()):
            return {key: ir_to_jsonable(value) for key, value in ir.items()}
        return {
            JSON_MARKER: "dict",
            "items": [[ir_to_jsonable(key), ir_to_jsonable(value)] for key, value in ir.items()],
        }
    if isinstance(ir, range):
        return {JSON_MARKER: "range", "start": ir.start, "stop": ir.stop, "step": ir.step}
    if isinstance(ir, slice):
        return {
            JSON_MARKER: "slice",
            "start": ir_to_jsonable(ir.start),
            "stop": ir_to_jsonable(ir.stop),
            "step": ir_to_jsonable(ir.step),
        }
    if isinstance(ir, datetime.datetime):
        return {JSON_MARKER: "datetime", "value": ir.isoformat()}
    if isinstance(ir, datetime.date):
        return {JSON_MARKER: "date", "value": ir.isoformat()}
    if isinstance(ir, datetime.time):
        return {JSON_MARKER: "time", "value": ir.isoformat()}
    if isinstance(ir, datetime.timedelta):
        return {JSON_MARKER: "timedelta", "seconds": ir.total_seconds()}
    if isinstance(ir, decimal.Decimal):
        return {JSON_MARKER: "decimal", "value": str(ir)}
    if isinstance(ir, fractions.Fraction):
        return {JSON_MARKER: "fraction", "numerator": ir.numerator, "denominator": ir.denominator}
    if isinstance(ir, uuid.UUID):
        return {JSON_MARKER: "uuid", "value": str(ir)}
    if isinstance(ir, pathlib.Path):
        return {JSON_MARKER: "path", "value": str(ir)}
    if isinstance(ir, Counter):
        return {JSON_MARKER: "counter", "items": ir_to_jsonable(dict(ir))}
    if isinstance(ir, OrderedDict):
        return {JSON_MARKER: "ordered_dict", "items": ir_to_jsonable(list(ir.items()))}
    if isinstance(ir, defaultdict):
        return {
            JSON_MARKER: "defaultdict",
            "default_factory": _safe_type_name(ir.default_factory),
            "items": ir_to_jsonable(dict(ir)),
        }
    if isinstance(ir, deque):
        return {JSON_MARKER: "deque", "items": ir_to_jsonable(list(ir))}
    if isinstance(ir, ChainMap):
        return {JSON_MARKER: "chainmap", "maps": ir_to_jsonable(list(ir.maps))}
    return {JSON_MARKER: "repr", "type": type(ir).__name__, "value": repr(ir)}


def ir_to_json(
    ir: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> str:
    """Convert a cerial IR into JSON text."""
    jsonable = ir_to_jsonable(ir)
    return json.dumps(jsonable, indent=indent, sort_keys=sort_keys)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _safe_type_name(factory: Any) -> str | None:
    if factory is None:
        return None
    return getattr(factory, "__name__", type(factory).__name__)
