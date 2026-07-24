"""Tests for the classic ASP / VBScript regex extractor (.asp) and the .inc
content-sniff dispatch that keeps Pascal .inc support intact."""
from pathlib import Path

from graphify.extract import (
    _get_extractor,
    extract_classic_asp,
    extract_pascal,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _labels(r):
    return [n["label"] for n in r["nodes"]]


def _relations(r):
    return {e["relation"] for e in r["edges"]}


def test_asp_ssi_includes_both_forms():
    r = extract_classic_asp(FIXTURES / "sample.asp")
    imports = {e["target"] for e in r["edges"] if e["relation"] == "imports"}
    assert any("header_inc" in t for t in imports)      # file="header.inc"
    assert any("shared_footer_asp" in t for t in imports)  # virtual="/shared/footer.asp"


def test_asp_server_createobject_uses_edge():
    r = extract_classic_asp(FIXTURES / "sample.asp")
    uses = [e for e in r["edges"] if e["relation"] == "uses"]
    assert uses and uses[0]["confidence"] == "INFERRED"
    assert any("ADODB.Connection" == n["label"] for n in r["nodes"])


def test_asp_class_and_methods():
    r = extract_classic_asp(FIXTURES / "sample.asp")
    assert "Account" in _labels(r)
    methods = [e for e in r["edges"]
               if e["relation"] == "method" and "account" in e["source"]]
    targets = {e["target"] for e in methods}
    assert any("getname" in t for t in targets)
    assert any("setname" in t for t in targets)


def test_asp_top_level_procedures_contained_by_file():
    r = extract_classic_asp(FIXTURES / "sample.asp")
    contains = [e for e in r["edges"] if e["relation"] == "contains"]
    top = {e["target"] for e in contains if e["source"].endswith("sample_asp")}
    assert any("renderpage" in t for t in top)
    assert any("getconnstring" in t for t in top)


def test_asp_missing_file():
    r = extract_classic_asp(Path("/nonexistent/file.asp"))
    assert "error" in r


# ── .inc content-sniff dispatch ───────────────────────────────────────────────

def test_inc_with_asp_delimiter_routes_to_classic_asp():
    assert _get_extractor(FIXTURES / "sample_asp.inc") is extract_classic_asp


def test_inc_pascal_still_routes_to_pascal():
    """Regression guard: a plain Pascal include (no <%) must remain on
    extract_pascal, so existing Pascal .inc support is unaffected."""
    assert _get_extractor(FIXTURES / "sample_pascal.inc") is extract_pascal
