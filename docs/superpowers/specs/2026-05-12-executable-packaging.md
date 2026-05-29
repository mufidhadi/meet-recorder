# Design Doc: Windows Executable Packaging (.exe)

## 1. Problem Statement
The user currently needs to install Python and `uv` to run Meet-Recorder. To improve accessibility and ease of use, a standalone Windows executable is needed.

## 2. Objective
Create a professional Windows application package (`.onedir`) using **PyInstaller** that allows Meet-Recorder to run on any Windows 10/11 machine without pre-installed Python.

## 3. Chosen Approach: Optimized Full Feature Set
We will include support for both **Gemini (Cloud)** and **Local Whisper (Local)** to ensure the user doesn't lose any functionality. 
- **Format**: `One-Directory` for fast startup times.
- **Optimizations**: Exclude unnecessary sub-libraries of PyTorch (like CUDA if not explicitly needed, or unit tests) to keep the size manageable.
- **External Resources**: Keep `.env` and `recordings/` as external files relative to the `.exe`.

## 4. Technical Strategy

### 4.1. Runtime Resource Handling
We must modify the code to handle `sys._MEIPASS` when running in a PyInstaller bundle. This ensures that icons or internal data files are found correctly.
- `get_base_path()` helper will be used to resolve file locations.

### 4.2. PyInstaller Specification (`.spec`)
A custom `.spec` file will be created to:
- Collect all `meeting_recorder` modules.
- Include static assets (if any).
- Exclude bloating packages: `notebook`, `matplotlib` (if present), `scipy` (unless needed).
- Handle `hiddenimports` for `google.generativeai` and `pydantic-settings`.

### 4.3. External Data Integration
The executable will look for:
- `.env`: In the same directory as the `.exe`.
- `recordings/`: In the same directory as the `.exe`.
- `models/`: In the same directory as the `.exe`.

## 5. Implementation Steps
1.  **Dependency Setup**: Add `pyinstaller` to dev dependencies.
2.  **Path Refactoring**: Update internal path logic to be "bundle-aware".
3.  **Build Script**: Create a script `build_exe.py` or `.cmd` to automate the complex build command.
4.  **Verification**: Test the built `.exe` on a clean environment or ensure it launches without the virtual environment active.

## 6. Success Criteria
- A folder named `dist/Meet-Recorder/` is generated.
- `Meet-Recorder.exe` launches the PyQt6 UI.
- Recording, Replay, and AI tasks work correctly.
- Startup time is less than 5 seconds.
