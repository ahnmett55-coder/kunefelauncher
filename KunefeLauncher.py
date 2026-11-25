import os
import sys
import io
import time
import hashlib
import zipfile
import socket
import struct
import re
import json
import uuid
import threading
import subprocess
import shutil
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
import uuid as _uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

mll = None  # ağır kütüphane: ilk ihtiyaçta (arka planda) yüklenir


def load_mll():
    global mll
    if mll is None:
        import minecraft_launcher_lib as _m
        mll = _m
    return mll

try:
    from PIL import Image, ImageTk
except Exception:  # Pillow yoksa ikonlar gösterilmez
    Image = ImageTk = None

def resource_path(rel):
    """PyInstaller (--onefile) içinde ve normal çalışmada dosya yolu."""
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# Ağ düzeltmeleri: (1) bozuk IPv6'da zaman aşımı olmasın diye sadece IPv4, (2) internet sağlayıcısı DNS'i
# Mojang/Modrinth adreslerini engelliyorsa (tarayıcı DoH kullandığı için açılır, Python açılmaz) adresleri DoH ile çöz.
try:
    import socket as _sk
    import urllib3.util.connection as _u3c
    _u3c.HAS_IPV6 = False
    _orig_gai = _sk.getaddrinfo
    _DOH_HOSTS = ("mojang.com", "minecraft.net", "modrinth.com", "fabricmc.net", "githubusercontent.com",
                  "github.com", "workers.dev", "kunefecraft.com.tr", "minotar.net", "azureedge.net")
    _doh_cache = {}

    def _doh_resolve(host):
        if host in _doh_cache:
            return _doh_cache[host]
        import json as _j
        import urllib.request as _ur
        for url in ("https://1.1.1.1/dns-query?name=%s&type=A", "https://8.8.8.8/resolve?name=%s&type=A"):
            try:
                rq = _ur.Request(url % host, headers={"accept": "application/dns-json"})
                with _ur.urlopen(rq, timeout=5) as r:
                    d = _j.loads(r.read().decode("utf-8"))
                ips = [a["data"] for a in d.get("Answer", []) if a.get("type") == 1]
                if ips:
                    _doh_cache[host] = ips
                    return ips
            except Exception:
                continue
        return []

    def _gai4(host, port, family=0, type=0, proto=0, flags=0):
        if isinstance(host, str) and host.endswith(_DOH_HOSTS):
            out = []
            for ip in _doh_resolve(host):
                try:
                    out += _orig_gai(ip, port, _sk.AF_INET, type, proto, flags)
                except Exception:
                    pass
            if out:
                return out
        try:
            r = _orig_gai(host, port, _sk.AF_INET, type, proto, flags)
            if r:
                return r
        except Exception:
            pass
        return _orig_gai(host, port, family, type, proto, flags)
    _sk.getaddrinfo = _gai4
except Exception:
    pass

# Mojang/Fabric adresi zaman aşımına uğrarsa (engelli ağlar) aynı dosyayı BMCLAPI yansısından dene
try:
    import requests as _rq
    _MIRRORS = [
        ("https://resources.download.minecraft.net/", "https://bmclapi2.bangbang93.com/assets/"),
        ("https://libraries.minecraft.net/", "https://bmclapi2.bangbang93.com/maven/"),
        ("https://launchermeta.mojang.com/", "https://bmclapi2.bangbang93.com/"),
        ("https://launcher.mojang.com/", "https://bmclapi2.bangbang93.com/"),
        ("https://piston-meta.mojang.com/", "https://bmclapi2.bangbang93.com/"),
        ("https://piston-data.mojang.com/", "https://bmclapi2.bangbang93.com/"),
        ("https://maven.fabricmc.net/", "https://bmclapi2.bangbang93.com/maven/"),
        ("https://meta.fabricmc.net/", "https://bmclapi2.bangbang93.com/fabric-meta/"),
    ]
    _orig_send = _rq.Session.send

    def _send(self, request, **kw):
        if kw.get("timeout") is None:
            kw["timeout"] = 20
        try:
            return _orig_send(self, request, **kw)
        except (_rq.exceptions.ConnectionError, _rq.exceptions.Timeout):
            for pre, mir in _MIRRORS:
                if request.url.startswith(pre):
                    request.url = mir + request.url[len(pre):]
                    return _orig_send(self, request, **kw)
            raise
    _rq.Session.send = _send
except Exception:
    pass

APP_NAME = "KünefeLauncher"
BASE_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), ".kunefelauncher")
MC_DIR = os.path.join(BASE_DIR, "minecraft")
CFG_FILE = os.path.join(BASE_DIR, "config.json")
os.makedirs(MC_DIR, exist_ok=True)

UA = "KunefeLauncher/2.0 (python launcher)"
APP_VERSION = "2.0"
VERSION = "1.21.4"  # sabit sürüm
SERVER_NAME = "KünefeCraft"
DEFAULT_SERVER = "87.232.127.49:25565"   # ana sunucu (otomatik /login sadece lobide: 87.232.127.49:25567)
# Otomatik kurulan modlar (Modrinth slug)
BASE_MODS = [
    "fabric-api", "sodium", "sodium-extra", "simple-voice-chat", "entityculling",
    "lithium", "ferrite-core", "immediatelyfast", "modernfix", "moreculling",
    "hud-mover", "emotecraft",
]
SITE_URL = "https://kunefecraft.com.tr"
# Mojang'a ulaşılamayan ağlar için hazır oyun paketi (GitHub Release; bkz. .github/workflows/game-pack.yml)
GAME_PACK_URLS = ["https://github.com/ahnmett55-coder/kunefelauncher/releases/download/game-1.21.4/game.zip"]
EXTRA_MODS = []   # ek özel modlar (ad, indirme adresi)
# Uygulamayla gelen hazır doku paketleri (otomatik kurulur ve etkinleştirilir) ve hazır modlar
READY_PACKS = ["dark_gold_gui.zip", "orange_pvp.zip"]                                   # assets/packs
LOCAL_MODS = ["showthelyrics-2.1.4-1.21.4.jar", "kunefe-menu.jar", "MoreCosmetics-Fabric-1.21.4.jar"]      # assets/extra_mods
# TAB logosu: Cloudflare Worker adresi (bkz. CLOUDFLARE_KURULUM_TR.txt)
PRESENCE_URL = "https://kunefe-online.mahmut-ulu-27.workers.dev"
SKIN_API = SITE_URL + "/skin.php"              # skin yükleme (site/skin.php dosyasını sitene koy)
SKIN_BASE_URL = SITE_URL + "/skins/"
SKIN_PACK = "kunefe_skin.zip"
OLD_UI_PACK = "kunefe_ui.zip"   # eski sürümlerin kendi doku paketi (artık kaldırılır)
DEFAULT_SKIN_NAMES = ("steve", "alex", "ari", "efe", "kai", "makena", "noor", "sunny", "zuri")
ANNOUNCE_URL = SITE_URL + "/duyurular.json"   # (isteğe bağlı) duyuruları siteden çek
# Siteden duyuru çekilemezse gösterilecek varsayılan duyurular
ANNOUNCEMENTS = [
    {"title": "KünefeCraft'a Hoş Geldin!", "text": "Sunucumuz Minecraft 1.21.4 ile yayında. OYNA'ya basman yeterli: oyun açılınca doğrudan sunucuya bağlanırsın."},
    {"title": "Sesli Sohbet Aktif", "text": "Simple Voice Chat otomatik kurulur. Oyundayken V tuşuyla ses ayarlarını açabilirsin."},
    {"title": "Müzik + Şarkı Sözleri 🎵", "text": "Artık KünefeLauncher ile Spotify, YouTube Music veya Apple Music hesaplarını bağlayarak şarkı sözleri (lyrics) eşliğinde müzik dinleyebilirsin."},
    {"title": "Sadece KünefeLauncher'lılara Özel", "text": "Yalnızca KünefeLauncher kullananların görebildiği kozmetiklere ve oyun içi emote'lara sahip olabilirsin!"},
    {"title": "KünefeLauncher v2 çıktı! 🎉", "text": "Künefe Menü modu (nişangah, modül listesi, skin mağazası, el konumu), yükleme ekranında ipucları ve TAB'da launcher logosu artık hazır. Hepsi OYNA'ya basınca otomatik kurulur."},
    {"title": "Kozmetikler Geldi! 🎩", "text": "MoreCosmetics artık otomatik kuruluyor: şapka, pelerin ve daha fazlası. ESC menüsündeki Özelleştir butonundan KP ile yeni kozmetikler alabilirsin."},
    {"title": "Arkadaşlar ve Mesajlaşma 💬", "text": "Launcher'dan arkadaş ekleyip bulut üzerinden mesajlaşabilirsin. Ana ekrandaki Arkadaşlar butonuna bas."},
    {"title": "Eğlence Başlasın!", "text": "Arkadaşlarınla sunucuya katıl, etkinlikleri ve yeni güncellemeleri buradan takip et."},
]
SKIN_URL = "https://minotar.net/helm/{name}/64.png"
IP_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?::(\d{1,5}))?$")

# renkler
FONT = "Segoe UI"
BG = "#0b0d12"
CARD = "#1a202b"
CARD_HOVER = "#262e3b"
BORDER = "#323b4b"
FG = "#f2f4f8"
MUTED = "#9aa4b5"
ACCENT = "#f5922a"
ACCENT_H = "#ffb04f"
OK = "#3ddc6b"
BAD = "#e5624f"
BTN2 = "#262e3b"



def load_cfg():
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def http_bytes(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        # Bazı bilgisayarlarda Windows sertifika deposu eksik olabilir: certifi ile tekrar dene
        if "CERTIFICATE" not in str(e).upper() and "SSL" not in str(e).upper():
            raise
        import ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read()


def http_json(url):
    return json.loads(http_bytes(url, 20).decode("utf-8"))


def offline_uuid(name):
    return str(uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer:" + name))


def fmt_num(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ---------- NBT (servers.dat) ----------
def _nbt_read(buf, pos, tid):
    if tid == 1:
        return struct.unpack_from(">b", buf, pos)[0], pos + 1
    if tid == 2:
        return struct.unpack_from(">h", buf, pos)[0], pos + 2
    if tid == 3:
        return struct.unpack_from(">i", buf, pos)[0], pos + 4
    if tid == 4:
        return struct.unpack_from(">q", buf, pos)[0], pos + 8
    if tid == 5:
        return struct.unpack_from(">f", buf, pos)[0], pos + 4
    if tid == 6:
        return struct.unpack_from(">d", buf, pos)[0], pos + 8
    if tid == 7:
        n = struct.unpack_from(">i", buf, pos)[0]
        return bytes(buf[pos + 4:pos + 4 + n]), pos + 4 + n
    if tid == 8:
        n = struct.unpack_from(">H", buf, pos)[0]
        return bytes(buf[pos + 2:pos + 2 + n]).decode("utf-8", "replace"), pos + 2 + n
    if tid == 9:
        et = buf[pos]
        n = struct.unpack_from(">i", buf, pos + 1)[0]
        pos += 5
        items = []
        for _ in range(n):
            v, pos = _nbt_read(buf, pos, et)
            items.append(v)
        return (et, items), pos
    if tid == 10:
        d = {}
        while True:
            t = buf[pos]
            pos += 1
            if t == 0:
                return d, pos
            n = struct.unpack_from(">H", buf, pos)[0]
            key = bytes(buf[pos + 2:pos + 2 + n]).decode("utf-8", "replace")
            pos += 2 + n
            v, pos = _nbt_read(buf, pos, t)
            d[key] = (t, v)
    if tid == 11:
        n = struct.unpack_from(">i", buf, pos)[0]
        return list(struct.unpack_from(f">{n}i", buf, pos + 4)), pos + 4 + 4 * n
    if tid == 12:
        n = struct.unpack_from(">i", buf, pos)[0]
        return list(struct.unpack_from(f">{n}q", buf, pos + 4)), pos + 4 + 8 * n
    raise ValueError("bilinmeyen NBT etiketi")


def _nbt_write(tid, v):
    if tid == 1:
        return struct.pack(">b", v)
    if tid == 2:
        return struct.pack(">h", v)
    if tid == 3:
        return struct.pack(">i", v)
    if tid == 4:
        return struct.pack(">q", v)
    if tid == 5:
        return struct.pack(">f", v)
    if tid == 6:
        return struct.pack(">d", v)
    if tid == 7:
        return struct.pack(">i", len(v)) + v
    if tid == 8:
        b = v.encode("utf-8")
        return struct.pack(">H", len(b)) + b
    if tid == 9:
        et, items = v
        return bytes([et]) + struct.pack(">i", len(items)) + b"".join(_nbt_write(et, i) for i in items)
    if tid == 10:
        out = b""
        for k, (t, val) in v.items():
            kb = k.encode("utf-8")
            out += bytes([t]) + struct.pack(">H", len(kb)) + kb + _nbt_write(t, val)
        return out + b"\x00"
    if tid == 11:
        return struct.pack(">i", len(v)) + struct.pack(f">{len(v)}i", *v)
    if tid == 12:
        return struct.pack(">i", len(v)) + struct.pack(f">{len(v)}q", *v)
    raise ValueError("bilinmeyen NBT etiketi")


def ensure_server_in_list():
    """servers.dat içine KünefeCraft'ı ekler (diğer sunucuları korur)."""
    path = os.path.join(MC_DIR, "servers.dat")
    entry = {"ip": (8, DEFAULT_SERVER), "name": (8, SERVER_NAME)}
    root = {}
    if os.path.exists(path):
        try:
            data = open(path, "rb").read()
            if data[0] != 10:
                raise ValueError
            n = struct.unpack_from(">H", data, 1)[0]
            root, _ = _nbt_read(data, 3 + n, 10)
        except Exception:
            try:
                os.replace(path, path + ".bak")
            except Exception:
                pass
            root = {}
    et, servers = root.get("servers", (9, (10, [])))[1]
    if et != 10:
        et, servers = 10, []
    # IP değiştiyse eski KünefeCraft kaydını sil
    servers = [sv for sv in servers if not (sv.get("name", (8, ""))[1] == SERVER_NAME
                                            and sv.get("ip", (8, ""))[1] != DEFAULT_SERVER)]
    for sv in servers:
        if sv.get("ip", (8, ""))[1] == DEFAULT_SERVER:
            sv["name"] = (8, SERVER_NAME)
            break
    else:
        servers.insert(0, entry)
    root["servers"] = (9, (10, servers))
    with open(path, "wb") as f:
        f.write(b"\x0a\x00\x00" + _nbt_write(10, root))


# ---------- Sunucu durumu (Server List Ping) ----------
def _varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def _read_varint(sock):
    r = 0
    for i in range(5):
        b = sock.recv(1)
        if not b:
            raise IOError("bağlantı kapandı")
        r |= (b[0] & 0x7F) << (7 * i)
        if not b[0] & 0x80:
            return r
    raise IOError("varint")


def ping_server(host, port, timeout=4):
    t0 = time.time()
    with socket.create_connection((host, port), timeout=timeout) as sk:
        sk.settimeout(timeout)
        ms = int((time.time() - t0) * 1000)
        hb = host.encode()
        pkt = _varint(0) + _varint(767) + _varint(len(hb)) + hb + struct.pack(">H", port) + _varint(1)
        sk.sendall(_varint(len(pkt)) + pkt)
        sk.sendall(_varint(1) + b"\x00")
        _read_varint(sk)
        _read_varint(sk)
        n = _read_varint(sk)
        data = b""
        while len(data) < n:
            chunk = sk.recv(n - len(data))
            if not chunk:
                break
            data += chunk
        info = json.loads(data.decode("utf-8", "replace"))
        pl = info.get("players", {})
        return pl.get("online", 0), pl.get("max", 0), ms


class FlatButton(tk.Label):
    """Basit, tıklanabilir, hover efektli buton."""

    def __init__(self, master, text, command, bg=ACCENT, fg="#1b1712", hover=ACCENT_H, **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, cursor="hand2",
                         font=(FONT, 10, "bold"), padx=14, pady=6, **kw)
        self._bg, self._hover, self._cmd = bg, hover, command
        self._enabled = True
        self.bind("<Enter>", lambda e: self._enabled and self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: self._enabled and self._cmd())

    def set_enabled(self, v):
        self._enabled = v
        self.config(bg=self._bg if v else "#5a4d38", cursor="hand2" if v else "arrow")

    def set_text(self, t, bg=None):
        self.config(text=t)
        if bg:
            self._bg = bg
            self.config(bg=bg)




import traceback
from PIL import ImageDraw, ImageFilter, ImageOps, ImageEnhance

W, H = 1100, 680
PAD = 14  # panel/buton gölge payı


def log_crash(text):
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(os.path.join(BASE_DIR, "crash.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + text + "\n")
    except Exception:
        pass


def total_ram_mb():
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("ml", ctypes.c_ulong), ("tp", ctypes.c_ulonglong),
                        ("ap", ctypes.c_ulonglong), ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong),
                        ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
        m = MS()
        m.l = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.tp // 1048576)
    except Exception:
        return 8192


# ---------------------------------------------------------------- 3D görsel üretimi (Pillow)
def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def _grad(w, h, c1, c2):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line((0, y, w, y), fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,))
    return im


def make_bg(w, h):
    k = 4
    sw, sh = w // k, h // k
    base = _grad(sw, sh, (25, 29, 41), (6, 7, 10))

    def blob(size, a, col):
        bw, bh = size
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).ellipse((bw * 0.30, bh * 0.30, bw * 0.70, bh * 0.70), fill=int(255 * a))
        m = m.filter(ImageFilter.GaussianBlur(min(bw, bh) * 0.075))
        layer = Image.new("RGBA", size, col + (0,))
        layer.putalpha(m)
        return layer
    gl = blob((375, 275), 0.55, (245, 146, 42))
    base.paste(gl, (-140, sh - 175), gl)
    gl2 = blob((300, 215), 0.30, (245, 146, 42))
    base.paste(gl2, (sw - 190, -118), gl2)
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).ellipse((-sw * 0.12, -sh * 0.18, sw * 1.12, sh * 1.18), fill=255)
    m = ImageOps.invert(m.filter(ImageFilter.GaussianBlur(18))).point(lambda v: int(v * 0.7))
    dark = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    dark.putalpha(m)
    base.paste(dark, (0, 0), dark)
    return base.resize((w, h), Image.BICUBIC).convert("RGB")


def make_glow(w, h, k):
    """OYNA butonunun arkasındaki parlama (yumuşak turuncu)."""
    sw, sh = w // 2, h // 2
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle((sw * 0.16, sh * 0.22, sw * 0.84, sh * 0.78), radius=sh * 0.3, fill=int(255 * k))
    m = m.filter(ImageFilter.GaussianBlur(sh * 0.12)).resize((w, h), Image.BICUBIC)
    layer = Image.new("RGBA", (w, h), (255, 140, 30, 0))
    layer.putalpha(m)
    return layer


def mix(c1, c2, t):
    return "#%02x%02x%02x" % tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


EMBER_COLS = ("#7a4318", "#9a561b", "#b4661f", "#5e3416", "#c9782a")
_WARM = []


def _card(face, r=18, border=(58, 68, 88), pad=PAD, shadow=True):
    w, h = face.size
    S = 2
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 6, pad + w, pad + h + 6), radius=r, fill=(0, 0, 0, 175))
        out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(9)))
    m = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=r * S, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    out.paste(face.convert("RGBA"), (pad, pad), m)
    ring = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(ring).rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=r * S, outline=255, width=2 * S)
    ring = ring.resize((w, h), Image.LANCZOS)
    out.paste(Image.new("RGBA", (w, h), tuple(border) + (255,)), (pad, pad), ring)
    return out


def make_panel(w, h, r=18, fill=(26, 32, 43), flat=False, border=(58, 68, 88)):
    if flat:
        face = Image.new("RGB", (w, h), fill)
    else:
        face = _grad(w, h, shade(fill, 1.22), shade(fill, 0.88))
        ImageDraw.Draw(face).line((r, 1, w - r, 1), fill=(255, 255, 255, 40))
    return _card(face, r, border)


def make_slide(hero, w, h, r=20):
    if hero is not None:
        sc = max(w / hero.width, h / hero.height)
        im = hero.resize((int(hero.width * sc) + 1, int(hero.height * sc) + 1), Image.LANCZOS)
        left, top = (im.width - w) // 2, (im.height - h) // 2
        face = im.crop((left, top, left + w, top + h)).convert("RGB")
        face = ImageEnhance.Brightness(face).enhance(0.82)
    else:
        face = _grad(w, h, (50, 40, 30), (14, 12, 12)).convert("RGB")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(h):
        t = max(0.0, (y - h * 0.25) / (h * 0.75))
        d.line((0, y, w, y), fill=(6, 8, 12, int(200 * t)))
    face = Image.alpha_composite(face.convert("RGBA"), ov)
    ov2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))  # sol kenar karartma (yazı okunsun)
    d2 = ImageDraw.Draw(ov2)
    for x in range(0, 300):
        d2.line((x, 0, x, h), fill=(6, 8, 12, int(120 * (1 - x / 300))))
    face = Image.alpha_composite(face, ov2)
    return _card(face, r, (78, 90, 112))


STYLES = {
    "primary": ((255, 186, 84), (231, 112, 24), "#2a1604"),
    "dark": ((66, 78, 99), (36, 44, 59), "#eef2f9"),
    "danger": ((238, 112, 98), (182, 54, 44), "#ffffff"),
    "ok": ((88, 230, 130), (30, 156, 70), "#08200f"),
    "off": ((72, 78, 90), (48, 53, 63), "#98a0b0"),
}


def make_button(w, h, top, bottom, pressed=False, r=14):
    S = 2
    depth = min(8, max(4, h // 9))
    pad = 12
    Wd, Hd = w * S, (h + pad) * S
    out = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    sh = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((8 * S, (depth + 5) * S, Wd - 8 * S, (h + 5) * S), radius=r * S, fill=(0, 0, 0, 190))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(5 * S)))
    d = ImageDraw.Draw(out)
    yface = (depth - 2) if pressed else 0
    d.rounded_rectangle((0, 4 * S, Wd - 1, h * S), radius=r * S, fill=shade(bottom, 0.5) + (255,))
    fh = h - depth
    face = _grad(Wd, fh * S, top, bottom)
    gl_h = fh * S // 2
    gloss = Image.new("RGBA", (Wd, gl_h), (255, 255, 255, 0))
    gd = ImageDraw.Draw(gloss)
    for gy in range(gl_h):
        gd.line((0, gy, Wd, gy), fill=(255, 255, 255, int(46 * (1 - gy / gl_h))))
    face.alpha_composite(gloss, (0, 0))
    m = Image.new("L", (Wd, fh * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, Wd - 1, fh * S - 1), radius=r * S, fill=255)
    out.paste(face, (0, yface * S), m)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, yface * S, Wd - 1, (yface + fh) * S - 1), radius=r * S, outline=shade(top, 0.62) + (255,), width=S)
    d.line((r * S, (yface + 2) * S, Wd - r * S, (yface + 2) * S), fill=(255, 255, 255, 95), width=S)
    return out.resize((w, h + pad), Image.LANCZOS), depth


_IMG = {}


def btn_ph(w, h, style, state, r):
    key = (w, h, style, state, r)
    if key not in _IMG:
        top, bottom, _ = STYLES[style]
        if state == "h":
            top, bottom = shade(top, 1.13), shade(bottom, 1.13)
        im, depth = make_button(w, h, top, bottom, pressed=(state == "p"), r=r)
        _IMG[key] = (ImageTk.PhotoImage(im), depth)
    return _IMG[key]


class CButton:
    """Canvas üzerinde 3D buton (görsel + yazı). Tıklama/hover/basılma efektleri var."""

    def __init__(self, cv, x, y, w, h, text, cmd, style="dark", fsize=12, r=14, text_color=None):
        self.cv, self.cmd, self.style = cv, cmd, style
        self.x, self.y, self.w, self.h, self.r = x, y, w, h, r
        self.enabled = True
        self.state = "n"
        self.tag = "cb%d" % id(self)
        ph, depth = btn_ph(w, h, style, "n", r)
        _WARM.extend([(w, h, style, "h", r), (w, h, style, "p", r)])
        self.depth = depth
        self.fg = text_color or STYLES[style][2]
        self.img = cv.create_image(x, y, anchor="nw", image=ph, tags=(self.tag,))
        self.txt = cv.create_text(x + w / 2, y + (h - depth) / 2, text=text, fill=self.fg,
                                  font=(FONT, fsize, "bold"), tags=(self.tag,))
        cv.tag_bind(self.tag, "<Enter>", lambda e: self._set("h"))
        cv.tag_bind(self.tag, "<Leave>", lambda e: self._set("n"))
        cv.tag_bind(self.tag, "<ButtonPress-1>", lambda e: self._set("p"))
        cv.tag_bind(self.tag, "<ButtonRelease-1>", self._release)

    def _set(self, st):
        if not self.enabled:
            return
        self.state = st
        ph, depth = btn_ph(self.w, self.h, self.style, st, self.r)
        self.cv.itemconfig(self.img, image=ph)
        dy = (depth - 2) if st == "p" else 0
        self.cv.coords(self.txt, self.x + self.w / 2, self.y + (self.h - depth) / 2 + dy)
        self.cv.config(cursor="hand2" if st in ("h", "p") else "")

    def _release(self, e):
        if not self.enabled:
            return
        inside = self.x <= e.x <= self.x + self.w and self.y <= e.y <= self.y + self.h
        self._set("h" if inside else "n")
        if inside:
            try:
                self.cmd()
            except Exception:
                log_crash(traceback.format_exc())

    def attach(self, item):
        self.cv.addtag_withtag(self.tag, item)

    def set_text(self, t):
        self.cv.itemconfig(self.txt, text=t)

    def set_style(self, style):
        self.style = style
        self.fg = STYLES[style][2]
        ph, _ = btn_ph(self.w, self.h, style, "n", self.r)
        self.cv.itemconfig(self.img, image=ph)
        self.cv.itemconfig(self.txt, fill=self.fg)

    def set_enabled(self, v, off_text=None):
        self.enabled = v
        st = "n"
        ph, depth = btn_ph(self.w, self.h, self.style if v else "off", st, self.r)
        self.cv.itemconfig(self.img, image=ph)
        self.cv.itemconfig(self.txt, fill=self.fg if v else STYLES["off"][2])
        self.cv.coords(self.txt, self.x + self.w / 2, self.y + (self.h - depth) / 2)
        if off_text is not None and not v:
            self.set_text(off_text)

    def set_visible(self, v):
        self.cv.itemconfig(self.tag, state="normal" if v else "hidden")
        self.enabled = v


class Toggle(tk.Canvas):
    def __init__(self, master, value, command, locked=False, bg=CARD):
        super().__init__(master, width=52, height=28, bg=bg, highlightthickness=0, bd=0,
                         cursor="arrow" if locked else "hand2")
        self.value, self.cmd, self.locked = value, command, locked
        self._draw()
        self.bind("<Button-1>", self._click)

    def _draw(self):
        self.delete("all")
        col = "#5a6376" if self.locked and self.value else (ACCENT if self.value else "#3a4457")
        rrect(self, 2, 2, 50, 26, 11, fill=col, outline="")
        x = 38 if self.value else 14
        self.create_oval(x - 10, 4, x + 10, 24, fill="#ffffff", outline="")

    def _click(self, e):
        if self.locked:
            return
        self.value = not self.value
        self._draw()
        try:
            self.cmd(self.value)
        except Exception:
            log_crash(traceback.format_exc())


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=CARD, **kw):
        super().__init__(master, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win, width=e.width))

    def wheel(self, e):
        try:
            self.canvas.yview_scroll(int(-e.delta / 120), "units")
        except Exception:
            pass

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


def rrect(c, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def default_head():
    im = Image.new("RGB", (8, 8), (112, 200, 44))
    px = im.load()
    for x, y in [(1, 2), (2, 2), (5, 2), (6, 2), (1, 3), (2, 3), (5, 3), (6, 3), (3, 4), (4, 4),
                 (3, 5), (4, 5), (2, 5), (5, 5), (2, 6), (5, 6)]:
        px[x, y] = (12, 14, 10)
    return im



# ---------------------------------------------------------------- 3D skin görüntüleyici (Pillow, yazılım render)
import math

SKIN_FACE_SHADE = (-0.45, 0.75, 0.55)  # ışık yönü


def norm_skin(im):
    """64x64 veya 64x32 skin'i 64x64 RGBA'ya çevirir. Geçersizse ValueError."""
    im = im.convert("RGBA")
    if im.size == (64, 64):
        return im
    if im.size == (64, 32):
        out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        out.paste(im, (0, 0))

        def mirror(src, dst, w, h, d):
            su, sv = src
            du, dv = dst
            faces = {  # (src offset, dst offset, boyut, çevir)
                "top": ((d, 0), (d, 0), (w, d)), "bottom": ((d + w, 0), (d + w, 0), (w, d)),
                "front": ((d, d), (d, d), (w, h)), "back": ((2 * d + w, d), (2 * d + w, d), (w, h)),
            }
            for (so, do_, sz) in faces.values():
                r = im.crop((su + so[0], sv + so[1], su + so[0] + sz[0], sv + so[1] + sz[1])).transpose(Image.FLIP_LEFT_RIGHT)
                out.paste(r, (du + do_[0], dv + do_[1]))
            right = im.crop((su, sv + d, su + d, sv + d + h)).transpose(Image.FLIP_LEFT_RIGHT)
            left = im.crop((su + d + w, sv + d, su + 2 * d + w, sv + d + h)).transpose(Image.FLIP_LEFT_RIGHT)
            out.paste(left, (du, dv + d))
            out.paste(right, (du + d + w, dv + d))
        mirror((0, 16), (16, 48), 4, 12, 4)   # sol bacak
        mirror((40, 16), (32, 48), 4, 12, 4)  # sol kol
        return out
    raise ValueError("Skin 64x64 veya 64x32 boyutunda olmalı.")


def detect_slim(im):
    """Slim (3 piksel kol) skin mi? Sağ kolun 4. sütunu tamamen şeffafsa evet."""
    px = im.load()
    return all(px[47, y][3] == 0 for y in range(20, 32))


def _parts(slim):
    aw = 3 if slim else 4
    return [
        ((-4, 0, -2), (4, 12, 4), (0, 16), 0), ((0, 0, -2), (4, 12, 4), (16, 48), 0),
        ((-4, 12, -2), (8, 12, 4), (16, 16), 0),
        ((-4 - aw, 12, -2), (aw, 12, 4), (40, 16), 0), ((4, 12, -2), (aw, 12, 4), (32, 48), 0),
        ((-4, 24, -4), (8, 8, 8), (0, 0), 0),
        ((-4, 0, -2), (4, 12, 4), (0, 32), 0.25), ((0, 0, -2), (4, 12, 4), (0, 48), 0.25),
        ((-4, 12, -2), (8, 12, 4), (16, 32), 0.25),
        ((-4 - aw, 12, -2), (aw, 12, 4), (40, 32), 0.25), ((4, 12, -2), (aw, 12, 4), (48, 48), 0.25),
        ((-4, 24, -4), (8, 8, 8), (32, 0), 0.5),
    ]


def _faces(origin, size, uv, e):
    (x, y, z), (w, h, d), (u, v) = origin, size, uv
    x0, y0, z0 = x - e, y - e, z - e
    W, H, D = w + 2 * e, h + 2 * e, d + 2 * e
    x1, y1, z1 = x0 + W, y0 + H, z0 + D
    return [  # P0, U, V, doku dikdörtgeni, normal
        ((x0, y1, z1), (W, 0, 0), (0, -H, 0), (u + d, v + d, w, h), (0, 0, 1)),
        ((x1, y1, z0), (-W, 0, 0), (0, -H, 0), (u + 2 * d + w, v + d, w, h), (0, 0, -1)),
        ((x0, y1, z0), (0, 0, D), (0, -H, 0), (u, v + d, d, h), (-1, 0, 0)),
        ((x1, y1, z1), (0, 0, -D), (0, -H, 0), (u + d + w, v + d, d, h), (1, 0, 0)),
        ((x0, y1, z0), (W, 0, 0), (0, 0, D), (u + d, v, w, d), (0, 1, 0)),
        ((x0, y0, z1), (W, 0, 0), (0, 0, -D), (u + d + w, v, w, d), (0, -1, 0)),
    ]


def render_skin(skin, slim, angle_deg, size=(300, 420), ss=2, tilt_deg=12):
    """Skin'i verilen açıyla (derece) çizer, RGBA döner."""
    Wd, Hd = size
    cv = Image.new("RGBA", (Wd * ss, Hd * ss), (0, 0, 0, 0))
    th, ph = math.radians(angle_deg), math.radians(tilt_deg)
    cth, sth, cph, sph = math.cos(th), math.sin(th), math.cos(ph), math.sin(ph)
    S = Hd * ss / 36.0
    cx, cy = Wd * ss / 2, Hd * ss * 0.52

    def rot(p, center=True):
        x, y, z = p[0], p[1] - (16 if center else 0), p[2]
        x2, z2 = x * cth + z * sth, -x * sth + z * cth
        y3, z3 = y * cph - z2 * sph, y * sph + z2 * cph
        return x2, y3, z3

    def rotn(n):
        x, y, z = n
        x2, z2 = x * cth + z * sth, -x * sth + z * cth
        return x2, y * cph - z2 * sph, y * sph + z2 * cph
    L = SKIN_FACE_SHADE
    ln = math.sqrt(sum(c * c for c in L))
    L = tuple(c / ln for c in L)

    jobs = []
    for origin, sz, uv, e in _parts(slim):
        if e:  # tamamen şeffaf katmanı atla
            u, v = uv
            w, h, d = sz
            if skin.crop((u, v, u + 2 * d + 2 * w, v + d + h)).getchannel("A").getextrema()[1] == 0:
                continue
        for p0, U, V, tex, nrm in _faces(origin, sz, uv, e):
            n = rotn(nrm)
            if n[2] <= 0.01:
                continue
            a, b, c = rot(p0), rot((p0[0] + U[0], p0[1] + U[1], p0[2] + U[2])), rot((p0[0] + V[0], p0[1] + V[1], p0[2] + V[2]))
            dpt = (a[2] + b[2] + c[2]) / 3 + (b[2] - a[2] + c[2] - a[2]) / 6
            lit = 0.55 + 0.45 * max(0.0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2])
            jobs.append((dpt, a, b, c, tex, lit))
    jobs.sort(key=lambda j: j[0])
    for _, a, b, c, tex, lit in jobs:
        tx, ty, tw, th_ = tex
        crop = skin.crop((tx, ty, tx + tw, ty + th_))
        r, g, bl, al = crop.split()
        k = lambda val, f=lit: min(255, int(val * f))
        crop = Image.merge("RGBA", (r.point(k), g.point(k), bl.point(k), al))
        A = (cx + a[0] * S, cy - a[1] * S)
        B = (cx + b[0] * S, cy - b[1] * S)
        C = (cx + c[0] * S, cy - c[1] * S)
        D = (B[0] + C[0] - A[0], B[1] + C[1] - A[1])
        eux, euy = (B[0] - A[0]) / tw, (B[1] - A[1]) / tw
        evx, evy = (C[0] - A[0]) / th_, (C[1] - A[1]) / th_
        det = eux * evy - evx * euy
        if abs(det) < 1e-6:
            continue
        xs, ys = (A[0], B[0], C[0], D[0]), (A[1], B[1], C[1], D[1])
        bx0, by0 = int(math.floor(min(xs))) - 1, int(math.floor(min(ys))) - 1
        bw, bh = int(math.ceil(max(xs))) - bx0 + 2, int(math.ceil(max(ys))) - by0 + 2
        co = (evy / det, -evx / det, (evy * (bx0 - A[0]) - evx * (by0 - A[1])) / det,
              -euy / det, eux / det, (-euy * (bx0 - A[0]) + eux * (by0 - A[1])) / det)
        warp = crop.transform((bw, bh), Image.AFFINE, co, Image.NEAREST)
        cv.paste(warp, (bx0, by0), warp)
    fig = cv.resize((Wd, Hd), Image.LANCZOS)
    # zemin gölgesi
    sh = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((Wd * 0.22, Hd * 0.885, Wd * 0.78, Hd * 0.945), fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    return Image.alpha_composite(sh, fig)


def render_frames(skin, slim, n=36, size=(300, 420)):
    return [render_skin(skin, slim, i * 360.0 / n, size) for i in range(n)]


def convert_arms(skin, to_slim):
    """Kolları klasik (4px) <-> slim (3px) arasında çevirir."""
    out = skin.copy()
    d, h = 4, 12
    w0, w1 = (4, 3) if to_slim else (3, 4)

    def faces(u, v, w):
        return {"top": (u + d, v, w, d), "bot": (u + d + w, v, w, d), "front": (u + d, v + d, w, h),
                "back": (u + 2 * d + w, v + d, w, h), "right": (u, v + d, d, h), "left": (u + d + w, v + d, d, h)}
    for (u, v) in ((40, 16), (40, 32), (32, 48), (48, 48)):
        src, dst = faces(u, v, w0), faces(u, v, w1)
        crops = {k: skin.crop((x, y, x + fw, y + fh)) for k, (x, y, fw, fh) in src.items()}
        out.paste((0, 0, 0, 0), (u, v, u + 16, v + 16))
        for k, (x, y, fw, fh) in dst.items():
            c = crops[k]
            if c.size != (fw, fh):
                c = c.resize((fw, fh), Image.NEAREST)
            out.paste(c, (x, y))
    return out


def default_skin():
    """İnternet yokken gösterilecek basit varsayılan skin."""
    sk = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(sk)
    tan, brown, cy, bl, dbl, dcy = (205, 155, 115, 255), (90, 55, 30, 255), (60, 170, 190, 255), (50, 60, 160, 255), (30, 35, 100, 255), (30, 110, 130, 255)

    def box(u, v, w, h, dd, c):
        d.rectangle((u + dd, v, u + dd + w - 1, v + dd - 1), fill=c[0])
        d.rectangle((u + dd + w, v, u + dd + 2 * w - 1, v + dd - 1), fill=c[1])
        d.rectangle((u, v + dd, u + dd - 1, v + dd + h - 1), fill=c[2])
        d.rectangle((u + dd, v + dd, u + dd + w - 1, v + dd + h - 1), fill=c[3])
        d.rectangle((u + dd + w, v + dd, u + 2 * dd + w - 1, v + dd + h - 1), fill=c[4])
        d.rectangle((u + 2 * dd + w, v + dd, u + 2 * dd + 2 * w - 1, v + dd + h - 1), fill=c[5])
    box(0, 0, 8, 8, 8, (brown, tan, tan, tan, tan, brown))
    box(16, 16, 8, 12, 4, (cy, cy, cy, cy, cy, dcy))
    box(40, 16, 4, 12, 4, (tan,) * 6)
    box(32, 48, 4, 12, 4, (tan,) * 6)
    box(0, 16, 4, 12, 4, (bl, bl, bl, bl, bl, dbl))
    box(16, 48, 4, 12, 4, (bl, bl, bl, bl, bl, dbl))
    for xy in ((10, 11), (13, 11)):
        d.point(xy, fill=(40, 60, 140, 255))
    d.rectangle((8, 8, 15, 9), fill=brown)
    d.rectangle((10, 14, 13, 14), fill=(130, 70, 60, 255))
    return sk


def http_post_multipart(url, fields, files, timeout=30):
    """Basit multipart/form-data gönderimi (certifi yedekli). Yanıtı JSON olarak döner."""
    boundary = "----kunefe" + _uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (fn, data, ctype) in files.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                 f'Content-Type: {ctype}\r\n\r\n').encode() + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Content-Type": "multipart/form-data; boundary=" + boundary})

    def go(ctx=None):
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    try:
        return go()
    except (urllib.error.HTTPError, json.JSONDecodeError):
        raise
    except Exception as e:
        if "CERTIFICATE" in str(e).upper() or "SSL" in str(e).upper():
            import ssl
            import certifi
            return go(ssl.create_default_context(cafile=certifi.where()))
        raise



SORTS = {"Alaka": "relevance", "İndirme": "downloads", "Takip": "follows", "En Yeni": "newest"}
MM_TABS = [("mod", "Modlar", "mods"), ("resourcepack", "Doku Paketleri", "resourcepacks"),
           ("shader", "Shader Paketleri", "shaderpacks")]
TYPE_TR = {"mod": "MOD", "resourcepack": "DOKU PAKETİ", "shader": "SHADER"}
ROW_BG = "#212938"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{max(0, (sw - W) // 2)}+{max(0, (sh - H - 40) // 2)}")
        self.resizable(False, False)
        self.configure(bg="#07080b")
        self.cfg = load_cfg()
        self.user = self.cfg.get("name") or ""
        self.heads = {}
        self.head_cache = {}
        self.fetching = set()
        self.default_head = default_head()
        self.srv = None
        self.busy = False
        self.is_installed = False
        self.slides = list(ANNOUNCEMENTS)
        self.slide_i = 0
        self.rot_job = None
        self.page = None
        self.scroller = None
        self.installed = set(self.cfg.get("installed_mods", []))
        self.search_token = 0
        self.hits = {}
        self.sel_hit = None
        self.cards = {}
        self.mm_type = "mod"
        self.store_type = "mod"
        self.pages = {}
        self.login_busy = False
        self.acc_open = False
        self.embers = {}
        self.fx_on = True
        self.fx_slow = 0
        self.fx_last = time.perf_counter()
        self.glow_imgs = []
        self.glow_idx = -1
        self.anim_id = 0
        self.warming = False
        self.sk_img = None
        self.sk_slim = False
        self.sk_ph = []
        self.sk_idx = -1
        self.sk_angle = 25.0
        self.sk_spin = True
        self.sk_idle = 0.0
        self.sk_drag = None
        self.sk_token = 0
        self.skin_pack_active = False
        self.game_proc = None
        self.mods_boot = False

        try:
            self.logo_pil = Image.open(resource_path(os.path.join("assets", "logo.png"))).convert("RGBA")
        except Exception:
            self.logo_pil = None
        try:
            self.hero_pil = Image.open(resource_path(os.path.join("assets", "hero.jpg"))).convert("RGB")
        except Exception:
            self.hero_pil = None
        self.keep = []  # PhotoImage referansları
        if self.logo_pil is not None:
            try:
                ic = ImageTk.PhotoImage(self.logo_pil.resize((128, 128), Image.LANCZOS))
                self.keep.append(ic)
                self.iconphoto(True, ic)
            except Exception:
                pass
        self.bg_img = ImageTk.PhotoImage(make_bg(W, H))
        self._style()
        self.bind_all("<MouseWheel>", lambda e: self.scroller.wheel(e) if self.scroller else None)

        self._build_home()
        if self.user:
            self.show("home")
        else:
            self.show("login")
        self.after(80, self._late_init)

    def report_callback_exception(self, exc, val, tb):
        log_crash("".join(traceback.format_exception(exc, val, tb)))

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Vertical.TScrollbar", background="#33404f", troughcolor=CARD, arrowcolor=ACCENT,
                    bordercolor=CARD, lightcolor="#33404f", darkcolor="#33404f", gripcount=0)

    # ----------------------------------------------------------------- yardımcılar
    def new_page(self, name):
        cv = tk.Canvas(self, width=W, height=H, highlightthickness=0, bd=0, bg="#07080b")
        cv.create_image(0, 0, anchor="nw", image=self.bg_img)
        self.pages[name] = cv
        return cv

    def panel(self, cv, x, y, w, h, **kw):
        ph = ImageTk.PhotoImage(make_panel(w, h, **kw))
        self.keep.append(ph)
        return cv.create_image(x - PAD, y - PAD, anchor="nw", image=ph)

    def show(self, name):
        for cv in self.pages.values():
            cv.place_forget()
        if name == "login" and "login" not in self.pages:
            self._build_login()
        if name == "settings" and "settings" not in self.pages:
            self._build_settings()
        if name == "skin" and "skin" not in self.pages:
            self._build_skin()
        if name == "social" and "social" not in self.pages:
            self._build_social()
        if name == "mods" and "mods" not in self.pages:
            self._build_mm()
        if name == "store" and "store" not in self.pages:
            self._build_store()
        self.page = name
        if name == "social":
            self.after(100, self._soc_enter)
        self.pages[name].place(x=0, y=0)
        self.scroller = None
        self.close_acc()
        if name == "home":
            self._refresh_header()
            self._schedule_rot()
        elif name == "mods":
            self.refresh_mm()
        elif name == "store":
            self.scroller = self.store_list
            if not self.hits:
                self.search_mods()
        elif name == "settings":
            self._load_settings_values()
        elif name == "skin":
            self._skin_open()
        elif name == "login":
            self.login_err_set("")
            self.btn_login_back.set_visible(bool(self.user))
            self.e_user.focus_set()
        self._start_warm()

    def open_folder(self, sub=""):
        try:
            p = os.path.join(MC_DIR, sub) if sub else MC_DIR
            os.makedirs(p, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(p)
        except Exception:
            pass

    def head_ph(self, name, size):
        key = (name, size)
        if key not in self.head_cache:
            im = self.heads.get(name) or self.default_head
            self.head_cache[key] = ImageTk.PhotoImage(im.resize((size, size), Image.NEAREST))
        return self.head_cache[key]

    def fetch_head(self, name):
        if not name or name in self.heads or name in self.fetching or not re.fullmatch(r"\w{1,16}", name):
            return
        self.fetching.add(name)

        def work():
            try:
                im = Image.open(io.BytesIO(http_bytes(SKIN_URL.format(name=urllib.parse.quote(name)), 10))).convert("RGBA")
                self.heads[name] = im
                self.head_cache = {k: v for k, v in self.head_cache.items() if k[0] != name}
                self.after(0, self._heads_changed)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _heads_changed(self):
        if self.page == "home":
            self._refresh_header()
            if self.acc_open:
                self.open_acc()

    # ----------------------------------------------------------------- GİRİŞ (sadece oyuncu adı)
    def _build_login(self):
        cv = self.new_page("login")
        self.cv_login = cv
        self.embers_for(cv)
        self.panel(cv, 330, 66, 440, 548)
        self.login_logo = None
        if self.logo_pil is not None:
            self.logo_big = ImageTk.PhotoImage(self.logo_pil.resize((130, 130), Image.LANCZOS))
            self.login_logo = cv.create_image(550, 150, image=self.logo_big)
        cv.create_text(550, 256, text="Künefe Launcher'a Hoş Geldin!", fill=FG, font=(FONT, 17, "bold"))
        cv.create_text(550, 286, text="Oyuncu adını yaz ve oyuna katıl:", fill=MUTED, font=(FONT, 11))
        cv.create_text(372, 314, anchor="w", text="Oyuncu Adı", fill=MUTED, font=(FONT, 9))
        self.e_user = tk.Entry(cv, bg="#232b3a", fg=FG, insertbackground=FG, relief="flat", font=(FONT, 14),
                               highlightthickness=2, highlightbackground=BORDER, highlightcolor=ACCENT, bd=0)
        cv.create_window(550, 342, window=self.e_user, width=356, height=40)
        self.e_user.bind("<Return>", lambda e: self.do_login())
        cv.create_text(372, 384, anchor="w", text="Oyun Şifresi (sitede kayıt olurken yazdığın)", fill=MUTED, font=(FONT, 9))
        self.e_pass = tk.Entry(cv, bg="#232b3a", fg=FG, insertbackground=FG, relief="flat", font=(FONT, 14), show="•",
                               highlightthickness=2, highlightbackground=BORDER, highlightcolor=ACCENT, bd=0)
        cv.create_window(550, 412, window=self.e_pass, width=356, height=40)
        self.e_pass.bind("<Return>", lambda e: self.do_login())
        self.login_err = cv.create_text(550, 448, text="", fill=BAD, font=(FONT, 10), width=360)
        self.btn_login = CButton(cv, 370, 466, 360, 56, "DEVAM ET", self.do_login, "primary", 15, 16)
        reg = cv.create_text(550, 524, text="Hesabın yok mu? Sitede kayıt ol →", fill=ACCENT, font=(FONT, 11, "underline"))
        cv.tag_bind(reg, "<Button-1>", lambda e: webbrowser.open("https://kunefecraft.com.tr/kayit"))
        cv.tag_bind(reg, "<Enter>", lambda e: cv.config(cursor="hand2"))
        cv.tag_bind(reg, "<Leave>", lambda e: cv.config(cursor=""))
        cv.create_text(550, 546, text="Şifre bu bilgisayarda saklanır; oyunda /login otomatik yapılır.", fill=MUTED, font=(FONT, 9))
        cv.create_text(550, 556, text="🍮  KünefeCraft", fill="#6f7a8f", font=(FONT, 10))
        self.btn_login_back = CButton(cv, 30, 24, 120, 42, "← Geri", lambda: self.show("home"), "dark", 11, 12)

    def login_err_set(self, t, ok=False):
        self.cv_login.itemconfig(self.login_err, text=t, fill=OK if ok else BAD)

    def do_login(self):
        u = self.e_user.get().strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", u):
            self.login_err_set("Oyuncu adı 3-16 karakter (harf, rakam, _) olmalı.")
            return
        pw = self.e_pass.get()
        pws = self.cfg.setdefault("pw", {})
        if pw:
            pws[u.lower()] = pw
        self.add_account(u)
        self.e_pass.delete(0, "end")
        self.show("home")

    # ----------------------------------------------------------------- HESAPLAR
    def accounts(self):
        return [a for a in self.cfg.get("accounts", []) if a]

    def add_account(self, name):
        accs = [a for a in self.accounts() if a.lower() != name.lower()] + [name]
        self.cfg["accounts"] = accs
        self.cfg["name"] = name
        save_cfg(self.cfg)
        self.user = name
        self.fetch_head(name)

    def switch_account(self, name):
        self.cfg["name"] = name
        save_cfg(self.cfg)
        self.user = name
        self.fetch_head(name)
        self.close_acc()
        self._refresh_header()

    def remove_account(self, name):
        accs = [a for a in self.accounts() if a != name]
        self.cfg["accounts"] = accs
        if self.user == name:
            self.user = accs[-1] if accs else ""
            self.cfg["name"] = self.user
        save_cfg(self.cfg)
        if not self.user:
            self.show("login")
        else:
            self._refresh_header()
            self.open_acc()

    # ----------------------------------------------------------------- ANA SAYFA
    def _build_home(self):
        cv = self.new_page("home")
        self.cv = cv
        self.embers_for(cv)
        self.play_glow = cv.create_image(550, 556)
        self.logo_h_id = None
        if self.logo_pil is not None:
            self.logo_h = ImageTk.PhotoImage(self.logo_pil.resize((76, 76), Image.LANCZOS))
            self.logo_h_id = cv.create_image(60, 30, anchor="nw", image=self.logo_h)
        cv.create_text(150, 56, anchor="w", text="KÜNEFECRAFT", fill=FG, font=(FONT, 22, "bold"))
        self.online_id = cv.create_text(150, 88, anchor="w", text="● Kontrol ediliyor...", fill=MUTED, font=(FONT, 11))
        # hesap butonu
        self.btn_acc = CButton(cv, 850, 34, 210, 66, "", self.toggle_acc, "dark", 12, 16)
        self.acc_head_id = cv.create_image(864, 44, anchor="nw")
        self.acc_name_id = cv.create_text(916, 62, anchor="w", text="", fill=FG, font=(FONT, 13, "bold"))
        self.btn_acc.attach(self.acc_head_id)
        self.btn_acc.attach(self.acc_name_id)
        self.kp_id = cv.create_text(916, 82, anchor="w", text="", fill=ACCENT_H, font=(FONT, 10, "bold"))
        self.btn_acc.attach(self.kp_id)
        # duyuru slaytı
        self.slide_ph = ImageTk.PhotoImage(make_slide(self.hero_pil, 780, 310))
        cv.create_image(160 - PAD, 118 - PAD, anchor="nw", image=self.slide_ph)
        cv.create_rectangle(200, 146, 292, 172, fill=ACCENT, outline="")
        cv.create_text(246, 159, text="DUYURU", fill="#2a1604", font=(FONT, 10, "bold"))
        self.sl_title = cv.create_text(200, 232, anchor="w", text="", fill="#ffffff", font=(FONT, 28, "bold"), width=700)
        self.sl_text = cv.create_text(200, 262, anchor="nw", text="", fill="#dfe4ec", font=(FONT, 13), width=680)
        self.btn_prev = CButton(cv, 62, 243, 60, 60, "❮", lambda: self.slide_move(-1), "dark", 16, 30)
        self.btn_next = CButton(cv, 978, 243, 60, 60, "❯", lambda: self.slide_move(1), "dark", 16, 30)
        # bilgi hapları
        pills = [(f"🔒  {DEFAULT_SERVER}", 270), (f"Minecraft {VERSION}  •  Fabric", 250),
                 ("⚡ FPS modları  •  🎙 Voice Chat  •  🇹🇷", 270)]
        x = (W - (sum(w for _, w in pills) + 16 * (len(pills) - 1))) // 2
        for text, pw in pills:
            rrect(cv, x, 446, x + pw, 482, 16, fill="#121823", outline="#2a3345")
            cv.create_text(x + pw / 2, 464, text=text, fill="#c9d1de", font=(FONT, 10))
            x += pw + 16
        # alt butonlar
        CButton(cv, 72, 528, 150, 56, "Skin", lambda: self.show("skin"), "dark", 12, 14)
        CButton(cv, 236, 528, 150, 56, "Ayarlar", lambda: self.show("settings"), "dark", 12, 14)
        self.btn_play = CButton(cv, 400, 512, 300, 88, "OYNA!", self.on_play, "primary", 26, 18)
        _WARM.append((300, 88, "off", "n", 18))
        CButton(cv, 714, 528, 150, 56, "Mod Yöneticisi", lambda: self.show("mods"), "dark", 12, 14)
        CButton(cv, 878, 528, 150, 56, "💬 Arkadaşlar", self.open_social, "dark", 12, 14)
        # durum + ilerleme
        self.status_id = cv.create_text(550, 636, text="", fill=MUTED, font=(FONT, 11), width=760)
        self.prog_bg = cv.create_rectangle(300, 658, 800, 664, fill="#262e3b", outline="", state="hidden")
        self.prog_fg = cv.create_rectangle(300, 658, 300, 664, fill=ACCENT, outline="", state="hidden")
        cv.bind("<Button-1>", self._home_click, add="+")
        self._draw_slide()

    def _home_click(self, e):
        if not self.acc_open:
            return
        cur = self.cv.find_withtag("current")
        tags = self.cv.gettags(cur[0]) if cur else ()
        if "accpop" in tags or self.btn_acc.tag in tags:
            return
        self.close_acc()

    def _refresh_header(self):
        self.cv.itemconfig(self.acc_name_id, text=self.user or "Giriş yap")
        ph = self.head_ph(self.user or "_", 42)
        self.cv.itemconfig(self.acc_head_id, image=ph)
        self.fetch_head(self.user)
        self.fetch_kp()

    def fetch_kp(self):
        """Siteden KünefePoint bakiyesini okur (site kapalıysa sessizce boş bırakır)."""
        name = self.user
        if not name or not re.fullmatch(r"\w{1,16}", name):
            self.cv.itemconfig(self.kp_id, text="")
            return

        def work():
            try:
                d = http_json(SITE_URL + "/kp.php?a=me&user=" + urllib.parse.quote(name.lower()))
                txt = f"{int(d.get('kp', 0))} KP" if d.get("ok") else ""
            except Exception:
                txt = ""
            self.after(0, lambda: name == self.user and self.cv.itemconfig(self.kp_id, text=txt))
        threading.Thread(target=work, daemon=True).start()

    # --- hesap paneli (açılır)
    def toggle_acc(self):
        if self.acc_open:
            self.close_acc()
        else:
            self.open_acc()

    def close_acc(self):
        self.acc_open = False
        if "home" in self.pages:
            self.cv.delete("accpop")
            for b in getattr(self, "acc_btns", []):
                b.cv.delete(b.tag)
            self.acc_btns = []

    def open_acc(self):
        cv = self.cv
        cv.delete("accpop")
        for b in getattr(self, "acc_btns", []):
            cv.delete(b.tag)
        self.acc_btns = []
        self.acc_open = True
        accs = self.accounts()
        rows = max(1, len(accs))
        ph_h = 70 + rows * 58 + 70
        x0, y0, w = 770, 112, 290
        ph = ImageTk.PhotoImage(make_panel(w, ph_h, 16, (24, 30, 41)))
        self.keep.append(ph)
        self.acc_panel_img = ph
        cv.create_image(x0 - PAD, y0 - PAD, anchor="nw", image=ph, tags=("accpop",))
        cv.create_text(x0 + 22, y0 + 28, anchor="w", text="Hesaplar", fill=FG, font=(FONT, 13, "bold"), tags=("accpop",))
        for i, a in enumerate(accs):
            ry = y0 + 60 + i * 58
            active = a == self.user
            r = rrect(cv, x0 + 14, ry, x0 + w - 14, ry + 50, 10, fill="#1f3a2c" if active else "#232b3a",
                      outline="#2f6b49" if active else BORDER, tags=("accpop",))
            hp = self.head_ph(a, 34)
            hi = cv.create_image(x0 + 26, ry + 8, anchor="nw", image=hp, tags=("accpop",))
            tx = cv.create_text(x0 + 70, ry + 25, anchor="w", text=a, fill=FG, font=(FONT, 12), tags=("accpop",))
            for it in (r, hi, tx):
                cv.tag_bind(it, "<Button-1>", lambda e, a=a: self.switch_account(a))
            self.fetch_head(a)
            xb = CButton(cv, x0 + w - 62, ry + 7, 40, 40, "✕", lambda a=a: self.remove_account(a), "danger", 11, 10)
            for it in (xb.img, xb.txt):
                cv.addtag_withtag("accpop", it)
            self.acc_btns.append(xb)
        if not accs:
            cv.create_text(x0 + w / 2, y0 + 86, text="Kayıtlı hesap yok", fill=MUTED, font=(FONT, 11), tags=("accpop",))
        ab = CButton(cv, x0 + 20, y0 + ph_h - 66, w - 40, 46, "+ Hesap Ekle", self._add_acc_clicked, "dark", 11, 12)
        for it in (ab.img, ab.txt):
            cv.addtag_withtag("accpop", it)
        self.acc_btns.append(ab)
        cv.tag_raise("accpop")

    def _add_acc_clicked(self):
        self.close_acc()
        self.show("login")
        self.e_user.delete(0, "end")

    # --- duyuru slaytı
    def _draw_slide(self, animate=False):
        cv = self.cv
        if not self.slides:
            return
        self.slide_i %= len(self.slides)
        s = self.slides[self.slide_i]
        cv.itemconfig(self.sl_title, text=s.get("title", ""))
        cv.itemconfig(self.sl_text, text=s.get("text", ""))
        cv.delete("dot")
        n = len(self.slides)
        x = 550 - ((n - 1) * 26 + 12) / 2
        for i in range(n):
            if i == self.slide_i:
                cv.create_oval(x - 11, 403, x + 11, 413, fill=ACCENT, outline="", tags="dot")
            else:
                cv.create_oval(x - 4, 404, x + 4, 412, fill="#6b7385", outline="", tags="dot")
            x += 26
        self.anim_id += 1
        if animate and self.fx_on:
            self._slide_anim(self.anim_id, 0)
        else:
            cv.coords(self.sl_title, 200, 232)
            cv.coords(self.sl_text, 200, 262)
            cv.itemconfig(self.sl_title, fill="#ffffff")
            cv.itemconfig(self.sl_text, fill="#dfe4ec")

    def _slide_anim(self, aid, i, n=9):
        if aid != self.anim_id or self.page != "home":
            return
        t = min(1.0, i / n)
        e = 1 - (1 - t) ** 3
        x = 200 + 46 * (1 - e)
        self.cv.coords(self.sl_title, x, 232)
        self.cv.coords(self.sl_text, x + 8, 262)
        self.cv.itemconfig(self.sl_title, fill=mix((40, 44, 56), (255, 255, 255), e))
        self.cv.itemconfig(self.sl_text, fill=mix((40, 44, 56), (223, 228, 236), e))
        if i < n:
            self.after(26, lambda: self._slide_anim(aid, i + 1, n))

    def slide_move(self, d):
        self.slide_i = (self.slide_i + d) % max(1, len(self.slides))
        self._draw_slide(animate=True)
        self._schedule_rot()

    def _schedule_rot(self):
        if self.rot_job:
            try:
                self.after_cancel(self.rot_job)
            except Exception:
                pass
        self.rot_job = self.after(6500, self._auto_rot)

    def _auto_rot(self):
        if self.page == "home" and len(self.slides) > 1:
            self.slide_i = (self.slide_i + 1) % len(self.slides)
            self._draw_slide(animate=True)
        self._schedule_rot()

    # --- animasyon motoru (hafif: önceden çizilmiş görseller + birkaç küçük öğe)
    def embers_for(self, cv):
        import random
        items = []
        for _ in range(16):
            r = random.choice((1.5, 2, 2.5, 3))
            x, y = random.uniform(0, W), random.uniform(0, H)
            it = cv.create_oval(x - r, y - r, x + r, y + r, fill=random.choice(EMBER_COLS), outline="")
            items.append([it, x, y, r, random.uniform(0.5, 1.4), random.uniform(0, 6.28)])
        self.embers[cv] = items

    def _make_glows(self):
        try:
            self.glow_imgs = [ImageTk.PhotoImage(make_glow(460, 230, 0.16 + 0.07 * i)) for i in range(6)]
            self.cv.itemconfig(self.play_glow, image=self.glow_imgs[0])
        except Exception:
            self.glow_imgs = []

    def _fx_tick(self):
        import math
        import random
        now = time.perf_counter()
        dt = now - self.fx_last
        self.fx_last = now
        if self.fx_on and self.page in ("home", "login", "skin", "social"):
            # bilgisayar yavşsa efektleri kendiliğinden kapat
            self.fx_slow = self.fx_slow + 1 if dt > 0.22 else max(0, self.fx_slow - 1)
            if self.fx_slow > 14:
                self.fx_on = False
                for cv, items in self.embers.items():
                    for it in items:
                        cv.itemconfig(it[0], state="hidden")
                if self.glow_imgs:
                    self.cv.itemconfig(self.play_glow, state="hidden")
            else:
                cv = self.pages[self.page]
                for it in self.embers.get(cv, []):
                    it[2] -= it[4]
                    it[1] += math.sin(now * 0.9 + it[5]) * 0.5
                    if it[2] < -8:
                        it[2], it[1] = H + 8, random.uniform(0, W)
                    r = it[3]
                    cv.coords(it[0], it[1] - r, it[2] - r, it[1] + r, it[2] + r)
                bob = math.sin(now * 1.7) * 3
                if self.page == "home":
                    if self.logo_h_id is not None:
                        cv.coords(self.logo_h_id, 60, 30 + bob)
                    if self.glow_imgs and not self.busy:
                        k = int((math.sin(now * 2.2) + 1) / 2 * (len(self.glow_imgs) - 1) + 0.5)
                        if k != self.glow_idx:
                            self.glow_idx = k
                            cv.itemconfig(self.play_glow, image=self.glow_imgs[k], state="normal")
                elif self.page == "login" and self.login_logo is not None:
                    cv.coords(self.login_logo, 550, 150 + bob)
                elif self.page == "skin":
                    self._sk_tick(now)
        self.after(50, self._fx_tick)

    def _start_warm(self):
        if not self.warming and _WARM:
            self.warming = True
            self.after(30, self._warm_next)

    def _warm_next(self):
        if _WARM:
            w, h, st, state, r = _WARM.pop(0)
            try:
                btn_ph(w, h, st, state, r)
            except Exception:
                pass
            self.after(14, self._warm_next)
        else:
            self.warming = False

    # --- arka plan işleri (açılışı kastırmasın diye hepsi thread'de)
    def _late_init(self):
        threading.Thread(target=self._bg_init, daemon=True).start()
        self.after(150, self._make_glows)
        self.after(500, self._start_warm)
        self.after(300, self._fx_tick)
        if "--prefetch" not in sys.argv:
            self.after(3000, self.bootstrap_mods)
        self.after(1500, self.refresh_server_status)
        if self.user:
            self._soc_bg(lambda: self.cloud("/hello"))
        if self.cfg.get("seen_version") != APP_VERSION:
            self.cfg["seen_version"] = APP_VERSION
            save_cfg(self.cfg)
            self.after(1200, self.celebrate)
        if self.user:
            self.fetch_head(self.user)

    def _bg_init(self):
        try:
            self.is_installed = self.quick_installed()
        except Exception:
            pass
        try:
            data = http_json(ANNOUNCE_URL)
            if isinstance(data, list):
                items = [d for d in data if isinstance(d, dict) and d.get("title")]
                if items:
                    keep = [a for a in ANNOUNCEMENTS if a["title"].startswith(("Müzik", "Sadece KünefeLauncher"))]
                    have = {i.get("title") for i in items}
                    items = items + [a for a in keep if a["title"] not in have]
                    self.slides = items[:8]
                    self.after(0, self._draw_slide)
        except Exception:
            pass
        self.after(0, self._set_ready_status)

    def _set_ready_status(self):
        if not self.busy:
            if self.is_installed:
                self.cv.itemconfig(self.status_id, text="✔ Sürüm yüklü, oyuna hazır!", fill=OK)
            else:
                self.cv.itemconfig(self.status_id, text="İlk açılışta oyun, Java ve modlar otomatik indirilir.", fill=MUTED)

    def quick_installed(self):
        vd = os.path.join(MC_DIR, "versions")
        ok = False
        if os.path.isdir(vd):
            for d in os.listdir(vd):
                if d.startswith("fabric-loader") and d.endswith(VERSION) and os.path.isfile(os.path.join(vd, d, d + ".json")):
                    ok = True
        md = os.path.join(MC_DIR, "mods")
        return ok and os.path.isdir(md) and any(f.endswith(".jar") for f in os.listdir(md))

    def refresh_server_status(self):
        threading.Thread(target=self._check_server, daemon=True).start()
        self.after(30000, self.refresh_server_status)

    def _check_server(self):
        host, port = DEFAULT_SERVER.split(":")
        try:
            self.srv = ping_server(host, int(port))
        except Exception:
            self.srv = False
        self.after(0, self._srv_changed)

    def _srv_changed(self):
        if self.srv:
            self.cv.itemconfig(self.online_id, text=f"● {self.srv[0]} Oyuncu Oyunda!  ({self.srv[2]} ms)", fill=OK)
        else:
            self.cv.itemconfig(self.online_id, text="● Sunucuya ulaşılamadı", fill=BAD)

    # ----------------------------------------------------------------- SKİN
    def skin_record(self, name=None):
        return self.cfg.get("skins", {}).get(name or self.user)

    def apply_skin_pack(self):
        """Seçili skin'i oyunda GÖRÜNÜR yapan kaynak paketini yazar (çevrimdışı hesaplarda varsayılan skin'ler değişir)."""
        rp_dir = os.path.join(MC_DIR, "resourcepacks")
        path = os.path.join(rp_dir, SKIN_PACK)
        self.install_ready()
        rec = self.skin_record()
        self.skin_pack_active = False
        try:
            if rec and os.path.isfile(rec.get("file", "")):
                sk = norm_skin(Image.open(rec["file"]))
                slim_now = bool(rec.get("slim"))
                classic = convert_arms(sk, False) if slim_now else sk
                slim = sk if slim_now else convert_arms(sk, True)
                blobs = {}
                for key, im in (("wide", classic), ("slim", slim)):
                    b = io.BytesIO()
                    im.save(b, "PNG")
                    blobs[key] = b.getvalue()
                os.makedirs(rp_dir, exist_ok=True)
                tmp = path + ".part"
                with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
                    z.writestr("pack.mcmeta", json.dumps({"pack": {
                        "pack_format": 46, "supported_formats": {"min_inclusive": 34, "max_inclusive": 75},
                        "description": f"{SERVER_NAME} skin ({self.user})"}}))
                    base = "assets/minecraft/textures/entity/"
                    for model in ("wide", "slim"):
                        for n in DEFAULT_SKIN_NAMES:
                            z.writestr(f"{base}player/{model}/{n}.png", blobs[model])
                    z.writestr(base + "steve.png", blobs["wide"])
                    z.writestr(base + "alex.png", blobs["slim"])
                os.replace(tmp, path)
                self.skin_pack_active = True
            elif os.path.exists(path):
                os.remove(path)
        except Exception:
            log_crash("skin pack: " + traceback.format_exc())

    def _build_skin(self):
        cv = self.new_page("skin")
        self.cv_sk = cv
        self.embers_for(cv)
        CButton(cv, 30, 24, 150, 46, "← Ana Menü", lambda: self.show("home"), "dark", 11, 12)
        CButton(cv, 200, 24, 190, 46, "🛒 Skin Mağazası", self.sk_store, "primary", 11, 12)
        cv.create_text(550, 46, text="SKİN", fill=FG, font=(FONT, 20, "bold"))
        # sol: 3D görüntüleyici
        self.panel(cv, 60, 90, 400, 540)
        self.sk_view = cv.create_image(260, 330)
        self.sk_msg = cv.create_text(260, 330, text="Hazırlanıyor...", fill=MUTED, font=(FONT, 12))
        cv.create_text(260, 566, text="Sürükleyerek döndür", fill=MUTED, font=(FONT, 10))
        self.btn_spin = CButton(cv, 170, 580, 180, 38, "⏸ Dönmeyi Durdur", self.sk_toggle_spin, "dark", 10, 12)
        cv.tag_bind(self.sk_view, "<ButtonPress-1>", self._sk_press)
        cv.tag_bind(self.sk_view, "<B1-Motion>", self._sk_motion)
        cv.tag_bind(self.sk_view, "<ButtonRelease-1>", self._sk_release)
        cv.tag_bind(self.sk_view, "<Enter>", lambda e: cv.config(cursor="fleur"))
        cv.tag_bind(self.sk_view, "<Leave>", lambda e: cv.config(cursor=""))
        # sağ: işlemler
        self.panel(cv, 490, 90, 550, 540, flat=True)
        x = 516
        cv.create_text(x, 116, anchor="w", text="Skin Ekle", fill=FG, font=(FONT, 14, "bold"))
        CButton(cv, x, 138, 242, 46, "📁 PNG Seç", self.sk_pick, "dark", 11, 12)
        CButton(cv, x + 256, 138, 242, 46, "↺ Varsayılana Dön", self.sk_reset, "dark", 11, 12)
        cv.create_text(x, 206, anchor="w", text="Ya da oyuncu adından al (orijinal hesap skin'i):", fill=MUTED, font=(FONT, 10))
        self.e_skname = tk.Entry(cv, bg="#232b3a", fg=FG, insertbackground=FG, relief="flat", font=(FONT, 12),
                                 highlightthickness=2, highlightbackground=BORDER, highlightcolor=ACCENT, bd=0)
        cv.create_window(x + 135, 246, window=self.e_skname, width=270, height=40)
        self.e_skname.bind("<Return>", lambda e: self.sk_fetch())
        CButton(cv, x + 284, 224, 214, 44, "⬇ Skin'ini Getir", self.sk_fetch, "dark", 11, 12)
        cv.create_text(x, 290, anchor="w", text="Model", fill=FG, font=(FONT, 12, "bold"))
        self.btn_classic = CButton(cv, x, 308, 242, 42, "Klasik (4 px kol)", lambda: self.sk_set_model(False), "primary", 11, 12)
        self.btn_slim = CButton(cv, x + 256, 308, 242, 42, "Slim (3 px kol)", lambda: self.sk_set_model(True), "dark", 11, 12)
        CButton(cv, x, 366, 498, 56, "✔ Kaydet ve Oyunda Uygula", self.sk_save, "ok", 13, 14)
        cv.create_line(x, 440, x + 498, 440, fill="#2a3342")
        cv.create_text(x, 460, anchor="w", text="Sunucuda da görün", fill=FG, font=(FONT, 14, "bold"))
        cv.create_text(x + 498, 462, anchor="e", text="sunucuda SkinsRestorer gerekir", fill=MUTED, font=(FONT, 9))
        rrect(cv, x, 482, x + 498, 520, 10, fill="#10151e", outline=BORDER)
        self.sk_cmd = cv.create_text(x + 12, 501, anchor="w", text="", fill="#c9d1de", font=("Consolas", 9))
        CButton(cv, x, 530, 242, 46, "☁ Sunucuya Gönder", self.sk_upload, "primary", 11, 12)
        CButton(cv, x + 256, 530, 242, 46, "⧉ Komutu Kopyala", self.sk_copy, "dark", 11, 12)
        self.sk_status = cv.create_text(x + 249, 604, text="", fill=MUTED, font=(FONT, 10), width=480)

    def sk_store(self):
        """Skin mağazası: sitenin skin listesinden (skins.json) ya da hazır listeden skin seçip indir."""
        win = tk.Toplevel(self)
        win.title("Skin Mağazası")
        win.configure(bg=BG)
        win.geometry("360x470")
        tk.Label(win, text="Skin Mağazası", bg=BG, fg=FG, font=(FONT, 14, "bold")).pack(pady=(14, 4))
        tk.Label(win, text="Bir skin seç ve indir (oyuncu adından alınır)", bg=BG, fg=MUTED, font=(FONT, 9)).pack()
        lb = tk.Listbox(win, bg="#232b3a", fg=FG, selectbackground=ACCENT, font=(FONT, 12), relief="flat", height=14)
        lb.pack(fill="both", expand=True, padx=16, pady=10)
        names = ["Dream", "Notch", "jeb_", "Dinnerbone", "Grian", "Mumbo", "Sapnap", "TommyInnit", "Philza", "Skeppy"]
        for n in names:
            lb.insert("end", n)

        def fill(lst):
            if lst:
                lb.delete(0, "end")
                for n in lst:
                    lb.insert("end", n)

        def load():
            try:
                with urllib.request.urlopen(urllib.request.Request(SITE_URL + "/skins.json", headers={"User-Agent": UA}), timeout=6) as r:
                    lst = [x for x in json.loads(r.read().decode("utf-8")) if re.fullmatch(r"\w{1,16}", str(x))]
                self.after(0, lambda: fill(lst))
            except Exception:
                pass
        threading.Thread(target=load, daemon=True).start()

        def pick():
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0])
            self.e_skname.delete(0, "end")
            self.e_skname.insert(0, name)
            win.destroy()
            self.sk_fetch()
        lb.bind("<Double-Button-1>", lambda e: pick())
        tk.Button(win, text="⬇ Skin'i İndir", command=pick, bg=ACCENT, fg="#101010", relief="flat", font=(FONT, 11, "bold")).pack(pady=(0, 14), ipadx=14, ipady=4)

    def _sk_set_status(self, text, color=MUTED):
        self.cv_sk.itemconfig(self.sk_status, text=text, fill=color)

    def _skin_open(self):
        rec = self.skin_record()
        self.e_skname.delete(0, "end")
        self.e_skname.insert(0, self.user or "")
        self._sk_set_status("")
        img = None
        slim = False
        if rec and os.path.isfile(rec.get("file", "")):
            try:
                img = norm_skin(Image.open(rec["file"]))
                slim = bool(rec.get("slim", detect_slim(img)))
            except Exception:
                img = None
        if img is None:
            img = default_skin()
            if self.user:  # kullanıcı adının skin'ini internetten getir (yoksa Steve gelir)
                threading.Thread(target=self._sk_fetch_work, args=(self.user, True), daemon=True).start()
        self._sk_is_default = True
        self.sk_img, self.sk_slim = img, slim
        self._sk_update_model_buttons()
        self._sk_update_cmd()
        self._sk_render()

    def _sk_update_model_buttons(self):
        self.btn_classic.set_style("dark" if self.sk_slim else "primary")
        self.btn_slim.set_style("primary" if self.sk_slim else "dark")

    def _sk_update_cmd(self):
        rec = self.skin_record()
        if rec and rec.get("uploaded"):
            txt = f"/skin url {SKIN_BASE_URL}{rec['sid']}.png?v={rec.get('ver', 1)}"
        else:
            txt = "Önce Kaydet'e, sonra 'Sunucuya Gönder'e bas."
        self.cv_sk.itemconfig(self.sk_cmd, text=txt)

    def _sk_render(self):
        if self.sk_img is None:
            return
        self.sk_token += 1
        tok = self.sk_token
        skin, slim = self.sk_img.copy(), self.sk_slim
        self.cv_sk.itemconfig(self.sk_msg, state="normal")

        def work():
            try:
                frames = render_frames(skin, slim, 36)
            except Exception:
                log_crash("skin render: " + traceback.format_exc())
                return
            self.after(0, lambda: self._sk_frames_ready(tok, frames))
        threading.Thread(target=work, daemon=True).start()

    def _sk_frames_ready(self, tok, frames):
        if tok != self.sk_token:
            return
        self._sk_pending, self._sk_new = frames, []
        self._sk_convert(tok)

    def _sk_convert(self, tok):
        if tok != self.sk_token:
            return
        for _ in range(6):
            i = len(self._sk_new)
            if i >= len(self._sk_pending):
                break
            self._sk_new.append(ImageTk.PhotoImage(self._sk_pending[i]))
        if len(self._sk_new) < len(self._sk_pending):
            self.after(8, lambda: self._sk_convert(tok))
        else:
            self.sk_ph, self._sk_pending = self._sk_new, []
            self.sk_idx = -1
            self.cv_sk.itemconfig(self.sk_msg, state="hidden")
            self._sk_show(self.sk_angle)

    def _sk_show(self, angle):
        if not self.sk_ph:
            return
        self.sk_angle = angle % 360.0
        idx = int(round(self.sk_angle / (360.0 / len(self.sk_ph)))) % len(self.sk_ph)
        if idx != self.sk_idx:
            self.sk_idx = idx
            self.cv_sk.itemconfig(self.sk_view, image=self.sk_ph[idx])

    def _sk_tick(self, now):
        import math
        if self.sk_ph and self.sk_spin and self.sk_drag is None and now > self.sk_idle:
            self._sk_show(self.sk_angle + 3.0)
        self.cv_sk.coords(self.sk_view, 260, 330 + math.sin(now * 1.7) * 2)

    def _sk_press(self, e):
        self.sk_drag = e.x

    def _sk_motion(self, e):
        if self.sk_drag is None:
            return
        self._sk_show(self.sk_angle + (e.x - self.sk_drag) * 1.1)
        self.sk_drag = e.x

    def _sk_release(self, e):
        self.sk_drag = None
        self.sk_idle = time.perf_counter() + 2.0

    def sk_toggle_spin(self):
        self.sk_spin = not self.sk_spin
        self.btn_spin.set_text("⏸ Dönmeyi Durdur" if self.sk_spin else "▶ Döndür")

    def sk_set_model(self, slim):
        if self.sk_img is None or slim == self.sk_slim:
            return
        self.sk_slim = slim
        self._sk_update_model_buttons()
        self._sk_render()

    def _sk_load(self, im, source):
        self._sk_is_default = False
        try:
            img = norm_skin(im)
        except ValueError as e:
            self._sk_set_status(str(e), BAD)
            return
        self.sk_img = img
        self.sk_slim = detect_slim(img)
        self._sk_update_model_buttons()
        self._sk_render()
        self._sk_set_status(f"{source} yüklendi. Beğendiysen Kaydet'e bas.", OK)

    def sk_pick(self):
        path = filedialog.askopenfilename(title="Skin PNG seç", filetypes=[("PNG skin", "*.png"), ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            im = Image.open(path)
            im.load()
        except Exception:
            self._sk_set_status("Bu dosya okunamadı. Geçerli bir PNG seç.", BAD)
            return
        self._sk_load(im, "Skin")

    def sk_fetch(self):
        n = self.e_skname.get().strip()
        if not re.fullmatch(r"\w{1,16}", n):
            self._sk_set_status("Geçerli bir oyuncu adı yaz.", BAD)
            return
        self._sk_set_status("Skin getiriliyor...", ACCENT_H)
        threading.Thread(target=self._sk_fetch_work, args=(n, False), daemon=True).start()

    def _sk_fetch_work(self, name, silent):
        try:
            im = Image.open(io.BytesIO(http_bytes("https://minotar.net/skin/" + urllib.parse.quote(name), 15)))
            im.load()
        except Exception:
            if not silent:
                self.after(0, lambda: self._sk_set_status("Skin getirilemedi. İnternetini veya adı kontrol et.", BAD))
            return

        def done():
            if self.page != "skin":
                return
            if silent and (self.skin_record() or not self._sk_is_default):
                return
            self._sk_load(im, name + " skin'i") if not silent else self._sk_load_silent(im)
        self.after(0, done)

    _sk_is_default = True

    def _sk_load_silent(self, im):
        try:
            img = norm_skin(im)
        except ValueError:
            return
        self.sk_img, self.sk_slim = img, detect_slim(img)
        self._sk_update_model_buttons()
        self._sk_render()

    def sk_reset(self):
        rec = self.cfg.get("skins", {}).pop(self.user, None)
        if rec:
            try:
                os.remove(rec.get("file", ""))
            except Exception:
                pass
            save_cfg(self.cfg)
        self.apply_skin_pack()
        self.sk_img, self.sk_slim = default_skin(), False
        self._sk_update_model_buttons()
        self._sk_update_cmd()
        self._sk_render()
        self._sk_set_status("Varsayılan skin'e dönüldü. Oyunu yeniden başlatınca geçerli olur.", OK)

    def sk_save(self):
        if self.sk_img is None or not self.user:
            return
        d = os.path.join(BASE_DIR, "skins")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, self.user + ".png")
        try:
            self.sk_img.save(path, "PNG")
        except Exception:
            self._sk_set_status("Skin kaydedilemedi.", BAD)
            return
        old = self.skin_record() or {}
        self.cfg.setdefault("skins", {})[self.user] = {
            "file": path, "slim": bool(self.sk_slim), "sid": old.get("sid") or _uuid.uuid4().hex[:16],
            "ver": old.get("ver", 0), "uploaded": False}
        save_cfg(self.cfg)
        self.apply_skin_pack()
        self._sk_update_cmd()
        self._sk_set_status("✔ Kaydedildi. Oyunu açınca skin'in görünür. Sunucuda görünmesi için 'Sunucuya Gönder'e bas.", OK)

    def sk_upload(self):
        rec = self.skin_record()
        if not rec or not os.path.isfile(rec.get("file", "")):
            self._sk_set_status("Önce 'Kaydet ve Oyunda Uygula'ya bas.", BAD)
            return
        self._sk_set_status("Sunucuya gönderiliyor...", ACCENT_H)
        threading.Thread(target=self._sk_upload_work, args=(rec["file"], rec["sid"], self.user), daemon=True).start()

    def _sk_upload_work(self, path, sid, user):
        try:
            with open(path, "rb") as f:
                data = f.read()
            res = http_post_multipart(SKIN_API, {"id": sid}, {"file": ("skin.png", data, "image/png")})
            ok = bool(isinstance(res, dict) and res.get("ok"))
            msg = res.get("message") if isinstance(res, dict) else None
        except urllib.error.HTTPError as e:
            ok, msg = False, f"Skin sunucusu hata verdi (HTTP {e.code})."
        except json.JSONDecodeError:
            ok, msg = False, "Skin sunucusu geçersiz yanıt verdi. Sitedeki skin.php dosyasını kontrol et."
        except Exception:
            ok, msg = False, "Skin sunucusuna ulaşılamadı. İnternetini kontrol et."

        def done():
            rec = self.skin_record(user)
            if ok and rec:
                rec["ver"] = rec.get("ver", 0) + 1
                rec["uploaded"] = True
                save_cfg(self.cfg)
                if self.page == "skin":
                    self._sk_update_cmd()
                    self._sk_set_status("✔ Gönderildi! 'Komutu Kopyala'ya bas, oyunda T'ye basıp yapıştır ve Enter'la.", OK)
            elif self.page == "skin":
                self._sk_set_status(msg or "Gönderilemedi.", BAD)
        self.after(0, done)

    def sk_copy(self):
        rec = self.skin_record()
        if not rec or not rec.get("uploaded"):
            self._sk_set_status("Önce Kaydet'e, sonra 'Sunucuya Gönder'e bas.", BAD)
            return
        cmd = f"/skin url {SKIN_BASE_URL}{rec['sid']}.png?v={rec.get('ver', 1)}"
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self._sk_set_status("Kopyalandı! Oyunda T'ye bas, Ctrl+V ile yapıştır, Enter'a bas.", OK)

    # ----------------------------------------------------------------- AYARLAR
    def _build_settings(self):
        cv = self.new_page("settings")
        self.cv_set = cv
        cv.create_text(550, 46, text="AYARLAR", fill=FG, font=(FONT, 20, "bold"))
        self.panel(cv, 90, 80, 920, 520, flat=True)
        x = 130
        cv.create_text(x, 116, anchor="w", text="Bellek (RAM)", fill=FG, font=(FONT, 14, "bold"))
        cv.create_text(x, 144, anchor="w", text="Minecraft için ayrılacak belleği seç. Çok düşük RAM takılmaya neden olabilir.",
                       fill=MUTED, font=(FONT, 10))
        self.max_ram = max(2048, min(16384, (total_ram_mb() - 2048) // 256 * 256))
        self.ram_var = tk.IntVar(value=4096)
        self.scale = tk.Scale(cv, from_=1024, to=self.max_ram, resolution=256, orient="horizontal", showvalue=0,
                              variable=self.ram_var, bg=CARD, troughcolor="#2f394a", activebackground=ACCENT_H,
                              highlightthickness=0, bd=0, sliderrelief="flat", sliderlength=26, width=10,
                              fg=FG, cursor="hand2")
        cv.create_window(x, 190, window=self.scale, anchor="w", width=700, height=30)
        self.e_ram = tk.Entry(cv, textvariable=self.ram_var, bg="#232b3a", fg=FG, insertbackground=FG, relief="flat",
                              font=(FONT, 13), justify="center", highlightthickness=2, highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        cv.create_window(870, 190, window=self.e_ram, width=110, height=40)
        cv.create_text(930, 190, anchor="w", text="MB", fill=MUTED, font=(FONT, 11))
        cv.create_line(x, 232, 970, 232, fill="#2a3342")
        cv.create_text(x, 262, anchor="w", text="Grafik", fill=FG, font=(FONT, 14, "bold"))
        cv.create_text(x, 296, anchor="w", text="Düşük Grafik", fill=FG, font=(FONT, 12))
        cv.create_text(x, 318, anchor="w", text="Görüntü mesafesi ve efektleri kısar; zayıf bilgisayarlarda FPS'i artırır.",
                       fill=MUTED, font=(FONT, 10))
        self.tg_low = Toggle(cv, bool(self.cfg.get("low_gfx")), lambda v: None)
        cv.create_window(940, 306, window=self.tg_low)
        cv.create_line(x, 352, 970, 352, fill="#2a3342")
        cv.create_text(x, 382, anchor="w", text="Oyun", fill=FG, font=(FONT, 14, "bold"))
        cv.create_text(x, 408, anchor="w", text="Oyun dili Türkçe, sunucu KünefeCraft olarak sabittir.", fill=MUTED, font=(FONT, 10))
        CButton(cv, x, 436, 230, 50, "Mod Klasörünü Aç", lambda: self.open_folder("mods"), "dark", 11, 12)
        CButton(cv, x + 245, 436, 230, 50, "Oyun Klasörünü Aç", self.open_folder, "dark", 11, 12)
        CButton(cv, x + 490, 436, 230, 50, "Dosyaları Onar", self.repair, "dark", 11, 12)
        self.set_msg = cv.create_text(550, 520, text="", fill=OK, font=(FONT, 11))
        CButton(cv, 130, 530, 130, 50, "Geri", lambda: self.show("home"), "dark", 12, 12)
        CButton(cv, 840, 530, 130, 50, "Kaydet", self.save_settings, "primary", 12, 12)

    def _load_settings_values(self):
        mb = self.cfg.get("ram_mb") or int(self.cfg.get("ram", 4)) * 1024
        self.ram_var.set(max(1024, min(self.max_ram, int(mb))))
        self.tg_low.value = bool(self.cfg.get("low_gfx"))
        self.tg_low._draw()
        self.cv_set.itemconfig(self.set_msg, text="")

    def save_settings(self):
        try:
            mb = int(self.ram_var.get())
        except Exception:
            mb = 4096
        mb = max(1024, min(self.max_ram, mb))
        self.ram_var.set(mb)
        self.cfg["ram_mb"] = mb
        self.cfg["low_gfx"] = bool(self.tg_low.value)
        save_cfg(self.cfg)
        self.cv_set.itemconfig(self.set_msg, text="✔ Kaydedildi", fill=OK)

    def repair(self):
        self.cfg["setup_done"] = False
        self.cfg["mods_checked"] = 0
        save_cfg(self.cfg)
        self.cv_set.itemconfig(self.set_msg, text="Sonraki OYNA'da tüm dosyalar yeniden doğrulanacak.", fill=ACCENT_H)

    # ----------------------------------------------------------------- MOD YÖNETİCİSİ
    def _build_mm(self):
        cv = self.new_page("mods")
        self.cv_mm = cv
        CButton(cv, 30, 24, 150, 46, "← Ana Menü", lambda: self.show("home"), "dark", 11, 12)
        self.panel(cv, 60, 90, 980, 560, flat=True)
        cv.create_text(96, 124, anchor="w", text="MOD YÖNETİCİSİ", fill=FG, font=(FONT, 16, "bold"))
        cv.create_text(96, 154, anchor="w", text="Yüklü modları aç/kapat veya Modrinth üzerinden yenilerini indir.", fill=MUTED, font=(FONT, 11))
        self.mm_count = cv.create_text(96, 180, anchor="w", text="", fill=ACCENT_H, font=(FONT, 11, "bold"))
        self.mm_tabs = {}
        for i, (key, label, _) in enumerate(MM_TABS):
            b = CButton(cv, 96 + i * 190, 206, 180, 46, label, lambda k=key: self.mm_select(k),
                        "primary" if key == self.mm_type else "dark", 11, 12)
            self.mm_tabs[key] = b
        CButton(cv, 770, 206, 240, 46, "⬇ Modrinth'ten İndir", self.open_store, "ok", 11, 12)
        self.mm_hint = cv.create_text(96, 276, anchor="w", text="", fill=MUTED, font=(FONT, 10))
        self.mm_list = ScrollFrame(cv, bg=CARD)
        cv.create_window(96, 296, window=self.mm_list, anchor="nw", width=914, height=330)

    def mm_select(self, key):
        self.mm_type = key
        for k, b in self.mm_tabs.items():
            b.set_style("primary" if k == key else "dark")
        self.refresh_mm()

    def open_store(self):
        self.store_type = self.mm_type
        self.hits = {}
        self.show("store")
        self._store_type_changed()

    def refresh_mm(self):
        pt = self.mm_type
        sub = next(s for k, _, s in MM_TABS if k == pt)
        d = os.path.join(MC_DIR, sub)
        files = []
        if os.path.isdir(d):
            files = sorted(f for f in os.listdir(d) if f.endswith((".jar", ".zip", ".jar.disabled", ".zip.disabled")))
        enabled_mods = total_mods = 0
        md = os.path.join(MC_DIR, "mods")
        if os.path.isdir(md):
            names = os.listdir(md)
            enabled_mods = sum(1 for f in names if f.endswith(".jar"))
            total_mods = enabled_mods + sum(1 for f in names if f.endswith(".jar.disabled"))
        txt = f"Yüklü mod: {total_mods}  (açık: {enabled_mods})"
        if self.mods_boot:
            txt += "   ⏳ Varsayılan modlar indiriliyor..."
        self.cv_mm.itemconfig(self.mm_count, text=txt)
        hints = {"mod": "Kapalı modlar oyuna yüklenmez. fabric-api zorunludur, kapatılamaz.",
                 "resourcepack": "Doku paketini oyunda Seçenekler > Kaynak Paketleri'nden etkinleştir.",
                 "shader": "Shader paketleri için Iris Shaders modunu da indirmen gerekir."}
        self.cv_mm.itemconfig(self.mm_hint, text=hints[pt])
        sf = self.mm_list
        sf.clear()
        self.scroller = sf
        if not files:
            tk.Label(sf.inner, text=("Varsayılan modlar indiriliyor, birkaç saniye bekle..." if self.mods_boot and pt == "mod"
                                     else "Henüz hiçbir şey yok. Yukarıdan Modrinth'ten indirebilirsin."), bg=CARD, fg=MUTED,
                     font=(FONT, 11)).pack(pady=40)
            return
        for fn in files:
            off = fn.endswith(".disabled")
            name = re.sub(r"\.(jar|zip)(\.disabled)?$", "", fn)
            row = tk.Frame(sf.inner, bg=ROW_BG, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", padx=(4, 10), pady=4)
            tk.Label(row, text=name, bg=ROW_BG, fg=MUTED if off else FG, font=(FONT, 11), anchor="w").pack(
                side="left", padx=16, pady=14)
            if pt == "mod":
                locked = fn.startswith("fabric-api")
                tg = Toggle(row, not off, lambda v, fn=fn: self.mm_toggle(fn, v), locked=locked, bg=ROW_BG)
                tg.pack(side="right", padx=(6, 16))
            if not fn.startswith("fabric-api"):
                FlatButton(row, "Sil", lambda fn=fn: self.mm_delete(fn), bg="#b8473b", fg="#fff", hover="#d65a4c").pack(
                    side="right", padx=4)

    def _mm_dir(self):
        return os.path.join(MC_DIR, next(s for k, _, s in MM_TABS if k == self.mm_type))

    def mm_toggle(self, fn, enable):
        d = self._mm_dir()
        src = os.path.join(d, fn)
        dst = os.path.join(d, fn[:-9] if fn.endswith(".disabled") else fn + ".disabled")
        try:
            os.replace(src, dst)
        except Exception:
            pass
        self.after(50, self.refresh_mm)

    def mm_delete(self, fn):
        if not messagebox.askyesno(APP_NAME, f"{fn} silinsin mi?"):
            return
        try:
            os.remove(os.path.join(self._mm_dir(), fn))
        except Exception:
            pass
        self.refresh_mm()

    # ----------------------------------------------------------------- MODRINTH MAĞAZASI
    def _build_store(self):
        cv = self.new_page("store")
        self.cv_st = cv
        CButton(cv, 30, 24, 190, 46, "← Mod Yöneticisi", lambda: self.show("mods"), "dark", 11, 12)
        self.st_title = cv.create_text(250, 47, anchor="w", text="MODRINTH (MOD)", fill=FG, font=(FONT, 13, "bold"))
        self.q = tk.StringVar()
        ent = tk.Entry(cv, textvariable=self.q, bg="#232b3a", fg=FG, insertbackground=FG, relief="flat", font=(FONT, 12),
                       highlightthickness=2, highlightbackground=BORDER, highlightcolor=ACCENT)
        cv.create_window(560, 47, window=ent, width=380, height=42)
        ent.bind("<Return>", lambda e: self.search_mods())
        CButton(cv, 760, 26, 110, 44, "Ara", self.search_mods, "primary", 11, 12)
        self.sort_var = tk.StringVar(value="Alaka")
        om = tk.OptionMenu(cv, self.sort_var, *SORTS.keys(), command=lambda v: self.search_mods())
        om.config(bg="#232b3a", fg=FG, activebackground=CARD_HOVER, activeforeground=FG, relief="flat",
                  highlightthickness=1, highlightbackground=BORDER, font=(FONT, 11), bd=0, width=9)
        om["menu"].config(bg="#232b3a", fg=FG, font=(FONT, 11))
        cv.create_window(960, 47, window=om, width=150, height=42)
        self.st_count = cv.create_text(36, 100, anchor="w", text="", fill=MUTED, font=(FONT, 10))
        self.panel(cv, 30, 118, 640, 536, flat=True)
        self.store_list = ScrollFrame(cv, bg=CARD)
        cv.create_window(36, 124, window=self.store_list, anchor="nw", width=628, height=524)
        # detay paneli
        self.panel(cv, 690, 118, 380, 536, flat=True)
        self.d_title = cv.create_text(712, 146, anchor="nw", text="İçerik seç", fill=FG, font=(FONT, 17, "bold"), width=336)
        self.d_meta = cv.create_text(712, 212, anchor="nw", text="", fill=ACCENT_H, font=(FONT, 10), width=336)
        self.d_desc = cv.create_text(712, 242, anchor="nw", text="Soldaki listeden bir içerik seç.", fill="#cfd5e0",
                                     font=(FONT, 11), width=336)
        cv.create_text(712, 520, anchor="w", text=f"Minecraft {VERSION}  •  Fabric", fill=MUTED, font=(FONT, 10))
        self.btn_inst = CButton(cv, 712, 540, 170, 58, "İndir", self.install_selected, "primary", 13, 14)
        self.btn_rem = CButton(cv, 896, 540, 150, 58, "Kaldır", self.remove_selected, "danger", 13, 14)
        self.btn_inst.set_enabled(False)
        self.btn_rem.set_enabled(False)

    def _store_type_changed(self):
        self.cv_st.itemconfig(self.st_title, text=f"MODRINTH ({TYPE_TR[self.store_type]})")

    def search_mods(self):
        self.search_token += 1
        token = self.search_token
        q, pt = self.q.get().strip(), self.store_type
        idx = SORTS.get(self.sort_var.get(), "relevance")
        if not q and idx == "relevance":
            idx = "downloads"
        self.cv_st.itemconfig(self.st_count, text="Modrinth'te aranıyor...")
        threading.Thread(target=self._search, args=(q, pt, idx, token), daemon=True).start()

    def _search(self, q, pt, idx, token):
        try:
            fl = [[f"project_type:{pt}"], [f"versions:{VERSION}"]]
            if pt == "mod":
                fl.insert(1, ["categories:fabric"])
            params = {"query": q, "facets": json.dumps(fl), "limit": 30, "index": idx}
            data = http_json("https://api.modrinth.com/v2/search?" + urllib.parse.urlencode(params))
            if token != self.search_token:
                return
            hits = data.get("hits", [])
            total = data.get("total_hits", len(hits))
            self.after(0, lambda: self.show_cards(hits, total, token))
        except Exception as e:
            err = "Arama hatası: " + str(e)[:80]
            self.after(0, lambda: self.cv_st.itemconfig(self.st_count, text=err))

    def show_cards(self, hits, total, token):
        if token != self.search_token:
            return
        sf = self.store_list
        sf.clear()
        self.scroller = sf
        self.cards = {}
        self.hits = {h["project_id"]: h for h in hits}
        self.cv_st.itemconfig(self.st_count, text=f"{total} {TYPE_TR[self.store_type].lower()} bulundu")
        if not hits:
            tk.Label(sf.inner, text="Sonuç yok 😕", bg=CARD, fg=MUTED, font=(FONT, 12)).pack(pady=40)
            return
        for h in hits:
            self.cards[h["project_id"]] = self.make_card(sf.inner, h)
        threading.Thread(target=self.load_icons, args=(hits, token), daemon=True).start()

    def make_card(self, parent, h):
        card = tk.Frame(parent, bg=ROW_BG, highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
        card.pack(fill="x", padx=(4, 10), pady=4)
        icon = tk.Label(card, bg=ROW_BG, text="🧩", font=(FONT, 22), width=4, height=2)
        icon.pack(side="left", padx=(10, 6), pady=8)
        card.icon = icon
        col = tk.Frame(card, bg=ROW_BG)
        col.pack(side="left", fill="both", expand=True, pady=8)
        t = tk.Label(col, text=h["title"], bg=ROW_BG, fg=FG, font=(FONT, 12, "bold"), anchor="w")
        t.pack(fill="x")
        d = h["description"]
        l2 = tk.Label(col, text=d if len(d) < 70 else d[:67] + "...", bg=ROW_BG, fg=MUTED, font=(FONT, 9), anchor="w")
        l2.pack(fill="x")
        l3 = tk.Label(col, text=f"İndirme: {fmt_num(h['downloads'])}   Takip: {fmt_num(h.get('follows', 0))}",
                      bg=ROW_BG, fg="#7f8aa0", font=(FONT, 9), anchor="w")
        l3.pack(fill="x")
        for w in (card, icon, col, t, l2, l3):
            w.bind("<Button-1>", lambda e, pid=h["project_id"]: self.select_hit(pid))
        return card

    def load_icons(self, hits, token):
        for h in hits:
            if token != self.search_token:
                return
            url = h.get("icon_url")
            if not url:
                continue
            try:
                im = Image.open(io.BytesIO(http_bytes(url, 15))).convert("RGBA").resize((56, 56))
                pid = h["project_id"]
                self.after(0, lambda im=im, pid=pid: self._set_icon(pid, im))
            except Exception:
                continue

    def _set_icon(self, pid, im):
        card = self.cards.get(pid)
        try:
            if card is not None and card.winfo_exists():
                ph = ImageTk.PhotoImage(im)
                card.icon.config(image=ph, text="", width=56, height=56)
                card.icon.image = ph
        except Exception:
            pass

    def select_hit(self, pid):
        self.sel_hit = pid
        h = self.hits.get(pid)
        if not h:
            return
        for p, c in self.cards.items():
            try:
                c.config(highlightbackground=ACCENT if p == pid else BORDER)
            except Exception:
                pass
        cv = self.cv_st
        cv.itemconfig(self.d_title, text=h["title"])
        cv.itemconfig(self.d_meta, text=f"{h.get('author', '')}   •   İndirme: {fmt_num(h['downloads'])}   •   Takip: {fmt_num(h.get('follows', 0))}")
        cv.itemconfig(self.d_desc, text=h["description"])
        self._update_detail_buttons()

    def _is_installed(self, pid):
        rec = self.cfg.get("mod_files", {}).get(pid)
        if not rec:
            return False
        return any(os.path.exists(os.path.join(MC_DIR, rec["dir"], f)) for f in rec["files"])

    def _update_detail_buttons(self):
        pid = self.sel_hit
        inst = bool(pid) and self._is_installed(pid)
        self.btn_inst.set_enabled(bool(pid) and not inst, "✔ Yüklü")
        self.btn_inst.set_text("✔ Yüklü" if inst else "İndir")
        self.btn_rem.set_enabled(inst)

    def install_selected(self):
        h = self.hits.get(self.sel_hit)
        if not h:
            return
        self.btn_inst.set_enabled(False, "İndiriliyor...")
        threading.Thread(target=self._install, args=(h, self.store_type), daemon=True).start()

    def remove_selected(self):
        pid = self.sel_hit
        rec = self.cfg.get("mod_files", {}).pop(pid, None)
        if rec:
            for f in rec["files"]:
                try:
                    os.remove(os.path.join(MC_DIR, rec["dir"], f))
                except Exception:
                    pass
            save_cfg(self.cfg)
        self._update_detail_buttons()

    def _install(self, hit, pt):
        try:
            params = {"game_versions": json.dumps([VERSION])}
            if pt == "mod":
                params["loaders"] = json.dumps(["fabric"])
            q = urllib.parse.urlencode(params)
            versions = http_json(f"https://api.modrinth.com/v2/project/{hit['project_id']}/version?{q}")
            if not versions:
                self.after(0, lambda: (self.btn_inst.set_enabled(False, "Uyumsuz"), self.cv_st.itemconfig(self.d_meta, text="Bu sürüm için uygun dosya yok.")))
                return
            sub = {"mod": "mods", "resourcepack": "resourcepacks", "shader": "shaderpacks"}[pt]
            d = os.path.join(MC_DIR, sub)
            os.makedirs(d, exist_ok=True)
            fn = self._download(versions[0]["files"], d, force=True)
            for dep in (versions[0].get("dependencies", []) if pt == "mod" else []):
                if dep.get("dependency_type") == "required" and dep.get("project_id"):
                    try:
                        dv = http_json(f"https://api.modrinth.com/v2/project/{dep['project_id']}/version?{q}")
                        if dv:
                            self._download(dv[0]["files"], d)
                    except Exception:
                        pass
            self.cfg.setdefault("mod_files", {})[hit["project_id"]] = {"dir": sub, "files": [fn]}
            save_cfg(self.cfg)
            self.after(0, self._update_detail_buttons)
        except Exception as e:
            err = "Yükleme hatası: " + str(e)[:90]
            self.after(0, lambda: (self.cv_st.itemconfig(self.d_meta, text=err), self.btn_inst.set_enabled(True), self.btn_inst.set_text("Tekrar dene")))

    # ----------------------------------------------------------------- oyun başlatma
    def set_status(self, text, color=ACCENT_H):
        self.after(0, lambda: self.cv.itemconfig(self.status_id, text=text, fill=color))

    def set_progress(self, v, m):
        def _u():
            self.cv.itemconfig(self.prog_bg, state="normal")
            self.cv.itemconfig(self.prog_fg, state="normal")
            frac = max(0.0, min(1.0, v / max(m, 1)))
            self.cv.coords(self.prog_fg, 300, 658, 300 + 500 * frac, 664)
        self.after(0, _u)

    def callback(self):
        state = {"max": 0}
        return {
            "setStatus": lambda t: self.set_status(t),
            "setMax": lambda m: state.update(max=m),
            "setProgress": lambda p: self.set_progress(p, state["max"]),
        }

    def on_play(self):
        if self.busy:
            return
        if not re.fullmatch(r"\w{1,16}", self.user or ""):
            self.show("login")
            return
        gp = self.game_proc
        if gp is not None and gp.poll() is None:
            if not messagebox.askyesno(APP_NAME, "Oyunu zaten açtın.\n\nYine de bir tane daha açmak ister misin?"):
                return
        if not IP_RE.match(DEFAULT_SERVER):
            messagebox.showerror(APP_NAME, "Sadece sayısal IPv4 adresli sunuculara girilebilir.")
            return
        host, port = DEFAULT_SERVER.split(":")
        mb = int(self.cfg.get("ram_mb") or int(self.cfg.get("ram", 4)) * 1024)
        self.busy = True
        self.btn_play.set_text("HAZIRLANIYOR...")
        self.btn_play.set_enabled(False)
        self.cv.itemconfig(self.play_glow, state="hidden")
        self.glow_idx = -1
        self.set_status("Başlatılıyor...")
        threading.Thread(target=self.launch, args=(self.user, host, port, mb), daemon=True).start()

    @staticmethod
    def _console_java(path):
        if path and path.lower().endswith("javaw.exe"):
            alt = path[:-9] + "java.exe"
            if os.path.exists(alt):
                return alt
        return path

    def apply_options(self):
        """options.txt: Türkçe dil (ilk açılış) ve düşük grafik ayarı."""
        path = os.path.join(MC_DIR, "options.txt")
        kv = {}
        order = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for l in f:
                    l = l.rstrip("\r\n")
                    if ":" in l:
                        k, v = l.split(":", 1)
                        kv[k] = v
                        order.append(k)
        changed = False

        def setkv(k, v):
            nonlocal changed
            if kv.get(k) != v:
                kv[k] = v
                changed = True
            if k not in order:
                order.append(k)
        if not self.cfg.get("emote_key_set") and "key_key.emotecraft.fastchoose" not in kv:
            setkv("key_key.emotecraft.fastchoose", "key.keyboard.y")
            self.cfg["emote_key_set"] = True
        if not self.cfg.get("lang_set"):
            setkv("lang", "tr_tr")
            self.cfg["lang_set"] = True
        low = bool(self.cfg.get("low_gfx"))
        prev = self.cfg.get("low_applied")
        if prev != low and not (prev is None and not low):
            if low:
                for k, v in (("graphicsMode", "0"), ("renderDistance", "6"), ("simulationDistance", "5"),
                             ("particles", "2"), ("entityShadows", "false")):
                    setkv(k, v)
            else:
                for k, v in (("graphicsMode", "1"), ("renderDistance", "12"), ("simulationDistance", "12"),
                             ("particles", "0"), ("entityShadows", "true")):
                    setkv(k, v)
        self.cfg["low_applied"] = low
        # skin kaynak paketini etkinleştir / kaldır
        pack_id = "file/" + SKIN_PACK
        try:
            rp = json.loads(kv.get("resourcePacks", '["vanilla"]'))
            if not isinstance(rp, list):
                rp = ["vanilla"]
        except Exception:
            rp = ["vanilla"]
        want = list(rp)
        if "file/" + OLD_UI_PACK in want:
            want.remove("file/" + OLD_UI_PACK)
        for rp_name in READY_PACKS:
            if "file/" + rp_name not in want and not self.cfg.get("pack_off_" + rp_name):
                want.append("file/" + rp_name)
        if pack_id in want:
            want.remove(pack_id)
        if self.skin_pack_active:
            want.append(pack_id)
        # uyumsuz sayılsa bile etkinleşsin (Minecraft sadece bu listedekileri uyumsuz olsa da açar)
        try:
            inc = json.loads(kv.get("incompatibleResourcePacks", "[]"))
            if not isinstance(inc, list):
                inc = []
        except Exception:
            inc = []
        inc2 = list(inc)
        for rp_name in READY_PACKS:
            if "file/" + rp_name not in inc2:
                inc2.append("file/" + rp_name)
        if inc2 != inc or "incompatibleResourcePacks" not in kv:
            setkv("incompatibleResourcePacks", json.dumps(inc2, separators=(",", ":")))
        if want != rp or "resourcePacks" not in kv:
            setkv("resourcePacks", json.dumps(want, separators=(",", ":")))
        save_cfg(self.cfg)
        if changed or not os.path.exists(path):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(f"{k}:{kv[k]}" for k in order) + "\n")

    def ensure_base_mods(self):
        """Varsayılan FPS/ses modlarını Modrinth'ten indirir (zaten varsa atlar)."""
        self.migrate_mods()
        mods_dir = os.path.join(MC_DIR, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        self.install_local_mods()
        q = urllib.parse.urlencode({"game_versions": json.dumps([VERSION]), "loaders": json.dumps(["fabric"])})
        self.clean_broken_mods()
        skipped, failed = [], []
        total = len(BASE_MODS)
        for i, slug in enumerate(BASE_MODS, 1):
            self.set_status(f"Modlar hazırlanıyor ({i}/{total}): {slug}")
            self.set_progress(i, total)
            try:
                versions = None
                for attempt in range(3):
                    try:
                        versions = http_json(f"https://api.modrinth.com/v2/project/{slug}/version?{q}")
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(1.5)
                if not versions:
                    skipped.append(slug)
                    continue
                self._download(versions[0]["files"], mods_dir)
                for dep in versions[0].get("dependencies", []):
                    if dep.get("dependency_type") == "required" and dep.get("project_id"):
                        dv = http_json(f"https://api.modrinth.com/v2/project/{dep['project_id']}/version?{q}")
                        if dv:
                            self._download(dv[0]["files"], mods_dir)
            except Exception as e:
                failed.append(f"{slug} ({str(e)[:80]})")
        # KünefeCraft'a özel mod(lar): siteden indirilir, site/jar yoksa sessizce atlanır
        for fn, url in EXTRA_MODS:
            try:
                self._download([{"filename": fn, "url": url, "primary": True}], mods_dir)
            except Exception:
                log_crash("extra mod " + fn + ": " + traceback.format_exc())
        have = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
        if failed and len(have) >= 6:
            failed = []   # mod dosyaları zaten kurulu: güncelleme kontrolü başarısızsa oyunu engelleme
        if failed:
            self.clean_broken_mods()
            raise RuntimeError(
                "Bazı modlar indirilemedi. İnternet bağlantını, antivirüsü ve güvenlik duvarını kontrol edip "
                "tekrar dene.\n\n" + "\n".join(failed))

    def install_ready(self):
        """Hazır doku paketlerini resourcepacks'a kopyalar (eski kendi paketimizi siler)."""
        rp_dir = os.path.join(MC_DIR, "resourcepacks")
        try:
            os.makedirs(rp_dir, exist_ok=True)
            old = os.path.join(rp_dir, OLD_UI_PACK)
            if os.path.exists(old):
                os.remove(old)
            for name in READY_PACKS:
                src = resource_path(os.path.join("assets", "packs", name))
                dst = os.path.join(rp_dir, name)
                if os.path.isfile(src) and (not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(src)):
                    shutil.copyfile(src, dst + ".part")
                    os.replace(dst + ".part", dst)
        except Exception:
            log_crash("ready packs: " + traceback.format_exc())

    def install_local_mods(self):
        """Uygulamayla gelen hazır modları mods klasörüne koyar (kullanıcı kapattıysa dokunmaz)."""
        md = os.path.join(MC_DIR, "mods")
        os.makedirs(md, exist_ok=True)
        for f in os.listdir(md):
            if f.lower().startswith("fancymenu") or f.lower().startswith("konkrete"):
                try:
                    os.remove(os.path.join(md, f))
                except OSError:
                    pass
        for name in LOCAL_MODS:
            src = resource_path(os.path.join("assets", "extra_mods", name))
            dst = os.path.join(md, name)
            try:
                if name == "kunefe-menu.jar" and os.path.isfile(src):
                    if not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(src):
                        shutil.copyfile(src, dst + ".part")
                        os.replace(dst + ".part", dst)
                elif os.path.isfile(src) and not os.path.exists(dst) and not os.path.exists(dst + ".disabled"):
                    shutil.copyfile(src, dst + ".part")
                    os.replace(dst + ".part", dst)
            except Exception:
                log_crash("local mod " + name + ": " + traceback.format_exc())

    def migrate_mods(self):
        """Oyun sürümü değiştiyse eski sürümün modlarını yedek klasöre taşır (uyumsuz modlar oyunu çökertir)."""
        if self.cfg.get("mods_mc") == VERSION:
            return
        md = os.path.join(MC_DIR, "mods")
        try:
            if os.path.isdir(md) and any(f.endswith((".jar", ".jar.disabled")) for f in os.listdir(md)):
                base = os.path.join(MC_DIR, "mods_yedek_" + str(self.cfg.get("mods_mc") or "eski"))
                dst, n = base, 1
                while os.path.exists(dst):
                    n += 1
                    dst = f"{base}_{n}"
                os.replace(md, dst)
        except Exception:
            log_crash("migrate mods: " + traceback.format_exc())
        self.cfg["mods_mc"] = VERSION
        save_cfg(self.cfg)

    def _presence_loop(self, name, proc):
        """Oyun açıkken Worker'a 'buradayım' der, çevrimiçi launcher oyuncularını kunefe_online.txt'ye indirir (mod TAB'da okur)."""
        if not PRESENCE_URL.startswith("http"):
            return
        out = os.path.join(MC_DIR, "kunefe_online.txt")
        base = PRESENCE_URL.rstrip("/")
        while proc.poll() is None:
            try:
                req = urllib.request.Request(base + "/ping?name=" + urllib.parse.quote(name.lower()), data=b"", method="POST", headers={"User-Agent": UA})
                urllib.request.urlopen(req, timeout=8).read()
                with urllib.request.urlopen(urllib.request.Request(base + "/online", headers={"User-Agent": UA}), timeout=8) as r:
                    names = [n for n in json.loads(r.read().decode("utf-8")).get("names", []) if re.fullmatch(r"\w{1,16}", str(n))]
                with open(out + ".tmp", "w", encoding="utf-8") as f:
                    f.write("\n".join(names))
                os.replace(out + ".tmp", out)
            except Exception:
                pass
            for _ in range(20):
                if proc.poll() is not None:
                    break
                time.sleep(1)

    # ----------------------------------------------------------------- ARKADAŞLAR / MESAJLAŞMA (bulut)
    def _cloud_token(self, name):
        import secrets
        toks = self.cfg.setdefault("cloud_tok", {})
        t = toks.get(name.lower())
        if not t:
            t = secrets.token_hex(16)
            toks[name.lower()] = t
            save_cfg(self.cfg)
        return t

    def cloud(self, path, payload=None, timeout=8):
        if not PRESENCE_URL.startswith("http") or not self.user:
            raise RuntimeError("Bulut ayarlı değil")
        body = dict(payload or {})
        body["name"] = self.user
        body["token"] = self._cloud_token(self.user)
        req = urllib.request.Request(PRESENCE_URL.rstrip("/") + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
        def go(ctx=None):
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                    raw = r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                raw = e.read().decode("utf-8", "replace")
                try:
                    return json.loads(raw)
                except Exception:
                    return {"ok": False, "err": f"Sunucu hatası HTTP {e.code}"}
            try:
                return json.loads(raw)
            except Exception:
                return {"ok": False, "err": "Worker eski sürüm: yanıt JSON değil. worker_sosyal.js'yi yapıştırıp Deploy et. (" + raw[:40] + ")"}
        try:
            return go()
        except Exception as e:
            if "CERTIFICATE" in str(e).upper() or "SSL" in str(e).upper():
                import ssl
                import certifi
                return go(ssl.create_default_context(cafile=certifi.where()))
            raise

    def open_social(self):
        if not self.user:
            self.show("login")
            return
        self.show("social")

    def _build_social(self):
        cv = self.new_page("social")
        self.cv_soc = cv
        self.embers_for(cv)
        self.soc_sel = None
        self.soc_last = 0
        self.soc_names = []
        self.soc_polling = False
        CButton(cv, 30, 24, 150, 46, "← Ana Menü", lambda: self.show("home"), "dark", 11, 12)
        cv.create_text(550, 46, text="ARKADAŞLAR", fill=FG, font=(FONT, 20, "bold"))
        ent = dict(bg="#232b3a", fg=FG, insertbackground=FG, relief="flat", font=(FONT, 12), highlightthickness=2,
                   highlightbackground=BORDER, highlightcolor=ACCENT, bd=0)
        lst = dict(bg="#10151e", fg=FG, selectbackground=ACCENT, selectforeground="#101010", relief="flat",
                   activestyle="none", highlightthickness=1, highlightbackground=BORDER, bd=0)
        # sol: liste
        self.panel(cv, 60, 90, 330, 540)
        cv.create_text(84, 116, anchor="w", text="Arkadaş Ekle", fill=FG, font=(FONT, 14, "bold"))
        self.soc_add = tk.Entry(cv, **ent)
        cv.create_window(184, 160, window=self.soc_add, width=190, height=40)
        self.soc_add.bind("<Return>", lambda e: self._soc_add_friend())
        CButton(cv, 290, 140, 86, 40, "+ Ekle", self._soc_add_friend, "primary", 10, 10)
        self.soc_status = cv.create_text(84, 198, anchor="w", text="", fill=MUTED, font=(FONT, 9), width=290)
        self.soc_list = tk.Listbox(cv, font=(FONT, 12), **lst)
        cv.create_window(225, 300, window=self.soc_list, width=290, height=164)
        self.soc_list.bind("<<ListboxSelect>>", lambda e: self._soc_select())
        cv.create_text(84, 400, anchor="w", text="Gelen istekler", fill=FG, font=(FONT, 12, "bold"))
        self.soc_req = tk.Listbox(cv, font=(FONT, 11), **lst)
        cv.create_window(225, 450, window=self.soc_req, width=290, height=64)
        CButton(cv, 80, 496, 140, 42, "✔ Kabul Et", self._soc_accept, "ok", 10, 10)
        CButton(cv, 230, 496, 140, 42, "✖ Arkadaşı Sil", self._soc_remove, "dark", 10, 10)
        cv.create_text(225, 570, text="● çevrimiçi   ○ çevrimdışı   (n) okunmamış", fill=MUTED, font=(FONT, 9))
        # sağ: sohbet
        self.panel(cv, 420, 90, 620, 540, flat=True)
        self.soc_title = cv.create_text(446, 116, anchor="w", text="Bir arkadaş seç", fill=FG, font=(FONT, 14, "bold"))
        self.soc_text = tk.Text(cv, font=(FONT, 11), wrap="word", state="disabled", padx=10, pady=8, **lst)
        cv.create_window(730, 306, window=self.soc_text, width=580, height=330)
        self.soc_text.tag_config("me", foreground=ACCENT_H)
        self.soc_text.tag_config("them", foreground="#7fd1ff")
        self.soc_msg = tk.Entry(cv, **ent)
        cv.create_window(618, 540, window=self.soc_msg, width=380, height=44)
        self.soc_msg.bind("<Return>", lambda e: self._soc_send())
        CButton(cv, 826, 518, 192, 44, "Gönder ➤", self._soc_send, "primary", 11, 12)

    def _soc_enter(self):
        if not getattr(self, "soc_polling", False):
            self.soc_polling = True
            self._soc_poll()

    def _soc_say(self, t):
        if self.page == "social":
            self.cv_soc.itemconfig(self.soc_status, text=t)

    def _soc_bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _soc_add_friend(self):
        n = self.soc_add.get().strip()
        if not n:
            return
        self.soc_add.delete(0, "end")

        def work():
            try:
                r = self.cloud("/friend/add", {"to": n})
                self.after(0, lambda: self._soc_say(r.get("msg") or r.get("err") or "Tamam"))
            except Exception:
                self.after(0, lambda: self._soc_say("Buluta bağlanılamadı"))
        self._soc_bg(work)

    def _soc_accept(self):
        sel = self.soc_req.curselection()
        if not sel:
            return
        n = self.soc_req.get(sel[0])
        self._soc_bg(lambda: self.cloud("/friend/accept", {"from": n}))

    def _soc_remove(self):
        if not self.soc_sel:
            return
        n = self.soc_sel
        if not messagebox.askyesno(APP_NAME, f"{n} arkadaşlıktan çıkarılsın mı?"):
            return
        self.soc_sel = None
        self._soc_bg(lambda: self.cloud("/friend/remove", {"other": n}))

    def _soc_select(self):
        sel = self.soc_list.curselection()
        if not sel or sel[0] >= len(self.soc_names):
            return
        self.soc_sel = self.soc_names[sel[0]]
        self.soc_last = 0
        self.cv_soc.itemconfig(self.soc_title, text=self.soc_sel)
        self.soc_text.config(state="normal")
        self.soc_text.delete("1.0", "end")
        self.soc_text.config(state="disabled")

    def _soc_send(self):
        t = self.soc_msg.get().strip()
        if not t or not self.soc_sel:
            return
        self.soc_msg.delete(0, "end")
        to = self.soc_sel

        def work():
            try:
                r = self.cloud("/msg/send", {"to": to, "text": t})
                if not r.get("ok"):
                    self.after(0, lambda: self._soc_say(r.get("err") or "Gönderilemedi"))
            except Exception:
                self.after(0, lambda: self._soc_say("Buluta bağlanılamadı"))
        self._soc_bg(work)

    def _soc_poll(self):
        if self.page != "social":
            self.soc_polling = False
            return
        sel, last = self.soc_sel, self.soc_last

        def work():
            try:
                r = self.cloud("/friends")
                if not r.get("ok"):
                    err = r.get("err") or "bilinmeyen hata"
                    self.after(0, lambda: self._soc_say("Bulut: " + err))
                    return
                msgs = None
                if sel:
                    m = self.cloud("/msg/list", {"with": sel, "after": last})
                    msgs = m.get("msgs") if m.get("ok") else None
                self.after(0, lambda: self._soc_render(r, sel, msgs))
            except Exception as e:
                msg = f"Buluta bağlanılamadı: {type(e).__name__}: {str(e)[:80]}"
                self.after(0, lambda: self._soc_say(msg))
        self._soc_bg(work)
        self.after(4000, self._soc_poll)

    def _soc_render(self, r, sel, msgs):
        if self.page != "social" or not r.get("ok"):
            return
        fr = r.get("friends", [])
        self.soc_names = [f["name"] for f in fr]
        self.soc_list.delete(0, "end")
        for f in fr:
            self.soc_list.insert("end", f"{'●' if f['online'] else '○'} {f['name']}" + (f"  ({f['unread']})" if f.get("unread") else ""))
        if sel in self.soc_names:
            self.soc_list.selection_set(self.soc_names.index(sel))
        self.soc_req.delete(0, "end")
        for n in r.get("incoming", []):
            self.soc_req.insert("end", n)
        if msgs and sel == self.soc_sel:
            self.soc_text.config(state="normal")
            for m in msgs:
                mine = m["from"].lower() == self.user.lower()
                hh = time.strftime("%H:%M", time.localtime(m["ts"]))
                self.soc_text.insert("end", f"[{hh}] {'Sen' if mine else m['from']}: {m['text']}\n", "me" if mine else "them")
                self.soc_last = max(self.soc_last, m["id"])
            self.soc_text.config(state="disabled")
            self.soc_text.see("end")

    def _prefetch_run(self):
        """Setup tarafından çağrılır: pencere göstermeden oyun, Java, Fabric ve modları indirir."""
        self.prefetch_err = None

        def work():
            host, port = DEFAULT_SERVER.split(":")
            try:
                self.launch("Oyuncu", host, port, 2048, prefetch=True)
            except Exception:
                self.prefetch_err = "hata"
            code = 1 if self.prefetch_err else 0
            if self.prefetch_err:
                try:
                    with open(os.path.join(BASE_DIR, "prefetch_error.txt"), "w", encoding="utf-8") as f:
                        f.write(str(self.prefetch_err))
                except Exception:
                    pass
            os._exit(code)
        threading.Thread(target=work, daemon=True).start()

    def celebrate(self):
        """v2 kutlaması: ana ekranda konfeti yağmuru."""
        import random
        cv = getattr(self, "cv", None)
        if cv is None or self.page != "home":
            return
        cols = ["#f5922a", "#ffd166", "#ef476f", "#06d6a0", "#4cc9f0", "#ffffff"]
        parts = []
        for _ in range(90):
            x = random.randint(0, 1100)
            sz = random.randint(5, 10)
            it = cv.create_rectangle(x, -random.randint(0, 400), x + sz, 0, fill=random.choice(cols), outline="")
            parts.append([it, random.uniform(3, 7), random.uniform(-1.5, 1.5)])
        t = cv.create_text(550, 330, text="🎉 KünefeLauncher v2 çıktı! 🎉", fill="#ffd166", font=(FONT, 30, "bold"))
        frames = [0]

        def step():
            frames[0] += 1
            for it, vy, vx in parts:
                cv.move(it, vx, vy)
            if frames[0] < 130:
                self.after(30, step)
            else:
                for it, _, _ in parts:
                    cv.delete(it)
                cv.delete(t)
        step()

    def bootstrap_mods(self):
        """Açılışta modlar yoksa arka planda indir (Oyna'ya basmadan da Mod Yöneticisi dolu olsun)."""
        if self.busy or self.mods_boot:
            return
        self.migrate_mods()
        md = os.path.join(MC_DIR, "mods")
        have = os.path.isdir(md) and any(f.endswith((".jar", ".jar.disabled")) for f in os.listdir(md))
        if have:
            return
        self.mods_boot = True
        if self.page == "mods":
            self.refresh_mm()

        def work():
            try:
                self.ensure_base_mods()
            except Exception:
                log_crash("bootstrap mods: " + traceback.format_exc())

            def done():
                self.mods_boot = False
                if self.page == "mods":
                    self.refresh_mm()
                if not self.busy:
                    self._set_ready_status()
            self.after(0, done)
        threading.Thread(target=work, daemon=True).start()

    def find_fabric(self):
        for v in load_mll().utils.get_installed_versions(MC_DIR):
            if v["id"].startswith("fabric-loader") and v["id"].endswith(VERSION):
                return v["id"]
        return None

    @staticmethod
    def _retry(fn, tries=3):
        last = None
        for i in range(tries):
            try:
                return fn()
            except Exception as e:
                last = e
                time.sleep(2 * (i + 1))
        raise last

    @staticmethod
    def _net_hint(msg):
        low = msg.lower()
        if any(k in low for k in ("443", "max retries", "connection", "timed out", "resolve", "getaddrinfo", "ssl", "name or service")):
            return ("İnternet bağlantısı kurulamadı (mojang.com / modrinth.com, port 443).\n\n"
                    "• İnternetin açık mı? Başka bir siteyi dene.\n"
                    "• Antivirüs veya Windows Güvenlik Duvarı launcher'ı engelliyor olabilir: KunefeLauncher.exe'ye izin ver.\n"
                    "• VPN/proxy açıksa kapat; DNS'i 1.1.1.1 yapmayı dene.\n"
                    "• Sonra tekrar OYNA'ya bas, kaldığı yerden devam eder.\n\nAyrıntı: " + msg[:200])
        return msg

    @staticmethod
    def _mojang_ok():
        for url in ("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
                    "https://resources.download.minecraft.net/87/87d5e8d5a978b0443d23741bb88434e88d60f60f"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                urllib.request.urlopen(req, timeout=8).read(64)
            except urllib.error.HTTPError:
                pass   # sunucuya ulaştık (404/403 olabilir)
            except Exception:
                return False
        return True

    def install_pack(self):
        """Mojang engelliyse: oyun + Java + Fabric + modlar hazır paketini indirip açar."""
        last = None
        for url in GAME_PACK_URLS:
            tmp = os.path.join(BASE_DIR, "game.zip.part")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as f:
                    total = int(r.headers.get("Content-Length") or 0)
                    done = 0
                    while True:
                        chunk = r.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.set_status(f"Hazır oyun paketi indiriliyor: {done // 1048576} / {total // 1048576} MB")
                            self.set_progress(done, total)
                if not zipfile.is_zipfile(tmp):
                    raise IOError("paket bozuk")
                self.set_status("Oyun paketi açılıyor...")
                keep = {os.path.join("minecraft", "options.txt"), os.path.join("minecraft", "servers.dat")}
                with zipfile.ZipFile(tmp) as z:
                    infos = [i for i in z.infolist() if not i.is_dir()]
                    for n, info in enumerate(infos):
                        arc = os.path.normpath(info.filename)
                        dst = os.path.join(BASE_DIR, arc)
                        if arc in keep and os.path.exists(dst):
                            continue
                        if os.path.isfile(dst) and os.path.getsize(dst) == info.file_size:
                            continue
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        with z.open(info) as src, open(dst + ".part", "wb") as out:
                            shutil.copyfileobj(src, out)
                        os.replace(dst + ".part", dst)
                        if n % 200 == 0:
                            self.set_progress(n, len(infos))
                os.remove(tmp)
                self.cfg["setup_done"] = True
                self.cfg["mods_mc"] = VERSION
                self.cfg["mods_checked"] = time.time()
                save_cfg(self.cfg)
                return True
            except Exception as e:
                last = e
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        raise RuntimeError("Hazır oyun paketi de indirilemedi: " + str(last)[:150])

    def launch(self, name, host, port, ram_mb, prefetch=False):
        ver = VERSION
        try:
            m = load_mll()
            cb = self.callback()
            fast = bool(self.cfg.get("setup_done")) and self.quick_installed()
            if not fast and not self._mojang_ok():
                self.set_status("Mojang'a ulaşılamıyor, hazır oyun paketi indiriliyor...")
                self.install_pack()
                fast = bool(self.cfg.get("setup_done")) and self.quick_installed()
            if not fast:
                self.set_status("Minecraft indiriliyor/kontrol ediliyor...")
                self._retry(lambda: m.install.install_minecraft_version(ver, MC_DIR, callback=cb))

            java_exe = None
            info = m.runtime.get_version_runtime_information(ver, MC_DIR)
            if info:
                jp = m.runtime.get_executable_path(info["name"], MC_DIR)
                if not fast or not (jp and os.path.exists(jp)):
                    self.set_status("Java hazırlanıyor...")
                    self._retry(lambda: m.runtime.install_jvm_runtime(info["name"], MC_DIR, callback=cb))
                    jp = m.runtime.get_executable_path(info["name"], MC_DIR)
                java_exe = jp if jp and os.path.exists(jp) else None
            if not java_exe:
                raise RuntimeError("Bu sürüm için Java indirilemedi. İnternet bağlantını kontrol edip tekrar dene.")

            launch_id = self.find_fabric() if fast else None
            if not launch_id:
                self.set_status("Fabric kuruluyor...")
                self._retry(lambda: m.fabric.install_fabric(ver, MC_DIR, callback=cb, java=self._console_java(java_exe)))
                launch_id = self.find_fabric()
            if not launch_id:
                raise RuntimeError("Fabric kuruldu ama sürüm bulunamadı.")

            if not fast or time.time() - self.cfg.get("mods_checked", 0) > 7 * 86400:
                self.ensure_base_mods()
                self.cfg["mods_checked"] = time.time()
            try:
                ensure_server_in_list()
            except Exception:
                pass
            self.apply_skin_pack()
            self.apply_options()
            self.cfg["setup_done"] = True
            save_cfg(self.cfg)
            if prefetch:
                return

            opts = {
                "username": name,
                "uuid": offline_uuid(name),
                "token": "0",
                "jvmArguments": [f"-Xmx{ram_mb}M", f"-Xms{min(ram_mb, 2048)}M"],
                "launcherName": APP_NAME,
                "launcherVersion": APP_VERSION,
                "executablePath": java_exe,
            }
            # Künefe Menü modu bu dosyaları okur: otomatik sunucuya giriş + hazır doku paketleri
            try:
                with open(os.path.join(MC_DIR, "kunefe_autojoin.txt"), "w", encoding="utf-8") as f:
                    f.write(f"{host}:{port}")
                lp = os.path.join(MC_DIR, "kunefe_login.txt")
                pw = (self.cfg.get("pw") or {}).get(name.lower(), "")
                if pw:
                    with open(lp, "w", encoding="utf-8") as f:
                        f.write(pw)
                elif os.path.exists(lp):
                    os.remove(lp)
                with open(os.path.join(MC_DIR, "kunefe_packs.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join("file/" + n for n in READY_PACKS if not self.cfg.get("pack_off_" + n)))
            except Exception:
                log_crash("autojoin files: " + traceback.format_exc())

            cmd = m.command.get_minecraft_command(launch_id, MC_DIR, opts)
            self.set_status("Oyun başlatılıyor...")
            flags = 0x08000000 if os.name == "nt" else 0
            self.game_proc = subprocess.Popen(cmd, cwd=MC_DIR, creationflags=flags)
            threading.Thread(target=self._presence_loop, args=(name, self.game_proc), daemon=True).start()
            self.set_status(f"Oyun açıldı, {SERVER_NAME} sunucusuna bağlanıyor 🍮", OK)
            time.sleep(3)
        except Exception as e:
            msg = self._net_hint(str(e))
            log_crash("launch: " + traceback.format_exc())
            self.prefetch_err = str(e)[:600]
            self.set_status("Hata: " + msg[:110].replace("\n", " "), BAD)
            if not prefetch:
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"Başlatılamadı:\n\n{msg}"))
        finally:
            def _done():
                self.busy = False
                self.is_installed = self.quick_installed()
                self.btn_play.set_enabled(True)
                self.btn_play.set_text("OYNA!")
                self.cv.itemconfig(self.prog_bg, state="hidden")
                self.cv.itemconfig(self.prog_fg, state="hidden")
                if not str(self.cv.itemcget(self.status_id, "text")).startswith("Hata"):
                    self._set_ready_status()
            self.after(0, _done)

    # ----------------------------------------------------------------- güvenli indirme
    @staticmethod
    def _file_ok(path, sha512=None):
        try:
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                return False
            if not zipfile.is_zipfile(path):
                return False
            if sha512:
                h = hashlib.sha512()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                return h.hexdigest().lower() == sha512.lower()
            return True
        except Exception:
            return False

    def _download(self, files, dest_dir, force=False):
        """Güvenli indirme: .part'a indir, doğrula, taşı. Kullanıcı kapattıysa (.disabled) dokunma."""
        f = next((x for x in files if x.get("primary")), files[0])
        dest = os.path.join(dest_dir, f["filename"])
        sha = (f.get("hashes") or {}).get("sha512")
        if not force and os.path.exists(dest + ".disabled"):
            return f["filename"]
        if self._file_ok(dest, sha):
            return f["filename"]
        tmp = dest + ".part"
        last = None
        for attempt in range(3):
            try:
                if os.path.exists(dest):
                    os.remove(dest)
                data = http_bytes(f["url"], 120)
                with open(tmp, "wb") as out:
                    out.write(data)
                if not self._file_ok(tmp, sha):
                    raise IOError("indirilen dosya bozuk veya eksik")
                os.replace(tmp, dest)
                return f["filename"]
            except Exception as e:
                last = e
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"{f['filename']} indirilemedi: {last}")

    def clean_broken_mods(self):
        for sub in ("mods", "resourcepacks", "shaderpacks"):
            d = os.path.join(MC_DIR, sub)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                p = os.path.join(d, fn)
                if fn.endswith(".part") or (fn.endswith((".jar", ".zip")) and not self._file_ok(p)):
                    try:
                        os.remove(p)
                    except Exception:
                        pass


if __name__ == "__main__":
    try:
        _app = App()
        if "--prefetch" in sys.argv:
            _app.withdraw()
            _app.after(500, _app._prefetch_run)
        _app.mainloop()
    except Exception:
        log_crash("startup: " + traceback.format_exc())
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(APP_NAME, "Launcher başlatılamadı.\nHata kaydı: " + os.path.join(BASE_DIR, "crash.log"))
        except Exception:
            pass
