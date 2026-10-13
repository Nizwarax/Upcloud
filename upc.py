import http.client
import json
import time
import random
import string
import sys
import os

# ==========================================
# FILE KONFIGURASI
# ==========================================
ACCOUNTS_FILE = "upcloud_accounts.json"
PASSWORD_FILE = "vps_passwords.json"

_credits_cache = {}

# ==========================================
# WARNA ANSI
# ==========================================
class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; MAGENTA = "\033[95m"; CYAN = "\033[96m"; WHITE = "\033[97m"

def c(text, color): return f"{color}{text}{C.RESET}"
def success(msg): print(c(f"✅ {msg}", C.GREEN))
def error(msg):   print(c(f"❌ {msg}", C.RED))
def warning(msg): print(c(f"⚠️  {msg}", C.YELLOW))
def info(msg):    print(c(f"ℹ️  {msg}", C.CYAN))

def print_line(char="─", length=55, color=C.CYAN):
    print(c(char * length, color))

def print_header(title):
    print()
    print_line("═", 55, C.CYAN)
    print(c(f"  {title}", C.BOLD + C.CYAN))
    print_line("═", 55, C.CYAN)

def progress_bar(seconds, label="Menunggu"):
    bar_length = 30
    for i in range(seconds):
        percent = (i + 1) / seconds
        filled = int(bar_length * percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        sys.stdout.write(f"\r  {label} [{bar}] {int(percent * 100)}%")
        sys.stdout.flush()
        time.sleep(1)
    print()

# ==========================================
# MANAJEMEN AKUN
# ==========================================
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return {"accounts": {}, "active": None}
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"accounts": {}, "active": None}

def save_accounts(data):
    try:
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        try: os.chmod(ACCOUNTS_FILE, 0o600)
        except: pass
        return True
    except Exception as e:
        error(f"Gagal menyimpan akun: {e}")
        return False

def add_account(name, token):
    data = load_accounts()
    data["accounts"][name] = {"token": token, "added": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not data["active"]:
        data["active"] = name
    return save_accounts(data)

def remove_account(name):
    data = load_accounts()
    if name in data["accounts"]:
        del data["accounts"][name]
        if data["active"] == name:
            data["active"] = list(data["accounts"].keys())[0] if data["accounts"] else None
        return save_accounts(data)
    return False

def set_active_account(name):
    data = load_accounts()
    if name in data["accounts"]:
        data["active"] = name
        return save_accounts(data)
    return False

def get_active_account():
    data = load_accounts()
    active = data.get("active")
    if active and active in data["accounts"]:
        return active, data["accounts"][active]["token"]
    return None, None

# ==========================================
# PENYIMPANAN PASSWORD
# ==========================================
def save_password(account_name, uuid, hostname, password):
    data = {}
    if os.path.exists(PASSWORD_FILE):
        try:
            with open(PASSWORD_FILE, 'r') as f:
                data = json.load(f)
        except:
            data = {}
    if account_name not in data:
        data[account_name] = {}
    data[account_name][uuid] = {"hostname": hostname, "password": password}
    try:
        with open(PASSWORD_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        try: os.chmod(PASSWORD_FILE, 0o600)
        except: pass
    except Exception as e:
        warning(f"Gagal menyimpan password: {e}")

def get_password(account_name, uuid):
    if not os.path.exists(PASSWORD_FILE): return None
    try:
        with open(PASSWORD_FILE, 'r') as f:
            data = json.load(f)
        return data.get(account_name, {}).get(uuid)
    except: return None

def remove_password(account_name, uuid):
    if not os.path.exists(PASSWORD_FILE): return
    try:
        with open(PASSWORD_FILE, 'r') as f:
            data = json.load(f)
        if account_name in data and uuid in data[account_name]:
            del data[account_name][uuid]
            if not data[account_name]:
                del data[account_name]
            with open(PASSWORD_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except: pass

# ==========================================
# DATA MASTER
# ==========================================
OS_OPTIONS = [
    {"id": "1", "name": "Debian 12 (Bookworm)", "uuid": "01000000-0000-4000-8000-000020070100", "star": "⭐"},
    {"id": "2", "name": "Debian 13 (Trixie)", "uuid": "01000000-0000-4000-8000-000020080100"},
    {"id": "3", "name": "Ubuntu 22.04 LTS", "uuid": "01000000-0000-4000-8000-000030220200"},
    {"id": "4", "name": "Ubuntu 24.04 LTS", "uuid": "01000000-0000-4000-8000-000030240200"},
    {"id": "5", "name": "Ubuntu 26.04 LTS", "uuid": "01000000-0000-4000-8000-000030260200"},
    {"id": "6", "name": "Rocky Linux 8", "uuid": "01000000-0000-4000-8000-000150010100"},
    {"id": "7", "name": "Rocky Linux 9", "uuid": "01000000-0000-4000-8000-000150020100"},
    {"id": "8", "name": "Rocky Linux 10", "uuid": "01000000-0000-4000-8000-000150030100"},
    {"id": "9", "name": "AlmaLinux 8", "uuid": "01000000-0000-4000-8000-000140010100"},
    {"id": "10", "name": "AlmaLinux 9", "uuid": "01000000-0000-4000-8000-000140020100"},
    {"id": "11", "name": "AlmaLinux 10", "uuid": "01000000-0000-4000-8000-000140030100"},
    {"id": "12", "name": "CentOS Stream 9", "uuid": "01000000-0000-4000-8000-000050020100"},
    {"id": "13", "name": "CentOS Stream 10", "uuid": "01000000-0000-4000-8000-000050030100"},
    {"id": "14", "name": "Fedora 42", "uuid": "01000000-0000-4000-8000-000040420100"},
]

PLAN_OPTIONS = [
    {"id": "1", "name": "1 Core / 1GB — DEV", "plan_id": "DEV-1xCPU-1GB", "storage": 20},
    {"id": "2", "name": "1 Core / 2GB — DEV", "plan_id": "DEV-1xCPU-2GB", "storage": 30},
    {"id": "3", "name": "2 Core / 4GB — DEV", "plan_id": "DEV-2xCPU-4GB", "storage": 60},
    {"id": "4", "name": "4 Core / 8GB — DEV", "plan_id": "DEV-4xCPU-8GB", "storage": 80},
    {"id": "5", "name": "8 Core / 16GB — DEV", "plan_id": "DEV-8xCPU-16GB", "storage": 100},
    {"id": "6", "name": "16 Core / 32GB — DEV", "plan_id": "DEV-16xCPU-32GB", "storage": 160},
    {"id": "7", "name": "2 Core / 4GB — PREMIUM", "plan_id": "PREMIUM-2xCPU-4GB", "storage": 50},
    {"id": "8", "name": "2 Core / 8GB — PREMIUM", "plan_id": "PREMIUM-2xCPU-8GB", "storage": 100},
    {"id": "9", "name": "4 Core / 8GB — PREMIUM", "plan_id": "PREMIUM-4xCPU-8GB", "storage": 160},
    {"id": "10", "name": "4 Core / 16GB — PREMIUM", "plan_id": "PREMIUM-4xCPU-16GB", "storage": 200},
    {"id": "11", "name": "8 Core / 16GB — PREMIUM", "plan_id": "PREMIUM-8xCPU-16GB", "storage": 300},
    {"id": "12", "name": "8 Core / 32GB — PREMIUM", "plan_id": "PREMIUM-8xCPU-32GB", "storage": 400},
]

ZONE_OPTIONS = [
    {"id": "1", "name": "Singapore", "zone_id": "sg-sin1", "flag": "🇸🇬"},
    {"id": "2", "name": "Japan (Osaka)", "zone_id": "jp-osa1", "flag": "🇯🇵"},
    {"id": "3", "name": "Amsterdam", "zone_id": "nl-ams1", "flag": "🇳🇱"},
    {"id": "4", "name": "Frankfurt", "zone_id": "de-fra1", "flag": "🇩🇪"},
    {"id": "5", "name": "London", "zone_id": "uk-lon1", "flag": "🇬🇧"},
    {"id": "6", "name": "New York", "zone_id": "us-nyc1", "flag": "🇺🇸"},
    {"id": "7", "name": "Stockholm", "zone_id": "se-sto1", "flag": "🇸🇪"},
    {"id": "8", "name": "Sydney", "zone_id": "au-syd1", "flag": "🇦🇺"},
]

# ==========================================
# PRESET FIREWALL
# ==========================================
def get_firewall_preset_default():
    """Preset minimal: SSH + HTTP + HTTPS (3 aturan)."""
    return [
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "80", "dst_port_end": "80", "comment": "HTTP"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "443", "dst_port_end": "443", "comment": "HTTPS"},
    ]

def get_firewall_preset_web():
    """Preset web server: SSH + HTTP + HTTPS + Ping (4 aturan)."""
    return [
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "80", "dst_port_end": "80", "comment": "HTTP"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "443", "dst_port_end": "443", "comment": "HTTPS"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "icmp", "comment": "Ping"},
    ]

def get_firewall_preset_ssh_only():
    """Preset SSH only (1 aturan)."""
    return [
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
    ]

def get_firewall_preset_web_db():
    """Preset web + database (5 aturan)."""
    return [
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "80", "dst_port_end": "80", "comment": "HTTP"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "443", "dst_port_end": "443", "comment": "HTTPS"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "3306", "dst_port_end": "3306", "comment": "MySQL"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "5432", "dst_port_end": "5432", "comment": "PostgreSQL"},
    ]

def get_firewall_preset_trial():
    """Preset khusus akun TRIAL: hanya 10 aturan penting."""
    return [
        # INBOUND IPv4 (5 aturan)
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "80", "dst_port_end": "80", "comment": "HTTP"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "tcp", "dst_port_start": "443", "dst_port_end": "443", "comment": "HTTPS"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS"},
        {"direction": "in", "action": "accept", "family": "IPv4",
         "protocol": "icmp", "comment": "Ping IPv4"},
        # INBOUND IPv6 (5 aturan)
        {"direction": "in", "action": "accept", "family": "IPv6",
         "protocol": "tcp", "dst_port_start": "22", "dst_port_end": "22", "comment": "SSH"},
        {"direction": "in", "action": "accept", "family": "IPv6",
         "protocol": "tcp", "dst_port_start": "80", "dst_port_end": "80", "comment": "HTTP"},
        {"direction": "in", "action": "accept", "family": "IPv6",
         "protocol": "tcp", "dst_port_start": "443", "dst_port_end": "443", "comment": "HTTPS"},
        {"direction": "in", "action": "accept", "family": "IPv6",
         "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS"},
        {"direction": "in", "action": "accept", "family": "IPv6",
         "protocol": "icmp", "comment": "Ping IPv6"},
    ]

def get_firewall_preset_mega():
    """Preset firewall LENGKAP 60+ aturan (butuh akun upgrade, bukan trial)."""
    rules = []
    
    # INBOUND IPv4
    inbound_tcp = [
        ("22", "22", "SSH"),
        ("80", "80", "HTTP"),
        ("443", "443", "HTTPS"),
        ("20", "21", "FTP"),
        ("23", "23", "Telnet"),
        ("25", "25", "SMTP"),
        ("110", "110", "POP3"),
        ("143", "143", "IMAP"),
        ("3389", "3389", "RDP"),
        ("8443", "8443", "HTTPS Alt"),
        ("8880", "8880", "HTTP Alt"),
        ("3306", "3306", "MySQL"),
        ("5432", "5432", "PostgreSQL"),
        ("6379", "6379", "Redis"),
    ]
    for start, end, comment in inbound_tcp:
        rules.append({
            "direction": "in", "action": "accept", "family": "IPv4",
            "protocol": "tcp", "dst_port_start": start, "dst_port_end": end,
            "comment": comment
        })
    rules.append({"direction": "in", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "123", "dst_port_end": "123", "comment": "NTP"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "33434", "dst_port_end": "33534", "comment": "Traceroute"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "1024", "dst_port_end": "65535", "comment": "UDP High"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv4",
                  "protocol": "icmp", "comment": "ICMP Ping"})
    
    # INBOUND IPv6
    for start, end, comment in inbound_tcp:
        rules.append({
            "direction": "in", "action": "accept", "family": "IPv6",
            "protocol": "tcp", "dst_port_start": start, "dst_port_end": end,
            "comment": comment
        })
    rules.append({"direction": "in", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "123", "dst_port_end": "123", "comment": "NTP"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "33434", "dst_port_end": "33534", "comment": "Traceroute"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "1024", "dst_port_end": "65535", "comment": "UDP High"})
    rules.append({"direction": "in", "action": "accept", "family": "IPv6",
                  "protocol": "icmp", "comment": "ICMP Ping"})
    
    # DROP ALL INBOUND
    rules.append({"direction": "in", "action": "drop", "family": "IPv4", "comment": "Drop All IPv4 In"})
    rules.append({"direction": "in", "action": "drop", "family": "IPv6", "comment": "Drop All IPv6 In"})
    
    # OUTBOUND IPv4
    outbound_tcp = [
        ("80", "80", "HTTP Out"),
        ("443", "443", "HTTPS Out"),
        ("8080", "8080", "HTTP Alt Out"),
        ("25", "25", "SMTP Out"),
        ("3306", "3306", "MySQL Out"),
        ("5432", "5432", "PostgreSQL Out"),
    ]
    for start, end, comment in outbound_tcp:
        rules.append({
            "direction": "out", "action": "accept", "family": "IPv4",
            "protocol": "tcp", "dst_port_start": start, "dst_port_end": end,
            "comment": comment
        })
    rules.append({"direction": "out", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS Out"})
    rules.append({"direction": "out", "action": "accept", "family": "IPv4",
                  "protocol": "udp", "dst_port_start": "123", "dst_port_end": "123", "comment": "NTP Out"})
    rules.append({"direction": "out", "action": "accept", "family": "IPv4",
                  "protocol": "icmp", "comment": "ICMP Ping Out"})
    
    # OUTBOUND IPv6
    for start, end, comment in outbound_tcp:
        rules.append({
            "direction": "out", "action": "accept", "family": "IPv6",
            "protocol": "tcp", "dst_port_start": start, "dst_port_end": end,
            "comment": comment
        })
    rules.append({"direction": "out", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "53", "dst_port_end": "53", "comment": "DNS Out"})
    rules.append({"direction": "out", "action": "accept", "family": "IPv6",
                  "protocol": "udp", "dst_port_start": "123", "dst_port_end": "123", "comment": "NTP Out"})
    rules.append({"direction": "out", "action": "accept", "family": "IPv6",
                  "protocol": "icmp", "comment": "ICMP Ping Out"})
    
    # DROP ALL OUTBOUND
    rules.append({"direction": "out", "action": "drop", "family": "IPv4", "comment": "Drop All IPv4 Out"})
    rules.append({"direction": "out", "action": "drop", "family": "IPv6", "comment": "Drop All IPv6 Out"})
    
    return rules

# ==========================================
# FUNGSI BANTUAN
# ==========================================
def generate_random_password(length=16):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for i in range(length))

def generate_random_name():
    return f"nexus-{''.join(random.choices(string.hexdigits.lower(), k=5))}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def press_enter():
    input(c("\n  ⏎ Tekan Enter untuk melanjutkan...", C.DIM))

def format_price(price_data, currency="EUR"):
    if not price_data:
        return None
    try:
        hourly = float(price_data.get("price", 0))
        monthly = hourly * 24 * 28
        curr = price_data.get("currency", currency)
        return f"~{monthly:.2f} {curr}/bln"
    except:
        return None

def extract_ips(server_data):
    ipv4 = "—"
    ipv6 = "—"
    if 'ip_addresses' in server_data and 'ip_address' in server_data['ip_addresses']:
        for ip in server_data['ip_addresses']['ip_address']:
            if ip.get('access') == 'public':
                fam = ip.get('family', '')
                addr = ip.get('address', '—')
                if fam == 'IPv4' and ipv4 == "—":
                    ipv4 = addr
                elif fam == 'IPv6' and ipv6 == "—":
                    ipv6 = addr
    return ipv4, ipv6

def refresh_server_data(manager, uuid):
    gs, gr = manager.get_server_details(uuid)
    if gs == 200:
        try:
            return json.loads(gr)['server']
        except:
            return None
    return None

def get_account_credits(manager, account_name):
    global _credits_cache
    if account_name in _credits_cache:
        return _credits_cache[account_name]
    try:
        status, res = manager.get_account_info()
        if status == 200:
            acc = json.loads(res)['account']
            credits = acc.get('credits', 0)
            currency = acc.get('currency', '')
            _credits_cache[account_name] = (credits, currency)
            return credits, currency
    except:
        pass
    return None, None

def show_account_header(account_name, credits, currency):
    if account_name:
        if credits is not None:
            try:
                credits_val = float(credits)
                balance_str = f"{credits_val:.2f} {currency}"
                if credits_val > 10:
                    balance_color = C.GREEN
                elif credits_val > 5:
                    balance_color = C.YELLOW
                else:
                    balance_color = C.RED
                balance_display = c(balance_str, balance_color + C.BOLD)
            except:
                balance_display = c(str(credits), C.CYAN)
        else:
            balance_display = c("— (gagal ambil)", C.DIM)
        print(f"  {c('👤 Akun:', C.BOLD)} {c(account_name, C.GREEN + C.BOLD)}")
        print(f"  {c('💰 Saldo:', C.BOLD)} {balance_display}")
    else:
        print(f"  {c('⚠️  Belum ada akun aktif', C.YELLOW)}")

def auto_delete_ipv6(manager, server_uuid):
    fresh = refresh_server_data(manager, server_uuid)
    if not fresh:
        return 0, 0
    state = fresh.get('state')
    if state != 'stopped':
        info(f"Server state '{state}', tidak bisa hapus IPv6. Harus 'stopped'.")
        return 0, 0

    s, r = manager.list_ip_addresses()
    if s != 200:
        return 0, 0
    try:
        all_ips = json.loads(r).get('ip_addresses', {}).get('ip_address', [])
    except:
        return 0, 0

    ipv6_list = [
        ip for ip in all_ips
        if ip.get('server') == server_uuid
        and ip.get('family') == 'IPv6'
        and ip.get('access') == 'public'
    ]
    if not ipv6_list:
        return 0, 0

    success_count = 0
    for ip in ipv6_list:
        ip_uuid = ip.get('uuid')
        if not ip_uuid:
            continue
        ds, dr = manager.delete_ip_address(ip_uuid)
        if ds in [200, 204]:
            success_count += 1
            success(f"IPv6 {ip.get('address')} dihapus.")
        else:
            error(f"Gagal hapus IPv6 {ip.get('address')}: {dr}")
    return success_count, len(ipv6_list)

# ==========================================
# KELAS API UPCLOUD
# ==========================================
class UpCloudManager:
    def __init__(self, token):
        self.token = token
        self.conn = http.client.HTTPSConnection("api.upcloud.com")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _request(self, method, path, body=None, retries=3):
        last_error = None
        for attempt in range(retries):
            try:
                self.conn.request(method, path, body, self.headers)
                res = self.conn.getresponse()
                data = res.read().decode()
                return res.status, data
            except (http.client.RemoteDisconnected, ConnectionResetError) as e:
                last_error = e
                warning(f"Koneksi terputus, mencoba ulang ({attempt + 1}/{retries})...")
                time.sleep(3)
                self.conn = http.client.HTTPSConnection("api.upcloud.com")
                continue
            except Exception as e:
                return 500, json.dumps({"error": str(e)})
        return 500, json.dumps({"error": f"Gagal setelah {retries} percobaan: {str(last_error)}"})

    def test_token(self):
        return self._request("GET", "/1.3/account")

    def get_prices(self):
        return self._request("GET", "/1.3/price")

    def list_servers(self):
        return self._request("GET", "/1.3/server")

    def get_server_details(self, uuid):
        return self._request("GET", f"/1.3/server/{uuid}")

    def stop_server(self, uuid):
        return self._request("POST", f"/1.3/server/{uuid}/stop",
                             json.dumps({"stop_server": {"stop_type": "soft"}}))

    def start_server(self, uuid):
        return self._request("POST", f"/1.3/server/{uuid}/start")

    def restart_server(self, uuid, timeout=60):
        payload = {
            "restart_server": {
                "stop_type": "soft",
                "timeout": timeout,
                "timeout_action": "destroy"
            }
        }
        return self._request("POST", f"/1.3/server/{uuid}/restart", json.dumps(payload))

    def get_console(self, uuid):
        return self._request("GET", f"/1.3/server/{uuid}/remote_access_details")

    def rename_server(self, uuid, new_hostname, new_title=None):
        payload = {"server": {"hostname": new_hostname}}
        if new_title:
            payload["server"]["title"] = new_title
        return self._request("PUT", f"/1.3/server/{uuid}", json.dumps(payload))

    def resize_server(self, uuid, new_plan):
        payload = {"server": {"plan": new_plan}}
        return self._request("PUT", f"/1.3/server/{uuid}", json.dumps(payload))

    def get_stats_cpu(self, uuid):
        return self._request("GET", f"/1.3/server/{uuid}/stats/cpu")

    def get_stats_disk(self, uuid, stat_type="bytes"):
        return self._request("GET", f"/1.3/server/{uuid}/stats/disk/{stat_type}")

    def get_stats_network(self, uuid, stat_type="bytes"):
        return self._request("GET", f"/1.3/server/{uuid}/stats/network/{stat_type}")

    def list_ip_addresses(self):
        return self._request("GET", "/1.3/ip_address")

    def get_server_ip_addresses(self, uuid):
        status, res = self.list_ip_addresses()
        if status != 200:
            return status, res
        try:
            all_ips = json.loads(res).get('ip_addresses', {}).get('ip_address', [])
            server_ips = [ip for ip in all_ips if ip.get('server') == uuid]
            return 200, json.dumps({"ip_addresses": {"ip_address": server_ips}})
        except Exception as e:
            return 500, json.dumps({"error": str(e)})

    def assign_ipv4(self, uuid):
        payload = {"ip_address": {"family": "IPv4", "server": uuid}}
        return self._request("POST", "/1.3/ip_address", json.dumps(payload))

    def assign_ipv6(self, uuid):
        payload = {"ip_address": {"family": "IPv6", "server": uuid}}
        return self._request("POST", "/1.3/ip_address", json.dumps(payload))

    def delete_ip_address(self, ip_address):
        return self._request("DELETE", f"/1.3/ip_address/{ip_address}")

    def delete_server(self, uuid, max_wait=180):
        status, response = self.get_server_details(uuid)
        if status != 200:
            return status, response

        server_data = json.loads(response)['server']
        current_state = server_data.get('state')
        info(f"State saat ini: {current_state}")

        if current_state == 'started':
            info("VPS sedang menyala, menghentikan paksa (hard stop)...")
            stop_status, stop_res = self._request(
                "POST", f"/1.3/server/{uuid}/stop",
                json.dumps({"stop_server": {"stop_type": "hard"}})
            )
            if stop_status not in [200, 202]:
                return stop_status, stop_res

        print(c("  Menunggu VPS siap dihapus ", C.CYAN), end="")
        elapsed = 0
        interval = 5
        new_state = current_state
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            print(c("●", C.DIM), end="", flush=True)
            check_status, check_res = self.get_server_details(uuid)
            if check_status != 200:
                continue
            try:
                new_state = json.loads(check_res)['server'].get('state')
            except:
                continue
            if new_state == 'stopped':
                print(c(" ✅", C.GREEN))
                break
            elif new_state == 'started':
                warning("VPS menyala lagi, stop ulang...")
                self._request("POST", f"/1.3/server/{uuid}/stop",
                              json.dumps({"stop_server": {"stop_type": "hard"}}))
        else:
            warning(f"Timeout {max_wait}s. State terakhir: {new_state}")

        info("Mengirim perintah hapus...")
        return self._request("DELETE", f"/1.3/server/{uuid}")

    def create_server(self, plan_id, zone_id, hostname, title, storage_uuid, storage_size, root_password, ssh_key=None):
        user_data_script = f"""#cloud-config
chpasswd:
  list: |
    root:{root_password}
  expire: False
ssh_pwauth: True
"""
        login_user = {"username": "root", "create_password": "no"}
        if ssh_key:
            login_user["ssh_keys"] = {"ssh_key": [ssh_key]}

        payload = {
            "server": {
                "zone": zone_id, "title": title, "hostname": hostname,
                "plan": plan_id, "metadata": "yes",
                "user_data": user_data_script,
                "storage_devices": {"storage_device": [{
                    "action": "clone", "storage": storage_uuid,
                    "title": f"{hostname}-disk0",
                    "size": storage_size, "tier": "maxiops"
                }]},
                "login_user": login_user
            }
        }
        return self._request("POST", "/1.3/server", json.dumps(payload))

    def list_storage(self):
        return self._request("GET", "/1.3/storage")

    def get_account_info(self):
        return self._request("GET", "/1.3/account")

    def list_firewall_rules(self, uuid):
        return self._request("GET", f"/1.3/server/{uuid}/firewall_rule")

    def create_firewall_rule(self, uuid, direction, action, family,
                             position=None, protocol=None, icmp_type=None,
                             src_addr_start=None, src_addr_end=None,
                             dst_addr_start=None, dst_addr_end=None,
                             src_port_start=None, src_port_end=None,
                             dst_port_start=None, dst_port_end=None,
                             comment=None):
        rule = {"direction": direction, "action": action, "family": family}
        if position is not None: rule["position"] = position
        if protocol is not None: rule["protocol"] = protocol
        if icmp_type is not None: rule["icmp_type"] = icmp_type
        if src_addr_start is not None: rule["source_address_start"] = src_addr_start
        if src_addr_end is not None: rule["source_address_end"] = src_addr_end
        if dst_addr_start is not None: rule["destination_address_start"] = dst_addr_start
        if dst_addr_end is not None: rule["destination_address_end"] = dst_addr_end
        if src_port_start is not None: rule["source_port_start"] = src_port_start
        if src_port_end is not None: rule["source_port_end"] = src_port_end
        if dst_port_start is not None: rule["destination_port_start"] = dst_port_start
        if dst_port_end is not None: rule["destination_port_end"] = dst_port_end
        if comment is not None: rule["comment"] = comment

        payload = {"firewall_rule": rule}
        return self._request("POST", f"/1.3/server/{uuid}/firewall_rule",
                             json.dumps(payload))

    def delete_firewall_rule(self, uuid, position):
        return self._request("DELETE", f"/1.3/server/{uuid}/firewall_rule/{position}")

# ==========================================
# MENU MANAJEMEN AKUN
# ==========================================
def accounts_menu():
    while True:
        clear_screen()
        print_header("👥 MANAJEMEN AKUN UPCLOUD")

        data = load_accounts()
        accounts = data.get("accounts", {})
        active = data.get("active")

        if not accounts:
            warning("Belum ada akun terdaftar.")
        else:
            print(c("  📋 Daftar Akun:", C.BOLD))
            print()
            for i, (name, info_acc) in enumerate(accounts.items(), 1):
                is_active = (name == active)
                mark = c("🟢 AKTIF", C.GREEN + C.BOLD) if is_active else c("⚪", C.DIM)
                token_preview = info_acc['token'][:15] + "..." if len(info_acc['token']) > 15 else info_acc['token']
                print(f"  {mark} {c(str(i) + '.', C.BOLD)} {c(name, C.CYAN + C.BOLD)}")
                print(f"     Token     : {c(token_preview, C.DIM)}")
                print(f"     Ditambah  : {info_acc.get('added', 'N/A')}")
                print()

        print_line("─", 55, C.CYAN)
        print(f"  {c('[1]', C.GREEN)} ➕  Tambah Akun Baru")
        print(f"  {c('[2]', C.GREEN)} 🔄  Ganti Akun Aktif")
        print(f"  {c('[3]', C.GREEN)} 🗑️   Hapus Akun")
        print(f"  {c('[4]', C.GREEN)} 🧪  Test Token Akun")
        print(f"  {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih: ", C.BOLD + C.CYAN)).strip()

        if cmd == "1":
            _add_account_menu()
        elif cmd == "2":
            _switch_account_menu()
        elif cmd == "3":
            _remove_account_menu()
        elif cmd == "4":
            _test_token_menu()
        elif cmd == "0":
            return

def _add_account_menu():
    clear_screen()
    print_header("➕ TAMBAH AKUN BARU")

    name = input(c("  Nama akun (contoh: akun-utama): ", C.CYAN)).strip()
    if not name:
        error("Nama tidak boleh kosong.")
        press_enter()
        return

    data = load_accounts()
    if name in data.get("accounts", {}):
        error(f"Akun '{name}' sudah ada.")
        press_enter()
        return

    print()
    info("Dapatkan token di: https://hub.upcloud.com → Account → API Tokens")
    print()
    token = input(c("  API Token (ucat_...): ", C.CYAN)).strip()
    if not token:
        error("Token tidak boleh kosong.")
        press_enter()
        return

    print()
    info("Memverifikasi token...")
    mgr = UpCloudManager(token)
    status, res = mgr.test_token()
    if status != 200:
        error(f"Token tidak valid! (Status: {status})")
        try:
            err = json.loads(res)
            print(f"     Pesan: {err.get('error', {}).get('error_message', res)}")
        except:
            print(res)
        press_enter()
        return

    try:
        acc = json.loads(res)['account']
        success(f"Token valid! Username: {acc.get('username')}, Credits: {acc.get('credits')}")
    except:
        success("Token valid!")

    if add_account(name, token):
        success(f"Akun '{name}' berhasil ditambahkan.")
    else:
        error("Gagal menyimpan akun.")
    press_enter()

def _switch_account_menu():
    clear_screen()
    print_header("🔄 GANTI AKUN AKTIF")

    data = load_accounts()
    accounts = data.get("accounts", {})
    if not accounts:
        warning("Belum ada akun.")
        press_enter()
        return

    for i, (name, info_acc) in enumerate(accounts.items(), 1):
        is_active = (name == data.get("active"))
        mark = "🟢" if is_active else "⚪"
        print(f"  {mark} {i}. {name}")

    print()
    choice = input(c("  ➤ Pilih nomor akun: ", C.BOLD + C.CYAN)).strip()

    try:
        idx = int(choice) - 1
        name = list(accounts.keys())[idx]
        if set_active_account(name):
            global _credits_cache
            _credits_cache.clear()
            success(f"Akun aktif diganti ke '{name}'.")
        else:
            error("Gagal mengganti akun.")
    except (ValueError, IndexError):
        error("Pilihan tidak valid.")
    press_enter()

def _remove_account_menu():
    clear_screen()
    print_header("🗑️  HAPUS AKUN")

    data = load_accounts()
    accounts = data.get("accounts", {})
    if not accounts:
        warning("Belum ada akun.")
        press_enter()
        return

    for i, name in enumerate(accounts.keys(), 1):
        print(f"  {i}. {name}")

    print()
    choice = input(c("  ➤ Pilih nomor akun yang dihapus: ", C.BOLD + C.CYAN)).strip()

    try:
        idx = int(choice) - 1
        name = list(accounts.keys())[idx]
        confirm = input(c(f"  Yakin hapus akun '{name}'? (y/n): ", C.YELLOW)).strip().lower()
        if confirm == 'y':
            if remove_account(name):
                _credits_cache.pop(name, None)
                success(f"Akun '{name}' berhasil dihapus.")
            else:
                error("Gagal menghapus akun.")
    except (ValueError, IndexError):
        error("Pilihan tidak valid.")
    press_enter()

def _test_token_menu():
    clear_screen()
    print_header("🧪 TEST TOKEN AKUN")

    data = load_accounts()
    accounts = data.get("accounts", {})
    if not accounts:
        warning("Belum ada akun.")
        press_enter()
        return

    for i, name in enumerate(accounts.keys(), 1):
        print(f"  {i}. {name}")

    print()
    choice = input(c("  ➤ Pilih nomor akun: ", C.BOLD + C.CYAN)).strip()

    try:
        idx = int(choice) - 1
        name = list(accounts.keys())[idx]
        token = accounts[name]['token']
        print()
        info(f"Menguji token '{name}'...")
        mgr = UpCloudManager(token)
        status, res = mgr.test_token()
        if status == 200:
            acc = json.loads(res)['account']
            success(f"Token valid!")
            print(f"     Username : {c(acc.get('username'), C.CYAN)}")
            print(f"     Credits  : {c(str(acc.get('credits')), C.GREEN)}")
            print(f"     Email    : {acc.get('email')}")
        else:
            error(f"Token tidak valid! (Status: {status})")
            print(c(res, C.DIM))
    except (ValueError, IndexError):
        error("Pilihan tidak valid.")
    press_enter()

# ==========================================
# MENU UTAMA
# ==========================================
def main_menu(account_name=None, credits=None, currency=None):
    clear_screen()
    print()
    print_line("═", 55, C.MAGENTA)
    print(c("  ☁️   UPCLOUD VPS MANAGER  v7.7", C.BOLD + C.MAGENTA))
    print_line("═", 55, C.MAGENTA)

    show_account_header(account_name, credits, currency)
    print()

    print(c("  📦 MANAJEMEN VPS", C.BOLD + C.YELLOW))
    print(f"    {c('[1]', C.GREEN)} 🚀  Buat VPS Baru")
    print(f"    {c('[2]', C.GREEN)} 📋  Daftar VPS Saya")
    print()
    print(c("  🔐 KREDENSIAL", C.BOLD + C.YELLOW))
    print(f"    {c('[3]', C.GREEN)} 🔑  Lihat / Hapus Password Tersimpan")
    print()
    print(c("  🌐 SUMBER DAYA", C.BOLD + C.YELLOW))
    print(f"    {c('[4]', C.GREEN)} 💾  Lihat Semua Storage")
    print(f"    {c('[5]', C.GREEN)} 🌍  Lihat Semua IP Address")
    print()
    print(c("  ⚙️  SISTEM", C.BOLD + C.YELLOW))
    print(f"    {c('[6]', C.GREEN)} 👤  Info Akun Aktif")
    print(f"    {c('[7]', C.GREEN)} 👥  Manajemen Akun (Multi-Akun)")
    print(f"    {c('[8]', C.GREEN)} 🔄  Refresh Saldo")
    print(f"    {c('[0]', C.RED)} 🚪  Keluar")
    print()
    print_line("─", 55, C.DIM)

# ==========================================
# BUAT VPS
# ==========================================
def create_vps_menu(manager, account_name):
    selected_os = selected_plan = selected_zone = None
    price_map = {}

    info("Mengambil daftar harga dari UpCloud...")
    price_status, price_res = manager.get_prices()
    if price_status == 200:
        try:
            prices = json.loads(price_res)["prices"]
            for key, val in prices.items():
                if key.startswith("server_plan_"):
                    plan_id = key.replace("server_plan_", "")
                    price_map[plan_id] = val
        except:
            pass

    while True:
        clear_screen()
        print_header(f"🚀 BUAT VPS BARU [{account_name}]")

        print()
        print(c("  📋 RINGKASAN PILIHAN", C.BOLD + C.YELLOW))
        print_line("─", 55, C.DIM)

        if selected_os:
            print(f"  {c('✅ OS', C.GREEN)}      : {c(selected_os['name'], C.CYAN + C.BOLD)}")
        else:
            print(f"  {c('⬜ OS', C.DIM)}      : {c('belum dipilih', C.DIM)}")

        if selected_plan:
            price_str = ""
            if price_map and selected_plan.get('plan_id') in price_map:
                price_str = f" — {c(format_price(price_map[selected_plan['plan_id']]), C.GREEN)}"
            print(f"  {c('✅ Spek', C.GREEN)}    : {c(selected_plan['name'], C.CYAN + C.BOLD)}{price_str}")
        else:
            print(f"  {c('⬜ Spek', C.DIM)}    : {c('belum dipilih', C.DIM)}")

        if selected_zone:
            print(f"  {c('✅ Lokasi', C.GREEN)}  : {selected_zone['flag']} {c(selected_zone['name'], C.CYAN + C.BOLD)}")
        else:
            print(f"  {c('⬜ Lokasi', C.DIM)}  : {c('belum dipilih', C.DIM)}")

        print_line("─", 55, C.DIM)

        if all([selected_os, selected_plan, selected_zone]):
            print()
            print(c("  ✨ Siap dibuat! Tekan [4] untuk eksekusi.", C.GREEN + C.BOLD))
        else:
            print()
            print(c("  ℹ️  Lengkapi semua pilihan dulu.", C.YELLOW))

        print()
        print_line("─", 55, C.CYAN)
        print(c("  ⚙️  KONFIGURASI", C.BOLD + C.YELLOW))
        print(f"    {c('[1]', C.GREEN)} 📀  Pilih OS         {c(f'({len(OS_OPTIONS)} pilihan)', C.DIM)}")
        print(f"    {c('[2]', C.GREEN)} 💻  Pilih Spek       {c(f'({len(PLAN_OPTIONS)} pilihan)', C.DIM)}")
        print(f"    {c('[3]', C.GREEN)} 📍  Pilih Lokasi     {c(f'({len(ZONE_OPTIONS)} pilihan)', C.DIM)}")
        print()
        print(c("  🚀 EKSEKUSI", C.BOLD + C.YELLOW))
        print(f"    {c('[4]', C.GREEN)} 🚀  Buat Sekarang (root + password auto)")
        print(f"    {c('[R]', C.YELLOW)} 🔄  Reset Pilihan")
        print(f"    {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih menu: ", C.BOLD + C.CYAN)).strip().upper()

        if cmd == "1":
            selected_os = choose_option_with_numbers(OS_OPTIONS, "OS")
        elif cmd == "2":
            selected_plan = choose_option_with_numbers(PLAN_OPTIONS, "Spek", price_map)
        elif cmd == "3":
            selected_zone = choose_option_with_numbers(ZONE_OPTIONS, "Lokasi")
        elif cmd == "R":
            selected_os = selected_plan = selected_zone = None
            info("Pilihan direset.")
            time.sleep(1)
        elif cmd == "4":
            if not all([selected_os, selected_plan, selected_zone]):
                error("Harap pilih OS, Spek, dan Lokasi terlebih dahulu!")
                press_enter()
                continue

            auto_password = generate_random_password()

            clear_screen()
            print_header("📝 NAMA VPS")
            print(f"  {c('[1]', C.GREEN)} 🎲  Otomatis (random)")
            print(f"  {c('[2]', C.GREEN)} ✏️   Manual (input sendiri)")
            print()
            name_choice = input(c("  ➤ Pilih (1/2) [default: 1]: ", C.BOLD + C.CYAN)).strip() or "1"

            if name_choice == "2":
                while True:
                    manual_name = input(c("  Masukkan nama VPS: ", C.CYAN)).strip()
                    if not manual_name:
                        error("Nama tidak boleh kosong.")
                        continue
                    if not all(ch.isalnum() or ch in '-_' for ch in manual_name):
                        error("Nama hanya boleh huruf, angka, '-' dan '_'.")
                        continue
                    vps_name = manual_name
                    break
                vps_password = input(c("  Masukkan password VPS: ", C.CYAN)).strip()
                if not vps_password:
                    vps_password = auto_password
            else:
                vps_name = generate_random_name()
                vps_password = auto_password

            clear_screen()
            print_header("📋 KONFIRMASI PEMBUATAN VPS")
            print(f"  {'Akun':<10}: {c(account_name, C.MAGENTA + C.BOLD)}")
            print(f"  {'OS':<10}: {c(selected_os['name'], C.CYAN)}")
            print(f"  {'Spek':<10}: {c(selected_plan['name'], C.CYAN)}")
            print(f"  {'Lokasi':<10}: {selected_zone['flag']} {c(selected_zone['name'], C.CYAN)}")
            print(f"  {'Nama':<10}: {c(vps_name, C.MAGENTA + C.BOLD)}")
            print(f"  {'Pass':<10}: {c(vps_password, C.YELLOW + C.BOLD)}")
            print()
            print_line("─", 55, C.YELLOW)
            if name_choice == "2":
                print(c("  🔐 Login: root + password (custom)", C.YELLOW))
            else:
                print(c("  🔐 Login: root + password (auto-generate)", C.YELLOW))
            print_line("─", 55, C.YELLOW)

            konfirmasi = input(c("\n  Ketik 'buat' untuk konfirmasi, atau 'batal': ", C.BOLD)).strip().lower()
            if konfirmasi != "buat":
                info("Dibatalkan.")
                time.sleep(1)
                continue

            print()
            info("Mengirim request ke UpCloud...")
            status, response = manager.create_server(
                plan_id=selected_plan['plan_id'],
                zone_id=selected_zone['zone_id'],
                hostname=vps_name, title=vps_name,
                storage_uuid=selected_os['uuid'],
                storage_size=selected_plan['storage'],
                root_password=vps_password
            )

            if status == 202:
                data = json.loads(response)
                server_uuid = data['server']['uuid']
                success(f"VPS Berhasil Dibuat! UUID: {server_uuid}")
                save_password(account_name, server_uuid, vps_name, vps_password)
                success(f"Password disimpan ke {PASSWORD_FILE}")

                progress_bar(30, "Menunggu VPS siap")

                get_status = None
                get_res = None
                for i in range(3):
                    get_status, get_res = manager.get_server_details(server_uuid)
                    if get_status == 200:
                        server_data = json.loads(get_res)['server']
                        ipv4, ipv6 = extract_ips(server_data)
                        if ipv4 != "—" or ipv6 != "—":
                            break
                    time.sleep(5)

                print()
                info("Memeriksa IPv6 untuk dihapus otomatis...")
                fresh = refresh_server_data(manager, server_uuid)
                if fresh:
                    server_data = fresh
                    state = server_data.get('state')
                    _, ipv6_addr = extract_ips(server_data)

                    if ipv6_addr != "—":
                        if state == 'started':
                            info("VPS menyala. Menghentikan sementara untuk hapus IPv6...")
                            manager.stop_server(server_uuid)
                            for _ in range(12):
                                time.sleep(5)
                                f = refresh_server_data(manager, server_uuid)
                                if f and f.get('state') == 'stopped':
                                    break
                            print()

                        deleted, total = auto_delete_ipv6(manager, server_uuid)
                        if total > 0:
                            success(f"IPv6 dihapus: {deleted}/{total}")
                            info("Menyalakan kembali VPS...")
                            manager.start_server(server_uuid)
                            time.sleep(3)
                        else:
                            info("Tidak ada IPv6 publik untuk dihapus.")
                    else:
                        info("VPS tidak memiliki IPv6 publik.")

                final = refresh_server_data(manager, server_uuid)
                if final:
                    server_data = final

                show_vps_detail(manager, server_data, account_name, root_password=vps_password)

                selected_os = selected_plan = selected_zone = None
            else:
                error(f"Gagal membuat VPS (Status: {status})")
                try:
                    err_data = json.loads(response)
                    print(f"     Kode: {c(err_data['error']['error_code'], C.RED)}")
                    print(f"     Pesan: {err_data['error']['error_message']}")
                except:
                    print(response)
                press_enter()

        elif cmd == "0":
            return

def choose_option_with_numbers(options, prompt, price_map=None):
    clear_screen()
    print_header(f"PILIH {prompt.upper()}")
    for idx, opt in enumerate(options, 1):
        price_str = ""
        if price_map and opt.get('plan_id') in price_map:
            price_str = f" — {c(format_price(price_map[opt['plan_id']]), C.GREEN)}"
        print(f"    {c(f'[{idx}]', C.YELLOW)} {opt['name']}{price_str}")
    print()
    print_line("─", 55, C.DIM)

    while True:
        try:
            choice = input(c(f"\n  ➤ Masukkan nomor {prompt}: ", C.BOLD + C.CYAN)).strip()
            if not choice.isdigit():
                error("Input harus berupa angka.")
                continue
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            error(f"Nomor harus antara 1-{len(options)}.")
        except KeyboardInterrupt:
            return None

# ==========================================
# DAFTAR VPS
# ==========================================
def list_vps_menu(manager, account_name):
    clear_screen()
    print_header(f"📋 DAFTAR VPS [{account_name}]")
    info("Mengambil data dari UpCloud...")

    status, response = manager.list_servers()
    if status != 200:
        error(f"Gagal mengambil daftar VPS (Status: {status})")
        print(response)
        press_enter()
        return

    servers = json.loads(response).get('servers', {}).get('server', [])
    if not servers:
        warning("Belum ada VPS yang dibuat.")
        press_enter()
        return

    print()
    print_line("─", 75, C.DIM)
    print(c(f"  {'No':<4} {'Hostname':<22} {'State':<10} {'Plan':<22} {'Zona'}", C.BOLD))
    print_line("─", 75, C.DIM)
    for idx, srv in enumerate(servers, 1):
        state = srv.get('state', 'N/A')
        icon = c("🟢", C.GREEN) if state == 'started' else c("🟡", C.YELLOW)
        host = c(srv.get('hostname', 'N/A'), C.CYAN)
        print(f"  {idx:<4} {host:<22} {icon} {state:<8} {srv.get('plan', 'N/A'):<22} {srv.get('zone', 'N/A')}")
    print_line("─", 75, C.DIM)
    print(f"\n  Total: {c(str(len(servers)), C.BOLD + C.GREEN)} VPS")

    cmd = input(c("\n  ➤ Masukkan nomor VPS untuk detail, atau '0': ", C.BOLD + C.CYAN)).strip()
    if cmd == "0":
        return

    try:
        idx = int(cmd) - 1
        if 0 <= idx < len(servers):
            server_uuid = servers[idx]['uuid']
            get_status, get_res = manager.get_server_details(server_uuid)
            if get_status == 200:
                show_vps_detail(manager, json.loads(get_res)['server'], account_name)
            else:
                error("Gagal mengambil detail VPS.")
                press_enter()
        else:
            error("Nomor tidak valid.")
            press_enter()
    except ValueError:
        error("Input tidak valid.")
        press_enter()

# ==========================================
# MENU PASSWORD
# ==========================================
def list_passwords_menu():
    while True:
        clear_screen()
        print_header("🔑 SEMUA PASSWORD TERSIMPAN")

        if not os.path.exists(PASSWORD_FILE):
            warning("Belum ada password yang tersimpan.")
            press_enter()
            return

        try:
            with open(PASSWORD_FILE, 'r') as f:
                all_data = json.load(f)
        except:
            error("Gagal membaca file password.")
            press_enter()
            return

        all_data = {k: v for k, v in all_data.items() if v}

        if not all_data:
            warning("Belum ada password yang tersimpan.")
            press_enter()
            return

        total_vps = 0
        menu_items = []

        for account_name, vps_data in all_data.items():
            print()
            print(c(f"  👤 Akun: {account_name}", C.BOLD + C.MAGENTA))
            print_line("─", 55, C.DIM)
            for i, (uuid, info_data) in enumerate(vps_data.items(), 1):
                total_vps += 1
                menu_items.append((account_name, uuid, info_data))
                idx = len(menu_items)
                print(f"  {c(f'[{idx}]', C.YELLOW)} {c(info_data.get('hostname', 'N/A'), C.CYAN + C.BOLD)}")
                print(f"       UUID     : {c(uuid, C.DIM)}")
                print(f"       Password : {c(info_data.get('password', 'N/A'), C.YELLOW + C.BOLD)}")
            print_line("─", 55, C.DIM)

        print(f"\n  Total: {c(str(total_vps), C.BOLD + C.GREEN)} password dari {c(str(len(all_data)), C.BOLD)} akun")

        print()
        print_line("─", 55, C.CYAN)
        print(c("  🗑️  HAPUS PASSWORD", C.BOLD + C.YELLOW))
        print(f"    {c('[D]', C.GREEN)} 🗑️   Hapus 1 password (pilih nomor)")
        print(f"    {c('[A]', C.GREEN)} 🧹  Hapus semua password 1 akun")
        print(f"    {c('[Z]', C.GREEN)} 💣  Hapus SEMUA password (semua akun)")
        print()
        print(f"    {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih aksi: ", C.BOLD + C.CYAN)).strip().upper()

        if cmd == "0":
            return
        elif cmd == "D":
            _delete_one_password(menu_items, all_data)
        elif cmd == "A":
            _delete_account_passwords(all_data)
        elif cmd == "Z":
            _delete_all_passwords()

def _delete_one_password(menu_items, all_data):
    if not menu_items:
        warning("Tidak ada password.")
        press_enter()
        return

    print()
    num = input(c("  ➤ Masukkan nomor VPS yang password-nya dihapus: ", C.BOLD + C.CYAN)).strip()
    if not num.isdigit():
        error("Input harus angka.")
        press_enter()
        return

    idx = int(num) - 1
    if not (0 <= idx < len(menu_items)):
        error(f"Nomor harus antara 1-{len(menu_items)}.")
        press_enter()
        return

    account_name, uuid, info_data = menu_items[idx]
    hostname = info_data.get('hostname', 'N/A')

    print()
    print_header("⚠️  KONFIRMASI HAPUS")
    print(f"  Akun     : {c(account_name, C.MAGENTA)}")
    print(f"  Hostname : {c(hostname, C.CYAN)}")
    print(f"  UUID     : {c(uuid, C.DIM)}")
    print()
    warning("Password ini akan dihapus permanen dari file lokal.")
    info("VPS di UpCloud TIDAK terhapus, hanya catatan password lokal.")

    confirm = input(c("\n  Yakin hapus? (y/n): ", C.RED + C.BOLD)).strip().lower()
    if confirm != 'y':
        info("Dibatalkan.")
        press_enter()
        return

    try:
        if account_name in all_data and uuid in all_data[account_name]:
            del all_data[account_name][uuid]
            if not all_data[account_name]:
                del all_data[account_name]
            with open(PASSWORD_FILE, 'w') as f:
                json.dump(all_data, f, indent=2)
            try: os.chmod(PASSWORD_FILE, 0o600)
            except: pass
            success(f"Password untuk '{hostname}' berhasil dihapus.")
        else:
            error("Password tidak ditemukan.")
    except Exception as e:
        error(f"Gagal menghapus: {e}")
    press_enter()

def _delete_account_passwords(all_data):
    accounts = list(all_data.keys())
    if not accounts:
        warning("Tidak ada akun.")
        press_enter()
        return

    print()
    print(c("  Pilih akun yang password-nya ingin dibersihkan:", C.BOLD))
    for i, name in enumerate(accounts, 1):
        count = len(all_data[name])
        print(f"    {c(f'[{i}]', C.YELLOW)} {name} {c(f'({count} VPS)', C.DIM)}")

    print()
    num = input(c("  ➤ Masukkan nomor akun: ", C.BOLD + C.CYAN)).strip()
    if not num.isdigit():
        error("Input harus angka.")
        press_enter()
        return

    idx = int(num) - 1
    if not (0 <= idx < len(accounts)):
        error(f"Nomor harus antara 1-{len(accounts)}.")
        press_enter()
        return

    account_name = accounts[idx]
    count = len(all_data[account_name])

    print()
    print_header("⚠️  KONFIRMASI")
    print(f"  Akun : {c(account_name, C.MAGENTA + C.BOLD)}")
    print(f"  Jumlah password: {c(str(count), C.RED + C.BOLD)}")
    print()
    warning("Semua password di akun ini akan dihapus dari file lokal.")
    info("VPS di UpCloud TIDAK terhapus.")

    confirm = input(c("\n  Ketik 'hapus' untuk konfirmasi: ", C.RED + C.BOLD)).strip().lower()
    if confirm != 'hapus':
        info("Dibatalkan.")
        press_enter()
        return

    try:
        del all_data[account_name]
        with open(PASSWORD_FILE, 'w') as f:
            json.dump(all_data, f, indent=2)
        try: os.chmod(PASSWORD_FILE, 0o600)
        except: pass
        success(f"Berhasil hapus {count} password dari akun '{account_name}'.")
    except Exception as e:
        error(f"Gagal menghapus: {e}")
    press_enter()

def _delete_all_passwords():
    print()
    print_header("💣 KONFIRMASI HAPUS SEMUA")
    warning("Ini akan menghapus SEMUA password di file lokal.")
    warning("Tindakan ini TIDAK BISA dibatalkan!")
    info("VPS di UpCloud TIDAK terhapus, hanya catatan password lokal.")

    confirm1 = input(c("\n  Ketik 'HAPUS SEMUA' untuk lanjut: ", C.RED + C.BOLD)).strip()
    if confirm1 != "HAPUS SEMUA":
        info("Dibatalkan.")
        press_enter()
        return

    confirm2 = input(c("  Konfirmasi terakhir (y/n): ", C.RED + C.BOLD)).strip().lower()
    if confirm2 != 'y':
        info("Dibatalkan.")
        press_enter()
        return

    try:
        with open(PASSWORD_FILE, 'w') as f:
            json.dump({}, f, indent=2)
        try: os.chmod(PASSWORD_FILE, 0o600)
        except: pass
        success("Semua password berhasil dihapus.")
    except Exception as e:
        error(f"Gagal menghapus: {e}")
    press_enter()

# ==========================================
# MENU STORAGE
# ==========================================
def list_storage_menu(manager, account_name):
    clear_screen()
    print_header(f"💾 DAFTAR STORAGE [{account_name}]")
    info("Mengambil data dari UpCloud...")

    status, response = manager.list_storage()
    if status != 200:
        error(f"Gagal mengambil data storage (Status: {status})")
        print(response)
        press_enter()
        return

    storages = json.loads(response).get('storages', {}).get('storage', [])
    if not storages:
        warning("Belum ada storage.")
        press_enter()
        return

    print()
    print_line("─", 75, C.DIM)
    print(c(f"  {'No':<4} {'Title':<30} {'Size':<10} {'Type':<12} {'State'}", C.BOLD))
    print_line("─", 75, C.DIM)
    for idx, st in enumerate(storages, 1):
        title = c(str(st.get('title', 'N/A'))[:28], C.CYAN)
        size = f"{st.get('size', 0)} GB"
        stype = st.get('type', 'N/A')
        state = st.get('state', 'N/A')
        print(f"  {idx:<4} {title:<30} {size:<10} {stype:<12} {state}")
    print_line("─", 75, C.DIM)
    print(f"\n  Total: {c(str(len(storages)), C.BOLD + C.GREEN)} storage")
    press_enter()

# ==========================================
# MENU IP ADDRESS
# ==========================================
def list_ip_menu(manager, account_name):
    clear_screen()
    print_header(f"🌍 DAFTAR IP ADDRESS [{account_name}]")
    info("Mengambil data dari UpCloud...")

    status, response = manager.list_ip_addresses()
    if status != 200:
        error(f"Gagal mengambil data IP (Status: {status})")
        print(response)
        press_enter()
        return

    ips = json.loads(response).get('ip_addresses', {}).get('ip_address', [])
    if not ips:
        warning("Belum ada IP address.")
        press_enter()
        return

    print()
    print_line("─", 75, C.DIM)
    print(c(f"  {'No':<4} {'IP Address':<40} {'Access':<10} {'Family':<8}", C.BOLD))
    print_line("─", 75, C.DIM)
    for idx, ip in enumerate(ips, 1):
        addr = c(ip.get('address', 'N/A'), C.CYAN)
        access = ip.get('access', 'N/A')
        family = ip.get('family', 'N/A')
        fam_color = C.GREEN if family == 'IPv4' else C.YELLOW
        print(f"  {idx:<4} {addr:<40} {access:<10} {c(family, fam_color):<8}")
    print_line("─", 75, C.DIM)
    print(f"\n  Total: {c(str(len(ips)), C.BOLD + C.GREEN)} IP")
    press_enter()

# ==========================================
# MENU INFO AKUN
# ==========================================
def account_info_menu(manager, account_name):
    clear_screen()
    print_header(f"👤 INFO AKUN [{account_name}]")
    info("Mengambil data dari UpCloud...")

    status, response = manager.get_account_info()
    if status != 200:
        error(f"Gagal mengambil info akun (Status: {status})")
        print(response)
        press_enter()
        return

    try:
        acc = json.loads(response)['account']
        print()
        print(f"  {'Nama Akun':<20}: {c(account_name, C.MAGENTA + C.BOLD)}")
        print(f"  {'Username':<20}: {c(acc.get('username', 'N/A'), C.CYAN)}")
        print(f"  {'Credits':<20}: {c(str(acc.get('credits', 0)), C.GREEN + C.BOLD)}")
        print(f"  {'Email':<20}: {acc.get('email', 'N/A')}")
        print(f"  {'Country':<20}: {acc.get('country', 'N/A')}")
        print(f"  {'Currency':<20}: {acc.get('currency', 'N/A')}")
        print(f"  {'Language':<20}: {acc.get('language', 'N/A')}")
        print(f"  {'Timezone':<20}: {acc.get('timezone', 'N/A')}")
    except Exception as e:
        error(f"Gagal parsing data: {e}")
        print(response)
    press_enter()

# ==========================================
# FIREWALL MENU - DENGAN DETEKSI TRIAL
# ==========================================
def _apply_firewall_rules(manager, server_uuid, rules, label="default"):
    """Apply list aturan firewall dengan deteksi TRIAL_FIREWALL."""
    print()
    info(f"Mengaktifkan firewall ({label})...")
    info(f"Total aturan: {len(rules)}")
    print()
    ok = 0
    fail = 0
    trial_error = False
    
    for i, r in enumerate(rules, 1):
        if trial_error:
            break
        
        s, res_create = manager.create_firewall_rule(server_uuid, **r)
        if s == 201:
            ok += 1
            sys.stdout.write(f"\r  Progress: {i}/{len(rules)} (OK: {ok})    ")
            sys.stdout.flush()
        else:
            fail += 1
            # Cek apakah error TRIAL_FIREWALL
            try:
                err_data = json.loads(res_create)
                err_code = err_data.get('error', {}).get('error_code', '')
                err_msg = err_data.get('error', {}).get('error_message', '')
                if err_code == 'TRIAL_FIREWALL':
                    trial_error = True
                    print()
                    print()
                    error(f"AKUN TRIAL! Limit firewall tercapai di aturan ke-{i}.")
                    print(c(f"  Pesan: {err_msg}", C.DIM))
                    warning("UpCloud membatasi jumlah aturan firewall untuk akun trial.")
                    info("Solusi:")
                    print(c("    1. Upgrade akun di https://hub.upcloud.com", C.YELLOW))
                    print(c("    2. Atau pakai preset 'TRIAL MODE' (10 aturan penting)", C.YELLOW))
                    break
            except:
                pass
            
            print()
            error(f"Gagal '{r.get('comment', '?')}': {res_create[:150]}")
    
    print()
    print()
    if trial_error:
        warning(f"DIHENTIKAN karena limit trial. Berhasil: {ok}, Gagal: {fail}")
        info(f"Firewall tetap aktif dengan {ok} aturan yang berhasil.")
    else:
        success(f"Berhasil membuat {ok}/{len(rules)} aturan.")
        if fail > 0:
            warning(f"Gagal: {fail} aturan.")
    warning("Perubahan aktif dalam 1-2 menit.")
    press_enter()

def check_and_activate_firewall(manager, server_uuid, server_hostname=""):
    clear_screen()
    print_header(f"🔥 FIREWALL - {server_hostname or server_uuid[:8]}")
    
    info("Mengecek status firewall...")
    status, res = manager.list_firewall_rules(server_uuid)
    
    if status != 200:
        error(f"Gagal mengecek firewall: {res}")
        press_enter()
        return
    
    try:
        rules = json.loads(res).get('firewall_rules', {}).get('firewall_rule', [])
    except:
        rules = []
    
    if not rules:
        print()
        print_line("─", 55, C.YELLOW)
        print(c("  🔥 Firewall: BELUM AKTIF", C.BOLD + C.YELLOW))
        print_line("─", 55, C.YELLOW)
        print(c("  Server terbuka semua port. Pilih preset:", C.WHITE))
        print_line("─", 55, C.YELLOW)
        print()
        print(f"  {c('[1]', C.GREEN)} ✅ Aktifkan Default (SSH/HTTP/HTTPS) — 3 aturan")
        print(f"  {c('[2]', C.GREEN)} 🌐 Aktifkan Web Server (+ Ping) — 4 aturan")
        print(f"  {c('[3]', C.GREEN)} 🎯 Aktifkan TRIAL MODE — 10 aturan {c('← untuk akun trial', C.YELLOW)}")
        print(f"  {c('[4]', C.GREEN)} 🛡️  Aktifkan Firewall LENGKAP — 60+ aturan {c('(butuh upgrade)', C.DIM)}")
        print(f"  {c('[0]', C.RED)} ⬅️  Kembali")
        print()
        
        cmd = input(c("  ➤ Pilih: ", C.BOLD + C.CYAN)).strip()
        
        if cmd == "1":
            _apply_firewall_rules(manager, server_uuid, get_firewall_preset_default(), "Default")
            show_firewall_menu(manager, server_uuid, server_hostname)
        elif cmd == "2":
            _apply_firewall_rules(manager, server_uuid, get_firewall_preset_web(), "Web Server")
            show_firewall_menu(manager, server_uuid, server_hostname)
        elif cmd == "3":
            _apply_firewall_rules(manager, server_uuid, get_firewall_preset_trial(), "TRIAL MODE")
            show_firewall_menu(manager, server_uuid, server_hostname)
        elif cmd == "4":
            warning("Preset ini butuh akun UPGRADE. Kalau trial, akan berhenti otomatis.")
            confirm = input(c("  Lanjut? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                _apply_firewall_rules(manager, server_uuid, get_firewall_preset_mega(), "LENGKAP 60+ Aturan")
                show_firewall_menu(manager, server_uuid, server_hostname)
        else:
            return
    else:
        show_firewall_menu(manager, server_uuid, server_hostname)

def show_firewall_menu(manager, server_uuid, server_hostname=""):
    while True:
        clear_screen()
        print_header(f"🔥 FIREWALL - {server_hostname or server_uuid[:8]}")
        print(f"  Server UUID: {c(server_uuid, C.DIM)}")
        print()
        warning("Perubahan firewall memerlukan 1-2 menit untuk aktif")
        print()
        print_line("─", 55, C.CYAN)
        print(c("  📋 ATURAN", C.BOLD + C.YELLOW))
        print(f"  {c('[1]', C.GREEN)} 📋  Lihat Semua Aturan")
        print(f"  {c('[2]', C.GREEN)} ➕  Tambah Aturan Baru")
        print(f"  {c('[3]', C.GREEN)} 🗑️   Hapus Aturan (1 per 1)")
        print()
        print(c("  ⚡ PRESET CEPAT", C.BOLD + C.YELLOW))
        print(f"  {c('[4]', C.GREEN)} ⚡  Preset Web/SSH/Database")
        print(f"  {c('[5]', C.GREEN)} 🎯  Preset TRIAL MODE (10 aturan)")
        print(f"  {c('[6]', C.GREEN)} 🛡️   Preset LENGKAP (60+ aturan) {c('(butuh upgrade)', C.DIM)}")
        print()
        print(c("  🧹 BERSIHKAN", C.BOLD + C.YELLOW))
        print(f"  {c('[8]', C.YELLOW)} 🔄  Reset ke Default (SSH/HTTP/HTTPS)")
        print(f"  {c('[9]', C.RED)} 💣  Hapus SEMUA Aturan")
        print()
        print(f"  {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih aksi: ", C.BOLD + C.CYAN)).strip()

        if cmd == "1":
            _view_firewall_rules(manager, server_uuid)
        elif cmd == "2":
            _add_firewall_rule(manager, server_uuid)
        elif cmd == "3":
            _delete_firewall_rule(manager, server_uuid)
        elif cmd == "4":
            _quick_firewall_setup(manager, server_uuid)
        elif cmd == "5":
            print()
            info("Preset khusus akun TRIAL. Hanya 10 aturan penting:")
            print(c("    • SSH, HTTP, HTTPS, DNS, Ping (IPv4 + IPv6)", C.CYAN))
            confirm = input(c("\n  Lanjut? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                _apply_firewall_rules(manager, server_uuid, get_firewall_preset_trial(), "TRIAL MODE")
        elif cmd == "6":
            print()
            warning("Preset ini butuh ~60 aturan. Akun TRIAL akan gagal di tengah.")
            warning("Kalau akun Anda trial, sebaiknya pakai [5] TRIAL MODE saja.")
            confirm = input(c("  ⚠️  Lanjut pasang firewall LENGKAP? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                _apply_firewall_rules(manager, server_uuid, get_firewall_preset_mega(), "LENGKAP 60+ Aturan")
        elif cmd == "8":
            _reset_firewall_to_default(manager, server_uuid)
        elif cmd == "9":
            _delete_all_firewall_rules(manager, server_uuid)
        elif cmd == "0":
            return

def _view_firewall_rules(manager, uuid):
    clear_screen()
    print_header("📋 DAFTAR ATURAN FIREWALL")
    info("Mengambil data...")

    status, res = manager.list_firewall_rules(uuid)
    if status != 200:
        error(f"Gagal: {res}")
        press_enter()
        return

    try:
        rules = json.loads(res).get('firewall_rules', {}).get('firewall_rule', [])
    except:
        warning("Tidak dapat parsing response.")
        press_enter()
        return

    if not rules:
        warning("Belum ada aturan firewall.")
        press_enter()
        return

    print()
    print_line("─", 100, C.DIM)
    print(c(f"  {'Pos':<5} {'Dir':<5} {'Action':<8} {'Proto':<6} {'Family':<6} "
            f"{'Port Range':<15} {'Source':<16} {'Comment'}", C.BOLD))
    print_line("─", 100, C.DIM)
    for r in rules:
        pos = str(r.get('position', '-'))
        direction = r.get('direction', '-')
        action = r.get('action', '-')
        proto = r.get('protocol', '-')
        family = r.get('family', '-')
        dst_start = r.get('destination_port_start', '')
        dst_end = r.get('destination_port_end', '')
        port = f"{dst_start}-{dst_end}" if dst_start else "-"
        src = r.get('source_address_start', '')
        if src:
            src_end = r.get('source_address_end', '')
            src = f"{src}" if src == src_end else f"{src}-{src_end}"
        else:
            src = "any"
        comment = str(r.get('comment', ''))[:20]
        action_col = C.GREEN if action == 'accept' else C.RED
        print(f"  {pos:<5} {direction:<5} {c(action, action_col):<8} {proto:<6} {family:<6} "
              f"{port:<15} {src:<16} {comment}")
    print_line("─", 100, C.DIM)
    print(f"\n  Total: {c(str(len(rules)), C.BOLD + C.GREEN)} aturan")
    press_enter()

def _add_firewall_rule(manager, uuid):
    clear_screen()
    print_header("➕ TAMBAH ATURAN FIREWALL")

    direction = input(c("  Direction (in/out) [in]: ", C.CYAN)).strip() or "in"
    action = input(c("  Action (accept/drop) [accept]: ", C.CYAN)).strip() or "accept"
    family = input(c("  Family (IPv4/IPv6) [IPv4]: ", C.CYAN)).strip() or "IPv4"
    protocol = input(c("  Protocol (tcp/udp/icmp, kosongkan jika tidak): ", C.CYAN)).strip() or None

    dst_port_start = None
    dst_port_end = None
    if protocol in ['tcp', 'udp']:
        port_in = input(c("  Port tujuan (contoh: 22, kosongkan jika tidak): ", C.CYAN)).strip()
        if port_in:
            dst_port_start = port_in
            dst_port_end = port_in

    comment = input(c("  Comment (opsional): ", C.CYAN)).strip() or None

    print()
    info("Mengirim request...")
    status, res = manager.create_firewall_rule(
        uuid, direction=direction, action=action, family=family,
        protocol=protocol, dst_port_start=dst_port_start,
        dst_port_end=dst_port_end, comment=comment
    )

    if status == 201:
        success("Aturan firewall berhasil dibuat!")
        warning("Perubahan aktif dalam 1-2 menit.")
    else:
        error(f"Gagal: {res}")
        try:
            err = json.loads(res)
            if err.get('error', {}).get('error_code') == 'TRIAL_FIREWALL':
                warning("Akun Anda TRIAL. Sudah mencapai limit aturan firewall.")
                info("Upgrade akun UpCloud untuk menambah aturan.")
        except:
            pass
    press_enter()

def _delete_firewall_rule(manager, uuid):
    clear_screen()
    print_header("🗑️  HAPUS ATURAN FIREWALL")

    pos = input(c("  Masukkan posisi aturan yang dihapus: ", C.CYAN)).strip()
    if not pos.isdigit():
        error("Input harus angka.")
        press_enter()
        return

    confirm = input(c(f"  Yakin hapus aturan posisi {pos}? (y/n): ", C.YELLOW)).strip().lower()
    if confirm != 'y':
        return

    status, res = manager.delete_firewall_rule(uuid, int(pos))
    if status in [200, 204]:
        success(f"Aturan posisi {pos} berhasil dihapus.")
        warning("Perubahan aktif dalam 1-2 menit.")
    else:
        error(f"Gagal: {res}")
    press_enter()

def _quick_firewall_setup(manager, uuid):
    clear_screen()
    print_header("⚡ PRESET FIREWALL CEPAT")

    print(c("  Pilih preset:", C.YELLOW))
    print()
    print(f"  {c('[1]', C.GREEN)} 🌐 Web Server (SSH + HTTP + HTTPS + Ping)")
    print(f"  {c('[2]', C.GREEN)} 🔒 SSH Only (paling aman)")
    print(f"  {c('[3]', C.GREEN)} 🗄️  Web + Database (MySQL/PostgreSQL)")
    print(f"  {c('[0]', C.RED)} ⬅️  Kembali")
    print()

    choice = input(c("  ➤ Pilih: ", C.BOLD + C.CYAN)).strip()

    if choice == "1":
        rules = get_firewall_preset_web()
    elif choice == "2":
        rules = get_firewall_preset_ssh_only()
    elif choice == "3":
        rules = get_firewall_preset_web_db()
    else:
        return

    print()
    info(f"Akan membuat {len(rules)} aturan:")
    for i, r in enumerate(rules, 1):
        port = r.get('dst_port_start', '-')
        print(f"    {i}. {r['comment']} ({r.get('protocol', '-')}/{port})")

    confirm = input(c("\n  Konfirmasi? (y/n): ", C.YELLOW)).strip().lower()
    if confirm != 'y':
        return

    _apply_firewall_rules(manager, uuid, rules, "preset cepat")

def _delete_all_firewall_rules(manager, server_uuid):
    clear_screen()
    print_header("💣 HAPUS SEMUA ATURAN FIREWALL")
    
    info("Mengambil daftar aturan...")
    status, res = manager.list_firewall_rules(server_uuid)
    if status != 200:
        error(f"Gagal: {res}")
        press_enter()
        return
    
    try:
        rules = json.loads(res).get('firewall_rules', {}).get('firewall_rule', [])
    except:
        rules = []
    
    if not rules:
        warning("Tidak ada aturan firewall.")
        press_enter()
        return
    
    print(f"\n  Total aturan: {c(str(len(rules)), C.BOLD + C.RED)}")
    warning("Semua aturan akan dihapus. VPS akan terbuka semua port!")
    print()
    confirm = input(c("  Ketik 'HAPUS' untuk konfirmasi: ", C.RED + C.BOLD)).strip()
    if confirm != "HAPUS":
        info("Dibatalkan.")
        press_enter()
        return
    
    positions = sorted([int(r.get('position', 0)) for r in rules], reverse=True)
    ok = 0
    fail = 0
    print()
    info(f"Menghapus {len(positions)} aturan...")
    for pos in positions:
        s, r = manager.delete_firewall_rule(server_uuid, pos)
        if s in [200, 204]:
            ok += 1
            print(c(f"  ✓ Posisi {pos} dihapus", C.GREEN))
        else:
            fail += 1
            print(c(f"  ✗ Posisi {pos} gagal: {r[:80]}", C.RED))
    
    print()
    success(f"Selesai! Berhasil: {ok}, Gagal: {fail}")
    warning("Tunggu 1-2 menit, lalu masuk menu Firewall lagi.")
    press_enter()

def _reset_firewall_to_default(manager, server_uuid):
    clear_screen()
    print_header("🔄 RESET FIREWALL KE DEFAULT")
    
    info("Mengambil daftar aturan saat ini...")
    status, res = manager.list_firewall_rules(server_uuid)
    if status != 200:
        error(f"Gagal: {res}")
        press_enter()
        return
    
    try:
        rules = json.loads(res).get('firewall_rules', {}).get('firewall_rule', [])
    except:
        rules = []
    
    print(f"\n  Aturan saat ini: {c(str(len(rules)), C.BOLD + C.YELLOW)}")
    warning("Semua aturan akan DIHAPUS dan diganti dengan default:")
    print(c("    • SSH (22)", C.GREEN))
    print(c("    • HTTP (80)", C.GREEN))
    print(c("    • HTTPS (443)", C.GREEN))
    print()
    confirm = input(c("  Ketik 'RESET' untuk konfirmasi: ", C.RED + C.BOLD)).strip()
    if confirm != "RESET":
        info("Dibatalkan.")
        press_enter()
        return
    
    if rules:
        positions = sorted([int(r.get('position', 0)) for r in rules], reverse=True)
        print()
        info(f"Menghapus {len(positions)} aturan lama...")
        for pos in positions:
            s, r = manager.delete_firewall_rule(server_uuid, pos)
            if s in [200, 204]:
                print(c(f"  ✓ Posisi {pos} dihapus", C.GREEN))
            else:
                print(c(f"  ✗ Posisi {pos} gagal", C.RED))
        time.sleep(2)
    
    print()
    info("Memasang aturan default baru...")
    rules_default = get_firewall_preset_default()
    ok = 0
    for r in rules_default:
        s, res_create = manager.create_firewall_rule(server_uuid, **r)
        if s == 201:
            ok += 1
        else:
            error(f"Gagal '{r['comment']}': {res_create}")
    
    print()
    success(f"Reset selesai! {ok}/{len(rules_default)} aturan default terpasang.")
    warning("Perubahan aktif dalam 1-2 menit.")
    press_enter()

# ==========================================
# MENU MANAJEMEN IP
# ==========================================
def show_ip_management_menu(manager, server_uuid, server_data):
    while True:
        fresh = refresh_server_data(manager, server_uuid)
        if fresh:
            server_data = fresh

        clear_screen()
        hostname = server_data.get('hostname', server_uuid[:8])
        print_header(f"🌐 IP MANAGEMENT - {hostname}")
        print(f"  Server UUID: {c(server_uuid, C.DIM)}")
        print()

        ipv4, ipv6 = extract_ips(server_data)
        print(c("  📋 IP Saat Ini:", C.BOLD))
        print(f"     IPv4 : {c(ipv4, C.GREEN + C.BOLD)}")
        print(f"     IPv6 : {c(ipv6, C.YELLOW)}")
        print()
        print(f"  💻 State: {server_data.get('state', 'N/A')}")
        print()

        if server_data.get('state') != 'stopped':
            warning("Server harus 'stopped' untuk ubah IP!")
            print()

        print_line("─", 55, C.CYAN)
        print(f"  {c('[1]', C.GREEN)} 🔄  Refresh Info IP")
        print(f"  {c('[2]', C.GREEN)} ➕  Assign IPv4 Baru")
        print(f"  {c('[3]', C.GREEN)} ➕  Assign IPv6 Baru")
        print(f"  {c('[4]', C.GREEN)} 🗑️   Hapus IPv6")
        print(f"  {c('[5]', C.GREEN)} 📋  Tampilkan Detail Semua IP")
        print(f"  {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih aksi: ", C.BOLD + C.CYAN)).strip()

        if cmd == "1":
            fresh = refresh_server_data(manager, server_uuid)
            if fresh:
                server_data = fresh
                success("Info IP diperbarui.")
            else:
                error("Gagal refresh data.")
            time.sleep(0.8)

        elif cmd == "2":
            fresh = refresh_server_data(manager, server_uuid)
            if not fresh:
                error("Gagal mengambil data server.")
                press_enter()
                continue
            server_data = fresh
            current_state = server_data.get('state')

            if current_state != 'stopped':
                error(f"Server harus 'stopped' (sekarang: {current_state})")
                press_enter()
                continue

            confirm = input(c("  Assign IPv4 publik baru? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                info("Mengirim request...")
                status, res = manager.assign_ipv4(server_uuid)
                if status in [200, 201, 202]:
                    success("IPv4 baru berhasil di-assign!")
                    info("Tunggu 1-2 menit lalu refresh.")
                else:
                    error(f"Gagal: {res}")
            press_enter()

        elif cmd == "3":
            fresh = refresh_server_data(manager, server_uuid)
            if not fresh:
                error("Gagal mengambil data server.")
                press_enter()
                continue
            server_data = fresh
            current_state = server_data.get('state')

            if current_state != 'stopped':
                error(f"Server harus 'stopped' (sekarang: {current_state})")
                info("Silakan stop server dulu di menu sebelumnya.")
                press_enter()
                continue

            ipv4, ipv6 = extract_ips(server_data)
            if ipv6 != "—":
                warning(f"Server sudah memiliki IPv6 ({ipv6}).")
                confirm = input(c("  Tetap assign IPv6 baru? (y/n): ", C.YELLOW)).strip().lower()
                if confirm != 'y':
                    press_enter()
                    continue

            confirm = input(c("  Assign IPv6 publik baru? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                info("Mengirim request ke UpCloud...")
                status, res = manager.assign_ipv6(server_uuid)
                if status in [200, 201, 202]:
                    success("IPv6 baru berhasil di-assign!")
                    info("Tunggu 1-2 menit lalu refresh [1].")
                else:
                    error(f"Gagal: {res}")
            press_enter()

        elif cmd == "4":
            fresh = refresh_server_data(manager, server_uuid)
            if not fresh:
                error("Gagal mengambil data server.")
                press_enter()
                continue
            server_data = fresh
            current_state = server_data.get('state')

            if current_state != 'stopped':
                error(f"Server harus 'stopped' (sekarang: {current_state})")
                press_enter()
                continue

            ipv4, ipv6 = extract_ips(server_data)
            if ipv6 == "—":
                warning("Tidak ada IPv6 yang terpasang.")
                press_enter()
                continue

            info("Mencari IPv6 address...")
            s, r = manager.get_server_ip_addresses(server_uuid)
            if s != 200:
                error(f"Gagal mengambil daftar IP: {r}")
                press_enter()
                continue

            try:
                ips = json.loads(r).get('ip_addresses', {}).get('ip_address', [])
                ipv6_uuid = None
                for ip in ips:
                    if ip.get('family') == 'IPv6':
                        ipv6_uuid = ip.get('uuid', ip.get('address'))
                        break

                if not ipv6_uuid:
                    warning("IPv6 tidak ditemukan di server.")
                    press_enter()
                    continue

                confirm = input(c(f"  ⚠️  Yakin hapus IPv6 {ipv6}? (y/n): ", C.RED)).strip().lower()
                if confirm == 'y':
                    info("Menghapus IPv6...")
                    ds, dr = manager.delete_ip_address(ipv6_uuid)
                    if ds in [200, 204]:
                        success("IPv6 berhasil dihapus!")
                        info("Tunggu 1-2 menit lalu refresh.")
                    else:
                        error(f"Gagal: {dr}")
                press_enter()
            except Exception as e:
                error(f"Error: {e}")
                press_enter()

        elif cmd == "5":
            clear_screen()
            print_header("📋 DETAIL SEMUA IP")
            s, r = manager.get_server_ip_addresses(server_uuid)
            if s == 200:
                try:
                    ips = json.loads(r).get('ip_addresses', {}).get('ip_address', [])
                    if not ips:
                        warning("Tidak ada IP address.")
                    else:
                        for idx, ip in enumerate(ips, 1):
                            fam = ip.get('family', '—')
                            fam_color = C.GREEN if fam == 'IPv4' else C.YELLOW
                            print(f"\n  {c(str(idx) + '.', C.BOLD)} {c(ip.get('address', '—'), C.CYAN + C.BOLD)}")
                            print(f"     UUID      : {c(ip.get('uuid', '—'), C.DIM)}")
                            print(f"     Family    : {c(fam, fam_color)}")
                            print(f"     Access    : {ip.get('access', '—')}")
                            print(f"     PTR Record: {ip.get('ptr_record', '—')}")
                except Exception as e:
                    error(f"Gagal parsing: {e}")
                    print(r)
            else:
                error(f"Gagal: {r}")
            press_enter()

        elif cmd == "0":
            return

# ==========================================
# DETAIL VPS
# ==========================================
def show_vps_detail(manager, server_data, account_name, root_password=None):
    uuid = server_data.get('uuid')
    if root_password:
        save_password(account_name, uuid, server_data.get('hostname', 'N/A'), root_password)

    while True:
        fresh = refresh_server_data(manager, uuid)
        if fresh:
            server_data = fresh

        clear_screen()
        print_header(f"📺 DETAIL VPS [{account_name}]")

        state = server_data.get('state', 'unknown')
        if state == "started":
            indicator = c("🟢", C.GREEN)
        elif state == "stopped":
            indicator = c("🔴", C.RED)
        else:
            indicator = c("🟡", C.YELLOW)

        ipv4, ipv6 = extract_ips(server_data)

        fw_status, fw_res = manager.list_firewall_rules(uuid)
        if fw_status == 200:
            try:
                fw_rules = json.loads(fw_res).get('firewall_rules', {}).get('firewall_rule', [])
                if fw_rules:
                    fw_indicator = c(f"🔥 Aktif ({len(fw_rules)} aturan)", C.GREEN + C.BOLD)
                else:
                    fw_indicator = c("⚠️  Nonaktif", C.RED + C.BOLD)
            except:
                fw_indicator = c("❓ Unknown", C.DIM)
        else:
            fw_indicator = c("❓ Unknown", C.DIM)

        print()
        print(f"  {indicator} {c(server_data.get('hostname', 'N/A'), C.BOLD + C.CYAN)}")
        print(f"  👤 User   : {c('root', C.GREEN + C.BOLD)}")
        print(f"  🌐 IPv4   : {c(ipv4, C.GREEN + C.BOLD)}")
        print(f"  🌐 IPv6   : {c(ipv6, C.DIM)}")
        print(f"  💻 State  : {state}")
        print(f"  🔥 Firewall: {fw_indicator}")
        print(f"  📦 Plan   : {server_data.get('plan', 'N/A')}")
        print(f"  📍 Zona   : {server_data.get('zone', 'N/A')}")
        print(f"  🆔 UUID   : {c(uuid, C.DIM)}")
        print()

        pwd_data = get_password(account_name, uuid)
        if pwd_data:
            print(f"  🔑 Password : {c(pwd_data['password'], C.YELLOW + C.BOLD)}")

        print()
        print_line("─", 55, C.CYAN)
        print(c("  ⚡ AKSI CEPAT", C.BOLD + C.YELLOW))
        print(f"    {c('[1]', C.GREEN)} 📋  Salin / Lihat IPv4")
        print(f"    {c('[2]', C.GREEN)} 🔑  Lihat Password Root")
        print(f"    {c('[3]', C.GREEN)} 🖥️   Buka Konsol (VNC)")
        print(f"    {c('[11]', C.GREEN)} 🌐  Manajemen IP (Assign IPv4 / IPv6 / Hapus IPv6)")
        print()
        print(c("  🔌 POWER", C.BOLD + C.YELLOW))
        print(f"    {c('[4]', C.GREEN)} ▶️   Start Server")
        print(f"    {c('[5]', C.GREEN)} ⬛  Stop Server")
        print(f"    {c('[6]', C.GREEN)} 🔄  Restart Server")
        print()
        print(c("  🛠️  MANAJEMEN", C.BOLD + C.YELLOW))
        print(f"    {c('[7]', C.GREEN)} ✏️   Rename VPS")
        print(f"    {c('[8]', C.GREEN)} 🔧  Resize (Ganti Spek)")
        print(f"    {c('[9]', C.GREEN)} 📊  Lihat Statistik")
        print(f"    {c('[10]', C.GREEN)} 🔥  Firewall Management")
        print()
        print(c("  ⚠️  ZONA BAHAYA", C.BOLD + C.RED))
        print(f"    {c('[99]', C.RED)} 🗑️   Hapus VPS (permanen)")
        print()
        print(f"    {c('[0]', C.RED)} ⬅️   Kembali")
        print_line("─", 55, C.CYAN)

        cmd = input(c("\n  ➤ Pilih aksi: ", C.BOLD + C.CYAN)).strip()

        if cmd == "1":
            print()
            success(f"IPv4: {c(ipv4, C.BOLD + C.GREEN)}")
            print(f"  IPv6: {c(ipv6, C.DIM)}")
            press_enter()

        elif cmd == "2":
            pwd_data = get_password(account_name, uuid)
            print()
            print_header("🔑 PASSWORD ROOT")
            if pwd_data:
                print(f"  Hostname : {pwd_data['hostname']}")
                print(f"  Password : {c(pwd_data['password'], C.YELLOW + C.BOLD)}")
            else:
                warning("Password tidak ditemukan di penyimpanan lokal.")
            press_enter()

        elif cmd == "3":
            print()
            info("Mengambil detail koneksi VNC...")
            status, res = manager.get_console(uuid)
            if status == 200:
                try:
                    data = json.loads(res)
                    remote_access = data.get('remote_access_details', data)

                    host = remote_access.get('host')
                    port = remote_access.get('port')
                    password = remote_access.get('password')
                    vnc_status = remote_access.get('vnc', 'unknown')

                    if host and port and password:
                        print()
                        print_header("🖥️  KONEKSI VNC")
                        print(f"  🖥️  Host     : {c(host, C.GREEN + C.BOLD)}")
                        print(f"  🔌 Port     : {c(str(port), C.GREEN + C.BOLD)}")
                        print(f"  🔒 Password : {c(password, C.YELLOW + C.BOLD)}")
                        print()
                        print_line("─", 55, C.DIM)
                        print(c("  📖 Cara Konek:", C.BOLD))
                        print(f"    1. Install VNC Viewer (RealVNC / TigerVNC / bVNC)")
                        print(f"    2. Buat koneksi baru ke:")
                        print(f"       {c(f'{host}:{port}', C.CYAN + C.BOLD)}")
                        print(f"    3. Masukkan password: {c(password, C.YELLOW + C.BOLD)}")
                        print(f"    4. Login: root / password root Anda")
                        print_line("─", 55, C.DIM)
                    elif vnc_status == 'off':
                        warning("VNC tidak aktif di server ini.")
                        info("Aktifkan VNC melalui Control Panel UpCloud:")
                        print(c("    Server → Console → toggle VNC ke ON", C.DIM))
                    else:
                        warning("Data VNC tidak lengkap dari API.")
                        print(c(f"  Response: {json.dumps(data, indent=2)}", C.DIM))
                except Exception as e:
                    error(f"Gagal parsing: {e}")
                    print(res)
            else:
                error(f"Gagal mengambil detail VNC (Status: {status})")
                print(c(res, C.DIM))
            press_enter()

        elif cmd == "4":
            current_state = server_data.get('state')
            if current_state == 'started':
                warning(f"VPS sudah dalam state '{current_state}'. Tidak perlu start.")
                press_enter()
                continue
            if current_state in ['maintenance', 'starting', 'stopping']:
                warning(f"VPS sedang dalam state '{current_state}'. Tunggu sebentar.")
                press_enter()
                continue

            print()
            info("Menyalakan VPS...")
            status, res = manager.start_server(uuid)
            if status in [200, 202]:
                success("VPS berhasil di-start.")
            else:
                error(f"Gagal: {res}")
            press_enter()

        elif cmd == "5":
            current_state = server_data.get('state')
            if current_state == 'stopped':
                warning(f"VPS sudah dalam state '{current_state}'. Tidak perlu stop.")
                press_enter()
                continue
            if current_state in ['maintenance', 'starting', 'stopping']:
                warning(f"VPS sedang dalam state '{current_state}'. Tunggu sebentar.")
                press_enter()
                continue

            confirm = input(c("  Yakin stop VPS? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                print()
                info("Menghentikan VPS...")
                status, res = manager.stop_server(uuid)
                if status in [200, 202]:
                    success("VPS berhasil di-stop.")
                else:
                    error(f"Gagal: {res}")
                press_enter()

        elif cmd == "6":
            current_state = server_data.get('state')
            if current_state != 'started':
                warning(f"VPS harus 'started' untuk restart (sekarang: {current_state}).")
                press_enter()
                continue

            confirm = input(c("  Yakin restart VPS? (y/n): ", C.YELLOW)).strip().lower()
            if confirm == 'y':
                print()
                info("Merestart VPS...")
                status, res = manager.restart_server(uuid)
                if status in [200, 202]:
                    success("VPS berhasil di-restart.")
                else:
                    error(f"Gagal: {res}")
                press_enter()

        elif cmd == "7":
            print()
            print_header("✏️  RENAME VPS")
            new_host = input(c("  Hostname baru: ", C.CYAN)).strip()
            if new_host:
                status, res = manager.rename_server(uuid, new_host)
                if status in [200, 202]:
                    success(f"VPS berhasil di-rename ke '{new_host}'.")
                else:
                    error(f"Gagal: {res}")
            press_enter()

        elif cmd == "8":
            print()
            print_header("🔧 RESIZE VPS")
            print(c("  Pilih plan baru:", C.YELLOW))
            for plan in PLAN_OPTIONS:
                print(f"    {plan['id']}. {plan['name']}")
            new_plan_id = input(c("\n  Nomor plan: ", C.CYAN)).strip()
            new_plan = next((p for p in PLAN_OPTIONS if p['id'] == new_plan_id), None)
            if new_plan:
                confirm = input(c(f"  Resize ke {new_plan['name']}? (y/n): ", C.YELLOW)).strip().lower()
                if confirm == 'y':
                    info("Mengirim request resize...")
                    status, res = manager.resize_server(uuid, new_plan['plan_id'])
                    if status in [200, 202]:
                        success(f"VPS berhasil di-resize ke {new_plan['name']}.")
                        info("Tunggu beberapa detik, lalu refresh.")
                    else:
                        error(f"Gagal: {res}")
                        try:
                            err = json.loads(res)
                            print(f"     Kode: {err['error']['error_code']}")
                            print(f"     Pesan: {err['error']['error_message']}")
                        except:
                            pass
            press_enter()

        elif cmd == "9":
            while True:
                clear_screen()
                print_header("📊 STATISTIK VPS")
                print(c("  Pilih jenis statistik:", C.YELLOW))
                print(f"    {c('[1]', C.GREEN)} CPU")
                print(f"    {c('[2]', C.GREEN)} Disk (bytes)")
                print(f"    {c('[3]', C.GREEN)} Disk (iops)")
                print(f"    {c('[4]', C.GREEN)} Network (bytes)")
                print(f"    {c('[5]', C.GREEN)} Network (packets)")
                print(f"    {c('[0]', C.RED)} Kembali")

                stat_choice = input(c("\n  ➤ Pilih: ", C.BOLD + C.CYAN)).strip()

                if stat_choice == "0":
                    break

                print()
                info("Mengambil data statistik...")

                if stat_choice == "1":
                    status, res = manager.get_stats_cpu(uuid)
                elif stat_choice == "2":
                    status, res = manager.get_stats_disk(uuid, "bytes")
                elif stat_choice == "3":
                    status, res = manager.get_stats_disk(uuid, "iops")
                elif stat_choice == "4":
                    status, res = manager.get_stats_network(uuid, "bytes")
                elif stat_choice == "5":
                    status, res = manager.get_stats_network(uuid, "packets")
                else:
                    continue

                if status == 200:
                    try:
                        stats = json.loads(res)
                        print(c(json.dumps(stats, indent=2), C.CYAN))
                    except:
                        print(res)
                else:
                    error(f"Gagal: {res}")
                press_enter()

        elif cmd == "10":
            fresh = refresh_server_data(manager, uuid)
            if fresh:
                server_data = fresh
            check_and_activate_firewall(manager, uuid, server_data.get('hostname', ''))

        elif cmd == "11":
            fresh = refresh_server_data(manager, uuid)
            if fresh:
                server_data = fresh
            show_ip_management_menu(manager, uuid, server_data)

        elif cmd == "99":
            print()
            confirm = input(c("  ⚠️  Yakin HAPUS VPS ini? (y/n): ", C.RED + C.BOLD)).strip().lower()
            if confirm == 'y':
                print()
                info("Memproses penghapusan (bisa memakan waktu hingga 3 menit)...")
                del_status, del_res = manager.delete_server(uuid)
                if del_status in [200, 202, 204]:
                    success("VPS berhasil dihapus.")
                    remove_password(account_name, uuid)
                    press_enter()
                    return
                else:
                    error("Gagal menghapus VPS:")
                    try:
                        err = json.loads(del_res)
                        print(f"     Kode: {err['error']['error_code']}")
                        print(f"     Pesan: {err['error']['error_message']}")
                    except:
                        print(f"     {del_res}")
                press_enter()

        elif cmd == "0":
            return

# ==========================================
# FUNGSI UTAMA
# ==========================================
def main():
    while True:
        account_name, token = get_active_account()

        credits = None
        currency = None
        if account_name and token:
            if account_name in _credits_cache:
                credits, currency = _credits_cache[account_name]
            else:
                manager_tmp = UpCloudManager(token)
                credits, currency = get_account_credits(manager_tmp, account_name)

        main_menu(account_name, credits, currency)
        cmd = input(c("  ➤ Pilih menu: ", C.BOLD + C.CYAN)).strip()

        if cmd == "7":
            accounts_menu()
            continue

        if cmd == "8":
            if account_name:
                _credits_cache.pop(account_name, None)
                info("Saldo di-refresh.")
                time.sleep(0.8)
            continue

        if cmd == "0":
            print(c("\n  👋 Sampai jumpa!\n", C.CYAN + C.BOLD))
            break

        if not account_name or not token:
            error("Belum ada akun aktif!")
            info("Silakan tambah akun dulu di menu [7] Manajemen Akun.")
            press_enter()
            continue

        manager = UpCloudManager(token)

        if cmd == "1":
            create_vps_menu(manager, account_name)
            _credits_cache.pop(account_name, None)
        elif cmd == "2":
            list_vps_menu(manager, account_name)
        elif cmd == "3":
            list_passwords_menu()
        elif cmd == "4":
            list_storage_menu(manager, account_name)
        elif cmd == "5":
            list_ip_menu(manager, account_name)
        elif cmd == "6":
            account_info_menu(manager, account_name)
        else:
            error("Pilihan tidak valid.")
            time.sleep(1)

if __name__ == "__main__":
    main()
