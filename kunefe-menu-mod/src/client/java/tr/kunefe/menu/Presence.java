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

    public static void tick(MinecraftClient mc) {
        if (mc.player == null || mc.getNetworkHandler() == null) return;
        long now = System.currentTimeMillis();
        String me = mc.player.getName().getString();
        if (now - lastPing > 60_000) {
            lastPing = now;
            ONLINE.add(me.toLowerCase(Locale.ROOT));
            Thread t = new Thread(() -> {
                try {
                    KunefeApi.ping(me);
                } catch (Exception ignored) {
                }
            }, "kunefe-ping");
            t.setDaemon(true);
            t.start();
        }
        if (now - lastFetch > 30_000) {
            lastFetch = now;
            Thread t = new Thread(() -> {
                try {
                    Set<String> names = KunefeApi.online();
                    ONLINE.clear();
                    ONLINE.addAll(names);
                    ONLINE.add(me.toLowerCase(Locale.ROOT));
                } catch (Exception ignored) {
                }
            }, "kunefe-online");
            t.setDaemon(true);
            t.start();
        }
    }
}
