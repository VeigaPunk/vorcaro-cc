# contexto — Vorcaro archive relatedness search

Live: https://veigapunk.github.io/contexto/

A Contexto-style semantic search over public material about Daniel Vorcaro: type anything (`restaurante`, `jantar em Paris`, `Banco Central`, `avião`) and get passages ranked by a calibrated 0–100% relatedness score, plus related keywords. Everything runs in your browser; no server.

## Sources
- Public chat archive (MasterWhats): 66,383 messages from 24 conversations (Martha Graeff WhatsApp export + Polícia Federal-transcribed excerpts).
- Polícia Federal report IPJ-A nº 3298613/2026 (PET 15.556, STF), 218 pages incl. screenshot figures.
The source PDF is **not** redistributed here.

## Method
1. **Text extraction.** Chat pages: PDF text layer (`pdftotext -layout`); it matched OCR exactly on spot checks. Report pages (incl. image-only figures): **Baidu Unlimited OCR** (`baidu/Unlimited-OCR`, rev 8249d20, transformers 4.57.1, bf16, `<image>document parsing.` gundam mode, 200 dpi) on an RTX 5070. Per page, OCR is kept if it covers ≥70% of the text-layer words; otherwise text layer + OCR figure text (6/218 pages; 2 pages timed out in repetition loops).
2. **Parsing.** Messages → (conversation, date, time, sender, text, page); grouped into windows (same chat/day, gaps ≤15 min, ≤8 msgs, ~600 chars). Report → ~700-char paragraph chunks with page numbers. 12,267 passages.
3. **Embeddings.** `intfloat/multilingual-e5-small` (384-d, `passage:`/`query:` prefixes), int8-quantized (global scale) for the browser; queries embedded client-side with `Xenova/multilingual-e5-small` via transformers.js. (A local build also uses BAAI/bge-m3; too large for the browser.)
4. **Calibration.** Null distribution = ~2,000 random corpus words/entity names × all passages. Raw score = cosine − 0.3·hubness (similarity of the passage to the corpus centroid, centred) + small bonus for literal matches. Null quantiles (50th, 90th, 99th, 99.9th, 99.99th, 99.999th percentile) map to 50, 75, 90, 95, 97 and 99%, so **90% ≈ top 1% of random query–passage pairs**. Keywords use the same scheme.
5. **Keywords.** spaCy `pt_core_news_lg` NER + heuristics; noisy (see limits).

## Redaction policy (applied to all published data and code, fail-closed)
Replaced with `[REDACTED]`: phone numbers and any ≥8-digit identifier, emails, CPF/CNPJ, CEP, bank agency/account/PIX/IBAN/SWIFT, card numbers, street addresses (PT/EN), IMEI/serial/UDID/ICCID, WhatsApp/participant IDs, forensic-extraction (Cellebrite) identifiers, long hex/UUID IDs. Media filenames → `[media]`. Kept: names, dates, times, money amounts, case/procedure numbers of the report, message and report text. `pipeline/audit.py` re-runs every detector over every published file; publication is blocked on any hit. Over-redaction is intentional.

## Rebuild
```
uv venv -p 3.12 .venv && . .venv/bin/activate
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install transformers==4.57.1 einops addict easydict matplotlib psutil sentence-transformers datasets==3.6.0 pymupdf spacy flask
python pipeline/ocr.py FIRST LAST         # Unlimited OCR on report pages
python pipeline/parse_chats.py && python pipeline/chunk_report.py && python pipeline/entities.py
python pipeline/build_index.py            # local bge-m3 index (engine.py/search.py/server.py)
python pipeline/build_site.py <data dir>  # redacted e5-small site data -> docs/data
python pipeline/audit.py .                # must exit 0
```
(scripts expect the PDF at `../vorcaro.pdf` and data in `data/`.)

## Limits
Scores measure semantic closeness, not facts or guilt. e5-small is weaker than bge-m3, especially cross-lingual (English queries over Portuguese text); lower the slider if nothing reaches 90%. Short messages can still rank high. Photos/audio in chats are only filenames. OCR of dense forensic tables is imperfect. Redaction is regex-based and may miss unusual formats.
