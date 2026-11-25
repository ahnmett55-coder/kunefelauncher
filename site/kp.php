<?php
// KünefePoint API. Sitene /kp.php olarak koy. Ayarları aşağıda doldur.
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
const DB_DSN  = 'mysql:host=localhost;dbname=VERITABANI;charset=utf8mb4';
const DB_USER = 'KULLANICI';
const DB_PASS = 'SIFRE';
const ADMIN_KEY = 'BURAYA_UZUN_RASTGELE_BIR_ANAHTAR_YAZ';   // KP vermek için (ödeme sayfan bunu kullanır)
const AUTHME_TABLE = 'authme';                                // AuthMe tablo adı
const RCON_HOST = '87.232.127.49';  // server.properties: enable-rcon=true, rcon.port, rcon.password
const RCON_PORT = 25575;
const RCON_PASS = 'RCON_SIFRESI';
const PERM_CMD  = 'lp user %s permission set %s true';   // LuckPerms kullanıyorsan; yoksa kendi komutunu yaz

// Minimal RCON istemcisi (Source RCON protokolü)
function rcon($cmd) {
    $s = @fsockopen(RCON_HOST, RCON_PORT, $en, $es, 4);
    if (!$s) return false;
    stream_set_timeout($s, 4);
    $send = function ($id, $type, $body) use ($s) {
        $pkt = pack('VV', $id, $type) . $body . "\0\0";
        fwrite($s, pack('V', strlen($pkt)) . $pkt);
        $len = unpack('V', fread($s, 4));
        if (!$len) return null;
        $r = ''; while (strlen($r) < $len[1]) { $c = fread($s, $len[1] - strlen($r)); if ($c === '' || $c === false) break; $r .= $c; }
        return unpack('Vid/Vtype', substr($r, 0, 8));
    };
    $auth = $send(1, 3, RCON_PASS);
    $ok = false;
    if ($auth && $auth['id'] === 1) { $send(2, 2, $cmd); $ok = true; }
    fclose($s);
    return $ok;
}

function out($ok, $msg = '', $extra = []) { echo json_encode(array_merge(['ok' => $ok, 'message' => $msg], $extra), JSON_UNESCAPED_UNICODE); exit; }
try { $db = new PDO(DB_DSN, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]); }
catch (Exception $e) { out(false, 'Veritabanına bağlanılamadı.'); }

function uname($s) { $s = strtolower(trim((string)$s)); return preg_match('/^\w{1,16}$/', $s) ? $s : null; }

// AuthMe SHA256 ($SHA$tuz$hash) doğrulama. bcrypt kullanıyorsan password_verify ile değiştir.
function authme_ok($db, $user, $pass) {
    $st = $db->prepare('SELECT password FROM ' . AUTHME_TABLE . ' WHERE username = ?');
    $st->execute([$user]);
    $h = $st->fetchColumn();
    if (!$h) return false;
    if (strpos($h, '$SHA$') === 0) { $p = explode('$', $h); return isset($p[3]) && hash_equals($p[3], hash('sha256', hash('sha256', $pass) . $p[2])); }
    if (strpos($h, '$2') === 0) return password_verify($pass, $h);
    return false;
}

$a = $_REQUEST['a'] ?? '';
if ($a === 'ping') {   // Künefe Menü/Launcher oyuncusu "buradayım" der (TAB logosu için)
    $n = uname($_POST['name'] ?? '');
    if (!$n) out(false, 'ad');
    $f = __DIR__ . '/online.json';
    $d = is_file($f) ? (json_decode(@file_get_contents($f), true) ?: []) : [];
    $now = time();
    $d[$n] = $now;
    foreach ($d as $k => $t) if ($now - $t > 120) unset($d[$k]);
    @file_put_contents($f, json_encode($d), LOCK_EX);
    out(true);
}
if ($a === 'online') {  // son 90 sn içinde ping atanlar
    $f = __DIR__ . '/online.json';
    $d = is_file($f) ? (json_decode(@file_get_contents($f), true) ?: []) : [];
    $now = time(); $names = [];
    foreach ($d as $k => $t) if ($now - $t <= 90) $names[] = $k;
    out(true, '', ['names' => $names]);
}
if ($a === 'catalog') {
    out(true, '', ['items' => $db->query('SELECT id,name,type,price FROM kp_cosmetics ORDER BY price')->fetchAll(PDO::FETCH_ASSOC)]);
}
if ($a === 'me') {   // herkese açık okuma: bakiye + sahip olunanlar (oyun/launcher bunu kullanır)
    $u = uname($_GET['user'] ?? ''); if (!$u) out(false, 'Geçersiz ad.');
    $st = $db->prepare('SELECT kp FROM kp_balance WHERE username=?'); $st->execute([$u]);
    $kp = (int)$st->fetchColumn();
    $st = $db->prepare('SELECT c.id,c.name,c.type,o.equipped FROM kp_owned o JOIN kp_cosmetics c ON c.id=o.cosmetic_id WHERE o.username=?');
    $st->execute([$u]);
    out(true, '', ['kp' => $kp, 'owned' => $st->fetchAll(PDO::FETCH_ASSOC)]);
}
if ($a === 'grant') {   // sadece sen: ödeme sonrası KP ekle. POST key, user, amount
    if (!hash_equals(ADMIN_KEY, (string)($_POST['key'] ?? ''))) out(false, 'Yetkisiz.');
    $u = uname($_POST['user'] ?? ''); $n = (int)($_POST['amount'] ?? 0);
    if (!$u || $n === 0) out(false, 'Eksik bilgi.');
    $db->prepare('INSERT INTO kp_balance (username,kp) VALUES (?,?) ON DUPLICATE KEY UPDATE kp = GREATEST(0, kp + VALUES(kp))')->execute([$u, $n]);
    out(true, 'Tamam');
}
if ($a === 'buy' || $a === 'equip') {   // POST user, pass (oyuncunun AuthMe şifresi), id
    $u = uname($_POST['user'] ?? ''); $id = preg_replace('/[^a-z0-9_]/', '', (string)($_POST['id'] ?? ''));
    if (!$u || !$id) out(false, 'Eksik bilgi.');
    if (!authme_ok($db, $u, (string)($_POST['pass'] ?? ''))) out(false, 'Kullanıcı adı veya şifre yanlış.');
    $st = $db->prepare('SELECT price,perm FROM kp_cosmetics WHERE id=?'); $st->execute([$id]);
    $row = $st->fetch(PDO::FETCH_ASSOC); if (!$row) out(false, 'Böyle bir kozmetik yok.');
    $price = (int)$row['price']; $perm = $row['perm'];
    $db->beginTransaction();
    if ($a === 'buy') {
        $st = $db->prepare('SELECT 1 FROM kp_owned WHERE username=? AND cosmetic_id=?'); $st->execute([$u, $id]);
        if ($st->fetchColumn()) { $db->rollBack(); out(false, 'Bu kozmetiğe zaten sahipsin.'); }
        $st = $db->prepare('UPDATE kp_balance SET kp = kp - ? WHERE username=? AND kp >= ?'); $st->execute([$price, $u, $price]);
        if ($st->rowCount() !== 1) { $db->rollBack(); out(false, 'Yeterli KP yok.'); }
        $db->prepare('INSERT INTO kp_owned (username,cosmetic_id) VALUES (?,?)')->execute([$u, $id]);
        // Sunucuda yetkiyi ver; olmazsa satın almayı geri al (KP kaybolmasın)
        if ($perm !== '' && !rcon(sprintf(PERM_CMD, $row_user = $u, $perm))) {
            $db->rollBack(); out(false, 'Oyun sunucusuna ulaşılamadı, satın alma iptal edildi. Biraz sonra tekrar dene.');
        }
    } else {
        $st = $db->prepare('SELECT 1 FROM kp_owned WHERE username=? AND cosmetic_id=?'); $st->execute([$u, $id]);
        if (!$st->fetchColumn()) { $db->rollBack(); out(false, 'Bu kozmetiğe sahip değilsin.'); }
        $db->prepare('UPDATE kp_owned SET equipped = (cosmetic_id = ?) WHERE username=?')->execute([$id, $u]);
    }
    $db->commit();
    out(true, 'Tamam');
}
out(false, 'Bilinmeyen işlem.');
