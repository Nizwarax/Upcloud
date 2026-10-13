#!/bin/bash
# install.sh - UPCLOUD STORE BOT - AUTO DOWNLOAD FROM GITHUB REPO
# Link repo: https://github.com/Nizwarax/Upcloud

BOT_URL="https://raw.githubusercontent.com/Nizwarax/Upcloud/main/bot_upcloud.py"
QRIS_URL="https://raw.githubusercontent.com/Nizwarax/Upcloud/main/qris.png"

echo -e "\033[1;33mInstalling UPCLOUD STORE Bot...\033[0m"
echo -e "Downloading bot from: $BOT_URL"
echo -e "QRIS from: $QRIS_URL"

PYTHON_EXEC="/usr/bin/python3"

if ! command -v $PYTHON_EXEC &> /dev/null; then
    echo "Installing Python3..."
    apt-get update
    apt-get install -y python3 python3-pip curl wget
fi

if ! $PYTHON_EXEC -m pip --version &> /dev/null; then
     apt-get install -y python3-pip
fi

echo "Installing python-telegram-bot, python-dotenv..."
if ! $PYTHON_EXEC -m pip install python-telegram-bot python-dotenv --break-system-packages 2>/dev/null; then
    $PYTHON_EXEC -m pip install python-telegram-bot python-dotenv
fi

mkdir -p /etc/upcloud
mkdir -p /usr/local/bin

echo "Downloading bot.py to /usr/local/bin/upcloud_bot.py..."
if command -v curl &> /dev/null; then
    curl -sSL "$BOT_URL" -o /usr/local/bin/upcloud_bot.py
else
    wget -qO /usr/local/bin/upcloud_bot.py "$BOT_URL"
fi

if [ ! -s /usr/local/bin/upcloud_bot.py ]; then
    echo -e "\033[1;31m❌ Gagal download bot dari $BOT_URL\033[0m"
    echo "Cek file lokal..."
    if [ -f "bot_upcloud.py" ]; then 
        cp bot_upcloud.py /usr/local/bin/upcloud_bot.py
        echo "✅ pakai file lokal bot_upcloud.py"
    elif [ -f "bot.py" ]; then 
        cp bot.py /usr/local/bin/upcloud_bot.py
    elif [ -f "/root/bot_upcloud.py" ]; then
        cp /root/bot_upcloud.py /usr/local/bin/upcloud_bot.py
    else 
        echo "❌ File bot tidak ada! Upload manual ke /usr/local/bin/upcloud_bot.py"; 
        exit 1; 
    fi
fi

chmod +x /usr/local/bin/upcloud_bot.py
ln -sf /usr/local/bin/upcloud_bot.py /usr/local/bin/upc.py 2>/dev/null || true
ln -sf /usr/local/bin/upcloud_bot.py /usr/local/bin/upc 2>/dev/null || true
echo -e "\033[1;32m✅ Bot downloaded & executable alias (upc / upc.py) created!\033[0m"

# === AUTO DOWNLOAD QRIS DARI GITHUB ===
echo "Downloading QRIS image..."
if command -v curl &> /dev/null; then
    curl -sSL "$QRIS_URL" -o /etc/upcloud/qris.png
    curl -sSL "$QRIS_URL" -o /etc/upcloud/qris.jpg
else
    wget -qO /etc/upcloud/qris.png "$QRIS_URL"
    wget -qO /etc/upcloud/qris.jpg "$QRIS_URL"
fi

if [ -s /etc/upcloud/qris.png ] || [ -s /etc/upcloud/qris.jpg ]; then
    echo -e "\033[1;32m✅ qris image downloaded dari GitHub!\033[0m"
else
    echo -e "\033[1;31m❌ Gagal download QRIS dari $QRIS_URL\033[0m"
    if [ -f "qris.png" ]; then
        cp qris.png /etc/upcloud/qris.png
        cp qris.png /etc/upcloud/qris.jpg
        echo "✅ qris.png copied dari lokal"
    elif [ -f "qris.jpg" ]; then
        cp qris.jpg /etc/upcloud/qris.png
        cp qris.jpg /etc/upcloud/qris.jpg
        echo "✅ qris.jpg copied dari lokal"
    else
        echo -e "\033[1;33m⚠️ Foto QRIS belum ada. Anda bisa set via menu admin di bot atau upload ke /etc/upcloud/qris.png\033[0m"
    fi
fi

# === Buat stok.txt kalau belum ada ===
if [ ! -f "/etc/upcloud/stok.txt" ]; then
    echo "Membuat /etc/upcloud/stok.txt..."
    cat > /etc/upcloud/stok.txt <<EOF
ucat_01M4PVA1M32KRFB7MX9RXGCMVT
ucat_01M4PVA1M32KRFB7MX9RXGCMVU
ucat_01M4PVA1M32KRFB7MX9RXGCMVV
EOF
    echo "✅ stok.txt contoh dibuat, edit: nano /etc/upcloud/stok.txt"
fi

# === Buat file data kosong kalau belum ada ===
[ -f /etc/upcloud/resellers.json ] || echo "{}" > /etc/upcloud/resellers.json
[ -f /etc/upcloud/all_members.json ] || echo "[]" > /etc/upcloud/all_members.json
[ -f /etc/upcloud/settings.json ] || echo '{"account_price":15000,"reseller_price":10000}' > /etc/upcloud/settings.json
[ -f /etc/upcloud/income_log.json ] || echo "[]" > /etc/upcloud/income_log.json
[ -f /etc/upcloud/sold_log.json ] || echo "[]" > /etc/upcloud/sold_log.json
[ -f /etc/upcloud/admins.json ] || echo "[]" > /etc/upcloud/admins.json
[ -f /etc/upcloud/transaction_counter.txt ] || echo "1" > /etc/upcloud/transaction_counter.txt

if [ ! -f "/etc/upcloud/bot_config.sh" ]; then
    echo -e "\033[1;33mBuat config /etc/upcloud/bot_config.sh\033[0m"
    read -p "Masukkan BOT TOKEN (dari @BotFather): " BOT_TOKEN
    read -p "Masukkan ADMIN CHAT_ID (bisa multi, pisah koma contoh 123,456): " CHAT_ID
    read -p "Masukkan CHANNEL_ID untuk log penjualan (opsional, kosongkan jika tidak ada): " CHANNEL_ID
    echo "BOT_TOKEN=\"$BOT_TOKEN\"" > /etc/upcloud/bot_config.sh
    echo "CHAT_ID=\"$CHAT_ID\"" >> /etc/upcloud/bot_config.sh
    if [ ! -z "$CHANNEL_ID" ]; then
        echo "CHANNEL_ID=\"$CHANNEL_ID\"" >> /etc/upcloud/bot_config.sh
    fi
    echo "Config saved ke /etc/upcloud/bot_config.sh"
else
    echo "Config sudah ada: /etc/upcloud/bot_config.sh"
    cat /etc/upcloud/bot_config.sh
fi

echo "Creating systemd service..."
cat > /etc/systemd/system/upcloud-bot.service <<EOF
[Unit]
Description=UPCLOUD STORE Telegram Bot
After=network.target

[Service]
ExecStart=$PYTHON_EXEC /usr/local/bin/upcloud_bot.py
Restart=always
RestartSec=10
User=root
WorkingDirectory=/etc/upcloud
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable upcloud-bot.service
systemctl restart upcloud-bot.service

echo "Checking service status..."
sleep 3

if systemctl is-active --quiet upcloud-bot.service; then
    echo -e "\033[1;32m✅ UPCLOUD Bot Service is RUNNING!\033[0m"
else
    echo -e "\033[1;31m❌ UPCLOUD Bot Service FAILED to start! Cek log:\033[0m"
    journalctl -u upcloud-bot --no-pager -n 50
fi

echo "--- Service Logs (last 20 lines) ---"
journalctl -u upcloud-bot --no-pager -n 20
echo "------------------------------------"

echo -e "\033[1;32mINSTALL SELESAI! Direct from GitHub (Nizwarax/Upcloud)\033[0m"
echo ""
echo -e "\033[1;33m=== PENTING ===\033[0m"
echo "📁 Folder data: /etc/upcloud/"
echo "📦 Stok: /etc/upcloud/stok.txt (edit: nano /etc/upcloud/stok.txt)"
echo "🔑 Bot: /usr/local/bin/upcloud_bot.py"
echo "🖼️ QRIS: /etc/upcloud/qris.png"
echo "⚙️ Config: /etc/upcloud/bot_config.sh"
echo "💾 Saldo: /etc/upcloud/resellers.json"
echo "📝 Log jual: /etc/upcloud/sold_log.json"
echo ""
echo -e "\033[1;33mPerintah Service:\033[0m"
echo "systemctl status upcloud-bot - cek status"
echo "systemctl restart upcloud-bot - restart bot"
echo "journalctl -u upcloud-bot -f - lihat log live"
