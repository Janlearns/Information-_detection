# CekFakta — Information Detection

**Prototipe asisten pemeriksaan klaim berbasis bukti dengan transformer, ekstraksi artikel, dan OCR.**

CekFakta membantu pengguna menemukan sumber yang berkaitan dengan sebuah klaim, membaca artikelnya, dan meninjau hubungan antara klaim dengan bukti. Proyek ini menyediakan aplikasi desktop Windows serta ekstensi browser untuk memulai pemeriksaan dari teks atau media yang dipilih pengguna.

> **Status: prototipe aktif.** Proyek ini dikembangkan untuk eksplorasi teknis dan portofolio. Hasilnya belum merupakan putusan kebenaran, belum memiliki pengukuran akurasi pada dataset representatif, dan belum ditujukan untuk penggunaan produksi yang membutuhkan jaminan ketepatan.

**Yang ditunjukkan proyek ini:** integrasi model NLP dengan pencarian web, ekstraksi artikel, OCR, API lokal, aplikasi desktop, dan ekstensi browser dalam satu alur pemeriksaan yang bisa ditelusuri ke sumber.

**Keterbatasan utama:** pencarian dapat gagal, sumber relevan dapat terlewat, dan kalimat yang benar secara fakta masih bisa menghasilkan “belum cukup bukti” karena bukti gagal dibaca atau hubungan antarentitas belum dikenali. Proyek ini mengintegrasikan model pralatih; belum melatih model pemeriksaan fakta sendiri.

## Daftar isi

- [Tentang proyek](#tentang-proyek) dan [fitur](#fitur-saat-ini)
- [Cara kerja sistem dan peran AI](#cara-kerja-sistem-dan-peran-ai)
- [Alur pemeriksaan dan makna persentase](#alur-pemeriksaan)
- [Teknologi](#teknologi) dan [kebutuhan sistem](#kebutuhan-sistem)
- [Instalasi dan konfigurasi .env](#instalasi)
- [Cara menggunakan](#cara-menggunakan)
- [API lokal](#api-lokal)
- [Penanganan masalah](#penanganan-masalah)
- [Kekurangan dan kasus kegagalan](#kekurangan-dan-kasus-kegagalan)
- [Kemampuan yang belum tersedia](#kemampuan-yang-belum-tersedia) dan [rencana pengembangan](#rencana-pengembangan)
- [Privasi dan aliran data](#privasi-dan-aliran-data)
- [Struktur proyek](#struktur-proyek) dan [pengujian](#pengujian)

## Tentang proyek

Kemiripan kata antara klaim dan artikel belum cukup untuk menyatakan bahwa artikel tersebut mendukung klaim. Kesalahan membaca angka, konteks, atau subjek juga dapat menghasilkan kesimpulan yang menyesatkan.

CekFakta mengeksplorasi pendekatan yang menggabungkan pencarian sumber, pemahaman konteks melalui **Natural Language Inference (NLI)**, dan pemeriksaan terstruktur untuk pola klaim tertentu. Pengguna dapat meninjau sumber, kutipan, serta alasan perbandingan agar hasil analisis dapat diperiksa kembali.

Fokus teknis proyek meliputi:

- Integrasi transformer multilingual untuk seleksi relevansi dan perbandingan bukti.
- Crawling terarah dengan target maksimal lima sumber terbaca, memakai hingga sepuluh kandidat website relevan untuk mengganti sumber yang gagal dibaca.
- Pemrosesan artikel panjang secara bertahap tanpa membuang bagian akhir teks hasil ekstraksi.
- Pemeriksaan nomor urut jabatan melalui pencocokan subjek, jabatan, lingkup, dan angka.
- Penyediaan alur pemeriksaan yang sama melalui aplikasi desktop dan ekstensi browser.

## Fitur saat ini

| Fitur | Kemampuan yang tersedia |
| --- | --- |
| Scan teks | Memeriksa teks pilihan di browser, teks clipboard, atau file lokal. |
| Seleksi sumber | Menilai relevansi judul dan ringkasan sebelum membuka website. Sumber yang membantah klaim tetap dapat terpilih. |
| Crawling artikel | Membaca teks utama dan tabel dari halaman yang dapat diakses. Menargetkan maksimal lima sumber terbaca dari hingga sepuluh hostname kandidat yang lolos seleksi relevansi. |
| Pemulihan sumber | Mengganti sumber gagal baca dengan kandidat relevan berikutnya dan mengikuti redirect terbatas pada website yang sama, termasuk perpindahan `www` ke alamat tanpa `www` atau sebaliknya. |
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

### Memilih mode penggunaan

| Kebutuhan | Mode | Cara menjalankan |
| --- | --- | --- |
| Memeriksa file atau teks yang disalin dari aplikasi lain | Desktop lokal, alur pemeriksaan bukti utama | `start-local.cmd` |
| Memeriksa teks/foto/video yang dipilih di website | Ekstensi browser dengan API lokal, alur pemeriksaan bukti utama | `start-desktop.cmd`, lalu gunakan menu klik kanan ekstensi |
| Mengintegrasikan scan dengan skrip lain | API lokal | Jalankan server, lalu gunakan `/api/scan` atau `/api/scan/jobs` |
| Mencoba klasifikasi kategori teks awal | Halaman web awal | Buka `http://127.0.0.1:8000` setelah server berjalan; hasilnya tidak setara dengan pemeriksaan bukti utama |

Untuk percobaan pertama, gunakan desktop dan satu klaim pendek dengan subjek yang jelas. Setelah hasil pertama tampil, tinjau teks yang dianalisis, sumber yang terbaca, dan rincian hubungan bukti sebelum mencoba dokumen panjang atau OCR.

### Batas input dan persiapan media

| Input | Batas atau perlakuan saat ini |
| --- | --- |
| Teks lokal / clipboard / field teks API | Maksimal 30.000 karakter; file teks lokal juga dibatasi 2.000.000 byte. |
| File teks UTF-16 | Harus memiliki penanda encoding (BOM); selain itu pembaca mencoba UTF-8, termasuk UTF-8 dengan BOM. |
| Foto lokal | Maksimal 50.000.000 byte dan 40 megapiksel; orientasi EXIF diperbaiki sebelum konversi. |
| Foto atau frame video lokal yang dikirim ke OCR | Diperkecil agar muat dalam 1.400 × 1.400 piksel dengan rasio tetap, lalu diubah menjadi JPEG kualitas 85 di memori. |
| Frame melalui API | Data URL JPEG/PNG; field maksimal 2.800.000 karakter, hasil decode maksimal 2.000.000 byte dan 4 megapiksel. |
| Video lokal | Satu frame pada posisi detik yang dipilih; keberhasilan pembacaan bergantung codec dan posisi frame. |
| SRT / VTT | Dibaca sebagai teks; belum ada parser subtitle khusus untuk menghapus seluruh timestamp dan metadata. |

Jika nama atau angka pada hasil OCR tidak sesuai gambar, perbaiki teks secara manual melalui clipboard dan lakukan scan teks. Antarmuka belum menyediakan editor koreksi OCR sebelum pencarian.

## Cara kerja sistem dan peran AI

Sistem berjalan ketika pengguna menekan **Scan**. Input diubah menjadi teks, digunakan untuk mencari sumber di internet, lalu dibandingkan dengan isi artikel yang berhasil dibaca. AI membantu membaca tulisan pada gambar dan menilai hubungan makna antara klaim dengan sumber. Pencarian, pengambilan halaman, pemeriksaan angka, dan penghitungan hasil diatur oleh kode aplikasi.

```text
Pengguna memilih teks / foto / satu frame video
                      |
                      v
Persiapan teks (OCR untuk tulisan pada gambar)
                      |
                      v
Pemisahan kalimat dan penyusunan kueri pencarian
                      |
                      v
Pencarian web melalui DDGS
                      |
                      v
Seleksi relevansi judul dan ringkasan dengan NLI / aturan nomor urut
                      |
                      v
Crawler membaca artikel (target maksimal 5 sumber; hingga 10 website dicoba)
                      |
                      v
Perbandingan isi artikel dengan setiap kalimat input
         NLI untuk hubungan makna + aturan untuk pola nomor urut
                      |
                      v
Penggabungan skor, kutipan, tautan, dan catatan keterbatasan
                      |
                      v
Pengguna meninjau hasil dan sumbernya
```

### Dari antarmuka ke mesin pemeriksaan

Pada **desktop**, `app/local_scan.py` menyiapkan input file, lalu mesin pemeriksaan di `app/context_scan.py` menjalankan scan. Teks clipboard juga masuk ke mesin yang sama. Pada **ekstensi browser**, input pilihan dikirim ke API lokal di `app/main.py`; aplikasi menjalankan pekerjaan scan dan ekstensi mengambil hasilnya untuk ditampilkan. Dengan demikian, kedua antarmuka memakai alur pemeriksaan bukti yang sama.

Mesin pemeriksaan mengoordinasikan pencarian, seleksi kandidat, pembacaan artikel, dan analisis. `app/relevance.py` memilih kandidat, `app/crawler.py` mengambil isi halaman, dan `app/evidence.py` membandingkan bukti serta menggabungkan hasil. Jika pencarian atau pembacaan gagal, status kegagalan diteruskan ke antarmuka; tidak adanya artikel tidak menghasilkan kesimpulan bahwa klaim salah.

### Apa yang dikerjakan AI?

| Tahap | Peran AI | Peran kode aplikasi |
| --- | --- | --- |
| Membaca foto atau frame video | EasyOCR mengenali tulisan berbahasa Indonesia dan Inggris menjadi teks. | Menyiapkan gambar/frame dan menggabungkan teks OCR dengan teks pendamping yang tersedia. |
| Memilih sumber | Model NLI menilai apakah judul dan ringkasan mendukung, membantah, atau tidak cukup berkaitan dengan klaim. | Menjumlahkan skor mendukung dan membantah sebagai relevansi, menerapkan ambang seleksi, memeriksa pola nomor urut, serta membatasi dan mengurutkan website. |
| Membandingkan bukti | Model NLI menilai hubungan makna isi artikel dengan kalimat input. | Membagi teks panjang menjadi potongan yang muat dalam model, memprosesnya bertahap, dan menggabungkan skor bagian yang relevan. |
| Memeriksa nomor urut jabatan | Pada pola tambahan tertentu, NLI membantu memeriksa hubungan orang dengan jabatan dalam kutipan. | Parser di `app/ordinal_facts.py` mencocokkan subjek, jabatan, lingkup, dan nomor; angka dari sumber dibandingkan secara langsung. |
| Menyajikan hasil | Skor NLI menjadi salah satu bahan hasil analisis. | Menghapus sumber duplikat, menghitung agregat atau kesepakatan bukti, lalu menyusun ringkasan, kutipan, tautan, dan pesan status. |

**NLI (Natural Language Inference)** menerima pasangan teks: isi sumber sebagai *premis* dan kalimat pengguna sebagai *klaim yang diuji*. Model menghasilkan tiga skor hubungan: **mendukung**, **membantah**, dan **netral/belum cukup**. Sumber yang membantah tetap penting untuk dipilih karena relevansi tidak sama dengan persetujuan terhadap klaim.

Model bawaan adalah `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`, sebuah Transformer pralatih. Saat scan, aplikasi melakukan **inferensi**, yaitu memakai model yang sudah dilatih untuk menghitung skor pada input baru. Scan tidak melatih ulang model atau otomatis menambahkan fakta ke pengetahuannya. NLI dan OCR dimuat saat dibutuhkan dan dijalankan secara lokal pada CPU; pencarian web serta pengambilan artikel tetap menggunakan internet.

Ringkasan hasil disusun dari skor, aturan, dan teks sumber oleh aplikasi. Alur ini tidak memakai model generatif untuk mengarang jawaban atau artikel bukti. Penjelasan istilah berasal dari kamus awal atau kalimat definisi yang ditemukan dalam artikel. Kutipan yang ditampilkan membantu peninjauan, sedangkan perbandingan NLI memproses seluruh teks hasil ekstraksi secara bertahap; kutipan tampilan bukan penjelasan lengkap atas setiap skor model.

### Contoh proses satu klaim

Misalnya pengguna memasukkan **“Tokoh A adalah presiden ke-4 Negara B.”** Contoh ini bersifat ilustratif:

1. Aplikasi mengenali pola subjek, jabatan, negara, dan nomor urut, lalu menyusun kueri untuk mencari sumber terkait.
2. Hasil pencarian disaring berdasarkan hubungannya dengan klaim. Artikel yang menyebut nomor berbeda tetap dapat dipilih sebagai calon bukti bantahan.
3. Crawler membuka kandidat terpilih dan mengambil teks artikelnya. Judul atau ringkasan pencarian saja tidak digunakan sebagai bukti akhir.
4. Jika isi artikel secara jelas menyebut Tokoh A sebagai presiden ke-4 Negara B, pemeriksaan terstruktur mencatat dukungan. Jika menyebut ke-5 dengan subjek, jabatan, dan lingkup yang cocok, hasilnya bantahan. Jika hubungan tersebut tidak jelas atau bukti angkanya ambigu, hasilnya belum cukup.
5. Aplikasi menggabungkan hasil dari sumber unik yang terbaca dan menampilkan kesepakatan beserta cakupannya. Pengguna dapat membuka tautan untuk memeriksa konteks asli.

Untuk klaim umum yang tidak masuk pola nomor urut, hubungan bukti dinilai melalui NLI. Persentase yang ditampilkan merupakan skor hubungan teks, bukan peluang bahwa klaim pasti benar. Peran AI adalah membantu menemukan dan membandingkan bukti; kualitas sumber dan ketepatan pembacaan tetap menentukan kegunaan hasil.

## Alur pemeriksaan

1. **Pilih input.** Scan berjalan setelah tindakan pengguna, tanpa pemantauan layar atau clipboard secara berkala.
2. **Siapkan teks.** Teks dipakai langsung; foto dan satu frame video dibaca melalui OCR.
3. **Cari kandidat sumber.** Kalimat unik dari seluruh teks menjadi dasar kueri, bukan hanya 35 kata pertama. Maksimal 12 bagian pencarian dipilih merata dari awal sampai akhir (dua kueri per bagian); cakupan yang dibatasi dilaporkan di hasil.
4. **Nilai relevansi.** Transformer membandingkan metadata pencarian dengan setiap kalimat. Sumber yang relevan terhadap kalimat di bagian akhir tetap dapat terpilih. Pemilihan mengutamakan cakupan kalimat yang belum diwakili website lain. Pola nomor urut yang eksplisit juga dapat dikenali secara terstruktur.
5. **Siapkan kandidat dan cadangan.** Kandidat diurutkan sebelum crawling. Hingga sepuluh hostname unik yang lolos ambang relevansi dapat dicoba untuk memperoleh maksimal lima sumber terbaca; `www` dan alamat tanpa `www` dihitung sebagai website yang sama.
6. **Baca artikel dan ganti sumber yang gagal.** Crawler mengambil halaman yang diizinkan dan mengekstrak teks utama serta tabel. Jika sumber gagal dibaca, kandidat berikutnya dicoba sampai target tercapai, kandidat habis, atau batas sepuluh website tercapai. Ringkasan pencarian hanya dipakai untuk seleksi, bukan bukti akhir.
7. **Bandingkan bukti per kalimat.** NLI menilai hubungan makna antara sumber dan kalimat input. Untuk pola nomor urut jabatan yang dikenali, angka diambil dari kutipan lalu dibandingkan langsung. Pemeriksaan struktur dan NLI membantu beberapa kalimat dengan pasangan orang–jabatan atau sisipan keterangan.
8. **Tinjau hasil.** Pengguna melihat persentase, kutipan, tautan sumber, dan catatan keterbatasan.

Teks multikalimat dianalisis per kalimat unik, dengan hasil dan sumber setiap kalimat ditampilkan terpisah. Pengulangan kalimat identik tidak menambah bobot. Kalimat di luar grammar parser tetap diproses oleh NLI, termasuk susunan nomor urut yang tidak dikenali; hasil tersebut adalah skor semantik, bukan pemeriksaan angka eksak. Nama tokoh dalam tes regresi hanya contoh, bukan syarat atau basis fakta sistem.

Pemisahan kalimat belum merupakan ekstraksi klaim atomik atau penyelesaian kata ganti. Maksimal lima sumber terbaca mungkin belum mencakup semua topik dalam dokumen. Semua kalimat unik tetap dibandingkan dengan sumber yang diperoleh; teks panjang menambah waktu inferensi. Rata-rata dokumen mencampurkan skor hubungan semantik dan, bila relevan, proporsi bukti angka; gunakan rincian per kalimat untuk interpretasi.

Kegagalan pencarian dibedakan dari hasil kosong, kegagalan penyaringan, dan kegagalan membaca artikel. Popup menampilkan rincian timeout, pembatasan layanan, sertifikat, atau koneksi. API menyertakan `search.status` dan `search.attempts`; status gagal tidak dianggap sebagai bukti yang membantah klaim.

### Pemulihan pembacaan sumber

Target lima sumber berlaku untuk artikel yang berhasil dibaca, bukan hanya tautan yang dipilih. Misalnya, bila dua kandidat awal gagal dibaca, aplikasi dapat melanjutkan ke kandidat keenam dan ketujuh yang sudah lolos seleksi. Ambang relevansi tetap berlaku; kandidat yang tidak relevan tidak dipakai hanya untuk memenuhi jumlah. Artikel yang terbaca juga belum tentu memuat bukti yang cukup untuk menilai klaim.

- **Batas percobaan:** hingga sepuluh hostname unik per scan, dengan normalisasi `www`. Kegagalan sementara dapat dicoba ulang hingga dua percobaan per kandidat. Batas website bukan jumlah permintaan HTTP, karena pemeriksaan `robots.txt`, redirect, dan percobaan ulang juga memerlukan permintaan.
- **Redirect terbatas:** perubahan alamat pada hostname yang sama, perpindahan `www` ↔ tanpa `www`, dan peningkatan HTTP ke HTTPS dapat diikuti. Alamat tujuan tetap melewati pemeriksaan DNS, sertifikat TLS untuk HTTPS, dan aturan `robots.txt`. Redirect ke domain lain dan penurunan HTTPS ke HTTP ditolak.
- **Batas akses tetap dihormati:** HTTP 403, pembatasan `robots.txt`, halaman berlogin, dan tantangan anti-bot tidak dilewati. Pembaca belum menjalankan JavaScript seperti browser; kandidat lain dicoba bila isi artikel tidak dapat diekstrak.
- **Jejak pembacaan:** API menyertakan `selection.reading` dengan `attempted_hosts`, `read_hosts`, `target`, `max_attempts`, dan `limit_reached`, serta `read_status` dan `read_errors` pada kandidat. Data ini membedakan sumber yang sudah dicoba, berhasil dibaca, atau gagal.

Penggantian hanya memakai kandidat dari pencarian yang sudah berjalan; belum ada fallback eksplisit tingkat aplikasi ke mesin pencari tambahan. Jika pencarian gagal, semua kandidat tidak dapat dibaca, atau tidak ada kandidat cadangan yang lolos relevansi, hasil tetap dapat berupa “belum cukup bukti”.

### Scan berulang dan pembatasan layanan pencarian

Aplikasi **tidak membatasi total scan menjadi empat atau jumlah tertentu**. Satu scan dapat menghasilkan beberapa kueri; layanan pencarian atau website tujuan tetap dapat membatasi permintaan. Kegagalan setelah beberapa scan belum otomatis membuktikan rate limit: periksa catatan timeout, koneksi, atau pembatasan layanan.

- Hasil pencarian yang berhasil disimpan dalam **cache memori selama 5 menit**, maksimal 128 kueri per proses. Kueri sama tidak perlu dikirim ulang selama cache berlaku. Hasil kosong/gagal tidak disimpan.
- Permintaan kueri baru diberi jeda minimal **2 detik** setelah permintaan sebelumnya selesai. Ini mengurangi lonjakan permintaan, bukan jaminan lolos pembatasan layanan.
- Setelah tanda HTTP 429/rate limit/CAPTCHA, kueri baru dijeda **60 detik**. Jika pembatasan berulang setelah mencoba lagi, jedanya meningkat menjadi 120, 240, hingga maksimal 300 detik. Aplikasi tidak mencoba melewati CAPTCHA.
- Setelah tiga kegagalan koneksi/timeout berturut-turut, permintaan baru dijeda **15 detik**. Scan berikutnya dapat mencoba lagi setelah jeda berakhir; tidak ada retry pencarian tanpa batas.
- Kueri yang masih memiliki cache boleh dipakai selama jeda. **Artikel tetap dibaca ulang** melalui crawler dan aturan retry/penggantian sumber; cache ini bukan penyimpanan putusan kebenaran.

Hasil menampilkan jumlah kueri cache dan perkiraan waktu tunggu melalui `search.cached_queries` serta `search.retry_after_seconds`. Waktu tunggu adalah kebijakan lokal, bukan janji kapan layanan luar pulih. Cache dan jeda berlaku pada proses aplikasi/server yang sedang berjalan, tidak dibagi antarbeberapa jendela proses terpisah, dan hilang ketika proses ditutup. Jumlah scan tidak dibatasi aplikasi, tetapi akses jaringan **bukan unlimited yang dijamin**.

### Memahami persentase

**Klaim umum — Persentase hubungan bukti.** Angka merupakan skor model atas hubungan teks sumber dengan klaim. Skor belum dikalibrasi sebagai probabilitas benar atau hoaks.

**Nomor urut — Kesepakatan bukti nomor urut.** Tampilan memisahkan kesepakatan bukti dari cakupan sumber setelah deduplikasi. Dua sumber mendukung, nol membantah, dan dua belum cukup menghasilkan kesepakatan mendukung 100% (2 dari 2 sumber dengan bukti tegas), dengan cakupan 2 dari 4 sumber. Sumber belum cukup/ambigu tetap ditampilkan tetapi tidak menjadi pembagi kesepakatan. Jika semua sumber belum cukup, persentase kesepakatan tidak ditampilkan. Ini bukan kepastian kebenaran; memperoleh lima sumber terbaca tidak otomatis menghasilkan dukungan 100%. Field API `scores` tetap memuat distribusi seluruh sumber untuk audit; `consensus` memuat kesepakatan dan cakupan yang ditampilkan.

Pemeriksaan angka tidak menyimpan daftar fakta tokoh beserta nomor jabatannya. Angka pembanding harus ditemukan dalam sumber. Tanggal, nomor acara, atau angka milik orang dan jabatan lain tidak otomatis dihitung sebagai bukti urutan jabatan.

Untuk kalimat pelantikan dengan pasangan orang-jabatan atau sisipan keterangan, jalur tambahan memeriksa struktur pasangan lalu memakai NLI untuk hubungan orang-jabatan (ambang dukungan 0,90 dan bantahan maksimal 0,05; belum dikalibrasi). Angka berasal dari pasangan jabatan-nomor yang diekstrak, bukan tebakan NLI. Kutipan asli dan skor pemeriksaan dicatat pada `comparisons[].semantic_checks`. Kalimat pertemuan, negasi, pasangan ambigu, dan angka yang saling bertentangan tidak otomatis dianggap mendukung. Ini perluasan terbatas, bukan jaminan memahami semua susunan berita. Uji model nyata: `python tests/semantic_smoke.py` (model harus sudah tersimpan lokal).

## Teknologi

| Komponen | Teknologi |
| --- | --- |
| Bahasa | Python dan JavaScript |
| API lokal | FastAPI, Uvicorn |
| Konfigurasi lokal | python-dotenv, environment variable |
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

Dependensi disusun bertingkat: `requirements.txt` berisi API, crawler, pencarian, dan pembaca `.env`; `requirements-ai.txt` menambahkan PyTorch serta Transformers; `requirements-desktop.txt` menambahkan Qt dan OCR. Gunakan paket desktop untuk mengikuti seluruh panduan ini. Memasang `requirements.txt` saja belum cukup untuk menjalankan inferensi AI dan OCR.

Model NLI dan OCR dimuat saat dibutuhkan. Pada penggunaan pertama, pastikan koneksi tersedia dan beri waktu untuk unduhan model. Alur bawaan tidak memerlukan API key berbayar.

### 4. Siapkan konfigurasi `.env`

Aplikasi otomatis membaca `.env` di direktori utama proyek saat dijalankan melalui desktop, API, atau skrip scan. Untuk checkout baru, salin contoh jika `.env` belum tersedia:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Konfigurasi yang dapat digunakan:

```dotenv
MODEL_ID=MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
HF_TOKEN=
# HF_HOME=D:/model-cache/huggingface
```

| Variabel | Wajib? | Nilai bawaan / perilaku | Lokasi penggunaan |
| --- | --- | --- | --- |
| `MODEL_ID` | Tidak | Model multilingual MiniLM di atas; nilai kosong memakai model bawaan. | Kedua jalur pemuatan Transformer melalui `app/config.py`. |
| `HF_TOKEN` | Tidak | Kosong; model publik bawaan tidak membutuhkan token. | Diteruskan ke pemuatan model di backend bila diisi. |
| `HF_HOME` | Tidak | Cache standar library bila tidak diatur. | Dibaca library Hugging Face setelah `.env` dimuat; gunakan path absolut bila diubah. |

Urutan pemuatan: Python mengimpor paket `app` → `app/__init__.py` membaca `.env` di akar proyek → `app/config.py` membaca pengaturan model/token → model dimuat saat inferensi pertama. Lokasi `.env` ditentukan dari lokasi paket, sehingga tidak bergantung pada direktori terminal saat aplikasi dipanggil. File UTF-8 dengan atau tanpa BOM dapat dibaca.

`MODEL_ID` memilih model NLI; model pengganti harus menyediakan label `contradiction`, `entailment`, dan `neutral`. `HF_HOME` bersifat opsional untuk menentukan lokasi cache Hugging Face, dengan path absolut. Mengubah lokasi cache dapat memerlukan unduhan model kembali.

Environment variable yang sudah ditetapkan pada proses lebih diutamakan daripada isi `.env`. Jika `.env` tidak tersedia, aplikasi tetap memakai konfigurasi bawaan. Mulai ulang aplikasi/server setelah mengubah konfigurasi. File `.env` diabaikan Git; `.env.example` disertakan sebagai contoh konfigurasi. Alur bawaan tetap tidak membutuhkan API key berbayar.

`HF_TOKEN` hanya diperlukan bila mengakses model privat atau gated yang memerlukan izin. Isi token asli di `.env` lokal, bukan di `.env.example`, JavaScript, atau manifest ekstensi. Konfigurasi model dipusatkan di `app/config.py`; kedua jalur pemuatan model menggunakan token tersebut secara eksplisit. Jika kosong, aplikasi tidak menggunakan token login tersimpan secara otomatis. Lihat [dokumentasi environment variable Hugging Face](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables) untuk pengaturan token dan cache.

`.env` adalah file teks biasa, bukan penyimpanan terenkripsi. `.gitignore` mengecualikan file environment, kredensial, private key, cache model pada folder yang disebutkan, dan file sementara Office. Simpan cache tambahan di luar repositori atau folder `model-cache/`. Aturan ignore tidak menghapus file yang sudah masuk Git maupun riwayat commit; jika kredensial pernah terpublikasi, cabut/ganti kredensial tersebut. Nama model publik, alamat loopback, dan batas keamanan crawler tetap boleh berada dalam kode karena bukan rahasia. API tetap untuk penggunaan lokal; `.env` tidak menambahkan autentikasi API.

Untuk instalasi yang sudah ada, jalankan ulang perintah instalasi dependensi pada langkah 3 agar `python-dotenv` terpasang. Konfigurasi alamat API ekstensi tetap `127.0.0.1:8000` seperti pada launcher.

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

Untuk langsung membuka satu file dan menjalankan scan melalui antarmuka desktop:

```powershell
.\.venv\Scripts\python.exe .\scan-local-file.py --file "D:\dokumen\contoh.txt"
.\.venv\Scripts\python.exe .\scan-local-file.py --file "D:\video\contoh.mp4" --seconds 12.5
```

Ganti path contoh dengan file yang tersedia. Perintah ini membuka antarmuka Qt, bukan menghasilkan JSON di terminal. Untuk video, `--seconds` harus tidak negatif; jika dihilangkan, aplikasi memakai posisi awal. Untuk integrasi tanpa antarmuka desktop, gunakan API lokal.

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

Untuk menghentikan server, tekan `Ctrl+C` pada terminal tempat server berjalan. Menutup popup ekstensi tidak menghentikan pekerjaan scan yang sudah dimulai. Setelah mengubah `.env` atau kode Python, hentikan dan jalankan ulang server; launcher tidak mengaktifkan reload otomatis.

### Menu File Explorer — opsional

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-local-menu.ps1
```

Skrip menambahkan menu **Scan dengan CekFakta** pada registry akun Windows saat ini untuk format yang didukung. Pada Windows 11, menu dapat berada di **Show more options**. Pasang ulang jika folder proyek dipindahkan karena registrasi menunjuk ke lokasi proyek. Video dari menu Explorer memakai frame awal.

### Membaca hasil scan

1. **Periksa teks input.** Pastikan teks pilihan, OCR, atau caption memuat klaim yang dimaksud, terutama nama, angka, dan kata penyangkalan.
2. **Periksa status pencarian.** Bedakan pencarian berhasil, sebagian berhasil, kosong, dan gagal. Status ini menjelaskan ketersediaan kandidat, bukan kebenaran klaim.
3. **Periksa sumber terbaca.** Kandidat pencarian belum tentu berhasil dibuka. Lihat jumlah artikel terbaca dan alasan kandidat gagal.
4. **Baca hasil per kalimat.** Dukungan terhadap satu kalimat tidak berlaku otomatis untuk seluruh dokumen. Tinjau kutipan dan buka artikel untuk memeriksa konteks.
5. **Baca jenis persentasenya.** Skor NLI menggambarkan hubungan teks; kesepakatan nomor urut menghitung sumber dengan bukti angka tegas. Keduanya memiliki dasar penghitungan berbeda.

Jika `analysis` tidak tersedia, antarmuka dapat tetap menampilkan sumber atau pesan kegagalan. Jika analisis tersedia tetapi hubungan bukti netral/ambigu, artinya sumber sudah dibandingkan namun belum memberikan dukungan atau bantahan yang cukup jelas.

## API lokal

Server bawaan mendengarkan di `http://127.0.0.1:8000`. Dokumentasi interaktif tersedia di `http://127.0.0.1:8000/docs` dan skema di `/openapi.json`. Endpoint belum memakai autentikasi; jalankan untuk akses lokal dan jangan membuka server ke jaringan publik.

| Metode dan endpoint | Kegunaan | Bentuk hasil |
| --- | --- | --- |
| `GET /api/health` | Memeriksa respons server dan konfigurasi nama model. | `status`, `model`, `model_loading`. Tidak menjalankan atau menguji inferensi model. |
| `POST /api/scan/jobs` | Memulai pemeriksaan bukti di background. | Objek berisi `id` pekerjaan. |
| `GET /api/scan/jobs/{id}` | Mengambil perkembangan/hasil pekerjaan. | `status: running`, atau `status: done` dengan `result`. |
| `POST /api/scan` | Pemeriksaan bukti sinkron; permintaan menunggu scan selesai. | Objek hasil scan langsung. |
| `POST /api/analyze` | Klasifikasi awal dari teks atau URL; dipakai halaman web awal. | `articles` dan `errors`; bukan alur pencarian bukti utama. |

### Contoh permintaan dari PowerShell

Jalankan server terlebih dahulu. Pemeriksaan health tidak mengunduh model:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health'
```

Mulai pekerjaan scan teks, lalu ambil statusnya. Ganti kalimat contoh dengan klaim yang ingin diperiksa; permintaan scan dapat mengakses internet dan memuat model:

```powershell
$payload = @{
    kind = 'text'
    text = 'Masukkan satu klaim yang ingin diperiksa.'
} | ConvertTo-Json

$scanJob = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:8000/api/scan/jobs' `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))

$scanStatus = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/scan/jobs/$($scanJob.id)"
$scanStatus | ConvertTo-Json -Depth 20
```

Jika status masih `running`, jalankan ulang bagian pengambilan status setelah beberapa detik; jangan membuat pekerjaan baru untuk sekadar mengecek hasil. API menerima satu pekerjaan analisis aktif per proses; permintaan analisis lain mendapat HTTP 429 selama pekerjaan tersebut berjalan. Ini berbeda dari pembatasan layanan pencarian luar.

Pekerjaan disimpan dalam memori, sehingga ID hilang ketika server dimulai ulang. Saat pekerjaan baru dibuat, entri yang sudah selesai dan berumur lebih dari 300 detik sejak dibuat dibersihkan. Ini bukan penyimpanan riwayat permanen atau jaminan masa simpan lima menit sejak selesai.

### Field input dan hasil

`/api/scan` dan `/api/scan/jobs` menerima JSON dengan `kind` bernilai `text`, `image`, atau `video`. Field `text` berisi klaim atau teks pendamping; `frame` berisi data URL gambar untuk OCR. API tidak menerima path file lokal atau file video mentah. Field opsional `media_note` dibatasi 500 karakter dan `linked_terms` maksimal 20 item.

| Field hasil scan | Cara membacanya |
| --- | --- |
| `text` | Teks yang masuk ke pencarian dan analisis, termasuk OCR jika ada. |
| `verification_status` | `evidence_compared` jika hasil analisis tersedia; `not_assessed` jika belum dapat dibandingkan. |
| `search` | Status pencarian, percobaan kueri, pemakaian cache, dan waktu tunggu. |
| `search_coverage` | Jumlah bagian pencarian yang tersedia/dipilih dan penanda cakupan terbatas. |
| `selection` | Kandidat, relevansi, hasil seleksi, serta catatan pembacaan website. |
| `sources` | Artikel yang terbaca: URL, judul, kutipan tampilan, dan teks hasil ekstraksi. |
| `analysis` | Skor dan perbandingan bukti, atau `null` jika tidak tersedia. Untuk beberapa kalimat, lihat `analysis.statements`. |
| `analysis_error` | Alasan analisis belum tersedia. |
| `terms` | Definisi kamus atau kutipan definisi dari sumber. |
| `errors`, `limitation`, `reason` | Catatan kegagalan, keterbatasan input, dan ringkasan proses. |

Skor pada JSON menggunakan skala 0–1; antarmuka mengubahnya menjadi persentase. Respons HTTP berhasil berarti permintaan diproses, bukan berarti sumber ditemukan atau klaim didukung. Periksa field status dan hasil analisis.

## Penanganan masalah

| Gejala | Pemeriksaan dan tindakan |
| --- | --- |
| `No module named dotenv`, `torch`, atau `PySide6` | Jalankan ulang instalasi `requirements-desktop.txt` menggunakan `.venv\Scripts\python.exe`; pastikan launcher memakai environment proyek. |
| Model belum siap / pemuatan pertama lama | Periksa koneksi, ruang cache, `MODEL_ID`, dan izin model jika memakai token. Nama model pengganti harus menyediakan label NLI yang didukung. Health yang berhasil belum membuktikan model siap. |
| Perubahan `.env` tidak berpengaruh | Pastikan file bernama `.env`, bukan `.env.txt`, berada di akar proyek; restart aplikasi. Environment variable proses lebih diprioritaskan. |
| Ekstensi gagal menghubungi server | Jalankan `start-desktop.cmd`, lalu periksa `/api/health`. Reload ekstensi dan halaman setelah perubahan JavaScript. |
| Port 8000 sudah dipakai | Periksa apakah server proyek sudah berjalan. Gunakan proses tersebut atau hentikan proses yang memang Anda jalankan sebelum memulai lagi. Mengubah port launcher saja membuat alamat ekstensi tidak cocok. |
| HTTP 429 dari API lokal: scan lain berjalan | Tunggu pekerjaan aktif selesai. Jangan berulang kali menekan Scan. |
| Pencarian timeout / rate limit / CAPTCHA | Baca `search.attempts` dan `retry_after_seconds`, lalu tunggu sesuai catatan. Tidak ada jaminan layanan luar pulih setelah jeda lokal berakhir. |
| Kandidat ada, tetapi artikel tidak terbaca | Baca catatan crawler; situs dapat diblokir, membutuhkan login/JavaScript, atau menolak crawler. Sistem mencoba kandidat cadangan yang relevan dalam batasnya. |
| OCR kosong atau keliru | Gunakan gambar dengan tulisan lebih jelas atau salin teks yang benar ke clipboard; foto tidak dianalisis untuk keaslian visual. |
| Frame video gagal dibaca | Pastikan format/codec dapat dibuka dan waktu frame berada dalam durasi video; coba posisi lain. |
| Hasil semua “belum cukup/ambigu” | Buka kutipan dan sumber; pastikan bukti membahas subjek, konteks, dan angka yang sama. Tidak ada sumber tegas berarti tidak ada dasar untuk memaksakan dukungan/bantahan. |
| Menu Explorer tidak muncul / path lama | Pada Windows 11, periksa **Show more options**. Jalankan ulang pemasangan menu setelah memindahkan folder proyek. |

Saat melaporkan masalah, sertakan mode penggunaan, jenis input, langkah reproduksi, dan pesan status yang sudah diperiksa agar tidak memuat data pribadi. Jangan menyertakan `.env` atau token asli. Untuk masalah model, pesan API sengaja tidak meneruskan detail exception internal tertentu.

## Kekurangan dan kasus kegagalan

Bagian ini mencatat batas implementasi dan temuan selama pengembangan, bukan hanya kemungkinan teoretis.

| Area | Kekurangan saat ini | Dampak pada hasil |
| --- | --- | --- |
| Pencarian web | Timeout layanan pencarian telah teramati dalam uji langsung. Aplikasi memakai DDGS; fallback eksplisit tingkat aplikasi ke backend alternatif belum diterapkan. | Klaim yang mudah diverifikasi manusia tetap bisa mendapat nol kandidat. Pesan diagnostik membantu menjelaskan kegagalan, tetapi tidak memulihkan akses. |
| Pemilihan sumber | Relevansi ditaksir dari judul/ringkasan dengan ambang eksperimen yang belum dikalibrasi. | Artikel relevan bisa tersisih, sedangkan artikel bertopik sama belum tentu menjawab klaim. |
| Cakupan sumber | Target maksimal lima sumber terbaca dengan hingga sepuluh hostname kandidat relevan. Sumber gagal baca diganti selama masih ada cadangan yang lolos; `www` dan alamat tanpa `www` dihitung bersama. | Hasil tetap bisa kurang dari lima artikel jika kandidat habis atau batas percobaan tercapai. Banyak topik dalam satu dokumen belum tentu mendapat bukti masing-masing. |
| Pembacaan artikel | Crawler menghormati `robots.txt`. Redirect pada hostname yang sama dan pasangan `www`/tanpa `www` didukung dengan validasi ulang; redirect domain lain atau HTTPS ke HTTP ditolak. Halaman berlogin, bergantung JavaScript, berpaginasi, diblokir HTTP 403, atau melebihi batas HTML 8 MB tidak selalu terbaca. | Penggantian kandidat membantu melanjutkan scan, tetapi tidak membuat website yang diblokir menjadi terbaca. “Seluruh teks diproses” berarti seluruh hasil ekstraksi, bukan seluruh isi visual website. |
| Pemahaman semantik | Uji langsung menemukan NLI bisa memberi skor tinggi pada angka yang salah dan menganggap “X bertemu presiden” mendukung “X adalah presiden”. Pengaman ditambahkan untuk pola yang diuji. | Skor tinggi saja tidak menjamin hubungan fakta benar. Kesalahan di luar kasus regresi masih mungkin terjadi. |
| Ekstraksi nomor urut | Mendukung pola tertentu untuk presiden, wakil presiden, dan perdana menteri; bukan ekstraktor fakta numerik umum. | Variasi penulisan nama, alias, struktur berita, atau lingkup jabatan yang belum dikenali masih dapat menghasilkan “belum cukup/ambigu”. |
| Teks panjang | Kalimat dipisahkan dan deduplikasi dilakukan, tetapi kata ganti dan klaim majemuk belum diselesaikan secara umum. Pencarian dibatasi 12 bagian; inferensi bertambah seiring jumlah kalimat dan artikel. | Konteks lintas kalimat dapat hilang, cakupan pencarian tidak menyeluruh, dan scan bisa lambat pada CPU. Input teks dibatasi 30.000 karakter. |
| Kualitas sumber | Deduplikasi berdasarkan hostname dan teks identik belum membuktikan independensi atau kredibilitas sumber. | Beberapa website dapat menyalin informasi salah yang sama; kesepakatan 100% bukan kebenaran 100%. |
| OCR | Angka, nama, dan kata penyangkalan dapat salah terbaca; kualitas OCR belum dibenchmark pada dataset representatif. | Kesalahan ekstraksi bisa mengubah klaim sebelum pencarian dimulai. |
| Evaluasi | Belum ada benchmark pemeriksaan fakta Indonesia yang representatif, kalibrasi skor, atau benchmark latensi/RAM lintas perangkat. | Belum dapat mengklaim persentase akurasi umum, keunggulan atas model lain, atau kesiapan produksi. |

**Kasus yang masih terbuka:** pernah muncul hasil tiga sumber terbaca tetapi semuanya “belum cukup/ambigu” untuk klaim sederhana. Sebagian penyebab pada pola kalimat sudah diperbaiki dan diuji dengan contoh terkontrol. Tiga artikel persis dari hasil tersebut belum diuji ulang, sehingga kasus dunia nyata itu belum dinyatakan selesai.

### Pelajaran dari pengembangan

Memperjelas persentase tidak memperbaiki ekstraksi bukti. Karena itu, aplikasi memisahkan status pencarian, cakupan sumber, kesepakatan bukti, dan skor model. Pemeriksaan angka juga tidak diserahkan sepenuhnya kepada NLI: hubungan bahasa diperiksa bersama struktur kalimat, sedangkan nilai angka tetap diambil dari kutipan. Pendekatan ini mengurangi beberapa kesalahan yang ditemukan, tetapi menambah ketergantungan pada pola bahasa yang didukung.

## Kemampuan yang belum tersedia

- **Putusan benar/hoaks yang terjamin untuk semua topik**, termasuk pemeriksaan otomatis kualitas, kebaruan, dan independensi sumber.
- **Pemahaman bahasa Indonesia secara menyeluruh**, termasuk semua parafrasa, alias, kata ganti, negasi kompleks, dan hubungan antarbagian dokumen.
- **Bi-LSTM atau model hasil pelatihan sendiri.** Saat ini memakai Transformer NLI pralatih; belum tersedia dataset berlabel dan checkpoint Bi-LSTM untuk proyek ini. Penambahan arsitektur belum dapat diklaim meningkatkan akurasi tanpa evaluasi pembanding.
- **Deteksi manipulasi foto, keaslian gambar, dan deepfake.** Foto dipakai sebagai input OCR, bukan analisis keaslian visual.
- **Transkripsi audio dan analisis video penuh.** Video lokal hanya diambil satu frame pada waktu yang dipilih; audio dan rangkaian adegan belum dianalisis.
- **Input langsung PDF, DOCX, dan file audio.** Teks PDF/DOCX perlu disalin ke input teks terlebih dahulu.
- **Pemeriksaan bukti sepenuhnya offline.** Inferensi berjalan lokal, tetapi pencarian dan pengambilan artikel tetap memerlukan internet.
- **Pembacaan semua website seperti browser.** Belum ada rendering JavaScript, autentikasi situs, atau pengambilan otomatis semua halaman artikel berpaginasi. Sumber yang membatasi akses tetap dapat gagal dibaca.
- **Kesetaraan fitur semua antarmuka.** Halaman web awal masih memakai klasifikasi kategori teks; alur pemeriksaan bukti utama tersedia melalui desktop dan ekstensi.

## Rencana pengembangan

Daftar berikut adalah arah pengembangan, **belum fitur yang tersedia atau janji jadwal rilis**. Prioritas awal adalah mengukur dan memperbaiki alur teks sebelum memperluas analisis media.

| Prioritas | Rencana | Ukuran keberhasilan yang akan dinilai |
| --- | --- | --- |
| 1 | Susun dataset evaluasi Indonesia lintas topik dengan parafrasa, angka, negasi, dan kasus tanpa bukti. | Precision/recall/F1, kesalahan per kategori, dan kemampuan menahan penilaian ketika bukti tidak cukup. |
| 2 | Evaluasi pemulihan sumber yang sudah diterapkan pada berbagai website; perkuat pencarian dan uji kueri alternatif ketika kandidat tidak memadai. | Tingkat keberhasilan pencarian dan pembacaan, relevansi artikel, cakupan bukti per klaim, serta waktu tambahan untuk kandidat cadangan. |
| 3 | Tingkatkan ekstraksi hubungan entitas, angka, dan konteks lintas kalimat; bandingkan pendekatan model pada data uji terpisah. | Penurunan salah dukung/salah bantah pada kasus yang belum pernah dipakai untuk pengembangan. |
| 4 | Kalibrasi skor, perjelas kutipan dasar penilaian, dan ukur kinerja teks panjang. | Kesesuaian skor dengan hasil evaluasi, keterlacakan alasan, latensi, serta penggunaan RAM. |
| 5 | Tingkatkan praproses OCR dan sediakan koreksi teks sebelum pencarian. | Kesalahan karakter/kata, terutama nama, angka, dan penyangkalan. |
| 6 | Tambahkan transkripsi audio bertimestamp dan OCR beberapa frame video. | Kualitas transkrip dan kemampuan menelusuri klaim ke segmen audio/frame asal. |

## Privasi dan aliran data

- Scan dimulai melalui tindakan pengguna. Alur utama tidak memantau layar, clipboard, kamera, atau mikrofon secara otomatis.
- Ekstensi mengirim input yang dipilih ke server lokal `127.0.0.1:8000`.
- Inferensi NLI dan OCR berlangsung lokal. Potongan teks klaim dikirim ke layanan pencarian, sehingga alur ini **tidak sepenuhnya offline**.
- Crawler mengakses website publik yang terpilih. Piksel media diproses dalam memori oleh alur scan; file asli tidak diubah.
- Model dapat diunduh dan disimpan dalam cache lokal pada penggunaan pertama.

| Tujuan data | Data yang digunakan | Kapan terjadi |
| --- | --- | --- |
| Proses desktop atau API di komputer pengguna | Input pilihan, piksel frame untuk OCR, artikel hasil ekstraksi, dan hasil analisis. | Selama scan dan penampilan hasil; pekerjaan API disimpan sementara di memori. |
| Layanan pencarian melalui DDGS | Kueri yang disusun dari potongan teks input. | Saat kueri belum tersedia di cache dan pencarian tidak sedang dijeda. |
| Website sumber | Permintaan halaman dan pemeriksaan akses seperti `robots.txt`. | Saat crawler membaca kandidat. |
| Layanan penyedia model | Permintaan berkas/metadata model; token bila dikonfigurasi untuk pemuatan model. | Saat library perlu mengakses model; bobot tersimpan dalam cache lokal. |

Konfigurasi `.env` tidak dikirim sebagai objek konfigurasi ke frontend. Token model hanya dipakai pada jalur pemuatan model; nama model tetap ditampilkan oleh health API dan sebagian hasil. Input yang mengandung informasi pribadi dapat ikut menjadi kueri pencarian, sehingga pilih hanya teks yang sesuai untuk dikirim ke layanan luar.

## Struktur proyek

```text
app/
  __init__.py          Pemuatan .env sebelum modul aplikasi
  config.py            Konfigurasi model dan token backend
  main.py              API dan pengelolaan pekerjaan scan
  context_scan.py      Orkestrasi pemeriksaan utama
  relevance.py         Seleksi kandidat sebelum crawling
  crawler.py           Pengambilan dan ekstraksi artikel
  evidence.py          Perbandingan bukti dan agregasi hasil
  ordinal_facts.py     Pemeriksaan nomor urut jabatan
  text_units.py        Pemisahan kalimat dan cakupan kueri teks panjang
  search_status.py     Diagnosis status dan kegagalan pencarian
  search_session.py    Cache kueri, pengaturan jeda, dan masa tunggu pencarian
  classifier.py        Model dan klasifikasi teks awal
  local_scan.py        Persiapan file teks, foto, dan video
  local_desktop.py     Antarmuka desktop
extension/             Ekstensi browser dan popup hasil
tests/                 Pengujian unit dan smoke test
requirements*.txt      Dependensi bertingkat
start-local.cmd        Launcher desktop lokal
start-desktop.cmd      Launcher server untuk ekstensi
install-local-menu.ps1 Integrasi menu File Explorer
.env                  Konfigurasi lokal, diabaikan Git
.env.example          Contoh konfigurasi tanpa token asli
.gitignore            Pengecualian file lokal, kredensial, dan artefak
```

## Pengujian

Jalankan dari direktori utama proyek setelah instalasi dependensi:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
node --test tests/extension.test.cjs
.\.venv\Scripts\python.exe -c "import runpy; runpy.run_path('tests/local_desktop_smoke.py')"
```

Tes mencakup input, pembatasan sumber, seleksi sebelum crawling, teks panjang, nomor urut, serta perilaku antarmuka. Tes pemulihan sumber memeriksa penggantian kandidat gagal, penghentian pada target atau batas percobaan, retry terbatas, serta validasi DNS/TLS/robots pada redirect. Sebagian tes menggunakan mock untuk model dan jaringan agar deterministik. Kelulusan tes regresi tidak setara dengan akurasi pemeriksaan fakta pada data dunia nyata.

Untuk uji kecil menggunakan model asli yang sudah tersimpan dalam cache lokal:

```powershell
.\.venv\Scripts\python.exe tests/semantic_smoke.py
```

Skrip ini memakai mode offline untuk pemuatan model. Jalankan alur aplikasi dengan internet terlebih dahulu bila model belum terunduh. Uji ini tidak mengakses mesin pencari atau artikel langsung.

### Catatan validasi — 20 September 2026

| Pemeriksaan | Hasil pada 20 September 2026 | Yang belum dibuktikan |
| --- | --- | --- |
| Unit/regresi Python | 77 tes lolos. | Akurasi model pada artikel dunia nyata; banyak tes memakai mock. |
| Model nyata lokal | 10 kasus terkontrol lolos: 4 pasangan NLI umum dan 6 kasus nomor urut/pengaman hubungan. | Generalisasi lintas topik dan bentuk kalimat; 10 kasus bukan benchmark akurasi. |
| Antarmuka desktop | Smoke test lolos untuk render hasil, escaping teks, dan tampilan per kalimat/kesepakatan. | Pengujian kegunaan atau kompatibilitas lintas perangkat. |
| Pencarian langsung | Timeout berhasil direproduksi; diagnosis kegagalan ditambahkan. | Pemulihan koneksi atau keberhasilan pencarian yang konsisten. |

Tabel ini adalah catatan historis pada 20 September 2026, sebelum perubahan pemulihan sumber dan redirect berikutnya. Jumlah tes bukan badge akurasi. Perintah pengujian di atas dapat dijalankan ulang untuk memeriksa keadaan checkout yang digunakan.

### Validasi pemulihan sumber — 21 September 2026

- **97 tes Python lolos**, termasuk 11 tes redirect crawler dan 9 tes pemulihan sumber/retry. Penggantian kandidat diuji pada batas jaringan yang dimock, termasuk skenario sumber awal diblokir, cadangan berhasil, kandidat habis, dan batas sepuluh website tercapai.
- **Tes ekstensi JavaScript dan smoke test desktop lolos**; pemeriksaan sintaks popup juga lolos.
- **Akses nyata berhasil:** halaman [dokumentasi Python tentang robots.txt](https://docs.python.org/3/library/urllib.robotparser.html) menghasilkan 2.186 karakter teks hasil ekstraksi tanpa error pada saat pengujian.
- **Redirect nyata berhasil, ekstraksi belum berhasil:** `https://python.org/about/` diarahkan ke `https://www.python.org/about/` dengan HTTP 200, tetapi tidak menghasilkan teks artikel yang cukup. Aplikasi tetap mencatatnya sebagai gagal baca, bukan bukti.

Uji jaringan dilakukan terpisah dari pencarian/model dan hasilnya dapat berubah mengikuti respons website. Hasil ini tidak membuktikan seluruh alur pencarian sampai pemeriksaan fakta selalu berhasil, ataupun menyelesaikan kasus tiga artikel ambigu yang dicatat di atas.

Pembaruan scan berulang pada tanggal yang sama menambah 7 tes untuk cache, kedaluwarsa, pacing, pemulihan setelah jeda, batas memori, dan pelaporan kueri yang ditunda. **104 tes Python lolos** setelah perubahan ini. Pengujian pembatasan memakai waktu dan layanan palsu yang terkendali; belum membuktikan DDGS selalu berhasil setelah banyak scan nyata.

## Referensi metode

- [Model multilingual MiniLM untuk NLI](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli)
- [Evaluating Numeracy of Language Models as a Natural Language Inference Task](https://aclanthology.org/2025.findings-naacl.467/)
- [TabVer: Tabular Fact Verification with Natural Logic](https://aclanthology.org/2024.tacl-1.89/)

Implementasi CekFakta menggabungkan NLI lokal dengan parser konservatif. Proyek ini bukan reproduksi TabVer atau sistem yang telah tervalidasi untuk seluruh jenis klaim.
