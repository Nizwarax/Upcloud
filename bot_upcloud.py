import logging
import json
import os
import subprocess
import time
import asyncio
import datetime
import random
import string
import re
import sys
import html
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode 
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.error import InvalidToken

# --- Global Configuration & Paths ---
DIR_PATH = "/etc/upcloud"
try:
    os.makedirs(DIR_PATH, exist_ok=True)
    with open(os.path.join(DIR_PATH, ".test"), "w") as f:
        f.write("test")
    os.remove(os.path.join(DIR_PATH, ".test"))
except:
    DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upcloud_data")
    os.makedirs(DIR_PATH, exist_ok=True)

STOCK_FILE = f"{DIR_PATH}/stok.txt"
RESELLER_DB = f"{DIR_PATH}/resellers.json"
MEMBER_DB = f"{DIR_PATH}/all_members.json"
SETTINGS_DB = f"{DIR_PATH}/settings.json"
INCOME_DB = f"{DIR_PATH}/income_log.json"
TRX_COUNTER_FILE = f"{DIR_PATH}/transaction_counter.txt"
BOT_CONFIG = f"{DIR_PATH}/bot_config.sh"
SOLD_DB = f"{DIR_PATH}/sold_log.json"
ADMIN_DB = f"{DIR_PATH}/admins.json"

# --- Helper to locate QRIS image ---
def get_qris_image_path():
    possible_paths = [
        os.path.join(DIR_PATH, "qris.png"),
        os.path.join(DIR_PATH, "qris.jpg"),
        os.path.join(DIR_PATH, "qris.jpeg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "qris.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "qris.jpg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "qris.jpeg"),
        "/etc/upcloud/qris.png",
        "/etc/upcloud/qris.jpg",
        "/etc/upcloud/qris.jpeg",
        "qris.png",
        "qris.jpg",
        "qris.jpeg"
    ]
    for path in possible_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None

# --- Backup Script ---
BACKUP_SCRIPT_PATH = "/usr/local/bin/upcloud-autobackup.sh"

# --- Global Variable for Uptime ---
BOT_START_TIME = time.time()

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
(
    SELECTING_ACTION,
    ADD_STOCK_INPUT,
    ADD_BALANCE_ID, ADD_BALANCE_AMOUNT,
    SET_PRICE_INPUT,
    SET_RESELLER_PRICE_INPUT,
    ADD_RESELLER,
    DEL_RESELLER,
    BROADCAST_MSG,
    BUY_CONFIRM,
    SET_QRIS_INPUT,
    ADD_ADMIN_INPUT,
    SET_ADMIN_CONTACT_INPUT,
) = range(13)

# --- Helper Functions ---

def get_config_value(key):
    if not os.path.exists(BOT_CONFIG): 
        if key == "BOT_TOKEN":
            return os.getenv("BOT_TOKEN")
        if key == "CHAT_ID":
            return os.getenv("CHAT_ID")
        if key == "CHANNEL_ID":
            return os.getenv("CHANNEL_ID")
        return None
    try:
        with open(BOT_CONFIG, 'r') as f: content = f.read()
        pattern = r'^\s*(?:export\s+)?' + re.escape(key) + r'\s*=\s*(["\']?)(.*?)\1\s*$'
        match = re.search(pattern, content, re.MULTILINE)
        if match: return match.group(2).strip()
    except: pass
    return os.getenv(key)

def load_json(filepath, default=None):
    if default is None:
        default = {} if "resellers" in filepath or "settings" in filepath else []
    if not os.path.exists(filepath): return default
    try:
        with open(filepath, 'r') as f: 
            return json.load(f)
    except: return default

def save_json(filepath, data):
    with open(filepath, 'w') as f: json.dump(data, f, indent=4)

# --- LOGIKA DATABASE & ROLE ---

def load_resellers_data():
    if not os.path.exists(RESELLER_DB): return {}
    try:
        with open(RESELLER_DB, 'r') as f: data = json.load(f)
        if isinstance(data, list): 
            new_data = {}
            for r_id in data:
                new_data[str(r_id)] = {"balance": 0, "role": "member"}
            save_json(RESELLER_DB, new_data)
            return new_data
        return data
    except: return {}

def save_resellers_data(data): save_json(RESELLER_DB, data)

def get_reseller_balance(user_id):
    data = load_resellers_data()
    return data.get(str(user_id), {}).get("balance", 0)

def update_reseller_balance(user_id, amount):
    data = load_resellers_data()
    str_id = str(user_id)
    if str_id not in data:
        data[str_id] = {"balance": 0, "role": "member"}
    current = data[str_id].get("balance", 0)
    data[str_id]["balance"] = current + amount
    save_resellers_data(data)
    return data[str_id]["balance"]

def check_is_reseller(user_id):
    data = load_resellers_data()
    user_data = data.get(str(user_id), {})
    return user_data.get("role") == "reseller"

def load_admins():
    admins = set()
    chat_id_raw = get_config_value("CHAT_ID") or ""
    if chat_id_raw:
        for cid in chat_id_raw.split(","):
            cid = cid.strip()
            if cid.isdigit():
                admins.add(cid)
    if os.path.exists(ADMIN_DB):
        try:
            with open(ADMIN_DB, 'r') as f:
                data = json.load(f)
                for a in data:
                    admins.add(str(a))
        except: pass
    resellers = load_resellers_data()
    for uid, info in resellers.items():
        if isinstance(info, dict) and info.get("role") == "admin":
            admins.add(str(uid))
    return admins

def save_admins(admin_list):
    save_json(ADMIN_DB, list(admin_list))

def is_admin(user_id):
    return str(user_id) in load_admins()

def check_is_admin_role(user_id):
    return is_admin(user_id)

def register_member(user_id):
    if not os.path.exists(MEMBER_DB): save_json(MEMBER_DB, [])
    members = load_json(MEMBER_DB, [])
    if user_id not in members:
        members.append(user_id)
        save_json(MEMBER_DB, members)

# --- HARGA ---
def get_account_price():
    data = load_json(SETTINGS_DB, {})
    if not isinstance(data, dict): return 15000
    return data.get("account_price", 15000)

def get_reseller_price():
    data = load_json(SETTINGS_DB, {})
    if not isinstance(data, dict): return 10000
    return data.get("reseller_price", 10000)

def get_admin_contact():
    data = load_json(SETTINGS_DB, {})
    if isinstance(data, dict) and data.get("admin_contact"):
        return data["admin_contact"]
    contact = get_config_value("ADMIN_CONTACT")
    if contact:
        return contact
    return None

def set_admin_contact(contact):
    data = load_json(SETTINGS_DB, {})
    if not isinstance(data, dict): data = {}
    data["admin_contact"] = contact.strip()
    save_json(SETTINGS_DB, data)

def set_account_price(price):
    data = load_json(SETTINGS_DB, {})
    if not isinstance(data, dict): data = {}
    data["account_price"] = int(price)
    save_json(SETTINGS_DB, data)

# --- STOK UPCLOUD ---
def load_stock():
    if not os.path.exists(STOCK_FILE):
        open(STOCK_FILE, 'w').close()
        return []
    with open(STOCK_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        return [line.strip() for line in f if line.strip()]

def save_stock(stock_list):
    with open(STOCK_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(stock_list))

def get_stock_count():
    return len(load_stock())

def pop_stock():
    stok = load_stock()
    if not stok:
        return None
    akun = stok.pop(0)
    save_stock(stok)
    return akun

def add_stock_baru(list_akun: list):
    stok = load_stock()
    baru = []
    for a in list_akun:
        a = a.strip()
        if not a: continue
        if a in stok: continue
        if a.startswith("ucat_") or len(a) > 10:
            baru.append(a)
    stok.extend(baru)
    save_stock(stok)
    return len(baru)

def remove_duplicate_stock():
    stok = load_stock()
    unique = list(dict.fromkeys(stok))
    removed = len(stok) - len(unique)
    save_stock(unique)
    return removed, len(unique)

# --- WIB TIME ---
def get_now_wib():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)

def get_indo_date():
    now = get_now_wib()
    return f"{now.strftime('%d')}.{now.strftime('%m')}.{now.strftime('%Y')}"

def get_time_wib():
    return get_now_wib().strftime("%H:%M:%S WIB")

def get_uptime_str():
    delta = int(time.time() - BOT_START_TIME)
    days = delta // 86400
    hours = (delta % 86400) // 3600
    minutes = (delta % 3600) // 60
    seconds = delta % 60
    return f"{days}d {hours}h {minutes}m {seconds}s"

def format_rupiah(value):
    try:
        return f"Rp {int(value):,.0f}".replace(",", ".")
    except:
        return str(value)

def get_public_ip():
    try: return subprocess.getoutput("curl -s ifconfig.me")
    except: return "127.0.0.1"

def get_domain():
    return get_public_ip()

def mask_string(text):
    if not text or text == "-": return "-"
    text = str(text).strip()
    if len(text) > 5: return text[:3] + "xxx" + text[-3:]
    elif len(text) > 0: return text[0] + "xxx"
    return "xxx"

# --- TRANSAKSI ---
def get_next_transaction_id():
    current = 1
    if os.path.exists(TRX_COUNTER_FILE):
        try:
            with open(TRX_COUNTER_FILE, 'r') as f:
                current = int(f.read().strip())
        except:
            current = 1
    with open(TRX_COUNTER_FILE, 'w') as f:
        f.write(str(current + 1))
    return current

def record_income(user_id, username, amount, description=""):
    if not os.path.exists(INCOME_DB):
        save_json(INCOME_DB, [])
    logs = load_json(INCOME_DB, [])
    entry = {
        "timestamp": int(time.time()),
        "user_id": str(user_id),
        "username": str(username),
        "amount": int(amount),
        "description": description
    }
    logs.append(entry)
    save_json(INCOME_DB, logs)

def get_income_summary(since_timestamp=0, user_id_filter=None):
    logs = load_json(INCOME_DB, []) if os.path.exists(INCOME_DB) else []
    filtered_logs = [
        log for log in logs
        if log["timestamp"] >= since_timestamp
        and (user_id_filter is None or log["user_id"] == str(user_id_filter))
    ]
    if not filtered_logs:
        return {"total": 0, "count": 0, "avg": 0, "max": 0}
    amounts = [log["amount"] for log in filtered_logs]
    return {
        "total": sum(amounts),
        "count": len(amounts),
        "avg": sum(amounts) // len(amounts),
        "max": max(amounts)
    }

def record_sold(user_id, username, akun, price):
    logs = load_json(SOLD_DB, [])
    logs.append({
        "waktu": get_indo_date() + " " + get_time_wib(),
        "timestamp": int(time.time()),
        "user_id": str(user_id),
        "username": str(username),
        "akun": akun,
        "price": price
    })
    save_json(SOLD_DB, logs)

async def send_log_to_channel(context, user_data, akun, price, role_user, remaining_stock):
    channel_ids_raw = get_config_value("CHANNEL_ID")
    if not channel_ids_raw or channel_ids_raw.strip() == "": return
    chat_ids = [cid.strip() for cid in channel_ids_raw.split(",") if cid.strip()]
    if not chat_ids: return
    trx_id = f"#{get_next_transaction_id()}"
    saldo_keluar = "Gratis" if role_user == "Admin" else format_rupiah(price)
    icon_role = "👑" if role_user == "Admin" else ("🏆" if role_user == "Reseller" else "👤")
    date_now = get_indo_date()
    time_now = get_time_wib()
    msg = (
        "<b>╭────────────────╮</b>\n"
        "   📦 <b>UPCLOUD TERJUAL</b> 📦\n"
        "<b>╰────────────────╯</b>\n\n"
        f"📒 <b>No Trx</b>       : {trx_id}\n"
        f"🌀 <b>Status</b>       : {role_user} {icon_role}\n"
        f"👤 <b>Username</b>     : @{html.escape(user_data['username']) if user_data['username'] else '-'}\n"
        f"🆔 <b>ID</b>           : <code>{user_data['id']}</code>\n\n"
        f"🔑 <b>Akun</b>         : <code>{html.escape(akun)}</code>\n"
        f"💳 <b>Harga</b>        : {saldo_keluar}\n"
        f"📦 <b>Sisa Stok</b>    : {remaining_stock} akun\n\n"
        f"📅 <b>Tanggal</b>      : {date_now}\n"
        f"⏰ <b>Waktu</b>        : {time_now}\n"
        "━━━━━━━━━━━━━━"
    )
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Gagal kirim notifikasi ke {chat_id}: {e}")

# --- MAIN MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, force_new=False):
    register_member(update.effective_user.id)
    user = update.effective_user
    user_id = str(user.id)
    safe_username = f"@{user.username}" if user.username else html.escape(user.first_name)

    saldo = 0
    status_user = "Member"
    if is_admin(user_id):
        status_user = "Admin"
        saldo = "∞ (Unlimited)"
    else:
        balance = get_reseller_balance(user_id)
        if check_is_reseller(user_id): status_user = "Reseller"
        else: status_user = "Member"
        saldo = format_rupiah(balance) if balance > 0 else "Rp 0"

    total_stock = get_stock_count()
    sold_logs = load_json(SOLD_DB, [])
    total_sold = len(sold_logs)
    uptime = get_uptime_str()
    waktu_skr = get_time_wib()
    tanggal_skr = get_indo_date()
    current_price = format_rupiah(get_account_price())
    reseller_price = format_rupiah(get_reseller_price())

    now_wib = get_now_wib()
    today_wib_midnight = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day = (today_wib_midnight - datetime.timedelta(hours=7)).timestamp()
    start_week_wib = (now_wib - datetime.timedelta(days=now_wib.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = (start_week_wib - datetime.timedelta(hours=7)).timestamp()

    stat_daily = 0
    stat_weekly = 0
    for s in sold_logs:
        created_at = s.get('timestamp', 0)
        if created_at >= start_of_day: stat_daily += 1
        if created_at >= start_of_week: stat_weekly += 1

    text = (
        f"📦━━━━━━━━━━━━━━━━━━━📦\n"
        f"      ✨ <b>UPCLOUD STORE</b> ✨\n"
        f"📦━━━━━━━━━━━━━━━━━━━📦\n\n"
        f"selamat datang di UPCloud Auto Store 💎\n"
        f"jual akun upcloud format <code>ucat_...</code> otomatis 🚀\n\n"
        f"🧭 <b>informasi akun</b>\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ 💰 saldo: {saldo}\n"
        f"┃ 👤 status: {status_user}\n"
        f"┃ 🌐 username: {safe_username}\n"
        f"┃ 🆔 id pengguna: <code>{user_id}</code>\n"
        f"┃ ⏱️ bot aktif: {uptime}\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🎯 <b>harga & stok</b>\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ 🏷️ harga member: {current_price} / akun\n"
        f"┃ 🏷️ harga reseller: {reseller_price} / akun\n"
        f"┃ 📦 sisa stok: {total_stock} akun\n"
        f"┃ 🔐 format: ucat_...\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🌍 <b>statistik penjualan</b>\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ 📆 hari ini: {stat_daily} akun\n"
        f"┃ 📅 minggu ini: {stat_weekly} akun\n"
        f"┃ 🗓️ total terjual: {total_sold} akun\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🕒 <b>waktu & server</b>\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ 🧭 waktu: {waktu_skr}\n"
        f"┃ 📅 tanggal: {tanggal_skr}\n"
        f"┃ 🖥️ stok ready: {total_stock}\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📦━━━━━━━━━━━━━━━━━━━📦\n"
        f"     🌐 dikelola oleh Admin\n"
        f"📦━━━━━━━━━━━━━━━━━━━📦"
    )

    buttons = [
        [InlineKeyboardButton(f"🛒 Beli Akun ({total_stock})", callback_data='menu_buy'), InlineKeyboardButton("📦 Cek Stok", callback_data='menu_stock')],
        [InlineKeyboardButton("💳 Topup Saldo", callback_data='menu_topup'), InlineKeyboardButton("📊 Riwayat Beli", callback_data='menu_my_history')],
    ]
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("📦 Kelola Stok", callback_data='menu_stock_manage')])
        buttons.append([InlineKeyboardButton("👥 Manage Resellers & Saldo", callback_data='menu_resellers')])
        buttons.append([InlineKeyboardButton("📢 Broadcast", callback_data='menu_broadcast'), InlineKeyboardButton("💾 Backup Data", callback_data='menu_backup')])
        buttons.append([InlineKeyboardButton("📈 Laporan Pendapatan", callback_data='menu_income')])

    reply_markup = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.answer()
        if force_new:
            try:
                await update.callback_query.delete_message()
            except Exception:
                pass
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            try:
                await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except Exception:
                try:
                    await update.callback_query.delete_message()
                except Exception:
                    pass
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

# --- CEK STOK ---
async def action_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = get_stock_count()
    if count > 0:
        text = f"📦 <b>STOK UPCLOUD READY</b>\n\nSisa stok: <b>{count} akun</b>\nFormat: <code>ucat_...</code>\n\nHarga Member: {format_rupiah(get_account_price())}\nHarga Reseller: {format_rupiah(get_reseller_price())}\n\nKlik Beli untuk mendapatkan akun otomatis."
    else:
        text = f"😥 <b>STOK HABIS</b>\n\nSisa stok: 0 akun\nHubungi admin untuk restok."
    keyboard = [[InlineKeyboardButton("🛒 Beli Sekarang", callback_data='menu_buy'), InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')]]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_ACTION

# --- BELI AKUN ---
async def action_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    
    stock = get_stock_count()
    if stock == 0:
        await query.edit_message_text("❌ <b>Stok Habis!</b>\nTidak bisa membeli saat ini.", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')]]))
        return SELECTING_ACTION

    if is_admin(user_id):
        price = 0
        role = "Admin"
    elif check_is_reseller(user_id):
        price = get_reseller_price()
        role = "Reseller"
    else:
        price = get_account_price()
        role = "Member"

    if not is_admin(user_id):
        balance = get_reseller_balance(user_id)
        if balance < price:
            await query.edit_message_text(
                f"🚫 <b>Saldo Tidak Cukup!</b>\n\nSaldo kamu: <code>{format_rupiah(balance)}</code>\nHarga akun ({role}): <code>{format_rupiah(price)}</code>\nSisa stok: {stock} akun\n\nSilakan Topup dulu.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Topup Saldo", callback_data='menu_topup'), InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')]])
            )
            return SELECTING_ACTION

    akun = pop_stock()
    if not akun:
        await query.edit_message_text("❌ Gagal ambil stok, coba lagi.", parse_mode=ParseMode.HTML)
        return SELECTING_ACTION

    if not is_admin(user_id):
        update_reseller_balance(user_id, -price)
        record_income(user_id, update.effective_user.username or "-", price, f"Beli {akun}")

    record_sold(user_id, update.effective_user.username or "-", akun, price)
    
    remaining = get_stock_count()
    user_data_log = {"id": user_id, "username": update.effective_user.username or "-" }
    await send_log_to_channel(context, user_data_log, akun, price, role, remaining)

    text = (
        f"✅ <b>PEMBELIAN BERHASIL!</b>\n\n"
        f"🔑 Akun UpCloud kamu:\n<code>{html.escape(akun)}</code>\n\n"
        f"💰 Harga: {format_rupiah(price) if price>0 else 'Gratis (Admin)'}\n"
        f"📦 Sisa Stok: {remaining} akun\n"
        f"📅 Tanggal: {get_indo_date()} {get_time_wib()}\n\n"
        f"⚠️ <i>Simpan baik-baik, jangan share!</i>\n"
        f"📝 Format: ucat_...\n\n"
        f"Terima kasih sudah membeli!"
    )
    keyboard = [[InlineKeyboardButton("🛒 Beli Lagi", callback_data='menu_buy'), InlineKeyboardButton("🔙 Menu Utama", callback_data='menu_back_new')]]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📋 Copy akun:\n<code>{html.escape(akun)}</code>", parse_mode=ParseMode.HTML)

    return SELECTING_ACTION

# --- RIWAYAT BELI USER ---
async def action_my_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    logs = load_json(SOLD_DB, [])
    my_logs = [l for l in logs if l["user_id"] == user_id][-10:]
    if not my_logs:
        text = "📊 Belum ada riwayat pembelian."
    else:
        text = f"📊 <b>10 Pembelian Terakhir Kamu:</b>\n\n"
        for l in reversed(my_logs):
            text += f"[{l['waktu']}] - <code>{html.escape(l['akun'])}</code> - {format_rupiah(l['price'])}\n"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')]]))
    return SELECTING_ACTION

# --- TOPUP ---
async def action_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    price_member = format_rupiah(get_account_price())
    price_reseller = format_rupiah(get_reseller_price())
    qris_path = get_qris_image_path()
    admin_contact = get_admin_contact()

    contact_info = f"📩 <b>Kontak Admin:</b> {admin_contact}\n\n" if admin_contact else ""

    text = (
        f"💳 <b>TOPUP SALDO</b>\n\n"
        f"🏷️ <b>Harga akun:</b>\n"
        f"• Member: {price_member} / akun\n"
        f"• Reseller: {price_reseller} / akun\n\n"
        f"📌 <b>Cara Topup:</b>\n"
        f"1. Scan / Transfer via QRIS di atas\n"
        f"2. Kirim bukti transfer ke Admin\n"
        f"3. Admin akan mengisikan saldo kamu\n\n"
        f"🆔 ID Telegram kamu: <code>{update.effective_user.id}</code>\n"
        f"💰 Saldo saat ini: <b>{format_rupiah(get_reseller_balance(update.effective_user.id))}</b>\n\n"
        f"{contact_info}"
        f"💬 Hubungi Admin setelah melakukan pembayaran."
    )

    keyboard = []
    if admin_contact:
        url = admin_contact if admin_contact.startswith("http") else f"https://t.me/{admin_contact.replace('@', '')}"
        keyboard.append([InlineKeyboardButton("📩 Hubungi Admin", url=url)])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')])

    if qris_path and os.path.exists(qris_path):
        try:
            with open(qris_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            try:
                await query.delete_message()
            except Exception:
                pass
            return SELECTING_ACTION
        except Exception as e:
            logger.error(f"Gagal kirim QRIS photo: {e}")

    await query.edit_message_text(
        text + "\n\n⚠️ <i>QRIS belum diset oleh admin. Hubungi admin secara langsung.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_ACTION

# --- KELOLA STOK (ADMIN) ---
async def stock_manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    count = get_stock_count()
    text = (
        f"📦 <b>KELOLA STOK UPCLOUD</b>\n\n"
        f"Sisa stok: <b>{count} akun</b>\n"
        f"File: <code>{STOCK_FILE}</code>\n\n"
        f"Pilih aksi:"
    )
    buttons = [
        [InlineKeyboardButton("➕ Tambah Stok (Paste)", callback_data='stock_add_paste'), InlineKeyboardButton("📎 Upload File .txt", callback_data='stock_add_info')],
        [InlineKeyboardButton("📋 List 20 Stok", callback_data='stock_list'), InlineKeyboardButton(f"📊 Jumlah: {count}", callback_data='stock_count')],
        [InlineKeyboardButton("🧹 Hapus Duplikat", callback_data='stock_dedup'), InlineKeyboardButton("💾 Backup Stok", callback_data='stock_backup')],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data='menu_back')]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECTING_ACTION

async def stock_list_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stok = load_stock()
    if not stok:
        text = "📦 Stok kosong"
    else:
        preview = "\n".join([f"{i+1}. {s}" for i, s in enumerate(stok[:20])])
        text = f"📦 Total {len(stok)} akun. 20 teratas:\n<pre>{html.escape(preview)}</pre>\n...dan {max(0, len(stok)-20)} lainnya"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

async def stock_count_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = get_stock_count()
    await query.edit_message_text(f"📊 Jumlah stok: <b>{count} akun</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

async def stock_dedup_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    removed, total = remove_duplicate_stock()
    await query.edit_message_text(f"🧹 Duplikat dihapus: {removed}\nTotal sekarang: {total}", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

async def stock_backup_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not os.path.exists(STOCK_FILE):
        await query.edit_message_text("❌ stok.txt tidak ada")
        return SELECTING_ACTION
    try:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(STOCK_FILE, 'rb'), filename="stok_backup.txt", caption=f"📦 Backup stok {get_stock_count()} akun - {get_indo_date()}")
        await query.edit_message_text("✅ Backup stok dikirim", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kelola Stok", callback_data='menu_stock_manage')]]), parse_mode=ParseMode.HTML)
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal backup: {e}")
    return SELECTING_ACTION

async def stock_add_paste_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return SELECTING_ACTION
    await query.edit_message_text(
        "📥 <b>Tambah Stok UpCloud</b>\n\nKirim list akun format:\n<code>ucat_01M4PVA1M32KRFB7MX9RXGCMVT</code>\n\nSatu baris satu akun. Bisa paste banyak sekaligus.\n\nKetik /cancel untuk batal.",
        parse_mode=ParseMode.HTML
    )
    return ADD_STOCK_INPUT

async def stock_add_paste_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    list_akun = [line.strip() for line in text.splitlines() if line.strip()]
    if not list_akun:
        await update.message.reply_text("❌ Tidak ada data, coba lagi")
        return ADD_STOCK_INPUT
    added = add_stock_baru(list_akun)
    await update.message.reply_text(f"✅ Berhasil tambah <b>{added}</b> akun baru!\n📦 Total stok sekarang: <b>{get_stock_count()}</b> akun", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

async def stock_add_file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📎 Kirim file .txt berisi list akun ucat_...\nBot akan otomatis menambahkannya.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Hanya admin bisa upload stok")
        return SELECTING_ACTION
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Harus file .txt")
        return SELECTING_ACTION
    file = await doc.get_file()
    temp_path = f"{DIR_PATH}/temp_upload.txt"
    await file.download_to_drive(temp_path)
    with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
        akun_list = [line.strip() for line in f if line.strip()]
    added = add_stock_baru(akun_list)
    try: os.remove(temp_path)
    except: pass
    await update.message.reply_text(f"✅ File diterima!\nBerhasil tambah {added} akun\nTotal stok: {get_stock_count()}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Kelola Stok", callback_data='menu_stock_manage')]]))
    return SELECTING_ACTION

# --- MANAGE RESELLER ---
async def reseller_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    admin_contact = get_admin_contact() or "Belum diset"
    text = (
        "👥 <b>MANAGE RESELLERS & SALDO</b>\n\n"
        f"📩 Kontak Admin Saat Ini: <code>{admin_contact}</code>\n"
        "Kelola member, reseller, saldo, harga akun, QRIS, dan kontak admin."
    )
    buttons = [
        [InlineKeyboardButton("➕ Tambah Reseller", callback_data='reseller_add'), InlineKeyboardButton("➖ Hapus Reseller", callback_data='reseller_del')],
        [InlineKeyboardButton("📋 List Reseller & Saldo", callback_data='reseller_list')],
        [InlineKeyboardButton("💰 Isi Saldo Member", callback_data='reseller_balance_add')],
        [InlineKeyboardButton("🏷️ Set Harga Member", callback_data='reseller_set_price'), InlineKeyboardButton("🏷️ Set Harga Reseller", callback_data='reseller_set_reseller_price')],
        [InlineKeyboardButton("👑 Daftar Admin", callback_data='admin_list'), InlineKeyboardButton("➕ Tambah Admin", callback_data='admin_add')],
        [InlineKeyboardButton("🖼️ Set Foto QRIS", callback_data='menu_set_qris'), InlineKeyboardButton("💬 Set Kontak Admin", callback_data='menu_set_contact')],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data='menu_back')]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECTING_ACTION

async def action_list_resellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    resellers = load_resellers_data()
    msg = f"📋 <b>Daftar Member & Saldo ({len(resellers)})</b>\n\n"
    if not resellers: msg += "Belum ada data."
    else:
        sorted_ids = sorted(resellers.keys(), key=lambda x: resellers[x].get('balance', 0), reverse=True)
        for r_id in sorted_ids[:50]:
            data = resellers[r_id]
            balance = format_rupiah(data.get('balance', 0))
            role_type = data.get('role', 'member')
            role_tag = "👑 Admin" if role_type == 'admin' else ("🏆 Reseller" if role_type == 'reseller' else "👤 Member")
            try:
                chat = await context.bot.get_chat(chat_id=r_id)
                name = html.escape(chat.first_name)
                user_display = f"@{chat.username}" if chat.username else ""
                msg += f"{role_tag} | <b>{name}</b> {user_display}\n🆔 <code>{r_id}</code> | 💰 {balance}\n━━━━━━━━━━━━\n"
            except:
                msg += f"{role_tag} | ID {r_id}\n💰 {balance}\n━━━━━━━━━━━━\n"
            await asyncio.sleep(0.05)
    if len(msg) > 4000: msg = msg[:4000] + "\n...terpotong"
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_add_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ <b>Tambah Reseller</b>\nMasukkan Telegram ID:", parse_mode=ParseMode.HTML)
    return ADD_RESELLER

async def add_reseller_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r_id = update.message.text.strip()
    data = load_resellers_data()
    if r_id not in data:
        data[r_id] = {"balance": 0, "role": "reseller"}
        save_resellers_data(data)
        await update.message.reply_text(f"✅ Reseller <code>{r_id}</code> ditambahkan.", parse_mode=ParseMode.HTML)
    else:
        data[r_id]["role"] = "reseller"
        save_resellers_data(data)
        await update.message.reply_text(f"✅ User <code>{r_id}</code> diupgrade jadi Reseller.", parse_mode=ParseMode.HTML)
    await update.message.reply_text("Kembali:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_del_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➖ <b>Hapus/Downgrade Reseller</b>\nMasukkan Telegram ID:", parse_mode=ParseMode.HTML)
    return DEL_RESELLER

async def del_reseller_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r_id = update.message.text.strip()
    data = load_resellers_data()
    if r_id in data:
        data[r_id]["role"] = "member"
        save_resellers_data(data)
        await update.message.reply_text(f"✅ Status Reseller <code>{r_id}</code> dicabut.", parse_mode=ParseMode.HTML)
    else: await update.message.reply_text("❌ Tidak ditemukan.")
    await update.message.reply_text("Kembali:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 <b>Isi Saldo Member</b>\nMasukkan ID Telegram Member/Reseller:", parse_mode=ParseMode.HTML)
    return ADD_BALANCE_ID

async def add_balance_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r_id = update.message.text.strip()
    context.user_data['bal_id'] = r_id
    await update.message.reply_text(f"✅ Target ID: <code>{r_id}</code>\nMasukkan Nominal Saldo (angka saja, contoh 20000):", parse_mode=ParseMode.HTML)
    return ADD_BALANCE_AMOUNT

async def add_balance_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: amount = int(update.message.text.strip())
    except ValueError: 
        await update.message.reply_text("❌ Harus angka!")
        return ADD_BALANCE_AMOUNT
    r_id = context.user_data['bal_id']
    new_bal = update_reseller_balance(r_id, amount)
    await update.message.reply_text(f"✅ Berhasil.\n💰 Saldo Sekarang: <code>{format_rupiah(new_bal)}</code>", parse_mode=ParseMode.HTML)
    await update.message.reply_text("Kembali:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    curr = format_rupiah(get_account_price())
    await query.edit_message_text(f"🏷️ <b>Set Harga Member per Akun</b>\nHarga saat ini: <code>{curr}</code>\nMasukkan harga baru (angka saja):", parse_mode=ParseMode.HTML)
    return SET_PRICE_INPUT

async def set_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: price = int(update.message.text.strip())
    except ValueError: 
        await update.message.reply_text("❌ Harus angka!")
        return SET_PRICE_INPUT
    set_account_price(price)
    await update.message.reply_text(f"✅ Harga member diubah menjadi: <code>{format_rupiah(price)}</code>", parse_mode=ParseMode.HTML)
    await update.message.reply_text("Kembali:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_set_reseller_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    curr = format_rupiah(get_reseller_price())
    await query.edit_message_text(f"🏷️ <b>Set Harga Reseller per Akun</b>\nHarga saat ini: <code>{curr}</code>\nMasukkan harga baru:", parse_mode=ParseMode.HTML)
    return SET_RESELLER_PRICE_INPUT

async def set_reseller_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: price = int(update.message.text.strip())
    except ValueError: return SET_RESELLER_PRICE_INPUT
    data = load_json(SETTINGS_DB, {})
    if not isinstance(data, dict): data = {}
    data["reseller_price"] = int(price)
    save_json(SETTINGS_DB, data)
    await update.message.reply_text(f"✅ Harga reseller diubah menjadi: <code>{format_rupiah(price)}</code>", parse_mode=ParseMode.HTML)
    await update.message.reply_text("Kembali:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def admin_list_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admins = load_admins()
    text = f"👑 <b>Daftar Admin ({len(admins)})</b>\n\n" + "\n".join([f"• <code>{a}</code>" for a in admins])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    await query.edit_message_text("👑 <b>Tambah Admin Baru</b>\nMasukkan ID Telegram admin baru:", parse_mode=ParseMode.HTML)
    return ADD_ADMIN_INPUT

async def add_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a_id = update.message.text.strip()
    if not a_id.isdigit():
        await update.message.reply_text("❌ ID Telegram harus angka!")
        return ADD_ADMIN_INPUT
    admins = load_admins()
    admins.add(a_id)
    save_admins(admins)
    resellers = load_resellers_data()
    if a_id in resellers:
        resellers[a_id]["role"] = "admin"
    else:
        resellers[a_id] = {"balance": 0, "role": "admin"}
    save_resellers_data(resellers)
    await update.message.reply_text(f"✅ Admin baru <code>{a_id}</code> berhasil ditambahkan!", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
    return SELECTING_ACTION

async def start_set_admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    await query.edit_message_text(
        "💬 <b>Set Kontak / Username Admin</b>\n\n"
        "Masukkan username Telegram admin (contoh: <code>@username_kamu</code> atau link <code>https://t.me/username_kamu</code>):",
        parse_mode=ParseMode.HTML
    )
    return SET_ADMIN_CONTACT_INPUT

async def set_admin_contact_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return SELECTING_ACTION
    contact = update.message.text.strip()
    if not contact:
        await update.message.reply_text("❌ Kontak admin tidak boleh kosong!")
        return SET_ADMIN_CONTACT_INPUT
    set_admin_contact(contact)
    await update.message.reply_text(
        f"✅ Kontak Admin berhasil diperbarui menjadi: <code>{html.escape(contact)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]])
    )
    return SELECTING_ACTION

async def start_set_qris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    await query.edit_message_text("🖼️ <b>Set Foto QRIS</b>\n\nSilakan kirimkan Foto QRIS pembayaran baru ke bot ini.", parse_mode=ParseMode.HTML)
    return SET_QRIS_INPUT

async def set_qris_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return SELECTING_ACTION
    photo = update.message.photo[-1] if update.message.photo else None
    doc = update.message.document
    file = None
    if photo:
        file = await photo.get_file()
    elif doc and doc.mime_type and doc.mime_type.startswith("image/"):
        file = await doc.get_file()

    if file:
        qris_png = os.path.join(DIR_PATH, "qris.png")
        qris_jpg = os.path.join(DIR_PATH, "qris.jpg")
        await file.download_to_drive(qris_png)
        await file.download_to_drive(qris_jpg)
        try:
            local_dir = os.path.dirname(os.path.abspath(__file__))
            await file.download_to_drive(os.path.join(local_dir, "qris.png"))
            await file.download_to_drive(os.path.join(local_dir, "qris.jpg"))
        except:
            pass
        await update.message.reply_text("✅ Foto QRIS berhasil diperbarui!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Reseller", callback_data='menu_resellers')]]))
        return SELECTING_ACTION
    else:
        await update.message.reply_text("❌ Silakan kirimkan gambar/foto QRIS.")
        return SET_QRIS_INPUT

# --- BROADCAST & INCOME & BACKUP ---

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 <b>Broadcast Message</b>\n\nSilakan kirim pesan (Teks/Gambar) yang ingin Anda sebarkan ke semua member:", parse_mode=ParseMode.HTML)
    return BROADCAST_MSG

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = load_json(MEMBER_DB, [])
    count = 0
    await update.message.reply_text("⏳ Sedang mengirim broadcast...")
    for uid in members:
        try:
            await update.message.copy(chat_id=uid)
            count += 1
        except: pass
        await asyncio.sleep(0.1)
    await update.message.reply_text(f"✅ <b>Broadcast Selesai</b>\nPesan terkirim ke: {count} member.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data='menu_back_new')]]), parse_mode=ParseMode.HTML)
    return SELECTING_ACTION

def ascii_bar(value, max_val, width=10):
    if max_val == 0: return "░" * width
    filled = int((value / max_val) * width)
    return "█" * filled + "░" * (width - filled)

async def action_income_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    now_wib = get_now_wib()
    today_wib = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = (today_wib - datetime.timedelta(hours=7)).timestamp()
    week_wib = (now_wib - datetime.timedelta(days=now_wib.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (week_wib - datetime.timedelta(hours=7)).timestamp()
    month_wib = now_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start = (month_wib - datetime.timedelta(hours=7)).timestamp()
    all_data = get_income_summary(0)
    today_data = get_income_summary(today_start)
    week_data = get_income_summary(week_start)
    month_data = get_income_summary(month_start)
    max_income = max(week_data["total"], month_data["total"], 1)
    bar_week = ascii_bar(week_data["total"], max_income)
    bar_month = ascii_bar(month_data["total"], max_income)
    msg = (
        "📈 <b>LAPORAN PENDAPATAN UPCLOUD (WIB)</b>\n\n"
        f"📆 <b>Hari Ini</b>\n   💰 Total: {format_rupiah(today_data['total'])}\n   🧾 Transaksi: {today_data['count']}\n\n"
        f"📅 <b>Minggu Ini</b>\n   💰 Total: {format_rupiah(week_data['total'])}\n   🧾 Transaksi: {week_data['count']}\n   📊 Grafik: <code>{bar_week}</code>\n\n"
        f"🗓️ <b>Bulan Ini</b>\n   💰 Total: {format_rupiah(month_data['total'])}\n   🧾 Transaksi: {month_data['count']}\n   📊 Grafik: <code>{bar_month}</code>\n\n"
        f"💼 <b>Seumur Hidup</b>\n   💰 Total: {format_rupiah(all_data['total'])}\n   🧾 Transaksi: {all_data['count']}\n   📈 Rata-rata: {format_rupiah(all_data['avg'])}\n   🥇 Terbesar: {format_rupiah(all_data['max'])}\n\n"
        f"📦 Sisa Stok: {get_stock_count()} akun\n"
        f"🗂️ Total Terjual: {len(load_json(SOLD_DB, []))} akun"
    )
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='menu_back')]]))
    return SELECTING_ACTION

async def action_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.message.reply_text("⛔ Hanya admin!")
        return SELECTING_ACTION
    try:
        await query.edit_message_text("⏳ <b>Membuat backup...</b>", parse_mode=ParseMode.HTML)
        zip_path = f"{DIR_PATH}/backup_upcloud_{int(time.time())}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for fp in [STOCK_FILE, RESELLER_DB, MEMBER_DB, SETTINGS_DB, INCOME_DB, SOLD_DB, ADMIN_DB]:
                if os.path.exists(fp):
                    zf.write(fp, os.path.basename(fp))
            qris_file = get_qris_image_path()
            if qris_file and os.path.exists(qris_file):
                zf.write(qris_file, os.path.basename(qris_file))
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(zip_path, 'rb'), filename=os.path.basename(zip_path), caption=f"💾 Backup UpCloud - {get_indo_date()} {get_time_wib()}\nStok: {get_stock_count()} akun")
        os.remove(zip_path)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Backup selesai!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data='menu_back_new')]]))
    except Exception as e:
        await query.message.reply_text(f"❌ Gagal backup: {e}")
    return SELECTING_ACTION

# --- Navigation ---
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE): return await start(update, context)
async def back_to_main_new(update: Update, context: ContextTypes.DEFAULT_TYPE): return await start(update, context, force_new=True)
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Cancelled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data='menu_back_new')]]))
    return SELECTING_ACTION

# --- Main Function ---
def main():
    try:
        token = get_config_value("BOT_TOKEN")
        try:
            from dotenv import load_dotenv
            load_dotenv()
            if not token:
                token = os.getenv("BOT_TOKEN")
        except: pass

        logger.info("--- Starting UPCLOUD Bot ---")
        if not token:
            logger.critical("BOT_TOKEN missing di /etc/upcloud/bot_config.sh atau .env - Buat file dengan isi BOT_TOKEN=... dan CHAT_ID=...")
            print("❌ BOT_TOKEN belum di set! Buat file /etc/upcloud/bot_config.sh dengan:\nBOT_TOKEN=token_bot_kamu\nCHAT_ID=id_admin_kamu (bisa multi: 123,456,789)\n")
            return
        app = ApplicationBuilder().token(token).build()

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", start), 
                CommandHandler("menu", start), 
                CallbackQueryHandler(back_to_main, pattern='^menu_back$'),
                CallbackQueryHandler(back_to_main_new, pattern='^menu_back_new$')
            ],
            states={
                SELECTING_ACTION: [
                    CallbackQueryHandler(action_buy, pattern='^menu_buy$'),
                    CallbackQueryHandler(action_stock, pattern='^menu_stock$'),
                    CallbackQueryHandler(action_topup, pattern='^menu_topup$'),
                    CallbackQueryHandler(action_my_history, pattern='^menu_my_history$'),
                    CallbackQueryHandler(stock_manage_menu, pattern='^menu_stock_manage$'),
                    CallbackQueryHandler(stock_list_action, pattern='^stock_list$'),
                    CallbackQueryHandler(stock_count_action, pattern='^stock_count$'),
                    CallbackQueryHandler(stock_dedup_action, pattern='^stock_dedup$'),
                    CallbackQueryHandler(stock_backup_action, pattern='^stock_backup$'),
                    CallbackQueryHandler(stock_add_paste_start, pattern='^stock_add_paste$'),
                    CallbackQueryHandler(stock_add_file_info, pattern='^stock_add_info$'),
                    CallbackQueryHandler(reseller_menu, pattern='^menu_resellers$'),
                    CallbackQueryHandler(start_add_reseller, pattern='^reseller_add$'),
                    CallbackQueryHandler(start_del_reseller, pattern='^reseller_del$'),
                    CallbackQueryHandler(action_list_resellers, pattern='^reseller_list$'),
                    CallbackQueryHandler(start_add_balance, pattern='^reseller_balance_add$'),
                    CallbackQueryHandler(start_set_price, pattern='^reseller_set_price$'),
                    CallbackQueryHandler(start_set_reseller_price, pattern='^reseller_set_reseller_price$'),
                    CallbackQueryHandler(admin_list_action, pattern='^admin_list$'),
                    CallbackQueryHandler(admin_add_start, pattern='^admin_add$'),
                    CallbackQueryHandler(start_set_qris, pattern='^menu_set_qris$'),
                    CallbackQueryHandler(start_set_admin_contact, pattern='^menu_set_contact$'),
                    CallbackQueryHandler(start_broadcast, pattern='^menu_broadcast$'),
                    CallbackQueryHandler(action_income_report, pattern='^menu_income$'),
                    CallbackQueryHandler(action_backup, pattern='^menu_backup$'),
                    CallbackQueryHandler(back_to_main, pattern='^menu_back$'),
                    CallbackQueryHandler(back_to_main_new, pattern='^menu_back_new$')
                ],
                ADD_STOCK_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, stock_add_paste_input)],
                ADD_BALANCE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_id_input)],
                ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount_input)],
                SET_PRICE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_price_input)],
                SET_RESELLER_PRICE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reseller_price_input)],
                ADD_RESELLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reseller_input)],
                DEL_RESELLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_reseller_input)],
                ADD_ADMIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_input)],
                SET_ADMIN_CONTACT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_admin_contact_input)],
                SET_QRIS_INPUT: [MessageHandler((filters.PHOTO | filters.Document.IMAGE | filters.TEXT) & ~filters.COMMAND, set_qris_photo_input)],
                BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, process_broadcast)],
            },
            fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start), CommandHandler("menu", start)]
        )
        app.add_handler(conv_handler)
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        logger.info(f"Bot polling... DIR={DIR_PATH} Stok={get_stock_count()}")
        print(f"Bot jalan... DIR={DIR_PATH} Stok={get_stock_count()} akun")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Error: {e}")
        import traceback; traceback.print_exc()
        time.sleep(5)

if __name__ == '__main__':
    main()
