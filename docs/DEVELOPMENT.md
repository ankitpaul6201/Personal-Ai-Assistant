# JARVIS AI Developer Setup & Guidelines

## Prerequisites
- Python **3.11** or higher
- Git
- Windows 10/11 (or macOS / Linux for head-less mode)
- PortAudio / Microphone input

---

## Developer Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/jarvis-ai.git
   cd jarvis-ai
   ```

2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies & Package in Editable Mode**:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Install Playwright Browsers**:
   ```powershell
   playwright install
   ```

5. **Configure API Credentials**:
   Copy `config/api_keys.json.example` to `config/api_keys.json` and insert your Gemini API Key:
   ```json
   {
     "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE"
   }
   ```

---

## Running the Application

- **Root Launcher**:
  ```powershell
  python main.py
  ```
- **PowerShell Script**:
  ```powershell
  .\run.ps1
  ```
- **Module Command**:
  ```powershell
  python -m jarvis
  ```

---

## Running Tests & Code Quality

- **Run Pytest**:
  ```powershell
  pytest
  ```

- **Run Linting**:
  ```powershell
  ruff check .
  ```

- **Run Type Checks**:
  ```powershell
  mypy src
  ```

---

## Adding New Action Plugins

To add a new tool or action to JARVIS:
1. Create a python module in `src/jarvis/actions/my_new_action.py`.
2. Define function calls with standard type hints and docstrings.
3. Import and register the action in `src/jarvis/main.py`.
4. Add unit test coverage under `tests/unit/test_my_new_action.py`.
