"""Classic ASP / VBScript extractor (regex-based; no tree-sitter grammar on PyPI).

Handles ``.asp`` pages and, when content-sniffed as classic ASP (``_get_extractor``
routes a ``.inc`` containing ``<%`` here rather than to extract_pascal), VBScript
include fragments. The raw file is scanned without tracking ``<% %>`` boundaries —
the VBScript keywords are distinctive enough in context, the same simplification
extract_razor makes for the Razor/HTML boundary.
"""
from __future__ import annotations

import re
from pathlib import Path

from graphify.extractors.base import _file_stem, _make_id

_INCLUDE_RE = re.compile(
    r'<!--\s*#include\s+(?:file|virtual)\s*=\s*"([^"]+)"\s*-->',
    re.IGNORECASE,
)
_CREATEOBJECT_RE = re.compile(
    r'(?:Server\.)?CreateObject\s*\(\s*"([^"]+)"\s*\)',
    re.IGNORECASE,
)
_CLASS_RE = re.compile(r'^\s*Class\s+(\w+)', re.IGNORECASE)
_END_CLASS_RE = re.compile(r'^\s*End\s+Class\b', re.IGNORECASE)
_PROC_RE = re.compile(
    r'^\s*(?:(?:Public|Private)\s+)?(?:Default\s+)?(?:Sub|Function)\s+(\w+)',
    re.IGNORECASE,
)


def extract_classic_asp(path: Path) -> dict:
    """Extract SSI includes, classes, procedures, and COM object use from classic ASP."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"nodes": [], "edges": [], "error": f"cannot read {path}"}

    str_path = str(path)
    stem = _file_stem(path)
    file_nid = _make_id(str_path)

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()

    def add_node(nid: str, label: str, line: int, file_type: str = "code") -> None:
        if nid and nid not in seen_ids:
            seen_ids.add(nid)
            nodes.append({
                "id": nid,
                "label": label,
                "file_type": file_type,
                "source_file": str_path,
                "source_location": f"L{line}",
            })

    def add_edge(src: str, tgt: str, relation: str, line: int,
                 confidence: str = "EXTRACTED") -> None:
        edges.append({
            "source": src,
            "target": tgt,
            "relation": relation,
            "confidence": confidence,
            "source_file": str_path,
            "source_location": f"L{line}",
            "weight": 1.0,
        })

    add_node(file_nid, path.name, 1)

    def _line_of(idx: int) -> int:
        return source[:idx].count("\n") + 1

    # SSI includes → imports edge to a path-based node (covers both file= and
    # virtual=, and the .inc-include pattern that shares this extractor).
    for m in _INCLUDE_RE.finditer(source):
        target = m.group(1)
        line = _line_of(m.start())
        inc_nid = _make_id(target)
        add_node(inc_nid, target, line)
        add_edge(file_nid, inc_nid, "imports", line)

    # Server.CreateObject("Prog.ID") → uses edge (INFERRED) to a synthetic COM node.
    for m in _CREATEOBJECT_RE.finditer(source):
        prog_id = m.group(1)
        line = _line_of(m.start())
        com_nid = _make_id("com", prog_id)
        add_node(com_nid, prog_id, line, file_type="concept")
        add_edge(file_nid, com_nid, "uses", line, confidence="INFERRED")

    # Classes and top-level procedures.
    current_class_nid: str | None = None
    for lineno, raw in enumerate(source.splitlines(), start=1):
        if _END_CLASS_RE.match(raw):
            current_class_nid = None
            continue
        cm = _CLASS_RE.match(raw)
        if cm:
            name = cm.group(1)
            class_nid = _make_id(stem, name)
            add_node(class_nid, name, lineno)
            add_edge(file_nid, class_nid, "contains", lineno)
            current_class_nid = class_nid
            continue
        pm = _PROC_RE.match(raw)
        if pm:
            name = pm.group(1)
            if current_class_nid is not None:
                proc_nid = _make_id(current_class_nid, name)
                add_node(proc_nid, f".{name}()", lineno)
                add_edge(current_class_nid, proc_nid, "method", lineno)
            else:
                proc_nid = _make_id(stem, name)
                add_node(proc_nid, name, lineno)
                add_edge(file_nid, proc_nid, "contains", lineno)
            continue

    return {"nodes": nodes, "edges": edges}
