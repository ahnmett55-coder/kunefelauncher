package tr.kunefe.menu;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/** kunefecraft.com.tr/kp.php istemcisi (sadece okuma). */
public final class KunefeApi {
    public static final String SITE = "https://kunefecraft.com.tr";
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

    private static JsonObject get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(SITE + path)).timeout(Duration.ofSeconds(10))
                .header("User-Agent", "KunefeMenu/1.0").GET().build();
        HttpResponse<byte[]> res = HTTP.send(req, HttpResponse.BodyHandlers.ofByteArray());
        if (res.statusCode() != 200) throw new IllegalStateException("HTTP " + res.statusCode());
        JsonObject o = JsonParser.parseString(new String(res.body(), StandardCharsets.UTF_8)).getAsJsonObject();
        if (!o.has("ok") || !o.get("ok").getAsBoolean()) throw new IllegalStateException("API hata");
        return o;
    }

    public static Me me(String player) throws Exception {
        JsonObject o = get("/kp.php?a=me&user=" + player.toLowerCase());
        Me m = new Me();
        m.kp = o.has("kp") ? o.get("kp").getAsInt() : 0;
        if (o.has("owned")) {
            for (JsonElement el : o.getAsJsonArray("owned")) m.owned.add(el.getAsJsonObject().get("name").getAsString());
        }
        return m;
    }

    public static List<Item> catalog() throws Exception {
        JsonObject o = get("/kp.php?a=catalog");
        List<Item> out = new ArrayList<>();
        JsonArray arr = o.getAsJsonArray("items");
        for (JsonElement el : arr) {
            JsonObject i = el.getAsJsonObject();
            Item it = new Item();
            it.name = i.get("name").getAsString();
            it.type = i.get("type").getAsString();
            it.price = i.get("price").getAsInt();
            out.add(it);
        }
        return out;
    }
}
