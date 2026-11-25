"""KünefeLauncher kurulum programı (Setup).
Launcher EXE'si bu dosyanın içine gömülüdür; ayrı bir araç gerekmez.
  KunefeLauncher_Setup.exe            -> kurar
  Uninstall.exe --uninstall           -> kaldırır
"""
import os
import sys
import shutil
import zipfile
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import winreg
except ImportError:  # Windows dışı (sadece test için)
    winreg = None

APP = "KünefeLauncher"
VERSION = "2.0"
EXE = "KunefeLauncher.exe"
LNK = "KünefeLauncher.lnk"
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "KunefeLauncher")
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".kunefelauncher")
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\KunefeLauncher"
NO_WINDOW = 0x08000000
DETACHED = 0x00000008

BG, CARD, FG, MUTED, ACCENT, ACCENT_H, OK = "#1b1712", "#2a241b", "#f3e3c3", "#a99677", "#ff9f1c", "#ffbf69", "#7bd88f"


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ---------- yardımcılar ----------
def q(s):
    return "'" + s.replace("'", "''") + "'"


def ps(script):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, text=True, creationflags=NO_WINDOW, timeout=60)
    return (r.stdout or "").strip()


def shortcut_path(folder):
    """folder: 'Desktop' veya 'Programs' (Başlat menüsü). OneDrive'a taşınmış masaüstünü de bulur."""
    d = ps(f"[Environment]::GetFolderPath('{folder}')")
    return os.path.join(d, LNK) if d else None


def make_shortcut(folder, target, workdir, icon):
    ps(
        f"$d=[Environment]::GetFolderPath('{folder}'); $p=Join-Path $d {q(LNK)}; "
        f"$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($p); "
        f"$s.TargetPath={q(target)}; $s.WorkingDirectory={q(workdir)}; $s.IconLocation={q(icon)}; "
        f"$s.Description='KünefeCraft'; $s.Save()"
    )


def write_uninstall_entry(uninstaller, exe):
    if winreg is None:
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, APP)
        winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "KünefeCraft")
        winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, exe)
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}" --uninstall')
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def delete_uninstall_entry():
    if winreg is None:
        return
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    except OSError:
        pass


# ---------- kaldırma ----------
def run_uninstall():
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno(APP, f"{APP} bilgisayarından kaldırılsın mı?"):
        return
    wipe = messagebox.askyesno(
        APP,
        "Oyun dosyaları, modlar ve ayarların da silinsin mi?\n\n"
        "Evet: Her şey silinir.\n"
        "Hayır: Oyun verilerin kalır, tekrar kurarsan kaldığın yerden devam edersin.",
        default="no")
    subprocess.run(["taskkill", "/F", "/IM", EXE], capture_output=True, creationflags=NO_WINDOW)
    for folder in ("Desktop", "Programs"):
        try:
            p = shortcut_path(folder)
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    delete_uninstall_entry()
    if wipe:
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    # Uninstall.exe kendini silemez: biz kapandıktan sonra klasörü sil
    subprocess.Popen(["cmd", "/c", f'ping 127.0.0.1 -n 4 >nul & rmdir /s /q "{INSTALL_DIR}"'],
                     creationflags=NO_WINDOW | DETACHED, close_fds=True)
    messagebox.showinfo(APP, "Kaldırıldı. Görüşürüz! 🍮")


# ---------- kurulum arayüzü ----------
class Setup(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} Kurulumu")
        self.geometry("640x430")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.logo = None
        try:
            img = tk.PhotoImage(file=resource_path(os.path.join("assets", "logo.png")))
            self.iconphoto(True, img.subsample(2, 2))
            self.logo = img.subsample(3, 3)  # 512 -> ~170 px
        except Exception:
            pass

        self.v_desktop = tk.BooleanVar(value=True)
        self.v_start = tk.BooleanVar(value=True)
        self.v_launch = tk.BooleanVar(value=True)
        self.installed_exe = None

        left = tk.Frame(self, bg=CARD, width=210)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        if self.logo:
            tk.Label(left, image=self.logo, bg=CARD).pack(pady=(60, 10))
        else:
            tk.Label(left, text="🍮", bg=CARD, font=("Segoe UI", 54)).pack(pady=(60, 10))
        tk.Label(left, text=f"v{VERSION}", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack()

        self.right = tk.Frame(self, bg=BG, padx=26, pady=22)
        self.right.pack(side="left", fill="both", expand=True)
        self.page_options()

    def clear(self):
        for w in self.right.winfo_children():
            w.destroy()

    def button(self, parent, text, cmd, accent=True):
        b = tk.Label(parent, text=text, bg=ACCENT if accent else CARD, fg="#1b1712" if accent else FG,
                     font=("Segoe UI", 11, "bold"), padx=26, pady=8, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(bg=ACCENT_H if accent else "#352d22"))
        b.bind("<Leave>", lambda e: b.config(bg=ACCENT if accent else CARD))
        return b

    def check(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=BG, fg=FG, selectcolor=CARD,
                              activebackground=BG, activeforeground=FG, font=("Segoe UI", 10),
                              anchor="w", highlightthickness=0, bd=0)

    # --- sayfa 1: seçenekler
    def page_options(self):
        self.clear()
        r = self.right
        tk.Label(r, text=f"{APP} kurulumuna\nhoş geldin", bg=BG, fg=ACCENT, justify="left",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(r, text="KünefeCraft sunucusuna girmek için gereken her şey (Minecraft 1.21.11, Fabric,\n"
                         "Java ve FPS modları) ilk açılışta otomatik indirilir.",
                 bg=BG, fg=MUTED, justify="left", font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 14))
        tk.Label(r, text="Kurulacak yer:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(r, text=INSTALL_DIR, bg=CARD, fg=FG, font=("Consolas", 9), anchor="w", padx=8, pady=5).pack(fill="x", pady=(2, 14))
        self.check(r, "Masaüstüne kısayol oluşturulsun mu?", self.v_desktop).pack(anchor="w", pady=2)
        self.check(r, "Başlat menüsüne kısayol eklensin mi?", self.v_start).pack(anchor="w", pady=2)
        self.check(r, "Kurulum bitince launcher şimdi başlatılsın mı?", self.v_launch).pack(anchor="w", pady=2)
        bar = tk.Frame(r, bg=BG)
        bar.pack(side="bottom", fill="x")
        self.button(bar, "İptal", self.destroy, accent=False).pack(side="right", padx=(8, 0))
        self.button(bar, "Kur", self.start_install).pack(side="right")

    # --- sayfa 2: ilerleme
    def page_progress(self):
        self.clear()
        tk.Label(self.right, text="Kuruluyor...", bg=BG, fg=ACCENT, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(60, 10))
        self.status = tk.StringVar(value="Hazırlanıyor...")
        tk.Label(self.right, textvariable=self.status, bg=BG, fg=FG, font=("Segoe UI", 10)).pack(anchor="w")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("K.Horizontal.TProgressbar", troughcolor="#3a3226", background=ACCENT, borderwidth=0)
        self.pb = ttk.Progressbar(self.right, style="K.Horizontal.TProgressbar", maximum=6, length=360)
        self.pb.pack(anchor="w", pady=14)

    # --- sayfa 3: bitti / hata
    def page_done(self, error=None):
        self.clear()
        r = self.right
        if error:
            tk.Label(r, text="Kurulum başarısız", bg=BG, fg="#e07a6a", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(50, 10))
            tk.Label(r, text=error, bg=BG, fg=FG, justify="left", wraplength=340, font=("Segoe UI", 10)).pack(anchor="w")
            bar = tk.Frame(r, bg=BG)
            bar.pack(side="bottom", fill="x")
            self.button(bar, "Kapat", self.destroy).pack(side="right")
            return
        tk.Label(r, text="Kurulum tamamlandı! 🎉", bg=BG, fg=OK, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(50, 10))
        extra = ""
        if getattr(self, "prefetch_failed", False):
            detail = ""
            try:
                with open(os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), ".kunefelauncher", "prefetch_error.txt"), encoding="utf-8") as f:
                    detail = "\n\nHata: " + f.read()[:350]
            except Exception:
                pass
            extra = ("\n\nOyun dosyaları indirilemedi. Launcher'ı açıp OYNA'ya basınca tekrar denenecek." + detail)
        tk.Label(r, text=f"{APP} bilgisayarına kuruldu.\nİyi oyunlar!" + extra, bg=BG, fg=FG, justify="left",
                 wraplength=340, font=("Segoe UI", 11)).pack(anchor="w")
        bar = tk.Frame(r, bg=BG)
        bar.pack(side="bottom", fill="x")
        self.button(bar, "Bitir", self.finish).pack(side="right")

    def finish(self):
        if self.v_launch.get() and self.installed_exe:
            try:
                subprocess.Popen([self.installed_exe], cwd=INSTALL_DIR, creationflags=DETACHED | NO_WINDOW, close_fds=True)
            except Exception:
                pass
        self.destroy()

    # --- kurulum işi
    def start_install(self):
        opts = (self.v_desktop.get(), self.v_start.get())
        self.page_progress()
        threading.Thread(target=self.install, args=opts, daemon=True).start()

    def step(self, n, text):
        self.after(0, lambda: (self.status.set(text), self.pb.configure(value=n)))

    def install(self, want_desktop, want_start):
        try:
            payload = resource_path(os.path.join("payload", "app.zip"))
            if not os.path.isfile(payload):
                raise RuntimeError("Kurulum dosyası eksik veya bozuk. Setup'ı yeniden indir.")

            self.step(1, "Açık launcher varsa kapatılıyor...")
            subprocess.run(["taskkill", "/F", "/IM", EXE], capture_output=True, creationflags=NO_WINDOW)

            self.step(2, "Dosyalar kuruluyor...")
            if os.path.isdir(INSTALL_DIR):
                shutil.rmtree(INSTALL_DIR, ignore_errors=True)
            os.makedirs(INSTALL_DIR, exist_ok=True)
            exe = os.path.join(INSTALL_DIR, EXE)
            try:
                with zipfile.ZipFile(payload) as z:
                    z.extractall(INSTALL_DIR)
            except PermissionError:
                raise RuntimeError(f"{APP} şu an açık görünüyor. Kapatıp kurulumu tekrar dene.")
            if not os.path.isfile(exe):
                raise RuntimeError("Kurulum eksik tamamlandı. Setup'ı yeniden indir.")

            uninstaller = os.path.join(INSTALL_DIR, "Uninstall.exe")
            if getattr(sys, "frozen", False):
                shutil.copy2(sys.executable, uninstaller)

            self.step(3, "Kısayollar oluşturuluyor...")
            if want_desktop:
                make_shortcut("Desktop", exe, INSTALL_DIR, exe)
            if want_start:
                make_shortcut("Programs", exe, INSTALL_DIR, exe)

            self.step(4, "Kayıt defterine ekleniyor...")
            if os.path.isfile(uninstaller):
                write_uninstall_entry(uninstaller, exe)

            self.installed_exe = exe
            game = resource_path(os.path.join("payload", "game.zip"))
            if os.path.isfile(game):
                self.step(4, "Oyun dosyaları kuruluyor (internet gerekmez)...")
                base = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), ".kunefelauncher")
                os.makedirs(base, exist_ok=True)
                keep = {"config.json", os.path.join("minecraft", "options.txt"), os.path.join("minecraft", "servers.dat")}
                with zipfile.ZipFile(game) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        arc = os.path.normpath(info.filename)
                        dst = os.path.join(base, arc)
                        if arc in keep and os.path.exists(dst):
                            continue
                        if os.path.isfile(dst) and os.path.getsize(dst) == info.file_size:
                            continue
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        with z.open(info) as src, open(dst + ".part", "wb") as out:
                            shutil.copyfileobj(src, out)
                        os.replace(dst + ".part", dst)
            self.step(5, "Oyun, Java ve modlar indiriliyor... (internet hızına göre birkaç dakika sürebilir)")
            self.prefetch_failed = False
            try:
                rc = subprocess.run([exe, "--prefetch"], cwd=INSTALL_DIR, creationflags=NO_WINDOW, timeout=3600).returncode
                self.prefetch_failed = rc != 0
            except Exception:
                self.prefetch_failed = True
            self.step(6, "Tamamlandı")
            self.after(300, self.page_done)
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self.page_done(error=msg))


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        run_uninstall()
    else:
        Setup().mainloop()
