"""Tests for the ASP.NET Web Forms regex extractor
(.aspx / .ascx / .asmx / .asax / .master)."""
from pathlib import Path

from graphify.extract import _make_id, extract_webforms

FIXTURES = Path(__file__).parent / "fixtures"


def _labels(r):
    return [n["label"] for n in r["nodes"]]


def _relations(r):
    return {e["relation"] for e in r["edges"]}


def _targets(r, relation):
    return {e["target"] for e in r["edges"] if e["relation"] == relation}


# ── .aspx (Page directive) ────────────────────────────────────────────────────

def test_aspx_inherits_and_import():
    r = extract_webforms(FIXTURES / "sample.aspx")
    assert any("acme_web_samplepage" in t for t in _targets(r, "inherits"))
    assert any("system_data" in t for t in _targets(r, "imports"))


def test_aspx_codebehind_edge_lands_on_real_cs_node():
    """The CodeBehind reference must be built with the same id-recipe the .cs
    file's own extractor uses for its file node, so the edge connects rather than
    landing on a disconnected stub."""
    r = extract_webforms(FIXTURES / "sample.aspx")
    expected = _make_id(str(FIXTURES / "sample.aspx.cs"))
    refs = _targets(r, "references")
    assert expected in refs


def test_aspx_register_allowlists_custom_control_only():
    r = extract_webforms(FIXTURES / "sample.aspx")
    # uc1:Footer is registered → a references edge; asp:GridView is built-in → excluded.
    ctrl_labels = {n["label"] for n in r["nodes"] if n["file_type"] == "concept"}
    assert "uc1:Footer" in ctrl_labels
    assert not any(lbl.startswith("asp:") for lbl in ctrl_labels)
    # Register Src also produces an imports edge to the control file.
    assert any("footer_ascx" in t for t in _targets(r, "imports"))


def test_aspx_inline_csharp_methods():
    r = extract_webforms(FIXTURES / "sample.aspx")
    labels = set(_labels(r))
    assert ".Page_Load()" in labels
    assert ".BindGrid()" in labels


# ── .ascx (Control directive, inline VB) ──────────────────────────────────────

def test_ascx_control_directive_and_vb_methods():
    r = extract_webforms(FIXTURES / "sample.ascx")
    assert any("acme_web_footer" in t for t in _targets(r, "inherits"))
    labels = set(_labels(r))
    assert ".Page_Init()" in labels
    assert ".RenderYear()" in labels
    # No spurious method from the "End Sub" terminator line.
    assert ".Private()" not in labels


# ── .asmx (WebService directive) ──────────────────────────────────────────────

def test_asmx_webservice_class_reference():
    r = extract_webforms(FIXTURES / "sample.asmx")
    assert any("acme_web_calculator" in t for t in _targets(r, "references"))


# ── .asax (Application directive) ─────────────────────────────────────────────

def test_asax_application_handlers():
    r = extract_webforms(FIXTURES / "sample.asax")
    assert any("acme_web_globalapp" in t for t in _targets(r, "inherits"))
    labels = set(_labels(r))
    assert ".Application_Start()" in labels
    assert ".Session_Start()" in labels


# ── .master (Master directive) ────────────────────────────────────────────────

def test_master_directive_and_register():
    r = extract_webforms(FIXTURES / "sample.master")
    assert any("acme_web_sitemaster" in t for t in _targets(r, "inherits"))
    assert any("sample_master_cs" in t for t in _targets(r, "references"))
    ctrl_labels = {n["label"] for n in r["nodes"] if n["file_type"] == "concept"}
    assert "uc1:Nav" in ctrl_labels


def test_webforms_missing_file():
    r = extract_webforms(Path("/nonexistent/file.aspx"))
    assert "error" in r
