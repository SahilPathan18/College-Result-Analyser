# 📊 Bangalore University Result Analyzer

A desktop application to parse and analyze Bangalore University Tabulation Register PDFs. Upload a PDF, and instantly get an interactive dashboard with student results, subject-wise breakdowns, and analytics.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **PDF Parsing** — Automatically extracts student data from Bangalore University Tabulation Register PDFs
- **Dashboard** — At-a-glance stats: pass rate, average SGPA/CGPA, toppers, and grade distribution
- **Student View** — Searchable, filterable table of all students with SGPA, CGPA, result, and term grade
- **Subject Analytics** — Course-wise pass rates and grade point breakdowns
- **Charts & Graphs** — Matplotlib-powered visualizations (SGPA distribution, pass/fail pie charts, boxplots)
- **Excel Export** — Export all parsed data to a multi-sheet `.xlsx` file
- **Dark Theme** — Modern dark UI built with CustomTkinter

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/result-analyzer.git
   cd result-analyzer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

## 📖 Usage

1. Click **Upload PDF** and select a Bangalore University Tabulation Register PDF
2. Use the sidebar to navigate between **Dashboard**, **Students**, **Subjects**, and **Analytics**
3. Filter students by **PASS/FAIL** status or search by name/USN
4. Click **Export to Excel** to save the parsed data

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| GUI | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) |
| PDF Parsing | [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) |
| Data Processing | [Pandas](https://pandas.pydata.org/) |
| Charts | [Matplotlib](https://matplotlib.org/) |
| Excel Export | [openpyxl](https://openpyxl.readthedocs.io/) |

## 📁 Project Structure

```
result-analyzer/
├── main.py              # Application entry point (parser + GUI)
├── requirements.txt     # Python dependencies
├── .gitignore
└── README.md
```

## 📄 License

This project is open source under the [MIT License](LICENSE).
