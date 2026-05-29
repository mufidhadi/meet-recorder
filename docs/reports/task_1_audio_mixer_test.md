# Laporan Akhir Tugas: Create Unit Test for Mixing Logic

- **Nama Tugas**: Create Unit Test for Mixing Logic
- **Histori Aksi**:
    1. Membuat file 	ests/unit/test_audio_mixer.py dengan test case yang gagal dan placeholder fungsi.
    2. Menjalankan test menggunakan uv run pytest dan mengonfirmasi kegagalan.
    3. Mengimplementasikan logika mixing audio (summation + clipping) di dalam file test tersebut.
    4. Menjalankan ulang test dan mengonfirmasi keberhasilan (pass).
    5. Melakukan commit terhadap perubahan dengan pesan 	est: add audio mixing logic unit test.
- **Tech Stack**: Python, pytest, numpy, uv.
- **List Kesulitan, Tantangan, Bug dan Solusi**:
    - Terjadi kesalahan sintaks PowerShell saat menggunakan && sebagai pemisah perintah. Solusi: Menggunakan ; sebagai pemisah perintah di PowerShell.
- **Lesson Learn**: Selalu perhatikan lingkungan shell saat menjalankan perintah gabungan untuk menghindari kesalahan sintaks.
