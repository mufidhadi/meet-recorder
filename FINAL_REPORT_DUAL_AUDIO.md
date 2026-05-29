# Laporan Akhir: Dual Audio Capture (Mic + Loopback)

## Nama Tugas
Implementasi Pencampuran Suara Mikrofon dan Sistem (Dual Audio Capture) pada Meet-Recorder.

## Histori Aksi
1.  **Analisa Root Cause**: Menemukan bahwa `WindowsCaptureEngine` hanya menangkap stream loopback.
2.  **Eksperimen**: Membuat `scratch/test_dual_capture.py` untuk membuktikan bahwa dua stream WASAPI bisa dibuka dan dicampur secara manual.
3.  **Dokumen Desain**: Menyusun spesifikasi teknis untuk Software Mixing di `docs/superpowers/specs/2026-05-12-dual-audio-capture-design.md`.
4.  **Unit Testing**: Membuat `tests/unit/test_audio_mixer.py` untuk memvalidasi logika penjumlahan audio dan pencegahan clipping.
5.  **Refactoring & Implementasi**: 
    - Menambahkan `meeting_recorder/processing/audio.py` sebagai utility mixer.
    - Mengubah `meeting_recorder/capture/windows.py` untuk mendukung dual stream, dual buffer (deque), dan background mixer thread.
    - Menambahkan penanganan "residue" untuk menyinkronkan data audio yang datang dengan ukuran berbeda.
6.  **Verifikasi**: Menambahkan `tests/unit/test_windows_capture_logic.py` untuk menguji alur data dari callback hingga mixer.

## Tech Stack
- **Language**: Python 3.12
- **Audio Library**: PyAudioWPatch (WASAPI support)
- **Processing**: NumPy (vectorized summation & clipping)
- **Concurrency**: Threading (Mixer Thread), Lock (Buffer Safety)
- **Testing**: Pytest

## List Kesulitan, Tantangan, Bug dan Solusi
- **Tantangan**: Ukuran chunk audio dari Loopback dan Mic tidak selalu sama persis dalam satu siklus callback.
- **Solusi**: Menggunakan "residue buffer". Sisa data yang tidak bisa dicampur pada siklus sekarang disimpan dan digabungkan dengan data baru pada siklus berikutnya, memastikan sinkronisasi sample-level.
- **Bug**: Penggunaan `.tolist()` pada buffer audio menyebabkan degradasi performa yang signifikan.
- **Solusi**: Menggunakan deque yang menyimpan objek `numpy.ndarray` secara langsung dan melakukan operasi `concatenate` hanya saat mixing.

## Lesson Learned
- WASAPI Shared Mode sangat fleksibel untuk menangkap banyak input audio secara bersamaan tanpa mengganggu aplikasi lain.
- Operasi `numpy` jauh lebih efisien daripada manipulasi list Python untuk data audio berdensitas tinggi.
- Sinkronisasi stream audio memerlukan penanganan khusus pada sisa data (residue) untuk mencegah pergeseran suara (audio drift).

## Status Akhir
- Unit tests: 5 passed (Mixer logic & Engine logic).
- Kode siap digunakan.
- Branch: `feat/dual-audio-capture`.
