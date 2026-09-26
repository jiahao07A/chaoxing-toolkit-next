"""Generate configuration constants from config/settings.schema.json.

The generated files are deterministic and include a hash of the source schema so
that a runtime can identify which contract produced its defaults and rules.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "config" / "settings.schema.json"
PYTHON_OUTPUT = ROOT / "tiku" / "app" / "generated_config.py"
JAVASCRIPT_OUTPUT = ROOT / "tiku" / "frontend" / "src" / "generated" / "config.js"
USERSCRIPT_OUTPUT = ROOT / "scripts" / "userscript" / "学习通脚本.js"


def _load_schema() -> tuple[dict, str]:
    raw = SCHEMA_PATH.read_bytes()
    schema = json.loads(raw.decode("utf-8"))
    canonical = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return schema, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_python(schema: dict, source_hash: str) -> None:
    properties = schema["properties"]
    defaults = {name: spec["default"] for name, spec in properties.items()}
    rules = {
        name: {
            key: spec[key]
            for key in ("type", "minimum", "maximum")
            if key in spec
        }
        for name, spec in properties.items()
    }
    constraints = schema.get("x-constraints", [])
    content = '''"""Generated from config/settings.schema.json; do not edit manually."""\n\n'''
    content += f"SCHEMA_VERSION = {int(schema['schemaVersion'])}\nSOURCE_SCHEMA_SHA256 = {source_hash!r}\n"
    content += f"GENERATED_DEFAULTS = {defaults!r}\nGENERATED_RULES = {rules!r}\n"
    content += f"GENERATED_CONSTRAINTS = {constraints!r}\n"
    PYTHON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PYTHON_OUTPUT.write_text(content, encoding="utf-8", newline="\n")


def _write_javascript(schema: dict, source_hash: str) -> None:
    fields = []
    for name, spec in schema["properties"].items():
        fields.append(
            {
                "key": name,
                "type": spec["type"],
                "default": spec["default"],
                "minimum": spec.get("minimum"),
                "maximum": spec.get("maximum"),
                "description": spec.get("description", name),
            }
        )
    serialized = json.dumps(fields, ensure_ascii=False, indent=2)
    content = (
        "// Generated from config/settings.schema.json; do not edit manually.\n"
        f"export const CONFIG_SCHEMA_VERSION = {int(schema['schemaVersion'])}\n"
        f"export const SOURCE_SCHEMA_SHA256 = {source_hash!r}\n"
        f"export const GENERATED_CONFIG_FIELDS = {serialized}\n"
    )
    JAVASCRIPT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JAVASCRIPT_OUTPUT.write_text(content, encoding="utf-8", newline="\n")


def _write_userscript_contract(schema: dict, source_hash: str) -> None:
    defaults = {
        name: spec["default"]
        for name, spec in schema["properties"].items()
        if name.startswith("randomPause") or name == "videoDiagnosticsEnabled"
    }
    contract = {
        "schemaVersion": int(schema["schemaVersion"]),
        "sourceSchemaSha256": source_hash,
        "defaults": defaults,
        "rules": {
            name: {
                key: spec[key]
                for key in ("type", "minimum", "maximum")
                if key in spec
            }
            for name, spec in schema["properties"].items()
            if name.startswith("randomPause") or name == "videoDiagnosticsEnabled"
        },
        "constraints": schema.get("x-constraints", []),
    }
    source = USERSCRIPT_OUTPUT.read_text(encoding="utf-8")
    replacement = "  const GENERATED_CONFIG_CONTRACT = " + json.dumps(
        contract, ensure_ascii=False, separators=(",", ":")
    ) + ";"
    pattern = r"  const GENERATED_CONFIG_CONTRACT = .*?;"
    updated, count = re.subn(pattern, replacement, source, count=1)
    if count != 1:
        raise RuntimeError("无法定位用户脚本配置契约标记")
    USERSCRIPT_OUTPUT.write_text(updated, encoding="utf-8", newline="\n")


def main() -> None:
    schema, source_hash = _load_schema()
    _write_python(schema, source_hash)
    _write_javascript(schema, source_hash)
    _write_userscript_contract(schema, source_hash)
    print(f"generated config contract ({source_hash})")


if __name__ == "__main__":
    main()
