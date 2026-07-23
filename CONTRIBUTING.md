# Contributing to J.A.R.V.I.S. AI

Thank you for your interest in contributing to **J.A.R.V.I.S. AI**! We welcome bug reports, feature suggestions, code refactorings, and documentation enhancements.

---

## Development Setup

1. **Fork & Clone Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Personal-Ai-Assistant.git
   cd Personal-Ai-Assistant
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest ruff mypy
   ```

4. **Verify Code Quality & Syntax**:
   ```bash
   ruff check .
   mypy .
   pytest tests/
   ```

---

## Commit Guidelines (Conventional Commits)

All commits should follow the Conventional Commit specification:

- `feat: add camera exposure slider`
- `fix: resolve race condition in camera feed loop`
- `security: sanitize path traversal in file_controller`
- `docs: update setup architecture diagrams`
- `test: add unit tests for memory_manager`

---

## Pull Request Process

1. Create a feature branch: `git checkout -b feat/your-feature-name`.
2. Ensure unit tests pass (`pytest tests/`).
3. Push your branch and submit a Pull Request targeting `main`.
4. Include a concise summary of changes and validation steps in the PR description.
