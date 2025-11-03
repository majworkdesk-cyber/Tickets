Made by: Michael Angelo Jordan
NIM: 535220246

Buku Manual: Modul Tickets & Analisis Klastering Pelanggan
Instalasi & Setup Lingkungan Odoo 16
Bagian ini merinci langkah-langkah teknis untuk mempersiapkan lingkungan pengembangan di Ubuntu, yang diperlukan sebelum menginstal modul tickets.
1.1. Persiapan Sistem Operasi & Virtualisasi
1.	Instal Oracle VirtualBox di komputer host.
2.	Buat Virtual Machine (VM) baru dan instal Ubuntu Desktop (misal: 22.04 LTS).
1.2. Instalasi Perangkat Lunak Pendukung
Setelah Ubuntu terinstal di VM, instal aplikasi berikut:
1.	Visual Studio Code (VSCode): Unduh file .deb dan instal.
2.	Google Chrome: Unduh file .deb dan instal.
3.	Ekstensi VSCode: Buka VSCode dan instal ekstensi Python, Pylance, dan Odoo Snippets.
1.3. Konfigurasi User Ubuntu (Fix Sudoers)
Jika Anda menemui error "user not found in sudoers" saat menggunakan sudo:
1.	Buka Terminal.
2.	Ketik su root dan masukkan password root.
3.	Ketik usermod -aG sudo <username> (ganti <username> dengan nama user Anda).
4.	Restart Ubuntu VM.
1.4. Instalasi PostgreSQL
Odoo membutuhkan database PostgreSQL.
1.	Buka Terminal: sudo apt update
2.	Instal PostgreSQL: sudo apt install postgresql
3.	Buat user database Odoo (misal: odoo_ptel):
Bash
sudo -u postgres createuser --createdb --username=odoo_ptel --no-password
1.5. Instalasi Odoo 16
1.	Buka Terminal, pindah ke Documents: cd ~/Documents
2.	Instal git dan python3-venv: sudo apt install git python3-venv
3.	Clone repositori Odoo 16:
Bash
git clone https://www.github.com/odoo/odoo --depth 1 --branch 16.0
4.	Buat Python Virtual Environment (venv):
Bash
python3 -m venv venv_odoo
5.	Aktifkan venv: source venv_odoo/bin/activate
6.	Upgrade pip: pip install --upgrade pip wheel
7.	Pindah ke direktori Odoo: cd odoo
8.	Instal semua dependensi Python: pip install -r requirements.txt
9.	Setelah selesai, nonaktifkan venv: deactivate
1.6. Konfigurasi & Menjalankan Server Odoo
1.	Pindah ke ~/Documents.
2.	Buat file odoo.conf: nano odoo.conf
3.	Isi file odoo.conf dengan konfigurasi Anda. PENTING: Sesuaikan addons_path agar menyertakan folder Odoo dan folder modul kustom Anda (ticketing).
[options]
admin_passwd = superadmin
db_host = False
db_port = False
db_user = odoot_ptel
db_password = False 
Ganti /home/maj/Documents/odoo/odoo/addons dan /home/maj/Documents/ticketing
dengan path yang benar di mesin Anda
addons_path = /home/maj/Documents/odoo/odoo/addons, /home/maj/Documents/ticketing
4.	Menjalankan Server:
1.	cd ~/Documents
2.	source venv_odoo/bin/activate
3.	cd odoo
4.	python odoo-bin -c /home/maj/Documents/odoo.conf
5.	Buka Chrome dan akses http://localhost:8069.
1.7. Instalasi Modul tickets
1.	Instal Library Python: Modul tickets memerlukan library eksternal. Aktifkan venv Anda (source venv_odoo/bin/activate) dan jalankan:
Bash
pip install scikit-learn numpy matplotlib
2.	Restart Server: Hentikan server Odoo (Ctrl+C) dan jalankan lagi (langkah 1.6.4).
3.	Update App List:
1.	Buka Odoo di browser (http://localhost:8069) dan login sebagai Admin.
2.	Aktifkan Developer Mode (Settings -> Activate the developer mode).
3.	Pergi ke menu Apps.
4.	Klik Update Apps List.
4.	Instal Modul:
1.	Cari tickets di search bar (hapus filter "Apps").
2.	Klik tombol Install.
1.8. Troubleshooting Instalasi
1.	Instalasi Paket .deb:
1.	cd ~/Downloads
2.	sudo dpkg -i nama_paket.deb
3.	Jika error: sudo apt-get install -f (memperbaiki dependensi).
2.	Port 8069 Terpakai:
1.	Cek port: sudo lsof -i :8069
2.	Matikan proses (PID): sudo kill <PID>
3.	Alternatif: Ubah port di odoo.conf (misal: xmlrpc_port = 8070).
3.	Edit File (Terminal): nano /path/to/file
 
Panduan Penggunaan Modul Tickets
Bagian ini menjelaskan alur kerja dan fungsionalitas modul Tickets yang sudah terinstal.
2.1. Peran Pengguna (User Roles)
Modul ini memiliki 4 peran utama dengan hak akses yang berbeda:
1.	Customer (Pelanggan)
1.	Grup: Customer (Read Own Tickets)
2.	Hak Akses: Hanya bisa melihat dan membuat tiket milik mereka sendiri (di mana customer_name_id = partner mereka). Tidak bisa mengedit tiket setelah dibuat (kecuali membatalkan).
3.	Tugas: Membuat tiket, memberi rating.
2.	Sales (Penjualan)
1.	Grup: Sales (Ticket Own Only)
2.	Hak Akses: Hanya bisa melihat/mengedit tiket di mana mereka terdaftar sebagai sales_person_id.
3.	Tugas: Membuat tiket untuk pelanggan, menugaskan Teknisi, memindahkan status tiket dari "Submit" ke "Progress", mengkalkulasi poin.
3.	Technician (Teknisi)
1.	Grup: Technician (Ticket Assigned Only)
2.	Hak Akses: Hanya bisa melihat/mengedit tiket di mana mereka terdaftar sebagai technician (berdasarkan user.partner_id mereka).
3.	Tugas: Mengerjakan tiket, mengisi tech_note, memindahkan status tiket dari "Progress" ke "Finish".
4.	Admin (Administrator)
1.	Grup: Admin (Ticket Full Access + Analysis)
2.	Hak Akses: Akses penuh ke semua tiket dan satu-satunya yang bisa mengakses semua menu analisis.
3.	Tugas: Mengelola semua tiket, menjalankan analisis, mengonfigurasi modul.
2.2. Alur Kerja Operasional (Manajemen Tiket)
1.	Pembuatan Tiket (Sales / Customer)
1.	Buka Tickets -> Menu Ticket -> Ticket dan klik New.
2.	Jika login sebagai Customer: Field "Customer" (customer_name_id) akan otomatis terisi dengan nama Anda dan tidak bisa diubah (readonly).
3.	Jika login sebagai Sales/Admin: Pilih Customer (customer_name_id). Field sales_person_id akan terisi otomatis.
4.	Isi Kategori dan Problem Definition.
5.	Assign Teknisi: (Hanya Sales/Admin) Pilih partner teknisi di field Technician (technician).
6.	Simpan. Tiket dibuat dalam status "Submit".
2.	Proses Tiket (Sales & Teknisi)
1.	Sales: Membuka tiket "Submit". Setelah diverifikasi, Sales mengklik tombol "Progress". Status tiket berubah ke "Progress" dan progress_date tercatat.
2.	Teknisi: Teknisi akan melihat tiket yang di-assign padanya (yang berstatus "Progress"). Setelah masalah selesai, Teknisi mengisi tech_note dan mengklik tombol "Finish". Status berubah ke "Finish" dan finish_date tercatat.

3.	Kalkulasi Poin & Rating (Sales / Customer)
1.	Sales/Admin: Setelah tiket "Finish", klik tombol "Calculate Cost" untuk mengurangi poin pelanggan (point_value).
2.	Customer: Memberikan Customer Rating (Worst, Bad, Good, Excellent).
2.3. Alur Kerja Analisis (Hanya Admin)
Ini adalah proses inti untuk menganalisis data yang sudah terkumpul.
Langkah 1: Persiapan Data (Wajib) Data mentah tiket diubah menjadi data rata-rata pelanggan.
1.	avg.ticket (Otomatis): Terupdate otomatis saat tiket diubah.
2.	eda.std (Manual):
1.	Buka Tickets -> [Menu EDA Anda] -> Global STD History.
2.	Klik RECALCULATE STD untuk menghitung ulang standar deviasi global dari semua data tiket.
3.	normalization.name (Manual/Terjadwal):
1.	WAJIB: Sebelum menjalankan K-Means, data Z-Score harus diperbarui.
2.	Jalankan recompute_all() pada model normalization.name melalui Odoo Shell, atau pastikan Scheduled Action sudah diatur untuk berjalan otomatis setiap hari.
Langkah 2: Analisis Korelasi (EDA)
1.	Buka Tickets -> [Menu EDA Anda] -> Correlation Analysis.
2.	Lihat Heatmap untuk memahami hubungan antar fitur (misal: Ticket Count vs Point AVG).
Langkah 3: Menentukan Klaster Optimal (k)
1.	Buka Tickets Intelligent K-Means.
2.	Klik New untuk membuat Run analisis baru.
3.	Buka tab Find Optimal K (Analysis).
4.	Atur Min k (misal: 2) dan Max k (misal: 10).
5.	Klik tombol STEP 1: FIND OPTIMAL K.
6.	Analisis Hasil:
1.	Elbow Method Graph: Cari "siku" (titik di mana grafik melandai). 
2.	Silhouette Results: Cari skor tertinggi. misal: 0.2900).
3.	Kesimpulan: Pilih k terbaik.
Langkah 4: Menjalankan Klastering Final
1.	Pindah ke tab Final Clustering (Run).
2.	Masukkan k pilihan Anda di field Chosen k (misal: 3).
3.	Klik tombol STEP 2: RUN FINAL CLUSTERING.
4.	Sistem akan menjalankan K-Means dan menyimpan hasilnya ke kmeans.result.
Langkah 5: Menganalisis Hasil Klastering
1.	Ringkasan (di Form K-Means):
1.	Lihat skor Final Silhouette Score dan Final Davies-Bouldin Index.
2.	Lihat tabel Final Centroids (Z-Scores) untuk memahami "profil" rata-rata tiap klaster.
2.	Detail Anggota (di Cluster Results):
1.	Klik tombol pintar "Results" di form K-Means, atau buka menu Cluster Results.
2.	Lihat daftar semua pelanggan, dikelompokkan berdasarkan Cluster (misal: Cluster 1: 39, Cluster 2: 114, dst.).
3.	Buka grup untuk melihat anggota dan nilai Z-Score individual mereka.
3.	Visualisasi (Scatter Plot):
1.	Di form Intelligent K-Means, klik tombol View Scatter Plot.
2.	Layar baru akan muncul. Gunakan dropdown X-Axis dan Y-Axis di kanan atas untuk memilih dua fitur Z-Score yang ingin Anda bandingkan.
3.	Hover: Arahkan mouse ke titik untuk melihat Nama Customer dan nilai Z-Score-nya.
4.	Klik: Klik pada sebuah titik untuk membuka daftar (Tree View) yang sudah difilter, berisi semua anggota klaster dari titik yang Anda klik tersebut.
5.	Gunakan tombol Back untuk kembali ke form K-Means.
2.4. Troubleshooting
1.	Error Library (ImportError, NameError): Pastikan library Python (scikit-learn, numpy, matplotlib) terinstal & Odoo di-restart.
2.	Tombol JS Tidak Berfungsi (Scatter Plot/Heatmap): Lakukan Hard Refresh (Ctrl+Shift+R) pada browser Anda.
3.	Error "Missing Run ID" (Scatter Plot): Pastikan record K-Means Run sudah disimpan sebelum mengklik tombol "View Scatter Plot". Periksa Developer Console (F12) untuk console.log.
4.	Data Analisis Tidak Berubah: Pastikan Anda telah menjalankan ulang proses yang relevan (misal: "RECALCULATE STD" atau recompute_all() untuk normalization.name) setelah data tiket baru ditambahkan.
5.	Technician/Sales Tidak Bisa Lihat Tiket (Tampilan Kosong): Ini PASTI karena Record Rule. Masalahnya ada di DATA. Pastikan ID partner yang terhubung ke User (di Settings Users) adalah ID partner YANG SAMA PERSIS dengan yang dipilih di field technician atau sales_person_id pada tiket.
6.	Access Error saat Mengedit Tiket: Ini juga karena Record Rule. Anda (sebagai Teknisi/Sales) mencoba mengedit tiket yang tidak di-assign ke Anda.
7.	Data Klastering Aneh (misal: 1 data di 1 klaster): Ini wajar. K-Means telah mengidentifikasi data tersebut sebagai outlier (pencilan) yang sangat berbeda dari data lainnya.

