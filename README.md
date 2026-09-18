# Information Detection

**Prototipe asisten pemeriksaan klaim berbasis bukti dengan transformer, ekstraksi artikel, dan OCR.**

CekFakta membantu pengguna menemukan sumber yang berkaitan dengan sebuah klaim, membaca artikelnya, dan meninjau hubungan antara klaim dengan bukti. Proyek ini menyediakan aplikasi desktop Windows serta ekstensi browser untuk memulai pemeriksaan dari teks atau media yang dipilih pengguna.

> **Status: prototipe aktif.** Proyek ini dikembangkan untuk eksplorasi teknis dan portofolio. Hasilnya belum merupakan putusan kebenaran, belum memiliki pengukuran akurasi pada dataset representatif, dan belum ditujukan untuk penggunaan produksi yang membutuhkan jaminan ketepatan.

## Tentang proyek

Kemiripan kata antara klaim dan artikel belum cukup untuk menyatakan bahwa artikel tersebut mendukung klaim. Kesalahan membaca angka, konteks, atau subjek juga dapat menghasilkan kesimpulan yang menyesatkan.

CekFakta mengeksplorasi pendekatan yang menggabungkan pencarian sumber, pemahaman konteks melalui **Natural Language Inference (NLI)**, dan pemeriksaan terstruktur untuk pola klaim tertentu. Pengguna dapat meninjau sumber, kutipan, serta alasan perbandingan agar hasil analisis dapat diperiksa kembali.

Fokus teknis proyek meliputi:

- Integrasi transformer multilingual untuk seleksi relevansi dan perbandingan bukti.
- Crawling terarah dengan maksimal lima website per scan.
- Pemrosesan artikel panjang secara bertahap tanpa membuang bagian akhir teks hasil ekstraksi.
- Pemeriksaan nomor urut jabatan melalui pencocokan subjek, jabatan, lingkup, dan angka.
- Penyediaan alur pemeriksaan yang sama melalui aplikasi desktop dan ekstensi browser.

## Fitur saat ini

| Fitur | Kemampuan yang tersedia |
| --- | --- |
| Scan teks | Memeriksa teks pilihan di browser, teks clipboard, atau file lokal. |
| Seleksi sumber | Menilai relevansi judul dan ringkasan sebelum membuka website. Sumber yang membantah klaim tetap dapat terpilih. |
| Crawling artikel | Membaca teks utama dan tabel dari halaman yang dapat diakses, dengan maksimal lima hostname website per scan. |
| Perbandingan bukti | Menampilkan hubungan mendukung, membantah, atau belum cukup/tidak relevan beserta sumbernya. |
| Pemeriksaan nomor urut | Membandingkan angka secara eksplisit untuk pola klaim jabatan berbahasa Indonesia yang didukung. |
| OCR foto | Mengekstrak tulisan pada foto melalui EasyOCR berbahasa Indonesia dan Inggris. |
| Pembacaan video terbatas | Mengambil satu frame video; caption atau subtitle aktif pada browser juga dapat digunakan jika tersedia. |
| Penjelasan istilah | Menampilkan arti dari kamus awal atau kutipan definisi dalam artikel yang sudah dibaca. |
| Integrasi Windows | Menyediakan popup desktop dan pemasangan menu Scan pada File Explorer secara opsional. |

### Format input lokal

| Jenis | Format |
| --- | --- |
| Teks dan subtitle | `.txt`, `.md`, `.srt`, `.vtt` — UTF-8 atau UTF-16 |
| Foto | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff` |
| Video | `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.m4v` — bergantung pada dukungan codec |

File audio, PDF, dan DOCX belum didukung sebagai input langsung. Teks dokumen dapat disalin dari aplikasi pembaca lalu diperiksa melalui clipboard.

## Alur pemeriksaan

1. **Pilih input.** Scan berjalan setelah tindakan pengguna, tanpa pemantauan layar atau clipboard secara berkala.
2. **Siapkan teks.** Teks dipakai langsung; foto dan satu frame video dibaca melalui OCR.
3. **Cari kandidat sumber.** Mesin pencari mengembalikan judul, ringkasan, dan tautan terkait klaim.
4. **Nilai relevansi.** Transformer membandingkan metadata pencarian dengan klaim. Pola nomor urut yang eksplisit juga dapat dikenali secara terstruktur.
5. **Pilih maksimal lima website.** Kandidat diurutkan sebelum crawling; jumlah tidak dipaksakan menjadi lima jika yang lolos lebih sedikit.
6. **Baca artikel.** Crawler mengambil halaman yang diizinkan dan mengekstrak teks utama serta tabel. Ringkasan pencarian hanya dipakai untuk seleksi, bukan bukti akhir.
7. **Bandingkan bukti.** Klaim umum diproses melalui NLI; pola nomor urut yang didukung diperiksa dengan pencocokan angka.
8. **Tinjau hasil.** Pengguna melihat persentase, kutipan, tautan sumber, dan catatan keterbatasan.

### Memahami persentase

**Klaim umum — Persentase hubungan bukti.** Angka merupakan skor model atas hubungan teks sumber dengan klaim. Skor belum dikalibrasi sebagai probabilitas benar atau hoaks.

**Nomor urut — Komposisi bukti nomor urut.** Angka merupakan proporsi sumber terbaca setelah deduplikasi yang mendukung, membantah, atau belum cukup menjelaskan klaim. Jika tiga dari lima sumber memuat angka yang bertentangan dan dua tidak menjelaskan urutannya, hasilnya adalah 60% membantah, 0% mendukung, dan 40% belum cukup.

Pemeriksaan angka tidak menyimpan daftar fakta tokoh beserta nomor jabatannya. Angka pembanding harus ditemukan dalam sumber. Tanggal, nomor acara, atau angka milik orang dan jabatan lain tidak otomatis dihitung sebagai bukti urutan jabatan.

## Teknologi

| Komponen | Teknologi |
| --- | --- |
| Bahasa | Python dan JavaScript |
| API lokal | FastAPI, Uvicorn |
| Inferensi model | PyTorch, Hugging Face Transformers |
| Model NLI bawaan | `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` |
| Penemuan sumber | DDGS |
| Ekstraksi artikel | Trafilatura, Beautiful Soup |
| OCR | EasyOCR |
| Pengolahan media | Pillow, OpenCV |
| Desktop | PySide6 / Qt |
| Ekstensi | Manifest V3 untuk Chrome dan Microsoft Edge |

## Kebutuhan sistem

### Software

- **Windows** untuk launcher, desktop, dan integrasi File Explorer. Panduan instalasi berikut ditujukan untuk Windows.
- **Python 3.11 64-bit**, sesuai lingkungan pengembangan proyek, beserta pip.
- **Chrome atau Microsoft Edge** jika menggunakan ekstensi.
- **Koneksi internet** untuk instalasi dependensi, unduhan model pertama, serta pencarian dan pengambilan sumber.
- **Node.js** hanya untuk menjalankan tes JavaScript ekstensi; tidak diperlukan untuk menjalankan aplikasi Python.

### Hardware

Spesifikasi berikut merupakan **estimasi awal untuk percobaan dan pengembangan**, bukan persyaratan minimum yang sudah dibuktikan melalui benchmark lintas perangkat.

| Komponen | Percobaan awal | Pengembangan yang lebih nyaman |
| --- | --- | --- |
| CPU | Prosesor x64 dengan 4 core | Prosesor modern dengan 6–8 core |
| RAM | 8 GB; tutup aplikasi berat saat memuat model | 16 GB atau lebih |
| Ruang kosong | Sekitar 8 GB untuk environment, dependensi, dan cache | 15 GB atau lebih pada SSD |
| GPU | Tidak wajib | Implementasi saat ini memakai CPU; akselerasi GPU belum dikonfigurasi |
| Jaringan | Koneksi stabil untuk mengakses sumber | Koneksi stabil untuk unduhan model dan artikel |

Waktu scan bergantung pada panjang artikel, OCR, jumlah kandidat, kemampuan CPU, dan respons website. Proses pertama dapat lebih lama karena unduhan model. Kamera dan mikrofon belum diperlukan; media saat ini berasal dari file atau elemen halaman yang dipilih.

## Instalasi

### 1. Siapkan proyek

Clone repositori ini atau unduh dan ekstrak arsipnya. Buka PowerShell pada direktori utama proyek, yaitu folder yang berisi `requirements-desktop.txt`.

Pastikan Python tersedia:

```powershell
py -3.11 --version
```

### 2. Buat virtual environment

```powershell
py -3.11 -m venv .venv
```

### 3. Pasang dependensi

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
```

File tersebut mencakup dependensi API, model AI, OCR, dan desktop. Pemanggilan interpreter secara langsung membuat aktivasi virtual environment tidak diperlukan.

Model NLI dan OCR dimuat saat dibutuhkan. Pada penggunaan pertama, pastikan koneksi tersedia dan beri waktu untuk unduhan model. Alur bawaan tidak memerlukan API key berbayar.

## Cara menggunakan

### Desktop lokal

```powershell
.\start-local.cmd
```

1. Pilih **Scan file lokal** untuk membaca teks, foto, atau video.
2. Untuk video, tentukan posisi frame dalam detik.
3. Untuk teks dari aplikasi lain, salin teks lalu pilih **Scan teks clipboard**.
4. Tinjau hasil bersama kutipan dan tautan sumber.

Mode desktop memanggil mesin scan secara langsung; server ekstensi tidak perlu dijalankan terpisah.

### Ekstensi browser

Jalankan server lokal dan biarkan jendelanya terbuka:

```powershell
.\start-desktop.cmd
```

Kemudian:

1. Buka `chrome://extensions` atau `edge://extensions`.
2. Aktifkan **Developer mode / Mode pengembang**.
3. Pilih **Load unpacked / Muat yang belum dipaketkan** dan arahkan ke folder [`extension`](extension).
4. Buka website, blok teks atau klik kanan foto/video, lalu pilih menu **Scan dengan CekFakta** yang sesuai.
5. Tinjau popup hasil pada halaman.

Setelah perubahan kode ekstensi, lakukan **Reload** pada halaman ekstensi dan muat ulang website. Halaman internal browser, toko ekstensi, dan beberapa penampil PDF tidak mengizinkan popup. Akses piksel media juga dapat dibatasi browser.

Server dapat dijalankan tanpa launcher:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Antarmuka web awal masih tersedia di `http://127.0.0.1:8000`, tetapi menggunakan klasifikasi teks awal dan belum mengikuti seluruh alur perbandingan bukti. Gunakan desktop atau ekstensi untuk mencoba alur utama proyek.

### Menu File Explorer — opsional

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-local-menu.ps1
```

Skrip menambahkan menu **Scan dengan CekFakta** pada registry akun Windows saat ini untuk format yang didukung. Pada Windows 11, menu dapat berada di **Show more options**. Pasang ulang jika folder proyek dipindahkan karena registrasi menunjuk ke lokasi proyek. Video dari menu Explorer memakai frame awal.

## Batasan prototipe

- **Akurasi belum tervalidasi secara menyeluruh.** Model dapat salah memahami konteks; sumber dapat keliru, saling menyalin, atau tidak cukup menjawab klaim.
- **Pemeriksaan angka masih terbatas.** Parser mendukung pola tertentu untuk presiden, wakil presiden, dan perdana menteri dalam bahasa Indonesia. Alias, pronomina, klaim majemuk, negasi, dan hubungan angka belum diselesaikan secara umum.
- **Relevansi belum dikalibrasi.** Ambang seleksi merupakan aturan eksperimen; kandidat relevan masih mungkin terlewat.
- **Crawling terbatas pada artikel terpilih.** Aplikasi tidak membaca seluruh halaman dalam satu domain. Batas lima website memakai hostname dengan penyamaan awalan `www`; website yang gagal diakses tetap memakai kuota pilihan.
- **Akses halaman tidak selalu berhasil.** Robots.txt tetap dihormati. Konten yang membutuhkan login, JavaScript, pagination, atau melewati batas HTML 8 MB belum dijamin terbaca.
- **Pembacaan lengkap mengacu pada hasil ekstraksi.** Seluruh teks yang berhasil diekstrak diproses, tetapi belum tentu mencakup setiap elemen visual halaman.
- **Foto masih berupa OCR.** Belum tersedia deteksi manipulasi gambar, pemahaman adegan, atau pemeriksaan keaslian visual.
- **Video masih satu frame.** Belum tersedia analisis urutan adegan, deepfake, atau transkripsi audio.
- **Input teks dibatasi 30.000 karakter.** Batas ini berlaku pada teks pilihan dan file lokal, bukan pemotongan artikel hasil crawling.

## Roadmap: ekstraksi foto dan suara

Pengembangan berikutnya berfokus pada kualitas ekstraksi sebelum memperluas penilaian klaim. Seluruh kemampuan di bawah merupakan **rencana pengembangan**, belum fitur yang tersedia.

| Tahap | Fokus | Target dan evaluasi |
| --- | --- | --- |
| 1 | Peningkatan OCR foto | Koreksi kemiringan, penyesuaian kontras, pengurangan noise, dan segmentasi area teks. Ukur kesalahan karakter/kata pada foto Indonesia, terutama angka dan nama. |
| 2 | Tinjauan hasil OCR | Tampilkan teks bersama area asal dan penanda bagian meragukan. Pengguna dapat mengoreksi hasil sebelum pencarian bukti. |
| 3 | Ekstraksi dan transkripsi suara | Tambahkan input audio dan ekstraksi track audio video. Evaluasi speech-to-text untuk bahasa Indonesia, campuran bahasa, noise, serta variasi pelafalan. |
| 4 | Transkrip dengan timestamp | Hubungkan segmen ucapan dengan waktu asal, tandai transkripsi meragukan, dan ukur ketepatan angka, nama, serta kata penyangkalan. |
| 5 | Penggabungan media | Selaraskan OCR beberapa frame dengan transkrip suara. Setiap klaim dapat ditelusuri ke teks, frame, atau segmen audio asal. |
| 6 | Evaluasi menyeluruh | Bangun dataset uji terpisah untuk ekstraksi, relevansi, dan perbandingan klaim. Catat akurasi, latensi, RAM, dan kasus kegagalan sebelum penggunaan lebih luas. |

Prioritasnya adalah menghasilkan teks yang dapat diperiksa kembali. Kesalahan membaca angka, nama, atau penyangkalan pada tahap OCR/transkripsi dapat mengubah makna klaim sebelum verifikasi dimulai.

## Privasi dan aliran data

- Scan dimulai melalui tindakan pengguna. Alur utama tidak memantau layar, clipboard, kamera, atau mikrofon secara otomatis.
- Ekstensi mengirim input yang dipilih ke server lokal `127.0.0.1:8000`.
- Inferensi NLI dan OCR berlangsung lokal. Potongan teks klaim dikirim ke layanan pencarian, sehingga alur ini **tidak sepenuhnya offline**.
- Crawler mengakses website publik yang terpilih. Piksel media diproses dalam memori oleh alur scan; file asli tidak diubah.
- Model dapat diunduh dan disimpan dalam cache lokal pada penggunaan pertama.

## Struktur proyek

```text
app/
  main.py              API dan pengelolaan pekerjaan scan
  context_scan.py      Orkestrasi pemeriksaan utama
  relevance.py         Seleksi kandidat sebelum crawling
  crawler.py           Pengambilan dan ekstraksi artikel
  evidence.py          Perbandingan bukti dan agregasi hasil
  ordinal_facts.py     Pemeriksaan nomor urut jabatan
  classifier.py        Model dan klasifikasi teks awal
  local_scan.py        Persiapan file teks, foto, dan video
  local_desktop.py     Antarmuka desktop
extension/             Ekstensi browser dan popup hasil
tests/                 Pengujian unit dan smoke test
requirements*.txt      Dependensi bertingkat
start-local.cmd        Launcher desktop lokal
start-desktop.cmd      Launcher server untuk ekstensi
install-local-menu.ps1 Integrasi menu File Explorer
```

## Pengujian

Jalankan dari direktori utama proyek setelah instalasi dependensi:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
node --test tests/extension.test.cjs
.\.venv\Scripts\python.exe -c "import runpy; runpy.run_path('tests/local_desktop_smoke.py')"
```

Tes mencakup input, pembatasan sumber, seleksi sebelum crawling, teks panjang, nomor urut, serta perilaku antarmuka. Sebagian tes menggunakan mock untuk model dan jaringan agar deterministik. Kelulusan tes regresi tidak setara dengan akurasi pemeriksaan fakta pada data dunia nyata.

## Referensi metode

- [Model multilingual MiniLM untuk NLI](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli)
- [Evaluating Numeracy of Language Models as a Natural Language Inference Task](https://aclanthology.org/2025.findings-naacl.467/)
- [TabVer: Tabular Fact Verification with Natural Logic](https://aclanthology.org/2024.tacl-1.89/)

Implementasi CekFakta menggabungkan NLI lokal dengan parser konservatif. Proyek ini bukan reproduksi TabVer atau sistem yang telah tervalidasi untuk seluruh jenis klaim.
