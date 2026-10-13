# 🚀 UPCLOUD STORE TELEGRAM BOT

Bot Telegram Auto Store untuk penjualan akun UpCloud (format `ucat_...`) secara otomatis, responsif, dan kaya fitur.

---

## ✨ Fitur Utama

- 💎 **Sistem Stok Otomatis**: Pembelian akun otomatis memotong stok dan langsung mengirimkan format `ucat_...` ke pembeli.
- 🖼️ **Tampilan Topup QRIS**: Otomatis menampilkan gambar QRIS saat member/reseller melakukan Topup Saldo.
- 👑 **Multi Admin & Management**: Tambah/hapus multi admin, reseller, isi saldo member/reseller, dan atur harga khusus member & reseller.
- 🖼️ **Update QRIS Langsung**: Admin bisa mengubah/mengunggah foto QRIS baru langsung melalui menu admin di Bot Telegram.
- 📦 **Manajemen Stok Fleksibel**:
  - Tambah stok via paste teks / kirim file `.txt`.
  - Hapus duplikat stok otomatis.
  - Cek stok, preview 20 stok teratas, dan backup stok file `.txt`.
- 📊 **Laporan & Log**:
  - Laporan pendapatan (Harian, Mingguan, Bulanan, Total) dilengkapi grafik ASCII.
  - Log transaksi otomatis terkirim ke Channel Telegram (opsional).
  - Riwayat 10 transaksi terakhir pengguna.
- 📢 **Broadcast**: Kirim pesan massal (Teks/Gambar) ke seluruh pengguna terdaftar.
- 💾 **Full Backup**: Backup seluruh database JSON, stok, dan gambar QRIS dalam bentuk zip.

---

## ⚡ Perintah Install Otomatis (1-Line Command)

Jalankan perintah berikut di VPS/Server Ubuntu/Debian kamu (sebagai `root`):

```bash
sysctl -w net.ipv6.conf.all.disable_ipv6=1 2>/dev/null; sysctl -w net.ipv6.conf.default.disable_ipv6=1 2>/dev/null; apt-get update && apt-get install -y curl wget python3 python3-pip && curl -sSL https://raw.githubusercontent.com/Nizwarax/Upcloud/main/install.sh | bash
```

---

## 🛠️ Panduan Instalasi Manual / Dari Repository

1. **Clone Repository & Jalankan Installer**:
   ```bash
   git clone https://github.com/Nizwarax/Upcloud.git /root/Upcloud
   cd /root/Upcloud
   chmod +x install.sh
   ./install.sh
   ```

2. **Isi Informasi Bot**:
   Saat installer berjalan, kamu akan diminta mengisi:
   - **BOT_TOKEN**: Token bot Telegram dari [@BotFather](https://t.me/BotFather).
   - **CHAT_ID**: Telegram ID kamu (bisa lebih dari 1 ID, dipisahkan koma: `1234567,8901234`).
   - **CHANNEL_ID**: Username/ID Channel log transaksi (Opsional, tekan Enter jika tidak ada).

---

## ⚙️ Perintah Pengelolaan Service (Systemd)

- **Cek Status Bot**:
  ```bash
  systemctl status upcloud-bot
  ```

- **Restart Bot**:
  ```bash
  systemctl restart upcloud-bot
  ```

- **Melihat Log Live**:
  ```bash
  journalctl -u upcloud-bot -f
  ```

- **Menghentikan Bot**:
  ```bash
  systemctl stop upcloud-bot
  ```

---

## 📁 Lokasi File Data & Config (`/etc/upcloud/`)

| Path | Deskripsi |
| :--- | :--- |
| `/usr/local/bin/upcloud_bot.py` / `upc.py` / `upc` | Script utama Bot Telegram |
| `/etc/upcloud/bot_config.sh` | Configuration token & chat ID |
| `/etc/upcloud/stok.txt` | File stok akun UpCloud (`ucat_...`) |
| `/etc/upcloud/qris.png` | Gambar QRIS Topup |
| `/etc/upcloud/resellers.json` | Database saldo & status member/reseller |
| `/etc/upcloud/admins.json` | Database daftar multi admin |
| `/etc/upcloud/sold_log.json` | Log riwayat akun terjual |
| `/etc/upcloud/income_log.json` | Log pendapatan & transaksi |

---

## 📜 Lisensi & Repository

- **Repository**: [https://github.com/Nizwarax/Upcloud](https://github.com/Nizwarax/Upcloud)
