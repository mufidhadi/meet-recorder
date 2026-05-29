# 04 — Meeting Detection: Membedakan Meeting dari Musik & Video

> **Versi:** 1.0  
> **Tanggal:** April 2026

---

## 1. Masalah & Kenapa Ini Susah

Sistem rekaman kita menangkap **semua** audio dari device — termasuk musik Spotify, YouTube, notifikasi, dll. Kita perlu tahu kapan "ini meeting beneran" vs "ini orang lagi nonton Netflix".

Tidak ada satu sinyal yang sempurna. Solusinya adalah **sistem berlapis** — gabungkan beberapa sinyal dengan sistem skor, dan rekam hanya kalau skor melewati threshold.

```
Sinyal 1: Proses Meeting Aktif?          → +40 poin
Sinyal 2: Judul Window Meeting?          → +30 poin
Sinyal 3: Koneksi Network ke Server?     → +20 poin
Sinyal 4: Pola Audio = Percakapan?       → +10 poin
──────────────────────────────────────────────────
Threshold rekam: ≥ 50 poin
Threshold stop:  <  20 poin selama 60 detik
```

---

## 2. Empat Sinyal Deteksi

### Sinyal 1 — Deteksi Proses (Paling Andal, Overhead Rendah)

Cek apakah ada proses meeting yang sedang berjalan di OS.

```python
# detection/process_detector.py
import psutil
from dataclasses import dataclass

MEETING_PROCESSES = {
    # (nama_proses, platform, nama_display)
    "zoom":                    ("all",     "Zoom"),
    "zoom.exe":                ("Windows", "Zoom"),
    "zoomus":                  ("Darwin",  "Zoom"),
    "ms-teams":                ("all",     "Microsoft Teams"),
    "ms-teams.exe":            ("Windows", "Microsoft Teams"),
    "teams":                   ("Linux",   "Microsoft Teams"),
    "webex":                   ("all",     "Cisco Webex"),
    "CiscoWebexMeetings.exe":  ("Windows", "Cisco Webex"),
    "Discord":                 ("all",     "Discord"),
    "discord":                 ("Linux",   "Discord"),
    "Slack":                   ("all",     "Slack Huddle"),
    "slack.exe":               ("Windows", "Slack Huddle"),
    "whereby":                 ("all",     "Whereby"),
    "skype":                   ("all",     "Skype"),
    "Skype.exe":               ("Windows", "Skype"),
}

@dataclass
class ProcessMatch:
    process_name: str
    app_name: str
    pid: int
    score: int = 40

class ProcessDetector:
    def detect(self) -> list[ProcessMatch]:
        matches = []
        running = {p.name().lower(): p for p in psutil.process_iter(["name", "pid"])}
        
        for proc_name, (platform, app_name) in MEETING_PROCESSES.items():
            if proc_name.lower() in running:
                proc = running[proc_name.lower()]
                matches.append(ProcessMatch(
                    process_name=proc_name,
                    app_name=app_name,
                    pid=proc.pid,
                ))
        return matches
```

> **Catatan:** Zoom kadang tetap berjalan di background meski tidak ada meeting. Sinyal ini perlu dikombinasikan dengan sinyal lain.

---

### Sinyal 2 — Deteksi Judul Window (Presisi Tinggi)

Window title biasanya berubah saat meeting aktif vs idle.

```python
# detection/window_detector.py
import platform
import subprocess
import re
from dataclasses import dataclass

MEETING_WINDOW_PATTERNS = [
    # (regex_pattern, score, app_name)
    (r"zoom meeting",            35, "Zoom"),
    (r"zoom - pro account",      25, "Zoom"),
    (r"google meet",             35, "Google Meet"),
    (r"meet\.google\.com",       30, "Google Meet"),
    (r"microsoft teams.*meeting",35, "Microsoft Teams"),
    (r"teams.*call",             30, "Microsoft Teams"),
    (r"webex.*meeting",          35, "Webex"),
    (r"discord.*voice",          25, "Discord"),
    (r"slack.*call",             25, "Slack"),
    (r"whereby",                 30, "Whereby"),
]

@dataclass
class WindowMatch:
    window_title: str
    app_name: str
    score: int

class WindowDetector:
    def detect(self) -> list[WindowMatch]:
        titles = self._get_all_window_titles()
        matches = []
        
        for title in titles:
            title_lower = title.lower()
            for pattern, score, app_name in MEETING_WINDOW_PATTERNS:
                if re.search(pattern, title_lower):
                    matches.append(WindowMatch(
                        window_title=title,
                        app_name=app_name,
                        score=score,
                    ))
                    break  # Satu window cukup satu match
        return matches

    def _get_all_window_titles(self) -> list[str]:
        system = platform.system()
        if system == "Windows":
            return self._get_windows_titles()
        elif system == "Darwin":
            return self._get_macos_titles()
        else:
            return self._get_linux_titles()

    def _get_windows_titles(self) -> list[str]:
        import win32gui
        titles = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    titles.append(title)
        win32gui.EnumWindows(callback, None)
        return titles

    def _get_macos_titles(self) -> list[str]:
        # Gunakan AppleScript — tidak butuh permission khusus
        script = '''
        tell application "System Events"
            set windowTitles to {}
            repeat with proc in (processes where background only is false)
                try
                    set wins to windows of proc
                    repeat with w in wins
                        set end of windowTitles to (name of w as string)
                    end repeat
                end try
            end repeat
            return windowTitles
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return [t.strip() for t in result.stdout.split(",") if t.strip()]
        return []

    def _get_linux_titles(self) -> list[str]:
        # Butuh: apt install xdotool
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", ""],
                capture_output=True, text=True, timeout=3
            )
            # Alternatif: wmctrl -l
            result2 = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=3
            )
            titles = []
            for line in result2.stdout.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    titles.append(parts[3])
            return titles
        except FileNotFoundError:
            return []  # Tool tidak terinstall
```

---

### Sinyal 3 — Deteksi Koneksi Network

Meeting platform menggunakan koneksi UDP/TCP ke server spesifik. Ini sinyal kuat karena sulit di-false-positive.

```python
# detection/network_detector.py
import psutil
import socket
from dataclasses import dataclass

# IP ranges dan port yang digunakan platform meeting
MEETING_NETWORK_SIGNATURES = [
    # Zoom: UDP 8801-8802, TCP 443, ke *.zoom.us
    {"name": "Zoom",           "ports": {8801, 8802, 3478, 3479}, "score": 25},
    # Teams: UDP/TCP ke *.teams.microsoft.com, *.skype.com
    {"name": "MS Teams",       "ports": {3478, 3479, 3480, 3481}, "score": 25},
    # Google Meet: STUN/TURN ke *.google.com port 19302, 443
    {"name": "Google Meet",    "ports": {19302, 19305, 19307},    "score": 25},
    # WebRTC generic (browser-based meetings)
    {"name": "WebRTC",         "ports": {3478, 5349},             "score": 15},
    # Cisco Webex
    {"name": "Cisco Webex",    "ports": {9000, 5004},             "score": 25},
]

# Domain patterns untuk deteksi berbasis DNS
MEETING_DOMAINS = [
    ("zoom.us",                 "Zoom",         25),
    ("teams.microsoft.com",     "MS Teams",     25),
    ("meet.google.com",         "Google Meet",  25),
    ("webex.com",               "Cisco Webex",  25),
    ("discord.com",             "Discord",      20),
    ("whereby.com",             "Whereby",      20),
    ("lync.com",                "MS Teams",     20),
    ("skype.com",               "Skype",        20),
]

@dataclass
class NetworkMatch:
    remote_address: str
    remote_port: int
    app_name: str
    score: int

class NetworkDetector:
    def detect(self) -> list[NetworkMatch]:
        matches = []
        
        try:
            connections = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            # Butuh elevated permission di beberapa OS
            return []

        active_ports = set()
        remote_addresses = []
        
        for conn in connections:
            if conn.status in ("ESTABLISHED", "SYN_SENT") and conn.raddr:
                active_ports.add(conn.raddr.port)
                remote_addresses.append(conn.raddr.ip)

        # Cek port signatures
        for sig in MEETING_NETWORK_SIGNATURES:
            matching_ports = active_ports & sig["ports"]
            if matching_ports:
                matches.append(NetworkMatch(
                    remote_address="",
                    remote_port=next(iter(matching_ports)),
                    app_name=sig["name"],
                    score=sig["score"],
                ))

        # Cek domain (reverse DNS — lambat, opsional)
        # Untuk produksi, lebih baik cache hasil DNS ini
        # for ip in remote_addresses[:10]:  # Limit untuk performa
        #     try:
        #         hostname = socket.gethostbyaddr(ip)[0]
        #         for domain, app_name, score in MEETING_DOMAINS:
        #             if domain in hostname:
        #                 matches.append(...)
        #     except socket.herror:
        #         pass

        return matches
```

---

### Sinyal 4 — Analisis Karakteristik Audio

Ini sinyal paling mahal secara komputasi tapi paling universal — tidak bergantung pada proses atau network. Membedakan **suara percakapan** dari **musik** berdasarkan karakteristik sinyal.

```
Karakteristik Percakapan (Meeting):
  ✓ Energi dominan di 300Hz – 3.5kHz (speech range)
  ✓ Ada silence/jeda antar giliran bicara (turn-taking)
  ✓ Tidak ada ritme/beat yang berulang
  ✓ Spektrum tidak flat (ada formant peaks)
  ✓ Zero-crossing rate moderate

Karakteristik Musik:
  ✗ Energi tersebar luas 20Hz – 20kHz
  ✗ Energi konsisten, jarang silence panjang
  ✗ Ada pola ritmis (beat detection)
  ✗ Spektrum lebih flat atau harmonis teratur

Karakteristik Video (dialog + musik):
  ~ Campuran — bisa ada silence saat iklan
  ~ Speech ratio lebih rendah dari meeting
```

```python
# detection/audio_analyzer.py
import numpy as np
from scipy import signal as scipy_signal
from dataclasses import dataclass

@dataclass
class AudioAnalysis:
    speech_energy_ratio: float    # Rasio energi di speech band (0-1)
    silence_ratio: float          # Rasio frame yang senyap (0-1)
    spectral_flatness: float      # 0=tonal/musik, 1=noise/speech
    zero_crossing_rate: float     # ZCR — speech ~0.05-0.15
    has_rhythm: bool              # True = kemungkinan musik
    score: int                    # Skor kontribusi ke sistem (0-15)

class AudioAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sr = sample_rate
        self._buffer: list[np.ndarray] = []
        self._max_buffer_s = 10   # Analisis 10 detik terakhir
    
    def push_audio(self, chunk: np.ndarray) -> None:
        """Tambahkan audio chunk ke buffer analisis."""
        self._buffer.append(chunk.astype(np.float32) / 32768.0)
        # Trim buffer ke max_buffer_s
        total_samples = sum(len(c) for c in self._buffer)
        max_samples = self._max_buffer_s * self.sr
        while total_samples > max_samples and self._buffer:
            removed = self._buffer.pop(0)
            total_samples -= len(removed)

    def analyze(self) -> AudioAnalysis | None:
        if not self._buffer:
            return None
        
        audio = np.concatenate(self._buffer)
        
        # 1. Speech Energy Ratio
        # Speech range: 300Hz - 3500Hz
        # Hitung energi di speech band vs total energi
        freqs, psd = scipy_signal.welch(audio, self.sr, nperseg=512)
        speech_mask = (freqs >= 300) & (freqs <= 3500)
        speech_energy = np.sum(psd[speech_mask])
        total_energy = np.sum(psd) + 1e-10
        speech_ratio = float(speech_energy / total_energy)
        
        # 2. Silence Ratio
        # Frame dianggap senyap jika RMS < threshold
        frame_size = int(0.02 * self.sr)  # 20ms frames
        frames = [audio[i:i+frame_size] for i in range(0, len(audio)-frame_size, frame_size)]
        rms_values = [np.sqrt(np.mean(f**2)) for f in frames]
        silence_threshold = 0.01
        silence_ratio = sum(1 for r in rms_values if r < silence_threshold) / len(rms_values)
        
        # 3. Spectral Flatness (Wiener entropy)
        # Rendah = tonal (musik), Tinggi = noise-like (speech/white noise)
        geometric_mean = np.exp(np.mean(np.log(psd + 1e-10)))
        arithmetic_mean = np.mean(psd) + 1e-10
        spectral_flatness = float(geometric_mean / arithmetic_mean)
        
        # 4. Zero Crossing Rate
        signs = np.sign(audio)
        zcr = float(np.mean(np.abs(np.diff(signs)) / 2))
        
        # 5. Rhythm Detection (sederhana)
        # Hitung variasi RMS antar frame — musik lebih teratur
        rms_array = np.array(rms_values)
        rms_std = np.std(rms_array)
        rms_autocorr = np.correlate(rms_array - np.mean(rms_array), 
                                     rms_array - np.mean(rms_array), mode='full')
        # Normalize dan cek peak di 0.5-2 detik (beat range 30-120 BPM)
        norm_corr = rms_autocorr / (rms_autocorr[len(rms_autocorr)//2] + 1e-10)
        lag_min = int(0.4 * self.sr / frame_size)   # ~0.4 detik
        lag_max = int(2.0 * self.sr / frame_size)   # ~2 detik
        if lag_max < len(norm_corr) // 2:
            beat_region = norm_corr[len(norm_corr)//2 + lag_min:
                                    len(norm_corr)//2 + lag_max]
            has_rhythm = bool(np.max(beat_region) > 0.3)
        else:
            has_rhythm = False
        
        # Scoring: apakah ini likely percakapan?
        score = 0
        if speech_ratio > 0.55:          score += 4  # Energi dominan di speech band
        if silence_ratio > 0.15:         score += 3  # Ada jeda bicara
        if spectral_flatness > 0.1:      score += 2  # Tidak terlalu tonal
        if 0.03 < zcr < 0.25:           score += 2  # ZCR tipikal speech
        if not has_rhythm:               score += 2  # Tidak ada beat musik
        # Maximum: 13 poin
        
        return AudioAnalysis(
            speech_energy_ratio=speech_ratio,
            silence_ratio=silence_ratio,
            spectral_flatness=spectral_flatness,
            zero_crossing_rate=zcr,
            has_rhythm=has_rhythm,
            score=min(score, 15),
        )
```

---

## 3. Sistem Scoring Terintegrasi

```python
# detection/meeting_detector.py
import threading
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum

from .process_detector import ProcessDetector
from .window_detector import WindowDetector
from .network_detector import NetworkDetector
from .audio_analyzer import AudioAnalyzer

class MeetingState(Enum):
    NO_MEETING   = "no_meeting"
    LIKELY       = "likely_meeting"    # 30-49 poin
    IN_MEETING   = "in_meeting"        # ≥ 50 poin
    UNCERTAIN    = "uncertain"         # Setelah IN_MEETING, turun ke 20-49

@dataclass
class DetectionResult:
    state: MeetingState
    total_score: int
    breakdown: dict[str, int]       # {detector_name: score}
    app_detected: str = ""
    confidence: float = 0.0         # 0.0 - 1.0

START_THRESHOLD = 50    # Skor untuk mulai rekam
STOP_THRESHOLD  = 20    # Skor untuk stop rekam
STOP_GRACE_S    = 60    # Detik tunggu sebelum benar-benar stop

class MeetingDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        poll_interval_s: float = 5.0,
        on_meeting_start: callable = None,   # () -> None
        on_meeting_end: callable = None,     # () -> None
    ):
        self.sr = sample_rate
        self.poll_interval = poll_interval_s
        self.on_meeting_start = on_meeting_start
        self.on_meeting_end = on_meeting_end
        
        self._process_det = ProcessDetector()
        self._window_det = WindowDetector()
        self._network_det = NetworkDetector()
        self._audio_analyzer = AudioAnalyzer(sample_rate)
        
        self._state = MeetingState.NO_MEETING
        self._below_threshold_since: float | None = None
        self._running = False
        self._thread = None

    def push_audio(self, chunk: np.ndarray) -> None:
        """Dipanggil dari AudioCaptureEngine callback."""
        self._audio_analyzer.push_audio(chunk)

    def detect_once(self) -> DetectionResult:
        """Jalankan satu siklus deteksi dan return hasilnya."""
        breakdown = {}
        total_score = 0
        detected_app = ""

        # --- Sinyal 1: Process ---
        proc_matches = self._process_det.detect()
        if proc_matches:
            best = max(proc_matches, key=lambda m: m.score)
            breakdown["process"] = best.score
            total_score += best.score
            detected_app = best.app_name

        # --- Sinyal 2: Window Title ---
        win_matches = self._window_det.detect()
        if win_matches:
            best = max(win_matches, key=lambda m: m.score)
            breakdown["window"] = best.score
            total_score += best.score
            if not detected_app:
                detected_app = best.app_name

        # --- Sinyal 3: Network ---
        net_matches = self._network_det.detect()
        if net_matches:
            best = max(net_matches, key=lambda m: m.score)
            breakdown["network"] = best.score
            total_score += best.score

        # --- Sinyal 4: Audio Analysis ---
        audio_analysis = self._audio_analyzer.analyze()
        if audio_analysis:
            breakdown["audio"] = audio_analysis.score
            total_score += audio_analysis.score

        # --- State Machine ---
        if total_score >= START_THRESHOLD:
            new_state = MeetingState.IN_MEETING
            self._below_threshold_since = None
        elif total_score >= 30:
            new_state = MeetingState.LIKELY
            self._below_threshold_since = None
        elif self._state == MeetingState.IN_MEETING and total_score >= STOP_THRESHOLD:
            new_state = MeetingState.UNCERTAIN
            self._below_threshold_since = self._below_threshold_since or time.time()
        else:
            # Cek grace period sebelum stop
            if (self._below_threshold_since and 
                time.time() - self._below_threshold_since > STOP_GRACE_S):
                new_state = MeetingState.NO_MEETING
                self._below_threshold_since = None
            else:
                new_state = self._state  # Pertahankan state sementara

        # Trigger callbacks
        if new_state == MeetingState.IN_MEETING and self._state != MeetingState.IN_MEETING:
            if self.on_meeting_start:
                self.on_meeting_start()
        
        if new_state == MeetingState.NO_MEETING and self._state != MeetingState.NO_MEETING:
            if self.on_meeting_end:
                self.on_meeting_end()

        self._state = new_state
        confidence = min(total_score / 100.0, 1.0)
        
        return DetectionResult(
            state=new_state,
            total_score=total_score,
            breakdown=breakdown,
            app_detected=detected_app,
            confidence=confidence,
        )

    def _poll_loop(self):
        while self._running:
            self.detect_once()
            time.sleep(self.poll_interval)

    def start_monitoring(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
```

---

## 4. Integrasi ke Main Pipeline

```python
# Di main.py — mode auto-detect

async def run_auto_mode(settings: Settings):
    """Rekam otomatis saat meeting terdeteksi, stop saat selesai."""
    
    recording_active = False
    capture_engine = None
    
    def on_meeting_start():
        nonlocal recording_active, capture_engine
        if not recording_active:
            console.print("[bold green]🎙 Meeting terdeteksi! Mulai rekam...[/bold green]")
            # Start capture engine
            capture_engine = create_and_start_recording(settings)
            recording_active = True

    def on_meeting_end():
        nonlocal recording_active, capture_engine
        if recording_active:
            console.print("[bold yellow]⏹ Meeting selesai. Stop rekam & generate summary...[/bold yellow]")
            # Stop dan generate summary
            asyncio.create_task(stop_and_summarize(capture_engine, settings))
            recording_active = False
            capture_engine = None

    detector = MeetingDetector(
        sample_rate=settings.sample_rate,
        poll_interval_s=5.0,
        on_meeting_start=on_meeting_start,
        on_meeting_end=on_meeting_end,
    )
    
    def audio_callback(chunk: np.ndarray):
        detector.push_audio(chunk)     # Feed audio ke analyzer
        if recording_active:
            ring_buffer.push(chunk)    # Juga push ke recording buffer

    detector.start_monitoring()
    console.print("[dim]🔍 Watching for meetings... (Ctrl+C to exit)[/dim]")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        detector.stop_monitoring()
```

---

## 5. Skenario & Hasil Deteksi

| Skenario | Proses | Window | Network | Audio | Total | State |
|---|---|---|---|---|---|---|
| Zoom meeting aktif | +40 | +35 | +25 | +10 | **110** | ✅ IN_MEETING |
| Zoom buka tapi di lobby | +40 | +15 | 0 | +5 | **60** | ✅ IN_MEETING |
| Google Meet di browser | 0 | +35 | +25 | +10 | **70** | ✅ IN_MEETING |
| Spotify musik | 0 | 0 | 0 | +2 | **2** | ❌ NO_MEETING |
| YouTube video | 0 | 0 | 0 | +4 | **4** | ❌ NO_MEETING |
| YouTube podcast/talk | 0 | 0 | 0 | +8 | **8** | ❌ NO_MEETING |
| Teams tapi tidak ada call | +40 | 0 | 0 | +3 | **43** | 🟡 LIKELY |
| Discord voice channel | +40 | +25 | +20 | +10 | **95** | ✅ IN_MEETING |
| Zoom closed, audio masih ada | 0 | 0 | 0 | +8 | **8** | ⏳ UNCERTAIN (grace 60s) |

---

## 6. Edge Cases & Penanganan

### Problem: YouTube dengan banyak dialog (podcast, webinar recording)
**Gejala:** Audio score tinggi karena speech-like, tapi tidak ada proses meeting.  
**Penanganan:** Tanpa sinyal proses/window/network, max score = 15 → jauh dari threshold 50. Aman.

### Problem: Zoom buka tapi tidak ada call (window title = "Zoom")
**Gejala:** Proses score +40, tapi tidak ada meeting aktif.  
**Penanganan:** Window title "Zoom" (tanpa "Meeting") hanya +15, network score 0 → total 55. Borderline.  
**Fix:** Tambahkan cek window title lebih spesifik:
```python
# Zoom window patterns dengan score berbeda
("zoom meeting", 35, "Zoom"),         # Saat meeting aktif
("zoom - pro account", 10, "Zoom"),   # Idle/home screen
("zoom webinar", 30, "Zoom"),
```

### Problem: Browser-based meeting (selain Google Meet)
**Skenario:** Whereby, Jitsi, Gather.town, dll.  
**Penanganan:** WebRTC port detection (+15) + audio analysis (+10) = 25 (LIKELY tapi tidak rekam).  
**Solusi tambahan:** Cek tab title browser aktif:
```python
# Tambahkan ke WindowDetector
BROWSER_MEETING_PATTERNS = [
    r"whereby\.com",
    r"jitsi\.org",
    r"gather\.town", 
    r"around\.co",
    r"huddle\.team",
]
```

### Problem: Rekaman masih jalan setelah meeting selesai
**Penanganan:** Grace period 60 detik + state machine UNCERTAIN. Jika dalam 60 detik skor naik lagi (misalnya reconnect), rekaman tidak terhenti. 

### Problem: macOS — Permission untuk baca window title
**Gejala:** `_get_macos_titles()` return empty karena accessibility permission.  
**Fix:** Minta user grant Accessibility permission di System Settings → Privacy → Accessibility untuk aplikasi Python/Terminal.

---

## 7. Mode Manual Override

Selalu sediakan escape hatch untuk user — deteksi otomatis tidak sempurna.

```bash
# Force start rekam meski detector bilang bukan meeting
python -m meeting_recorder record --force

# Jalankan dalam mode auto-detect
python -m meeting_recorder watch

# Lihat skor deteksi saat ini (debug mode)
python -m meeting_recorder status
# Output:
# Process:  40 (Zoom detected)
# Window:   35 (Zoom Meeting)
# Network:  25 (port 8801 active)
# Audio:     8 (speech-like)
# ─────────────────────────────
# Total:   108 / 100  →  IN_MEETING ✅
```

---

## 8. Dependency Tambahan

```toml
# Tambahkan ke pyproject.toml
[project.optional-dependencies]
detection = [
    "psutil>=5.9",         # Process & network detection (semua platform)
    "scipy>=1.12",         # Audio analysis (spectral)
    "pywin32>=306",        # Window title detection (Windows only)
]
```

```bash
# Linux: install xdotool atau wmctrl untuk window detection
sudo apt install wmctrl       # Ubuntu/Debian
sudo pacman -S wmctrl         # Arch
```
