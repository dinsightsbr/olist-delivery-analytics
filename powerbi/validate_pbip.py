"""
validate_pbip.py — validates every PBIR JSON file against the official Microsoft
schema named in its "$schema" (fetched from developer.microsoft.com), and runs
basic shape checks on the TMDL files.

Run:  python validate_pbip.py
"""
import json
import sys
import urllib.request
from pathlib import Path

from jsonschema import validators
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parent / "Olist Delivery Experience"
_cache: dict = {}


def retrieve(uri: str) -> Resource:
    if uri not in _cache:
        with urllib.request.urlopen(uri, timeout=30) as r:
            _cache[uri] = json.load(r)
    contents = _cache[uri]
    try:
        return Resource.from_contents(contents)
    except Exception:
        return Resource.from_contents(contents, default_specification=DRAFT7)


def main() -> int:
    registry = Registry(retrieve=retrieve)
    errors = 0
    checked = 0
    for f in sorted(ROOT.rglob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        uri = doc.get("$schema") if isinstance(doc, dict) else None
        if not uri or "developer.microsoft.com" not in uri:
            continue
        try:
            schema = registry.get_or_retrieve(uri).value.contents
            cls = validators.validator_for(schema, default=validators.Draft7Validator)
            v = cls(schema, registry=registry)
            errs = sorted(v.iter_errors(doc), key=lambda e: list(e.path))
        except Exception as ex:  # network / schema fetch problems
            print(f"!! {f.relative_to(ROOT)}: could not validate ({ex})")
            errors += 1
            continue
        checked += 1
        for e in errs:
            errors += 1
            path = "/".join(str(p) for p in e.path) or "<root>"
            print(f"XX {f.relative_to(ROOT)} :: {path}\n     {e.message[:300]}")
    # TMDL: tabs only for indentation, every table has a partition
    for t in sorted((ROOT / "Olist Delivery Experience.SemanticModel" / "definition").rglob("*.tmdl")):
        text = t.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip("\t")
            if stripped.startswith(" ") and not line.startswith("\t\t\t"):
                print(f"XX {t.name}:{i} space-indented line outside an expression block")
                errors += 1
        if t.parent.name == "tables" and "partition " not in text:
            print(f"XX {t.name}: no partition")
            errors += 1
    print(f"\n{checked} JSON files validated against their schemas, {errors} problem(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
