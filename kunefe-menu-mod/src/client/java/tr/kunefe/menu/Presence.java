package tr.kunefe.menu;

import net.minecraft.client.MinecraftClient;
import net.minecraft.text.MutableText;
import net.minecraft.text.Style;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/** KünefeLauncher/Künefe Menü kullanan oyuncular: TAB listesinde isim önüne logo koymak için. */
public final class Presence {
    private static final Set<String> ONLINE = ConcurrentHashMap.newKeySet();
    private static long lastPing;
    private static long lastFetch;

    private Presence() {}

    /** Logo (özel yazı tipindeki  karakteri) + boşluk. */
    public static MutableText logo() {
        return Text.literal(" ").setStyle(Style.EMPTY.withFont(Identifier.of("kunefemenu", "logo")));
    }

    public static boolean isLauncher(String name) {
        return name != null && ONLINE.contains(name.toLowerCase(Locale.ROOT));
    }

    /** Launcher, çevrimiçi launcher oyuncularını oyun klasöründeki kunefe_online.txt'ye yazar; buradan okunur. */
    public static void tick(MinecraftClient mc) {
        if (mc.player == null || mc.getNetworkHandler() == null) return;
        long now = System.currentTimeMillis();
        if (now - lastFetch < 10_000) return;
        lastFetch = now;
        String me = mc.player.getName().getString().toLowerCase(Locale.ROOT);
        try {
            java.nio.file.Path f = net.fabricmc.loader.api.FabricLoader.getInstance().getGameDir().resolve("kunefe_online.txt");
            Set<String> names = new java.util.HashSet<>();
            if (java.nio.file.Files.exists(f)) {
                for (String l : java.nio.file.Files.readAllLines(f, java.nio.charset.StandardCharsets.UTF_8)) {
                    if (!l.isBlank()) names.add(l.trim().toLowerCase(Locale.ROOT));
                }
            }
            names.add(me);
            ONLINE.clear();
            ONLINE.addAll(names);
        } catch (Exception ignored) {
        }
    }
}
