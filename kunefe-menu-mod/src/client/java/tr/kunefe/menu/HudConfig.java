package tr.kunefe.menu;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import net.fabricmc.loader.api.FabricLoader;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/** HUD modüllerinin açık/kapalı durumu ve konumları (config/kunefemenu_hud.json). */
public final class HudConfig {
    public static final class Mod {
        public boolean on;
        public int x;
        public int y;

        Mod(boolean on, int x, int y) {
            this.on = on;
            this.x = x;
            this.y = y;
        }
    }

    public static final Map<String, Mod> MODS = new LinkedHashMap<>();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    static {
        defaults();
    }

    private HudConfig() {}

    private static void defaults() {
        MODS.put("fps", new Mod(true, 6, 6));
        MODS.put("ping", new Mod(true, 6, 22));
        MODS.put("coords", new Mod(true, 6, 38));
        MODS.put("direction", new Mod(false, 6, 54));
        MODS.put("clock", new Mod(false, 6, 70));
        MODS.put("armor", new Mod(true, 6, 90));
        MODS.put("keys", new Mod(false, 6, 170));
        MODS.put("cps", new Mod(true, 6, 250));
        MODS.put("combo", new Mod(false, 6, 266));
        MODS.put("potions", new Mod(false, 6, 282));
        MODS.put("target", new Mod(false, 120, 6));
        MODS.put("reach", new Mod(false, 120, 22));
    }

    private static Path file() {
        return FabricLoader.getInstance().getConfigDir().resolve("kunefemenu_hud.json");
    }

    public static void load() {
        try {
            Path p = file();
            if (!Files.exists(p)) return;
            Map<String, Mod> saved = GSON.fromJson(Files.readString(p, StandardCharsets.UTF_8),
                    new TypeToken<Map<String, Mod>>() {}.getType());
            if (saved == null) return;
            for (Map.Entry<String, Mod> e : saved.entrySet()) {
                Mod cur = MODS.get(e.getKey());
                if (cur != null && e.getValue() != null) {
                    cur.on = e.getValue().on;
                    cur.x = e.getValue().x;
                    cur.y = e.getValue().y;
                }
            }
        } catch (Exception ignored) {
            // bozuk dosya: varsayılanlarla devam
        }
    }

    public static void save() {
        try {
            Files.writeString(file(), GSON.toJson(MODS), StandardCharsets.UTF_8);
        } catch (Exception ignored) {
        }
    }
}
