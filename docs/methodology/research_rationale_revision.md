# Research rationale and accessible explanation revision

Completed 2026-10-03. The revised papers are separate RATIONALE_REVISED copies
of the retained INDICATOR_REVISED manuscripts. The earlier papers and proposal
copies are not overwritten.

The revision explains why the topic matters, why the two indicator groups are
examined, what each analysis answers and how verified operational evidence
could support human review. Key introductory paragraphs use plainer language;
technical methods, approved questions, statistical evidence and rubrics remain.

## Added material

- Chapter I: everyday connectivity, preparation and recovery, the documented
  Tonga example, Philippine digital-service relevance and bounded contribution.
- Chapter III: a seven-row analysis-purpose table, accessible descriptions of
  recall, precision and ranking, and the reason for checking later years.
- Each existing figure: what it answers, why it is needed and what it cannot
  establish. No additional graph or fabricated time series was necessary.
- Later-stage results: practical interpretation of the existing indicator
  comparisons and error counts, without changing development selection.
- Master/Final conclusions: a future human-review pathway and evidence needed
  to establish an actual benefit. No reduction in faults or repair cost is claimed.
- References: two newly verified primary-source articles; complete retained
  reference lists were also added to Prelim and Midterm.

Sources and verification dates are in
`docs/source_record/external_reference_sources.md`. Tonga and Philippine
connectivity evidence remain narrative context, not cable-row model inputs.
Synthetic source provenance remains disclosed; no new observations, asset
crosswalk, model fitting or final-test access occurred during this revision.

## Reproduction

Use the existing project environment and the document requirements. The
renderer invokes the document skill's canonical renderer with the existing
Windows LibreOffice/PyMuPDF adapters.

```powershell
.venv\Scripts\python.exe scripts/revise_research_rationale.py build
.venv\Scripts\python.exe scripts/render_indicator_documents.py --revision rationale --iteration first_pass
.venv\Scripts\python.exe scripts/revise_research_rationale.py paginate --pdf-dir deliverables/review/rationale_revision/first_pass
.venv\Scripts\python.exe scripts/render_indicator_documents.py --revision rationale --iteration final_pass
.venv\Scripts\python.exe scripts/verify_indicator_documents.py --revision rationale --pdf-dir deliverables/review/rationale_revision/final_pass --check-pages
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

Wait for each command to finish. Inspect the rendered PNGs after pagination;
structural checks alone do not establish visual correctness.

## Verified delivery

The delivery_review render has 72 Master, 73 Final, 59 Midterm and 51 Prelim
physical pages. All 255 page bodies match full-size inspected images from this
revision or pixel-identical previously reviewed representatives. Footer
furniture matches the previous reviewed renders after masking only PAGE field
characters; every main-matter page number, font and size is checked separately.

A4, one-inch margins, Times New Roman 12-point double-spaced body, cover,
headers, footers, styles, numbering and media are retained. Static contents and
caption lists match the rendered pages and appear in body order. Chapter starts
are fresh pages and ending gaps range from 19.3 to 74.5pt, below the 96pt limit.
Reference additions clone the retained hanging-indent format. Only empty hard
page-break spacer paragraphs are compacted to prevent blank pages.

All 19 tests passed. The three original source CSV hashes, primary-selection
JSON hash and final-test-status hash match the preceding completed revision.
The final test remains locked. No commit or push was performed.
