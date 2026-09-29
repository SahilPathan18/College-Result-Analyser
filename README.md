# College Result Analyser

A high-performance, 100% offline desktop application built to parse, analyze, and visualize Bangalore University Tabulation Register PDF ledgers. Upload a university marksheet ledger to generate an interactive analytics dashboard featuring student rankings, subject-level breakdowns, statistical grade distributions, and multi-sheet Excel exports.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-2e8b57)](https://github.com/TomSchimansky/CustomTkinter)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/SahilPathan18/College-Result-Analyser)

---

## Features

- **High-Speed PDF Parsing** — Automated extraction of student metadata, USN, courses, internal/external marks, SGPA, and CGPA from Bangalore University tabulation registers using PyMuPDF.
- **100% Offline and Private** — Operates entirely locally. No student records, marks, or institution data are transmitted externally.
- **Executive Dashboard** — Key batch metrics at a glance:
  - Total candidates, overall pass rate, and average SGPA/CGPA
  - Top rank holders and semester toppers
  - Overall grade frequency distribution
- **Student Record Explorer** — Interactive data grid with multi-attribute filtering (PASS, FAIL, PROMOTED) and instant search by Student Name or Register Number (USN).
- **Subject-Wise Analytics** — Granular course analysis covering pass percentages, average scores, and failure rates per subject.
- **Data Visualizations** — Embedded Matplotlib visualizations:
  - SGPA distribution curves
  - Pass/Fail outcome ratios
  - Course-level score distributions
- **Multi-Sheet Excel Export** — Direct export generating formatted `.xlsx` workbooks containing master ledgers, subject summaries, and rank lists.
- **Modern User Interface** — Clean dark-themed desktop interface built with CustomTkinter.

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **User Interface** | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Hardware-accelerated desktop UI components |
| **Document Ingestion** | [PyMuPDF](https://pymupdf.readthedocs.io/) | High-throughput offline PDF extraction engine |
| **Data Processing** | [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) | In-memory data transformation, aggregation, and statistics |
| **Visualization** | [Matplotlib](https://matplotlib.org/) | Analytical charts embedded into the GUI |
| **Spreadsheet Engine** | [openpyxl](https://openpyxl.readthedocs.io/) | Multi-sheet Excel workbook generation |
| **Packaging** | [PyInstaller](https://pyinstaller.org/) | Compilation into standalone Windows executables and setup installers |

---

## Project Structure

```
College-Result-Analyser/
├── src/
│   ├── main.py              # Application entry point and window lifecycle
│   ├── backend.py           # PDF parsing engine, regex parsers, and data models
│   └── frontend.py          # CustomTkinter interface, views, and plot rendering
├── scripts/
│   ├── build.ps1            # Packaging pipeline (app folder + standalone installer)
│   └── installer.py         # Self-extracting desktop setup logic
├── dist/                    # Compiled binaries and release installers
├── requirements.txt         # Runtime Python dependencies
├── .gitignore               # Ignored build artifacts, virtual environments, and PDF inputs
└── README.md                # Project documentation
```

---

## Getting Started

### Prerequisites

- **Python 3.10** or higher

### Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SahilPathan18/College-Result-Analyser.git
   cd College-Result-Analyser
   ```

2. **Create and activate a virtual environment (recommended):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application:**
   ```bash
   python src/main.py
   ```

---

## Building the Windows Installer

To compile the application into a standalone Windows installer (`dist/ResultAnalyzerSetup.exe`) that runs without requiring Python:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

The output installer will be generated in `dist/ResultAnalyzerSetup.exe`.

---

## Usage Workflow

1. Open the application and click **Upload PDF**.
2. Select a Bangalore University Tabulation Register PDF file.
3. The parser processes the document in seconds and displays the **Dashboard**.
4. Use the navigation sidebar to access:
   - **Dashboard**: Batch summary metrics and topper lists.
   - **Students**: Individual candidate records, marks, and filters.
   - **Subjects**: Course-by-course performance and pass rates.
   - **Analytics**: Distribution charts and graphical breakdowns.
5. Click **Export to Excel** to produce a spreadsheet report.
