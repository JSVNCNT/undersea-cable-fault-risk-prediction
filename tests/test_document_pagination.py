import pymupdf

from scripts.revise_indicator_documents import locate


def test_contents_locator_ignores_heading_mentions_in_body_prose():
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 100), "The introduction discusses Statistical Analysis as future work.")
    pdf.new_page().insert_text((72, 100), "Statistical Analysis")
    assert locate(pdf, "Statistical Analysis", 0) == 1


def test_contents_locator_handles_wrapped_chapter_title():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 100), "CHAPTER II: REVIEW OF RELATED LITERATURE AND DATA SCIENCE")
    page.insert_text((72, 125), "STUDIES")
    assert locate(pdf, "REVIEW OF RELATED LITERATURE AND DATA SCIENCE STUDIES", 0) == 0
