This an experimental repository to develop a way to create an ADA-accessible document.

# Document Accessibility Assistant

An employee upload application for Word and PDF accessibility scans, Word remediation, tagged PDF export, and HTML text conversion. Automated formatting and scanning do not certify ADA compliance. Files still require human review.

## Run locally

Requires Python 3.10 or newer. Tagged PDF export also requires LibreOffice (`soffice` or `libreoffice` on PATH). On Ubuntu/Debian, install with `sudo apt-get install libreoffice-writer`; on Windows or macOS install LibreOffice and add its program directory to PATH. Word and HTML downloads work without LibreOffice, with a report explaining the missing PDF exporter.

```sh
cd /workspace/ADA-Compliance-Repository
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:8000 in your browser. On a different computer, use the directory where you extracted or cloned the application instead of `/workspace/ADA-Compliance-Repository`. On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

1. Upload a `.docx` or searchable `.pdf` (maximum 15 MB).
2. For Word, optionally identify likely headings. Confirm the table-header option only if the first row of **every** table contains column headings.
3. Download the improved Word copy, tagged PDF (when selected and available), HTML text export, and accessibility review report.
4. Compare the result with the original and finish the required manual review before distribution.

## Capabilities

**Word:** preserves content and most structure; updates standard text and heading styles; adds missing title and default language metadata; optionally assigns likely headings and repeats table header rows. Reports missing image descriptions, small directly formatted text, absent/skipped heading levels, unclear table headers, merged/nested tables, text boxes, and tracked changes. Existing direct formatting may override updated styles. The original upload is unchanged.

**PDF:** extracts text from searchable PDFs, checks whether marked structure and default language metadata exist, and generates a Word text copy plus HTML. The scan does not validate existing tag quality. Page headings preserve page boundaries; extraction may reorder columns or lose table relationships. Pages without extractable text are reported. Entirely scanned documents are rejected with an OCR instruction. PDF uploads are limited to 200 pages. This implementation does not repair the original PDF in place, perform OCR, or extract PDF image descriptions. Optional tagged PDF export creates a **new text-based PDF** from the reconstructed Word document. It does not preserve source PDF layout, images, or table relationships. Review omissions against the original before distribution. Use a dedicated PDF accessibility editor when preserving the original PDF is required.

**Tagged PDF:** uses LibreOffice headless export with `PDFUACompliance` and `UseTaggedPDF` enabled. Verifies the output has a marked structure tree before offering a PDF download. For Word sources, the exporter writes headings, paragraphs, tables, and supported visual content into a new tagged PDF. A structure tree is not proof of PDF/UA or ADA compliance: run a PDF accessibility validator and review image descriptions and reading order. Inferred Word titles use the Title style; review heading semantics. Layout may differ from Word. PDF export failures leave Word and HTML available with an explanation in the report. Temporary conversion files and isolated LibreOffice profiles are deleted after export.

**HTML:** creates standalone UTF-8 HTML with a language attribute, page title, main landmark, semantic headings, and simple tables in main-body document order. Confirmed header rows become column headers. Text is escaped so uploaded markup cannot execute. Complex tables are flattened into clearly labeled text requiring review. This is a **text export**: images, headers/footers, footnotes, text boxes, list numbering, hyperlink destinations and advanced Word features are not exported. The generated HTML states these limits. Review against the original for omissions and fix semantics before publication.

No external document API receives uploads. Alt text is never invented. Metadata and original language tags are retained where supported; confirm languages manually. Advanced Word features may not survive python-docx round trips; compare fields, revisions, embedded objects, and third-party extensions against the original. Macro-enabled, encrypted, and older `.doc` documents are unsupported. Save older Word files as `.docx` first.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover content preservation, heading and table options, PDF extraction and scan findings, OCR/encryption errors, HTML escaping and ordering, HTTP upload/download/expiration behavior, and actual tagged PDF export with heading and table structure when LibreOffice is installed. Microsoft Word's Accessibility Checker, screen-reader review, and a PDF accessibility validator must still be used by a reviewer; the app has not run them.

## Employee deployment

This is a local prototype using Python's development HTTP server. Before shared deployment, add employee authentication, HTTPS, per-user download authorization, rate limiting, isolated resource-bounded processing, and a retention policy on your approved hosting stack. PDF parsing and decompression can consume resources despite basic size limits; the server is not hardened for untrusted public traffic.

Uploads are processed in memory. Download copies use random tokens, expire after 30 minutes, and are limited to the 20 most recent results. Expired bytes are removed on the next upload; stopping the process clears all results. Possession of a token grants access. Filenames and download tokens are excluded from server access logs. Downloads have explicit `.docx`, `.html`, and `.txt` attachment filenames.

## WCAG 2.2 framework and contrast

The app uses the full WCAG 2.2 success criterion inventory, not just contrast. Each report lists all 86 A/AA/AAA criteria with guideline-specific review instructions, partial-automation or not-tested status, and an explicit requirement for human applicability decisions. See https://www.w3.org/TR/WCAG22/ and https://www.w3.org/TR/wcag2ict/ for interpretation for non-web documents. The inventory is a review framework, not automated coverage of every requirement. AA conformance requires applicable A and AA criteria; AAA items are additional guidance. App UI accessibility is separate from uploaded document accessibility.

High-contrast correction is checked by default. It writes explicit black text on white run/paragraph/cell backgrounds (21:1), including main-body text, text in hyperlinks, tables, headers, footers, and supported text boxes. It removes highlights and underlines links. Theme text colors are replaced. This intentionally changes color formatting; verify color-dependent meaning. Other direct formatting such as font size remains. The report provides diagnostic examples of explicit source colors compared against white, without claiming to resolve source theme or background inheritance. WCAG SC 1.4.3 requires 4.5:1 ordinary text and 3:1 large text; black/white exceeds both and the enhanced text contrast ratios. Text in images, drawing/WordArt effects, footnotes/endnotes and unsupported parts still needs rendered review. PDF source appearance is not analyzed: reconstructed text receives high-contrast formatting; the original PDF is unchanged.

## Guided corrections (current version)

Upload and process a document, then choose **Review and correct remaining issues** before sharing downloads. The new review panel shows current headings with suggested levels, embedded raster image previews and alt-text fields, a preview/action for each table, and editable link labels alongside unchanged destinations. Review the original when previews are missing or truncated. No image meaning is invented and blank descriptions remain unresolved. Decorative-image marking is not implemented; use Word for that case.

Select header settings per table rather than applying the all-tables option. Converting a table to sequential paragraphs requires explicit confirmation and preserves cell paragraphs, embedded images and links, but removes its grid and relationships. This can change meaning: choose it only after reviewing the original. Nested tables may still remain and require a further review. Employee edits regenerate the Word, HTML text, PDF (if selected/available), and report downloads. HTML remains a text export with its documented omissions; image alt text is retained in Word and supported PDF export, not an image-containing HTML export.

The default small-text option enlarges directly formatted or resolved style-based editable text below 12 points to 12 points, including supported headers/footers and table text. It does not claim a WCAG minimum size rule and may change pagination. Footnotes, drawing text and unsupported parts still require Word review. Reports distinguish source findings from corrections; a source small-text warning may remain alongside a record of the automatic correction.

Review sessions use the same 30-minute token expiry and memory-only storage as downloads. An expired review requires uploading again. Applying changes issues a new download token and preserves the earlier output until expiry/eviction. Startup now announces the listening address only after the server has successfully bound the port, avoiding a misleading success message on port conflicts.
