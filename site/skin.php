<?php
// KünefeLauncher skin yükleme ucu. Sitene /skin.php olarak koy; /skins/ klasörü yazılabilir olmalı.
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
function out($ok, $msg = '', $extra = []) { echo json_encode(array_merge(['ok' => $ok, 'message' => $msg], $extra)); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(false, 'Sadece POST.');
$id = $_POST['id'] ?? '';
if (!preg_match('/^[a-f0-9]{16,32}$/', $id)) out(false, 'Geçersiz kimlik.');
if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) out(false, 'Dosya alınamadı.');
if ($_FILES['file']['size'] > 100 * 1024) out(false, 'Skin en fazla 100 KB olabilir.');
$info = @getimagesize($_FILES['file']['tmp_name']);
if (!$info || $info[2] !== IMAGETYPE_PNG) out(false, 'Sadece PNG kabul edilir.');
if (!($info[0] === 64 && ($info[1] === 64 || $info[1] === 32))) out(false, 'Skin 64x64 veya 64x32 olmalı.');
$dir = __DIR__ . '/skins';
if (!is_dir($dir)) @mkdir($dir, 0755, true);
// basit hız sınırı: IP başına dakikada 6 yükleme
$rl = sys_get_temp_dir() . '/kunefe_skin_' . md5($_SERVER['REMOTE_ADDR'] ?? '');
$now = time(); $hits = [];
if (is_file($rl)) $hits = array_filter(array_map('intval', explode(',', (string)file_get_contents($rl))), fn($t) => $now - $t < 60);
if (count($hits) >= 6) out(false, 'Çok hızlı denedin, biraz bekle.');
$hits[] = $now; @file_put_contents($rl, implode(',', $hits));
// GD ile yeniden kodla (içine gizlenmiş veri olmasın)
$im = @imagecreatefrompng($_FILES['file']['tmp_name']);
if (!$im) out(false, 'PNG okunamadı.');
imagealphablending($im, false); imagesavealpha($im, true);
if (!@imagepng($im, "$dir/$id.png")) out(false, 'Kaydedilemedi (skins klasörü yazılabilir mi?).');
imagedestroy($im);
out(true, 'Yüklendi', ['url' => 'https://' . $_SERVER['HTTP_HOST'] . "/skins/$id.png"]);
