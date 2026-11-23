package tr.kunefe.menu;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/** kunefecraft.com.tr istemcisi: KP, katalog, çevrimiçi launcher oyuncuları, skin listesi. */
public final class KunefeApi {
    public static final String SITE = "https://kunefecraft.com.tr";
    public static final String SERVER_IP = "87.232.127.49:25567";
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(8)).build();

    private KunefeApi() {}

    public static final class Me {
        public int kp;
        public final List<String> owned = new ArrayList<>();
    }

    public static final class Item {
        public String name;
        public String type;
        public int price;
    }

    public static byte[] getBytes(String url) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(12))
                .header("User-Agent", "KunefeMenu/2.0").GET().build();
        HttpResponse<byte[]> res = HTTP.send(req, HttpResponse.BodyHandlers.ofByteArray());
        if (res.statusCode() != 200 || res.body().length > 2 * 1024 * 1024) throw new IllegalStateException("HTTP " + res.statusCode());
        return res.body();
    }

    private static JsonObject getJson(String path) throws Exception {
        JsonObject o = JsonParser.parseString(new String(getBytes(SITE + path), StandardCharsets.UTF_8)).getAsJsonObject();
        if (!o.has("ok") || !o.get("ok").getAsBoolean()) throw new IllegalStateException("API hata");
        return o;
    }

    public static Me me(String player) throws Exception {
        JsonObject o = getJson("/kp.php?a=me&user=" + player.toLowerCase(Locale.ROOT));
        Me m = new Me();
        m.kp = o.has("kp") ? o.get("kp").getAsInt() : 0;
        if (o.has("owned")) {
            for (JsonElement el : o.getAsJsonArray("owned")) m.owned.add(el.getAsJsonObject().get("name").getAsString());
        }
        return m;
    }

    public static List<Item> catalog() throws Exception {
        JsonObject o = getJson("/kp.php?a=catalog");
        List<Item> out = new ArrayList<>();
        for (JsonElement el : o.getAsJsonArray("items")) {
            JsonObject i = el.getAsJsonObject();
            Item it = new Item();
            it.name = i.get("name").getAsString();
            it.type = i.get("type").getAsString();
            it.price = i.get("price").getAsInt();
            out.add(it);
        }
        return out;
    }

    /** Oyuncu şu an KünefeLauncher/Menü ile oyunda: siteye "buradayım" bildirir. */
    public static void ping(String name) throws Exception {
        String body = "a=ping&name=" + URLEncoder.encode(name, StandardCharsets.UTF_8);
        HttpRequest req = HttpRequest.newBuilder(URI.create(SITE + "/kp.php")).timeout(Duration.ofSeconds(8))
                .header("User-Agent", "KunefeMenu/2.0").header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HTTP.send(req, HttpResponse.BodyHandlers.discarding());
    }

    /** Son 90 saniyede bildirimde bulunan launcher oyuncuları (küçük harf). */
    public static Set<String> online() throws Exception {
        JsonObject o = getJson("/kp.php?a=online");
        Set<String> out = new HashSet<>();
        JsonArray arr = o.getAsJsonArray("names");
        for (JsonElement el : arr) out.add(el.getAsString().toLowerCase(Locale.ROOT));
        return out;
    }

    /** Sitenin skin listesi (skins.json: ["Ad1","Ad2",...]); yoksa yerleşik liste. */
    public static List<String> featuredSkins() {
        List<String> out = new ArrayList<>();
        try {
            JsonArray arr = JsonParser.parseString(new String(getBytes(SITE + "/skins.json"), StandardCharsets.UTF_8)).getAsJsonArray();
            for (JsonElement el : arr) {
                String n = el.getAsString();
                if (n.matches("\\w{1,16}")) out.add(n);
            }
        } catch (Exception ignored) {
        }
        if (out.isEmpty()) {
            for (String n : new String[]{"Dream", "Notch", "jeb_", "Dinnerbone", "Grian", "Mumbo", "Sapnap", "TommyInnit", "Philza", "Skeppy"}) out.add(n);
        }
        return out;
    }
}
