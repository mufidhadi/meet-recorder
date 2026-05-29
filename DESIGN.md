# Design System: Meet-Recorder Desktop

## 1. Visual Theme & Atmosphere
The application follows a **Modern Windows 11 Fluent Design** philosophy. The atmosphere is **Professional, Utilitarian, and Clean**, focusing on high readability for long transcripts and clear feedback during active recording. It supports both Light and Dark modes, adapting to system-wide preferences.

## 2. Color Palette & Roles
*   **Deep Slate Background (#1E1E1E / #F3F3F3):** Primary background for the application window.
*   **Acrylic Sidebar (#252526 / #FFFFFF):** Slightly different shade to differentiate the navigation area.
*   **Success Green (#4CAF50):** Used for "Complete" status badges and active VU meter levels.
*   **Warning Amber (#FFC107):** Used for "Incomplete" status and low-level VU meter signals.
*   **Recording Red (#E81123):** High-contrast red for the pulsing recording icon and "Stop" button.
*   **Playback Highlight (#FFEB3B / #0078D4):** Transparent yellow highlight for active transcript lines during replay.

## 3. Typography Rules
*   **Primary Font:** `Segoe UI Variable` or `Inter`.
*   **Headings:** Semi-bold weight, used for session dates and section titles.
*   **Transcript Body:** Regular weight, monospaced or highly legible sans-serif, optimized for long-form reading with generous line-height (1.5).
*   **Status Labels:** Small caps or bold-compact font for badges (e.g., "DONE", "LIVE").

## 4. Layout Principles & Components
The layout uses a **Sidebar + Multi-tab Content Area** structure.

### 4.1. Global Sidebar
*   Fixed-width left panel.
*   Vertical list of recording sessions with date/time labels.
*   Status dots (🟢/🟡) next to each session entry.

### 4.2. Recording Control Page
*Ref: nanobanana-output/a_detailed_wireframe_mockup_for_.png*
*   **Active Session Header:** Displays a red pulsing icon and session name.
*   **Control Column (Left):**
    *   **Action Button:** Large "Start/Stop" button with icon-text combo.
    *   **VU Meters:** Two vertical or horizontal bars showing real-time amplitude for System and Mic.
    *   **Timer:** Large digital clock format (HH:MM:SS).
*   **Live Feed Column (Right):**
    *   **Transcription Log:** Auto-scrolling text area showing latest processed segments.
    *   **Chunk Status Table:** Compact list of `.wav` chunks with their processing state (Recording, Transcribing, Done).

### 4.3. History & Playback Page
*Ref: nanobanana-output/a_wireframe_mockup_of_a_windows_.png*
*   **Summary View:** Top section displaying AI-generated markdown summary.
*   **Transcript View:** Middle scrollable section with timestamp-anchored text blocks.
*   **Media Player Bar:** Bottom-docked bar with:
    *   Center-aligned Play/Pause/Seek controls.
    *   Progress slider that tracks audio position.
    *   Auto-scroll toggle to keep the highlighted transcript line in view.

## 5. Shape & Depth
*   **Corners:** Subtly rounded (8px radius) for buttons, cards, and panels.
*   **Elevation:** Whisper-soft diffused shadows for floating elements like context menus or dropdowns.
*   **Borders:** Fine 1px stroke (#333333 / #CCCCCC) to separate major layout zones.
