-- KünefePoint (KP) tabloları. AuthMe veritabanında (veya aynı MySQL sunucusunda ayrı bir DB'de) çalıştır.
CREATE TABLE IF NOT EXISTS kp_balance (
  username VARCHAR(32) NOT NULL PRIMARY KEY,   -- küçük harfli oyuncu adı
  kp INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kp_cosmetics (
  id VARCHAR(32) NOT NULL PRIMARY KEY,         -- örn. cape_orange
  name VARCHAR(64) NOT NULL,
  type VARCHAR(16) NOT NULL,                   -- cape | hat | wings | aura | trail
  price INT NOT NULL,
  perm VARCHAR(96) NOT NULL DEFAULT ''         -- UltraCosmetics yetki düğümü, örn. ultracosmetics.hats.santa
);
CREATE TABLE IF NOT EXISTS kp_owned (
  username VARCHAR(32) NOT NULL,
  cosmetic_id VARCHAR(32) NOT NULL,
  equipped TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (username, cosmetic_id)
);
-- Örnek kayıtlar: perm değerlerini UltraCosmetics'in gerçek yetki adlarıyla DOĞRULA (oyunda /uc menu > ilgili eşya,
-- ya da eklentinin wiki/config sayfası). Sadece örnektir.
INSERT IGNORE INTO kp_cosmetics (id,name,type,price,perm) VALUES
 ('hat_santa','Noel Şapkası','hat',100,'ultracosmetics.hats.santa'),
 ('pet_parrot','Omuz Papağanı','pet',250,'ultracosmetics.pets.parrot');
