"""Tests for the VB6 regex extractors (.cls / .frm / .bas) and the .cls
content-sniff dispatch that keeps Salesforce Apex .cls support intact."""
from pathlib import Path

from graphify.extract import (
    _get_extractor,
    extract_apex,
    extract_vb6,
    extract_vb6_form,
    extract_vb6_module,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _labels(r):
    return [n["label"] for n in r["nodes"]]


def _relations(r):
    return {e["relation"] for e in r["edges"]}


# ── .cls (VB6 class module) ───────────────────────────────────────────────────

def test_vb6_class_named_from_vb_name_attribute():
    r = extract_vb6(FIXTURES / "sample_vb6.cls")
    assert "CustomerAccount" in _labels(r)


def test_vb6_implements_edge():
    r = extract_vb6(FIXTURES / "sample_vb6.cls")
    impls = {e["target"] for e in r["edges"] if e["relation"] == "implements"}
    assert any("ipersistable" in t for t in impls)


def test_vb6_property_trio_deduped_to_one_member():
    """Property Get/Let for Balance must collapse to a single member node/edge."""
    r = extract_vb6(FIXTURES / "sample_vb6.cls")
    balance_methods = [e for e in r["edges"]
                       if e["relation"] == "method" and "balance" in e["target"]]
    assert len(balance_methods) == 1
    method_targets = {e["target"] for e in r["edges"] if e["relation"] == "method"}
    assert any("deposit" in t for t in method_targets)
    assert any("withdraw" in t for t in method_targets)


# ── .frm (VB6 form) ───────────────────────────────────────────────────────────

def test_vb6_form_controls_contained():
    r = extract_vb6_form(FIXTURES / "sample.frm")
    labels = set(_labels(r))
    assert "Command1 (CommandButton)" in labels
    assert "txtName (TextBox)" in labels
    # The form's own "Begin VB.Form frmMain" declaration is not a child control.
    assert "frmMain (Form)" not in labels


def test_vb6_form_handler_references_control_by_naming_convention():
    r = extract_vb6_form(FIXTURES / "sample.frm")
    ref = [e for e in r["edges"]
           if e["relation"] == "references" and "command1_click" in e["source"]]
    assert ref and ref[0]["confidence"] == "INFERRED"
    assert "command1" in ref[0]["target"]


# ── .bas (VB6 standard module) ────────────────────────────────────────────────

def test_vb6_module_named_and_members():
    r = extract_vb6_module(FIXTURES / "sample.bas")
    assert "Utilities" in _labels(r)
    method_targets = {e["target"] for e in r["edges"] if e["relation"] == "method"}
    assert any("add" in t for t in method_targets)
    assert any("printbanner" in t for t in method_targets)
    assert any("internalhelper" in t for t in method_targets)


def test_vb6_missing_file():
    r = extract_vb6(Path("/nonexistent/file.cls"))
    assert "error" in r


# ── .cls content-sniff dispatch ───────────────────────────────────────────────

def test_cls_vb6_routes_to_vb6():
    assert _get_extractor(FIXTURES / "sample_vb6.cls") is extract_vb6


def test_cls_apex_still_routes_to_apex():
    """Critical regression guard: the existing Apex fixture (no VERSION/VB_Name
    header) must remain on extract_apex — Salesforce .cls support is unaffected."""
    assert _get_extractor(FIXTURES / "sample.cls") is extract_apex
