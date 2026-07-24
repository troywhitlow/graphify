"""Tests for the VB.NET regex extractor (.vb)."""
from pathlib import Path

from graphify.extract import extract_vbnet

FIXTURES = Path(__file__).parent / "fixtures"


def _labels(r):
    return [n["label"] for n in r["nodes"]]


def _relations(r):
    return {e["relation"] for e in r["edges"]}


def _edge(r, relation, src_sub=None, tgt_sub=None):
    for e in r["edges"]:
        if e["relation"] != relation:
            continue
        if src_sub and src_sub not in e["source"]:
            continue
        if tgt_sub and tgt_sub not in e["target"]:
            continue
        return e
    return None


def test_vbnet_types_extracted():
    r = extract_vbnet(FIXTURES / "sample.vb")
    labels = set(_labels(r))
    assert "IGreeter" in labels
    assert "BaseService" in labels
    assert "AccountService" in labels


def test_vbnet_imports():
    r = extract_vbnet(FIXTURES / "sample.vb")
    imports = {e["target"] for e in r["edges"] if e["relation"] == "imports"}
    assert any("system" == t for t in imports)
    assert any("system_collections_generic" == t for t in imports)


def test_vbnet_inherits_on_separate_line():
    """Inherits sits on its own line after the declaration and must still attach
    to AccountService (the VB.NET-specific quirk this extractor handles)."""
    r = extract_vbnet(FIXTURES / "sample.vb")
    e = _edge(r, "inherits", src_sub="accountservice", tgt_sub="baseservice")
    assert e is not None
    assert e["confidence"] == "EXTRACTED"


def test_vbnet_implements_two_interfaces():
    r = extract_vbnet(FIXTURES / "sample.vb")
    impls = [e for e in r["edges"]
             if e["relation"] == "implements" and "accountservice" in e["source"]]
    targets = {e["target"] for e in impls}
    assert any("igreeter" in t for t in targets)
    assert any("idisposable" in t for t in targets)


def test_vbnet_members_scoped_to_type():
    r = extract_vbnet(FIXTURES / "sample.vb")
    # Greet/Dispose/Count belong to AccountService; Log belongs to BaseService.
    methods = [e for e in r["edges"] if e["relation"] == "method"]
    acc_methods = {e["target"] for e in methods if "accountservice" in e["source"]}
    assert any("greet" in t for t in acc_methods)
    assert any("dispose" in t for t in acc_methods)
    assert any("count" in t for t in acc_methods)
    base_methods = {e["target"] for e in methods if e["source"].endswith("baseservice")}
    assert any("log" in t for t in base_methods)


def test_vbnet_interface_method():
    r = extract_vbnet(FIXTURES / "sample.vb")
    # The top-level interface's Greet is a method of IGreeter, not of a class.
    e = _edge(r, "method", src_sub="igreeter", tgt_sub="greet")
    assert e is not None


def test_vbnet_missing_file():
    r = extract_vbnet(Path("/nonexistent/file.vb"))
    assert "error" in r
