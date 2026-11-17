#!/usr/bin/env python3
"""KünefeCraft Android modpack'i (.mrpack) üretir.

Zalith tabanlı launcher'da bu dosyayı bir kez içe aktarırsın: Minecraft 1.21.11 + Fabric + modlar,
Türkçe dil ve sunucu listesi tek seferde kurulur.

Kullanım:  python tools/make_mrpack.py            -> KunefeCraft-Android-1.21.11.mrpack
GitHub Actions bunu otomatik çalıştırıp APK ile birlikte yükler.
Sadece Python 3 standart kütüphanesi gerekir (internet gerekir).
"""
import hashlib
import io
import json
import struct
import sys
import urllib.parse
import urllib.request
import zipfile

MC = "1.21.11"
NAME = "KünefeCraft"
SERVER_NAME = "KünefeCraft"
SERVER_IP = "87.232.127.49:25565"
OUT = f"KunefeCraft-Android-{MC}.mrpack"
UA = "KunefeLauncher-Android/1.0 (modpack builder)"

# Android'de güvenli mod listesi. Sodium / Sodium Extra / ImmediatelyFast bilerek YOK:
# OpenGL çevirisiyle (Pojav renderer'ları) çalışmayabiliyor ve oyunu çökertebiliyor.
MODS = ["fabric-api", "lithium", "ferrite-core", "modernfix", "entityculling", "moreculling"]


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url):
    return json.loads(get(url).decode("utf-8"))


def latest_version(project):
    q = urllib.parse.urlencode({"game_versions": json.dumps([MC]), "loaders": json.dumps(["fabric"])})
    vs = get_json(f"https://api.modrinth.com/v2/project/{project}/version?{q}")
    return vs[0] if vs else None


def fabric_loader():
    data = get_json(f"https://meta.fabricmc.net/v2/versions/loader/{MC}")
    for d in data:
        if d["loader"].get("stable"):
            return d["loader"]["version"]
    return data[0]["loader"]["version"]


# ---- servers.dat (NBT) ----
def _str(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def servers_dat():
    entry = b"\x08" + _str("ip") + _str(SERVER_IP) + b"\x08" + _str("name") + _str(SERVER_NAME) + b"\x00"
    servers = b"\x09" + _str("servers") + b"\x0a" + struct.pack(">i", 1) + entry
    return b"\x0a" + _str("") + servers + b"\x00"


def build(mods=MODS, loader=None, fetch_version=latest_version, fetch_file=get):
    loader = loader or fabric_loader()
    files, seen, queue = [], set(), list(mods)
    missing = []
    while queue:
        slug = queue.pop(0)
        if slug in seen:
            continue
        seen.add(slug)
        v = fetch_version(slug)
        if not v:
            missing.append(slug)
            continue
        f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
        data = fetch_file(f["url"])
        sha1, sha512 = hashlib.sha1(data).hexdigest(), hashlib.sha512(data).hexdigest()
        expected = (f.get("hashes") or {}).get("sha512")
        if expected and expected.lower() != sha512:
            raise RuntimeError(f"{f['filename']} hash uyuşmuyor")
        files.append({
            "path": f"mods/{f['filename']}",
            "hashes": {"sha1": sha1, "sha512": sha512},
            "env": {"client": "required", "server": "unsupported"},
            "downloads": [f["url"]],
            "fileSize": len(data),
        })
        for d in v.get("dependencies", []):
            if d.get("dependency_type") == "required" and d.get("project_id"):
                queue.append(d["project_id"])
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.0.0",
        "name": NAME,
        "summary": "KünefeCraft sunucusu için Android paketi",
        "files": files,
        "dependencies": {"minecraft": MC, "fabric-loader": loader},
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
        z.writestr("overrides/options.txt", "lang:tr_tr\n")
        z.writestr("overrides/servers.dat", servers_dat())
    return buf.getvalue(), index, missing


if __name__ == "__main__":
    data, index, missing = build()
    with open(OUT, "wb") as f:
        f.write(data)
    print(f"{OUT}: {len(index['files'])} dosya, fabric-loader {index['dependencies']['fabric-loader']}")
    if missing:
        print("UYARI: bu sürüm için bulunamayan modlar atlandı:", ", ".join(missing), file=sys.stderr)
