"""VB.NET extractor (regex-based; no maintained tree-sitter grammar on PyPI).

Follows the same regex line-scan approach as extract_apex, tailored to VB.NET's
braceless syntax: ``Inherits``/``Implements`` sit on their own statement lines
*after* the type declaration, so the enclosing type is tracked as running state
via a scope stack that pops on the matching ``End <Kind>`` line.
"""
from __future__ import annotations

import re
from pathlib import Path

from graphify.extractors.base import _file_stem, _make_id

# Leading modifier soup that can precede a declaration keyword. Optional and
# repeatable so stacked modifiers (``Public Shared Function``) are consumed.
_MODIFIER = (
    r"(?:(?:Public|Private|Protected|Friend|Partial|MustInherit|NotInheritable|"
    r"Shared|Shadows|Overloads|Overrides|Overridable|MustOverride|NotOverridable|"
    r"Default|ReadOnly|WriteOnly|Async|Iterator|Global)\s+)*"
)

_TYPE_RE = re.compile(
    rf"^{_MODIFIER}(Module|Class|Structure|Interface|Enum)\s+(\w+)",
    re.IGNORECASE,
)
_MEMBER_RE = re.compile(
    rf"^{_MODIFIER}(Sub|Function|Property)\s+(\w+)",
    re.IGNORECASE,
)
_NAMESPACE_RE = re.compile(r"^Namespace\s+[\w.]+", re.IGNORECASE)
_INHERITS_RE = re.compile(r"^Inherits\s+([\w.]+)", re.IGNORECASE)
_IMPLEMENTS_RE = re.compile(r"^Implements\s+(.+)$", re.IGNORECASE)
_IMPORTS_RE = re.compile(r"^Imports\s+(?:\w+\s*=\s*)?([\w.]+)", re.IGNORECASE)
_END_RE = re.compile(
    r"^End\s+(Namespace|Module|Class|Structure|Interface|Enum)\b", re.IGNORECASE
)

_TYPE_KINDS = frozenset({"module", "class", "structure", "interface", "enum"})


def extract_vbnet(path: Path) -> dict:
    """Extract namespaces, types, inheritance, imports, and members from .vb files."""
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

    def add_node(nid: str, label: str, line: int) -> None:
        if nid and nid not in seen_ids:
            seen_ids.add(nid)
            nodes.append({
                "id": nid,
                "label": label,
                "file_type": "code",
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

    # Scope stack of (kind_lower, nid); namespaces carry an empty nid since they
    # are tracked only for End-keyword balancing, never modeled as nodes.
    scope: list[tuple[str, str]] = []

    def enclosing_type() -> str | None:
        for kind, nid in reversed(scope):
            if kind in _TYPE_KINDS:
                return nid
        return None

    def _ref_node(name: str, line: int) -> str:
        nid = _make_id(stem, name)
        if nid not in seen_ids:
            nid = _make_id(name)
        if nid not in seen_ids:
            add_node(nid, name, line)
        return nid

    for lineno, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("'"):
            continue

        em = _END_RE.match(stripped)
        if em:
            kind = em.group(1).lower()
            for i in range(len(scope) - 1, -1, -1):
                if scope[i][0] == kind:
                    del scope[i]
                    break
            continue

        if _NAMESPACE_RE.match(stripped):
            scope.append(("namespace", ""))
            continue

        tm = _TYPE_RE.match(stripped)
        if tm:
            kind, name = tm.group(1).lower(), tm.group(2)
            type_nid = _make_id(stem, name)
            add_node(type_nid, name, lineno)
            add_edge(enclosing_type() or file_nid, type_nid, "contains", lineno)
            scope.append((kind, type_nid))
            continue

        hm = _INHERITS_RE.match(stripped)
        if hm:
            t = enclosing_type()
            if t is not None:
                base = hm.group(1).split("(")[0]
                add_edge(t, _ref_node(base, lineno), "inherits", lineno)
            continue

        pm = _IMPLEMENTS_RE.match(stripped)
        if pm:
            t = enclosing_type()
            if t is not None:
                for iface in pm.group(1).split(","):
                    iface = iface.strip().split("(")[0]
                    if iface:
                        add_edge(t, _ref_node(iface, lineno), "implements", lineno)
            continue

        mi = _IMPORTS_RE.match(stripped)
        if mi:
            ns = mi.group(1)
            ns_nid = _make_id(ns)
            add_node(ns_nid, ns, lineno)
            add_edge(file_nid, ns_nid, "imports", lineno)
            continue

        mm = _MEMBER_RE.match(stripped)
        if mm:
            member_name = mm.group(2)
            owner = enclosing_type() or file_nid
            method_nid = _make_id(owner, member_name)
            add_node(method_nid, f".{member_name}()", lineno)
            add_edge(owner, method_nid, "method", lineno)
            continue

    return {"nodes": nodes, "edges": edges}
