package tr.kunefe.menu;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Künefe Menü ayarları (config/kunefemenu.json): nişangah ve el eşyası konumu. */
public final class KunefeConfig {
    public static final class Data {
        // nişangah
        public boolean crossOn = false;
        public int crossStyle = 0;      // 0 artı, 1 nokta, 2 kare, 3 T
        public int crossColor = 0;      // CROSS_COLORS indeksi
        public int crossSize = 5;
        public int crossGap = 3;
        public int crossThick = 1;
        public boolean crossRedOnTarget = true;
        // el eşyası konumu (0.01 blok birimi)
        public boolean handOn = false;
        public int handX = 0;
        public int handY = 0;
        public int handZ = 0;
    }

    public static final int[] CROSS_COLORS = {0xFFFF8C00, 0xFFFFFFFF, 0xFF55FF55, 0xFFFF5555, 0xFF55AAFF, 0xFFFFFF55};
    public static final String[] CROSS_COLOR_NAMES = {"Turuncu", "Beyaz", "Yeşil", "Kırmızı", "Mavi", "Sarı"};
    public static final String[] CROSS_STYLES = {"Artı", "Nokta", "Kare", "T"};

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    public static Data d = new Data();

    private KunefeConfig() {}

    private static Path file() {
        return FabricLoader.getInstance().getConfigDir().resolve("kunefemenu.json");
    }

    public static void load() {
        try {
            Path p = file();
            if (!Files.exists(p)) return;
            Data x = GSON.fromJson(Files.readString(p, StandardCharsets.UTF_8), Data.class);
            if (x != null) d = x;
        } catch (Exception ignored) {
            // bozuk dosya: varsayılanlar
        }
    }

    public static void save() {
        try {
            Files.writeString(file(), GSON.toJson(d), StandardCharsets.UTF_8);
        } catch (Exception ignored) {
        }
    }
}
