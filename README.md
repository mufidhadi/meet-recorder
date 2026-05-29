# Meet Recorder 🎙️

Meet Recorder adalah aplikasi desktop modern berbasis Python untuk merekam rapat, mentranskripsikan percakapan secara real-time, dan menghasilkan ringkasan otomatis menggunakan kekuatan **Gemini AI**.

Dirancang dengan filosofi desain **Windows 11 Fluent Design**, aplikasi ini memberikan pengalaman yang bersih, profesional, dan efisien untuk mendokumentasikan setiap pertemuan Anda.

---

## ✨ Fitur Utama

- **Dual Audio Capture**: Merekam suara dari Mikrofon (input) dan System Audio (output) secara bersamaan—sempurna untuk Zoom, Google Meet, atau Microsoft Teams.
- **Real-time Transcription**: Lihat teks percakapan muncul saat rapat sedang berlangsung.
- **AI-Powered Summarization**: Menghasilkan ringkasan rapat otomatis dalam format Markdown menggunakan model Gemini AI terbaru.
- **History Viewer**: Telusuri rekaman lama lengkap dengan audio player yang tersinkronisasi dengan baris transkrip.
- **Modern UI**: Interface cantik dengan dukungan Dark Mode, VU Meter real-time, dan animasi yang halus.
- **Offline Capable**: Mendukung pemrosesan lokal dan manajemen chunk audio untuk efisiensi resource.

---

## 🚀 Persiapan & Instalasi

Project ini dikelola menggunakan [**uv**](https://github.com/astral-sh/uv) untuk manajemen paket yang sangat cepat.

### 1. Prasyarat
- Python 3.10 atau lebih tinggi.
- API Key Google Gemini (Dapatkan di [Google AI Studio](https://aistudio.google.com/)).

### 2. Kloning Repository
```bash
git clone https://github.com/mufidhadi/meet-recorder.git
cd meet-recorder
```

### 3. Instalasi Dependensi
```bash
uv sync
```

### 4. Konfigurasi Environment
Salin file `.env.example` menjadi `.env` dan masukkan API Key Anda:
```bash
cp .env.example .env
```
Isi variabel berikut:
- `GEMINI_API_KEY`: API Key Gemini Anda.
- `GEMINI_MODEL_ID`: Model yang ingin digunakan (default: `gemini-2.0-flash`).

---

## 🛠️ Cara Penggunaan

### Menjalankan Aplikasi Desktop (GUI)
Gunakan perintah berikut untuk membuka interface grafis:
```bash
uv run python ui_app.py
```

### Menjalankan via CLI
Anda juga bisa memulai perekaman langsung melalui terminal:
```bash
uv run main.py record
```

---

## 🏗️ Arsitektur Sistem

- **Backend**: Python dengan asinkronus processing.
- **Frontend**: Custom Desktop UI (berbasis desain Fluent).
- **AI Engine**: Google Generative AI (Gemini) untuk transkripsi dan ringkasan.
- **Audio Engine**: Menangani *loopback capture* untuk merekam audio sistem di Windows.

---

## 📝 Lisensi

Distribusi project ini mengikuti kebijakan kepemilikan [mufidhadi](https://github.com/mufidhadi). Silakan hubungi pemilik repository untuk pertanyaan lebih lanjut.

---
*Dibuat dengan ❤️ oleh Mas Mufid menggunakan Gemini CLI.*
