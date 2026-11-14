# Technology Stack

## Proposed stack
| Layer | Choice | Role | Caveat |
|---|---|---|---|
| UI | Streamlit | Local interactive web UI | Launch with `streamlit run app.py` |
| Language | Python | Application logic | Python 3.13.5 reported installed; validate package support |
| Image I/O | Pillow | Decode, EXIF orientation, safe image handling | Validate untrusted input |
| Image processing | OpenCV | Thresholding, denoising, deskew, perspective correction | Prefer headless package for hosted/server environments |
| OCR wrapper | pytesseract | Python interface | Does not install OCR engine |
| OCR engine | Tesseract 5.5.3 | Text recognition | Separate executable; reported path `C:\\Program Files\\Tesseract-OCR` |
| Tabular data | pandas | CSV loading and validation | Preserve batch values as strings |
| Candidate similarity | RapidFuzz | Supporting name/candidate comparison | Scores are not probabilities and cannot confirm fuzzy batch match |
| Tests | pytest | Unit/integration tests | Include deterministic fixtures |

## Installation distinctions
Tesseract has two parts: the native Tesseract executable and the Python `pytesseract` wrapper. Installing one does not guarantee the other is available. Verify:
```powershell
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```
If PATH is not configured, set the executable path explicitly in application configuration. Do not hard-code a developer-specific path in reusable code.

## Dependency management
Do not copy arbitrary version pins from examples. In a clean virtual environment:
1. verify each package supports the installed Python version;
2. install candidate versions;
3. run import and smoke tests;
4. run the complete test suite;
5. freeze the verified environment into a lock/requirements file;
6. record OS and Tesseract engine version separately.

## Not in the stack
No external OCR API, cloud database, authentication provider, payment system, analytics or telemetry in the initial scope.
