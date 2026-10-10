"""The manuscript explanation must not silently change the evidence scope."""
from docx import Document

from scripts import build_research_documents as base
from scripts import revise_indicator_documents as retained
from scripts.revise_research_rationale import (
    add_analysis_purpose, add_practical_results, add_rationale, new_path,
)


def paper():
    result = base.Paper.__new__(base.Paper)
    result.doc = Document()
    result.chapter_number = None
    result.section_number = result.subsection_number = 0
    return result


def test_rationale_preserves_authenticity_and_limits():
    target = paper()
    add_rationale(target)
    text = " ".join(p.text for p in target.doc.paragraphs)
    assert "World Bank (2025)" in text and "ITU (2022)" in text
    assert "publisher-declared synthetic" in text
    assert "possible uses, not benefits already demonstrated" in text
    assert "not an assessment of Philippine cable performance" in text


def test_prelim_analysis_purpose_remains_planned():
    target = paper()
    add_analysis_purpose(target, "prelim")
    assert len(target.doc.tables) == 1
    assert len(target.doc.tables[0].rows) == 8
    text = " ".join(p.text for p in target.doc.paragraphs)
    assert "planned for later development" in text
    assert "not presented as completed Prelim findings" in text


def test_practical_results_are_bounded_development_evidence():
    target = paper()
    add_practical_results(target)
    text = " ".join(p.text for p in target.doc.paragraphs)
    assert "170 positive validation labels" in text
    assert "69 and misses 101" in text
    assert "not newly collected incidents" in text
    assert "do not establish a financial saving" in text


def test_output_paths_do_not_replace_current_manuscripts():
    for stage in retained.STAGES:
        assert new_path(stage) != retained.new_path(stage)
        assert new_path(stage).parent == retained.new_path(stage).parent
