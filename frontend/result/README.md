# B.Com Semester V Result Analyzer

This Flask dashboard analyzes a supported result PDF selected through the browser. The uploaded file is read into memory for the current analysis and is not stored permanently. No database is used.

## Run on Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

Open the upload screen, choose or drag in a PDF, and select **Analyze Results**. Uploading another PDF replaces the current in-memory analysis without restarting Flask. Excel reports are generated on demand in `output/` and are also returned by `/download-excel`.

The parser validates theory + internal totals and subject-total sums when the PDF exposes those values. Any mismatches are retained as warnings instead of changing source values. `CURRENT_YEAR_PATTERN` in `app.py` is intentionally configurable and is inferred from the USN years found in the source PDF at startup.
