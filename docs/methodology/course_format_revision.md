# Course-format compliance revision

Completed 2026-10-10 against the supplied
`2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx`. The Downloads reference
and repository copy are identical (SHA-256
`48c0a7b94d7df72262eb71cd9827845f76905bf21997d1e93cc3d3d08a0abdf7`).
Neither reference nor any earlier paper or proposal copy was overwritten.

## Scope and rule selection

Separate COURSE_FORMAT_REVISED copies retain the rationale-expanded content.
The document skill governed the render/inspection process. The course's
institutional-template exception takes precedence over generic APA Letter and
left-alignment defaults: the retained college layout stays A4 with one-inch
margins and justified, half-inch-indented Times New Roman 12pt body paragraphs.
The main papers stay double-spaced. The proposal-only 1.5 spacing instruction
does not replace the course's research-paper spacing rule.

Changes are limited to formatting and document navigation:

- Cover submission labels follow the course sample, including the instructor
  on the next line and the Faculty line above the college name.
- Every non-rubric research table is numbered; bold numbers and italic titles
  occupy separate lines above tables. Caption lists include the formerly
  unnumbered definition, alignment, traceability and record-template tables.
- Figure captions move above the unchanged image data; source notes and
  existing purpose explanations remain below, with explicit Figure references.
- Research tables use top/bottom/header rules rather than decorative full
  grids. Results/context tables have a minimum 10pt font. Rows do not split;
  the last row stays with its note. The Midterm metric columns have consistent
  DXA geometry and visibly separated numeric values.
- References retain alphabetical order, double spacing and half-inch hanging
  indents; appropriate book/report/webpage titles and journal name/volume
  receive italics. Existing URL/DOI text becomes active black hyperlinks.
- Original styles, numbering, headers, footers and image media remain
  byte-identical. Only intentional local paragraph/table/drawing formatting
  changes occur. Charts are proportionally resized modestly for caption space.
- Official rubric criteria and blank scoring cells remain unchanged.

The task-local `deliverables/review/course_format_revision/artifact.md` records
exact local overrides and fidelity requirements. QA artifacts remain internal.

## Verification

The final handoff_render contains 74 Master, 75 Final, 60 Midterm and 52 Prelim
pages (261 total). All final page bodies have full-resolution inspection records
or exact pixel matches to previously inspected bodies. Footer furniture matches
the retained reviewed output; every main-matter page number/font/size is checked
separately. Static contents and caption-list numbers match the final PDFs.

All chapters start fresh pages. Ending gaps are 19.3–74.5pt, below the retained
96pt/four-line limit. Body text is not shortened or reduced in size or spacing.
The four original manuscripts, all existing research-table cells, all rubric
forms, three original CSV hashes, model-selection JSON and final-test-status
hash remain unchanged. Synthetic provenance remains disclosed. No model was
refitted, observations created, datasets joined or final test unblinded.

The structural/visual gates passed, all 23 tests passed, and `git diff --check`
reported no whitespace errors. No commit or push was requested or performed.

## Reproduction

Use the existing document environment and Windows LibreOffice/PyMuPDF adapter
for the canonical document-skill renderer. Wait for each step to finish.

```powershell
.venv\Scripts\python.exe scripts/revise_course_format.py build
.venv\Scripts\python.exe scripts/render_indicator_documents.py --revision course_format --iteration first_pass
.venv\Scripts\python.exe scripts/revise_course_format.py paginate --pdf-dir deliverables/review/course_format_revision/first_pass
.venv\Scripts\python.exe scripts/render_indicator_documents.py --revision course_format --iteration final_pass
.venv\Scripts\python.exe scripts/revise_course_format.py verify --pdf-dir deliverables/review/course_format_revision/final_pass
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

Inspect the actual final PNGs; passing structural tests alone is insufficient.
If the source papers or course instructions change, recheck the template
contract before regeneration. The FINAL copy remains a near-final draft pending
authorized held-out evaluation, not a completed empirical fault-prediction study.
