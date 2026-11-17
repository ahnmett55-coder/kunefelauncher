package tr.kunefe.menu;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.PlayerListEntry;
import net.minecraft.entity.EquipmentSlot;
import net.minecraft.item.ItemStack;
import net.minecraft.text.Text;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/** Künefe HUD modülleri: FPS, ping, koordinat, yön, saat, zırh, tuş göstergesi. */
public final class HudModules {
    private static final int ORANGE = 0xFFFF8C00;
    private static final int WHITE = 0xFFFFFFFF;
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm");

    private HudModules() {}

    public static String title(String id) {
        switch (id) {
            case "fps": return "FPS";
            case "ping": return "Ping";
            case "coords": return "Koordinat";
            case "direction": return "Yön";
            case "clock": return "Saat";
            case "armor": return "Zırh";
            case "keys": return "Tuşlar";
            default: return id;
        }
    }

    public static int width(MinecraftClient mc, String id) {
        if (id.equals("armor")) return 22;
        if (id.equals("keys")) return 70;
        return mc.textRenderer.getWidth(line(mc, id)) + 10;
    }

    public static int height(String id) {
        if (id.equals("armor")) return 4 * 18 + 4;
        if (id.equals("keys")) return 3 * 22;
        return 14;
    }

    private static String line(MinecraftClient mc, String id) {
        try {
            switch (id) {
                case "fps":
                    return "FPS: " + mc.getCurrentFps();
                case "ping": {
                    int ms = 0;
                    if (mc.player != null && mc.getNetworkHandler() != null) {
                        PlayerListEntry e = mc.getNetworkHandler().getPlayerListEntry(mc.player.getUuid());
                        if (e != null) ms = e.getLatency();
                    }
                    return "Ping: " + ms + " ms";
                }
                case "coords":
                    if (mc.player == null) return "XYZ: -";
                    return String.format("XYZ: %d %d %d", (int) Math.floor(mc.player.getX()),
                            (int) Math.floor(mc.player.getY()), (int) Math.floor(mc.player.getZ()));
                case "direction":
                    return mc.player == null ? "Yön: -" : "Yön: " + mc.player.getHorizontalFacing().name();
                case "clock":
                    return LocalTime.now().format(CLOCK);
                default:
                    return id;
            }
        } catch (Exception e) {
            return id;
        }
    }

    /** Tek modülü (x, y) konumuna çizer. */
    public static void draw(DrawContext ctx, MinecraftClient mc, String id, int x, int y) {
        int w = width(mc, id);
        int h = height(id);
        if (id.equals("armor")) {
            ctx.fill(x, y, x + w, y + h, 0x88000000);
            ctx.fill(x, y, x + 2, y + h, ORANGE);
            if (mc.player == null) return;
            EquipmentSlot[] slots = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
            for (int i = 0; i < slots.length; i++) {
                ItemStack st = mc.player.getEquippedStack(slots[i]);
                if (!st.isEmpty()) ctx.drawItem(st, x + 4, y + 2 + i * 18);
            }
            return;
        }
        if (id.equals("keys")) {
            keys(ctx, mc, x, y);
            return;
        }
        ctx.fill(x, y, x + w, y + h, 0x88000000);
        ctx.fill(x, y, x + 2, y + h, ORANGE);
        ctx.drawTextWithShadow(mc.textRenderer, Text.literal(line(mc, id)), x + 6, y + 3, WHITE);
    }

    private static void key(DrawContext ctx, MinecraftClient mc, int x, int y, int w, String label, boolean down) {
        ctx.fill(x, y, x + w, y + 20, down ? 0xCCFF8C00 : 0x88000000);
        ctx.drawCenteredTextWithShadow(mc.textRenderer, Text.literal(label), x + w / 2, y + 6, WHITE);
    }

    private static void keys(DrawContext ctx, MinecraftClient mc, int x, int y) {
        if (mc.options == null) return;
        key(ctx, mc, x + 24, y, 22, "W", mc.options.forwardKey.isPressed());
        key(ctx, mc, x, y + 22, 22, "A", mc.options.leftKey.isPressed());
        key(ctx, mc, x + 24, y + 22, 22, "S", mc.options.backKey.isPressed());
        key(ctx, mc, x + 48, y + 22, 22, "D", mc.options.rightKey.isPressed());
        key(ctx, mc, x, y + 44, 70, "ZIPLA", mc.options.jumpKey.isPressed());
    }

    /** Oyun içi HUD: açık modülleri çizer. */
    public static void renderAll(DrawContext ctx) {
        MinecraftClient mc = MinecraftClient.getInstance();
        if (mc.player == null || mc.options.hudHidden) return;
        for (java.util.Map.Entry<String, HudConfig.Mod> e : HudConfig.MODS.entrySet()) {
            if (e.getValue().on) draw(ctx, mc, e.getKey(), e.getValue().x, e.getValue().y);
        }
    }
}
