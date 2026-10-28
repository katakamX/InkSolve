# InkSolve — Handwritten Equation Solver ✍️

**Upload handwritten maths, recognize the equation, and solve it in a clean web interface.**

InkSolve is an educational Python project combining image preprocessing, OCR, and symbolic mathematics. It provides a small Streamlit app where you can upload an equation image or type an equation, inspect the recognized expression, solve supported algebraic inputs, and revisit previous results.

> **Important:** This project uses Tesseract OCR as a baseline recognizer. OCR accuracy for handwritten mathematics varies significantly. Review the recognized text before solving. This repository does **not** include a custom-trained CNN or claim guaranteed recognition accuracy.

## Features

- **Image upload** for PNG, JPG, and BMP images.
- **Image preprocessing** using OpenCV: grayscale conversion, resizing, denoising, and thresholding.
- **OCR integration** through Tesseract, when installed on your system.
- **Equation solving** with SymPy for common single-variable equations and basic expressions.
- **Input correction** so you can review and edit OCR output before solving.
- **Equation history** stored locally in SQLite.
- **Example inputs** for quick testing.
- **Simple responsive UI** built with Streamlit.

## Tech stack

| Component | Technology |
|---|---|
| Interface | Streamlit |
| Image processing | OpenCV, Pillow, NumPy |
| OCR | Tesseract OCR + pytesseract |
| Symbolic maths | SymPy |
| History | SQLite |
| Tests | pytest |

## How it works

```text
Upload handwritten image
          |
          v
 OpenCV preprocessing
          |
          v
 Tesseract OCR (best effort)
          |
          v
 Review / correct recognized text
          |
          v
 Parse equation with SymPy
          |
          v
 Solve and display result
          |
          v
 Save result to local SQLite history
```

You can also type an equation directly and skip OCR.

## Requirements

- Python 3.10 or newer recommended
- pip
- Tesseract OCR installed separately for image recognition

### Install Tesseract

The Python package `pytesseract` is only a wrapper. The Tesseract application itself must also be installed.

- **Windows:** Install Tesseract OCR from the UB Mannheim Windows builds: https://github.com/UB-Mannheim/tesseract/wiki. If the installer does not add Tesseract to `PATH`, add its installation folder to `PATH`, then reopen your terminal.
- **Ubuntu / Debian:**
  ```bash
  sudo apt update
  sudo apt install tesseract-ocr
  ```
- **macOS with Homebrew:**
  ```bash
  brew install tesseract
  ```

If Tesseract is not installed, the app can still solve equations typed manually; image recognition will show an explanatory message.

## Run locally

### 1. Download or clone the repository

```bash
git clone <your-repository-url>
cd Handwritten-Equation-Solver
```

If you downloaded the ZIP, extract it and open the extracted folder in your terminal or editor.

### 2. Create a virtual environment

**Windows CMD:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**PowerShell / macOS / Linux:**
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Launch the app

```bash
streamlit run app.py
```

Streamlit will show a local URL, usually http://localhost:8501. Open it in your browser.

## Try these examples

- `2*x + 3 = 7` → \(x = 2\)
- `x^2 - 4 = 0` → \(x = -2, 2\)
- `3*x + 2 = 11` → \(x = 3\)
- `2 + 3 * 4` → `14`

For multiplication, explicit notation such as `2*x` is recommended. Use `^` for powers, for example `x^2`.

## Image tips

- Use a close crop containing only the equation.
- Use dark writing on a plain, light background.
- Avoid shadows, ruled lines, blur, and tilted photos.
- After OCR, check minus signs, multiplication signs, digits, and exponents carefully.

## Run tests

```bash
pytest -q
```

Tests cover core normalization and solving behavior. OCR quality depends on the installed OCR engine and image quality and is not covered by these unit tests.

## Project structure

```text
Handwritten-Equation-Solver/
├── app.py                 # Streamlit UI, preprocessing, OCR, solver, history
├── requirements.txt       # Python dependencies
├── tests/
│   └── test_solver.py     # Unit tests for solver and normalization
├── sample_images/         # Place your own sample images here
├── .gitignore
└── README.md
```

## Current limitations

- OCR is a general-purpose baseline and may misread handwriting or mathematical symbols.
- Complex notation such as fractions, matrices, integrals, roots, and multi-line systems may not be recognized reliably.
- Multi-variable single equations may not have a unique solution.
- This project does not train a custom CNN or include a pretrained mathematical handwriting model.
- The history database is local to the machine running the app.
- The app is designed for education and experimentation, not as a production math service.

## Roadmap

- [ ] Add a handwriting canvas for drawing equations in the browser.
- [ ] Improve math OCR with a model trained for mathematical notation.
- [ ] Add a structured equation preview and manual correction workflow.
- [ ] Expand support for systems of equations and richer polynomial cases.
- [ ] Add more automated tests and packaging/deployment support.

## Contributing

1. Create a feature branch.
2. Make a focused change.
3. Run `pytest -q`.
4. Open a pull request with a description of the change.

## License

No license has been selected. Add a `LICENSE` file before distributing or accepting external contributions.

---

Built as a learning project at the intersection of computer vision, OCR, and symbolic mathematics.
"# InkSolve" 
