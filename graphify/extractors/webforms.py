"""ASP.NET Web Forms extractor (regex-based; no tree-sitter grammar on PyPI).

One shared function for ``.aspx``/``.ascx``/``.asmx``/``.asax``/``.master`` — the
root-directive regex tries every directive keyword, so the same code parses a Page,
Control, WebService, WebHandler (Global.asax) Application, or Master page without
knowing which extension it was handed. ``CodeBehind``/``CodeFile`` and ``Register
Src`` references are resolved against the file's own directory and built with
``_make_id(str(resolved))`` — the same id-recipe the referenced file's own extractor
uses for its file node — so the edge lands on the real node rather than a stub.
"""
from __future__ import annotations

import re
from pathlib import Path

from graphify.extractors.base import _file_stem, _make_id

_DIRECTIVE_RE = re.compile(
    r'<%@\s*(?:Page|Control|WebService|WebHandler|Application|Master)\b(.*?)%>',
    re.IGNORECASE | re.DOTALL,
)
_IMPORT_RE = re.compile(
    r'<%@\s*Import\s+Namespace\s*=\s*"([^"]+)"\s*%>', re.IGNORECASE
)
_REGISTER_RE = re.compile(r'<%@\s*Register\b(.*?)%>', re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_SCRIPT_RE = re.compile(
    r'<script[^>]*\brunat\s*=\s*"?server"?[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_USE_RE = re.compile(r'<(\w+):(\w+)[\s/>]')
# VB-style (Sub/Function keyword-anchored) and C#-style (modifier-prefixed
# return type) — run unconditionally; structurally disjoint (VB modifiers are
# capitalized keywords, the C# regex is case-sensitive lowercase) so they don't
# collide, and dedup on the node id absorbs any overlap.
_VB_METHOD_RE = re.compile(
    r'^\s*(?:(?:Public|Private|Protected|Friend|Shared|Overrides|Overloads|'
    r'Shadows|Default|Async)\s+)*(?:Sub|Function)\s+(\w+)',
    re.IGNORECASE | re.MULTILINE,
)
_CS_METHOD_RE = re.compile(
    r'(?:public|private|protected|internal|static|async|override|virtual|abstract)\s+'
    r'[\w<>\[\],\s]+\s+(\w+)\s*\('
)


def _resolve_ref(path: Path, ref: str) -> Path:
    """Resolve a WebForms path reference against the file's own directory.

    ``~/`` (IIS-app-root-relative) and leading ``/`` are best-effort stripped and
    joined relative to the file's directory — graphify has no concept of an IIS
    app root, so this is a documented approximation, not a guarantee.
    """
    ref = ref.strip().replace("\\", "/")
    if ref.startswith("~/"):
        ref = ref[2:]
    ref = ref.lstrip("/")
    return path.parent / ref


def extract_webforms(path: Path) -> dict:
    """Extract directives, code-behind/control refs, imports, and inline handlers."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"nodes": [], "edges": [], "error": f"cannot read {path}"}

    str_path = str(path)
    file_nid = _make_id(str_path)

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()

    def add_node(nid: str, label: str, line: int, file_type: str = "code",
                 source_file: str | None = None) -> None:
        if nid and nid not in seen_ids:
            seen_ids.add(nid)
            nodes.append({
                "id": nid,
                "label": label,
                "file_type": file_type,
                # Cross-file reference targets (code-behind, registered control)
                # carry the RESOLVED file's path so the extract() id-remap derives
                # the same id as that file's own node and the edge connects rather
                # than splitting into a source_file-keyed ghost.
                "source_file": source_file if source_file is not None else str_path,
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

    registered_prefixes: set[str] = set()

    # Root directive (first Page/Control/WebService/... occurrence).
    dm = _DIRECTIVE_RE.search(source)
    if dm:
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(dm.group(1))}
        line = _line_of(dm.start())
        if attrs.get("inherits"):
            val = attrs["inherits"]
            nid = _make_id(val)
            add_node(nid, val, line)
            add_edge(file_nid, nid, "inherits", line)
        if attrs.get("class"):
            val = attrs["class"]
            nid = _make_id(val)
            add_node(nid, val, line)
            add_edge(file_nid, nid, "references", line)
        for key in ("codebehind", "codefile"):
            if attrs.get(key):
                resolved = _resolve_ref(path, attrs[key])
                nid = _make_id(str(resolved))
                add_node(nid, resolved.name, line, source_file=str(resolved))
                add_edge(file_nid, nid, "references", line)
                break

    # <%@ Import Namespace="X.Y" %> → imports.
    for m in _IMPORT_RE.finditer(source):
        ns = m.group(1)
        line = _line_of(m.start())
        nid = _make_id(ns)
        add_node(nid, ns, line)
        add_edge(file_nid, nid, "imports", line)

    # <%@ Register ... %> → imports to the referenced control, and register the
    # tag-prefix into the allowlist for custom-control usage below.
    for m in _REGISTER_RE.finditer(source):
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(m.group(1))}
        line = _line_of(m.start())
        if attrs.get("tagprefix"):
            registered_prefixes.add(attrs["tagprefix"].lower())
        if attrs.get("src"):
            resolved = _resolve_ref(path, attrs["src"])
            nid = _make_id(str(resolved))
            add_node(nid, resolved.name, line, source_file=str(resolved))
            add_edge(file_nid, nid, "imports", line)

    # Custom-control usage — only for prefixes registered in this file; built-in
    # asp: controls (framework-provided, not user code) are excluded by absence
    # from the allowlist.
    for m in _TAG_USE_RE.finditer(source):
        prefix, tag = m.group(1), m.group(2)
        if prefix.lower() not in registered_prefixes:
            continue
        line = _line_of(m.start())
        ctrl_nid = _make_id("control", prefix, tag)
        add_node(ctrl_nid, f"{prefix}:{tag}", line, file_type="concept")
        add_edge(file_nid, ctrl_nid, "references", line, confidence="INFERRED")

    # Inline <script runat="server"> event handlers (VB and C#).
    for sm in _SCRIPT_RE.finditer(source):
        block = sm.group(1)
        block_start = sm.start(1)
        for rx in (_VB_METHOD_RE, _CS_METHOD_RE):
            for mm in rx.finditer(block):
                name = mm.group(1)
                method_nid = _make_id(_file_stem(path), name)
                if method_nid in seen_ids:
                    continue
                line = _line_of(block_start + mm.start())
                add_node(method_nid, f".{name}()", line)
                add_edge(file_nid, method_nid, "contains", line)

    return {"nodes": nodes, "edges": edges}
