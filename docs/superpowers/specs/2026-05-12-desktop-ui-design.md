# Design Doc: Meet-Recorder Desktop UI (PyQt6)

## 1. Problem Statement
Meet-Recorder currently operates purely via CLI and `.cmd` scripts. While functional, it's difficult for users to browse past recordings, re-run AI tasks with different models, or replay recordings with synchronized transcripts. A native desktop interface is needed to consolidate all management, recording, and configuration tasks.

## 2. Objective
Build a native Windows desktop application using **PyQt6** that provides a complete GUI for the Meet-Recorder ecosystem, including session management, interactive playback, manual recording control, and settings.

## 3. Architecture
The application will follow a **Model-View-Controller (MVC)** pattern:
- **Model**: Interfaces with `meeting_recorder` core modules (Capture, Transcription, AI).
- **View**: PyQt6 Jendela Utama with a Sidebar + Tabbed Content area.
- **Controller/Manager**: Orchestrates background threads for long-running tasks (recording, transcription) to keep the UI responsive.

## 4. Key Features & Components

### 4.1. Recording List (Sidebar)
- **Watcher**: Automatically monitors the `recordings/` directory for changes.
- **Display**: List of sessions (Timestamp based) with status badges:
    - 🟢 Complete (Audio + Transcript + Summary)
    - 🟡 Missing Summary/Transcript
    - 🔴 Error/Incomplete
- **Search**: Filter by date or keywords in session name.

### 4.2. Session Detail View
- **Summary Panel**: Markdown viewer for `summary.md`.
    - **Re-generate Button**: Select model from dropdown -> Trigger `GeminiSummarizer`.
- **Transcript Panel**: Scrollable area showing full transcript.
    - **Re-transcribe Button**: Trigger `GeminiTranscriber` or `FasterWhisperTranscriber`.
- **Media Player (Bottom Bar)**:
    - Uses `QtMultimedia` for audio playback.
    - **Synchronized Highlighting**: As audio plays, the corresponding segment in the transcript is highlighted.
    - **Click-to-Seek**: Clicking any transcript segment jumps the audio playback to that timestamp.

### 4.3. Recording Center (Tab)
- **Monitor**: Live VU meters for Mic and System Loopback.
- **Controls**: Large Start/Stop buttons.
- **Status**: Display real-time duration and chunk count.
- **Live Feed (CLI-like)**: 
    - **Transcription Log**: A scrolling list showing new transcript segments as they are processed by the AI.
    - **Chunk Status**: A list or grid showing completed audio chunks with their processing status (e.g., "Chunk 01: Transcribing...", "Chunk 01: Done").
- **Integration**: Bridges to `WindowsCaptureEngine` and `AudioChunker`, capturing signals from the transcription worker.

### 4.4. Settings Dashboard (Tab)
- **API Config**: Edit `.env` values (API Keys, Model IDs).
- **Audio Config**: Device selection for Mic and Output.
- **UI Config**: Dark/Light mode toggle, font size.

### 4.5. System Tray Icon (Background Control)
- **Persistence**: Application can minimize to the system tray.
- **Context Menu**:
    - **Status**: Show recording state (Recording/Idle).
    - **Quick Actions**: Start/Stop recording, Open Main Window, Exit.
    - **Notifications**: Bubble notifications for task completion (e.g., "Transcription Done").
- **Integration**: Uses `QSystemTrayIcon` to provide control while background workers are active.

## 5. Technical Details

### 5.1. File Structure
- `meeting_recorder/ui/`: New directory for GUI code.
    - `main_window.py`: Entry point and layout.
    - `sidebar.py`: Recording list component.
    - `viewer.py`: Summary and Transcript views.
    - `player.py`: Multimedia control logic.
    - `recorder_view.py`: Recording control panel.
    - `worker.py`: Generic QThread for AI/Recording tasks.

### 5.2. Data Synchronization
- Each transcript segment will be stored as a custom PyQt widget or a metadata-tagged block in `QTextEdit`.
- The `positionChanged` signal from `QMediaPlayer` will be mapped to segment start/end times to trigger highlighting.

## 6. Testing Strategy
1. **Component Testing**: Test UI widgets in isolation with mocked recording data.
2. **Integration Testing**: Verify that "Re-generate" correctly calls the existing AI engines and updates the local files.
3. **Manual Verification**: Run recording sessions and verify the UI updates correctly.

## 7. Success Criteria
- User can see all past recordings in a list.
- User can play audio and see synchronized transcript highlights.
- User can start/stop recordings without using the CLI.
- AI tasks can be re-run with different models via the GUI.
