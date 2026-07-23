# 🛠️ J.A.R.V.I.S. AI - Building Guide

This guide explains how to package **J.A.R.V.I.S. AI** into a standalone Windows executable (`Jarvis.exe`) and create an installer (`Jarvis_Setup.exe`).

---

## 📋 Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python**: Python 3.11 or 3.12 installed ([download](https://www.python.org/downloads/)).
3. **Inno Setup** (Optional, for building `Jarvis_Setup.exe` installer): Download from [jrsoftware.org](https://jrsoftware.org/isdl.php).

---

## ⚡ Quick One-Click Build

Simply double-click or run:

```cmd
build.bat
```

This automated batch script will:
1. Create a Python virtual environment (`venv`).
2. Install all required dependencies from `requirements.txt` including `pyinstaller`.
3. Clean old build outputs.
4. Run PyInstaller with `Jarvis.spec`.
5. Copy the standalone application into the `release/` folder.

---

## 🧹 Cleaning Build Files

To clean temporary build caches and intermediate files:

```cmd
clean.bat
```

---

## 🚀 Running the Executable

To test launch the built executable:

```cmd
run.bat
```

Or open `release/Jarvis/Jarvis.exe`.

---

## 📦 Building Inno Setup Installer

If you have Inno Setup installed:

1. Right-click `Jarvis_Setup.iss` in File Explorer.
2. Select **Compile**.
3. Output installer `Jarvis_Setup.exe` will be generated.
