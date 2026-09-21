# CekFakta — Information Detection

**Prototipe asisten pemeriksaan klaim berbasis bukti dengan transformer, ekstraksi artikel, dan OCR.**

CekFakta membantu pengguna menemukan sumber yang berkaitan dengan sebuah klaim, membaca artikelnya, dan meninjau hubungan antara klaim dengan bukti. Proyek ini menyediakan aplikasi desktop Windows serta ekstensi browser untuk memulai pemeriksaan dari teks atau media yang dipilih pengguna.

> **Status: prototipe aktif.** Proyek ini dikembangkan untuk eksplorasi teknis dan portofolio. Hasilnya belum merupakan putusan kebenaran, belum memiliki pengukuran akurasi pada dataset representatif, dan belum ditujukan untuk penggunaan produksi yang membutuhkan jaminan ketepatan.

**Yang ditunjukkan proyek ini:** integrasi model NLP dengan pencarian web, ekstraksi artikel, OCR, API lokal, aplikasi desktop, dan ekstensi browser dalam satu alur pemeriksaan yang bisa ditelusuri ke sumber.

**Keterbatasan utama:** pencarian dapat gagal, sumber relevan dapat terlewat, dan kalimat yang benar secara fakta masih bisa menghasilkan “belum cukup bukti” karena bukti gagal dibaca atau hubungan antarentitas belum dikenali. Proyek ini mengintegrasikan model pralatih; belum melatih model pemeriksaan fakta sendiri.

[Fitur](#fitur-saat-ini) · [Instalasi](#instalasi) · [Keterbatasan](#kekurangan-dan-kasus-kegagalan) · [Belum tersedia](#kemampuan-yang-belum-tersedia) · [Pengujian](#pengujian)

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

## Struktur proyek

```text
app/
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
