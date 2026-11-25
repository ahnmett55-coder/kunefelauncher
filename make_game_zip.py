"""gamecache\\.kunefelauncher klasorunu payload/game.zip yapar (hesap bilgileri ve loglar haric)."""
import json, os, sys, zipfile

root = os.path.join("gamecache", ".kunefelauncher")
out = os.path.join("payload", "game.zip")
if not os.path.isdir(os.path.join(root, "minecraft", "versions")):
    print("gamecache bos: oyun dosyalari indirilmemis")
    sys.exit(1)
os.makedirs("payload", exist_ok=True)
if os.path.exists(out):
    os.remove(out)
skip_dirs = {os.path.join("minecraft", "logs"), os.path.join("minecraft", "crash-reports"), "skins"}
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dp, dn, fn in os.walk(root):
        rel_dir = os.path.relpath(dp, root)
        dn[:] = [d for d in dn if os.path.normpath(os.path.join(rel_dir, d)) not in skip_dirs]
        for f in fn:
            if f.endswith((".part", ".log")) or f in ("crash.log", "prefetch_error.txt"):
                continue
            p = os.path.join(dp, f)
            arc = os.path.normpath(os.path.relpath(p, root))
            if arc == "config.json":
                continue
            z.write(p, arc)
            n += 1
print(f"game.zip hazir: {n} dosya, {os.path.getsize(out) // 1048576} MB")
