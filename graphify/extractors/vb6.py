"""Visual Basic 6 extractor (regex-based) for .cls/.frm/.bas.

VB6 has no braces and no in-source ``Class ... End Class`` wrapper: the whole file
*is* the class/module/form, named by IDE-generated metadata (``Attribute VB_Name``).
The file node therefore doubles as the container node, labeled with the VB_Name.
``.cls`` is content-sniffed (``_get_extractor`` → ``_classify_cls_file``) so genuine
Salesforce Apex ``.cls`` still routes to extract_apex.
"""
from __future__ import annotations

import re
from pathlib import Path

from graphify.extractors.base import _make_id

_VB_NAME_RE = re.compile(r'Attribute\s+VB_Name\s*=\s*"([^"]+)"', re.IGNORECASE)
_IMPLEMENTS_RE = re.compile(r'^\s*Implements\s+(\w+)', re.IGNORECASE)
_MEMBER_RE = re.compile(
    r'^\s*(?:(?:Public|Private|Friend|Static|Global)\s+)*'
    r'(?:Sub|Function|Property\s+(?:Get|Let|Set))\s+(\w+)',
    re.IGNORECASE,
)
_BEGIN_CONTROL_RE = re.compile(r'Begin\s+VB\.(\w+)\s+(\w+)', re.IGNORECASE)


def _collectors(str_path: str):
    """Build the (nodes, edges, seen_ids, add_node, add_edge) tuple shared by the
    three VB6 entry points."""
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

    return nodes, edges, seen_ids, add_node, add_edge


def _vb6_extract_members(source, container_nid, add_node, add_edge, seen_ids):
    """Attach ``Implements`` and Sub/Function/Property members to *container_nid*.

    A property's Get/Let/Set trio collapses to one member node/edge (deduped on
    the name-derived id). Returns the member records so callers (forms) can build
    naming-convention edges from event handlers to controls.
    """
    members: list[dict] = []
    for lineno, raw in enumerate(source.splitlines(), start=1):
        im = _IMPLEMENTS_RE.match(raw)
        if im:
            iface = im.group(1)
            iface_nid = _make_id(iface)
            add_node(iface_nid, iface, lineno)
            add_edge(container_nid, iface_nid, "implements", lineno)
            continue
        mm = _MEMBER_RE.match(raw)
        if mm:
            name = mm.group(1)
            member_nid = _make_id(container_nid, name)
            if member_nid in seen_ids:
                continue
            add_node(member_nid, f".{name}()", lineno)
            add_edge(container_nid, member_nid, "method", lineno)
            members.append({"name": name, "nid": member_nid, "line": lineno})
    return members


def _container_name(source: str, path: Path) -> str:
    m = _VB_NAME_RE.search(source)
    return m.group(1) if m else path.stem


def extract_vb6(path: Path) -> dict:
    """Extract a VB6 class module (.cls): one class node plus its members."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"nodes": [], "edges": [], "error": f"cannot read {path}"}
    str_path = str(path)
    nodes, edges, seen_ids, add_node, add_edge = _collectors(str_path)
    container_nid = _make_id(str_path)
    add_node(container_nid, _container_name(source, path), 1)
    _vb6_extract_members(source, container_nid, add_node, add_edge, seen_ids)
    return {"nodes": nodes, "edges": edges}


def extract_vb6_form(path: Path) -> dict:
    """Extract a VB6 form (.frm): the form class, its child controls, its members,
    and naming-convention (``Control_Event``) handler → control references."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"nodes": [], "edges": [], "error": f"cannot read {path}"}
    str_path = str(path)
    nodes, edges, seen_ids, add_node, add_edge = _collectors(str_path)
    container_nid = _make_id(str_path)
    add_node(container_nid, _container_name(source, path), 1)

    # The first Begin VB.<Type> match is the form's own declaration (skipped —
    # superseded by VB_Name); every later match is a child control or menu item.
    controls: dict[str, str] = {}
    for idx, mm in enumerate(_BEGIN_CONTROL_RE.finditer(source)):
        if idx == 0:
            continue
        ctype, cname = mm.group(1), mm.group(2)
        line = source[:mm.start()].count("\n") + 1
        ctrl_nid = _make_id(container_nid, "control", cname)
        add_node(ctrl_nid, f"{cname} ({ctype})", line, file_type="concept")
        add_edge(container_nid, ctrl_nid, "contains", line)
        controls[cname.lower()] = ctrl_nid

    members = _vb6_extract_members(source, container_nid, add_node, add_edge, seen_ids)

    # Bonus INFERRED edge: a handler named <ControlName>_<Event> references the control.
    for mem in members:
        lower = mem["name"].lower()
        for cname_l, ctrl_nid in controls.items():
            if lower.startswith(cname_l + "_"):
                add_edge(mem["nid"], ctrl_nid, "references", mem["line"],
                         confidence="INFERRED")
                break

    return {"nodes": nodes, "edges": edges}


def extract_vb6_module(path: Path) -> dict:
    """Extract a VB6 standard module (.bas): a flat procedure container."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"nodes": [], "edges": [], "error": f"cannot read {path}"}
    str_path = str(path)
    nodes, edges, seen_ids, add_node, add_edge = _collectors(str_path)
    container_nid = _make_id(str_path)
    add_node(container_nid, _container_name(source, path), 1)
    _vb6_extract_members(source, container_nid, add_node, add_edge, seen_ids)
    return {"nodes": nodes, "edges": edges}
