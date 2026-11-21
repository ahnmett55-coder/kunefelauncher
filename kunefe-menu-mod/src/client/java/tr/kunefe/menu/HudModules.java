package tr.kunefe.menu;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.PlayerListEntry;
import net.minecraft.entity.EquipmentSlot;
import net.minecraft.entity.effect.StatusEffectInstance;
import net.minecraft.item.ItemStack;
import net.minecraft.text.Text;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.hit.EntityHitResult;
import net.minecraft.util.hit.HitResult;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

/** Künefe HUD modülleri. */
public final class HudModules {
    private static final int ORANGE = 0xFFFF8C00;
    private static final int WHITE = 0xFFFFFFFF;
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm");

    private static final ArrayDeque<Long> LEFT = new ArrayDeque<>();
    private static final ArrayDeque<Long> RIGHT = new ArrayDeque<>();
    private static boolean lastL;
    private static boolean lastR;
    private static int combo;
    private static long lastHit;

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
            case "cps": return "CPS";
            case "combo": return "Kombo";
            case "potions": return "İksirler";
            case "target": return "Hedef (blok/varlık)";
            case "reach": return "Vuruş menzili";
            case "itemcount": return "Eşya Sayacı";
            case "shield": return "Kalkan Durumu";
            default: return id;
        }
    }

    /** Her tick: CPS ve kombo sayaçlarını günceller. */
    public static void tick(MinecraftClient mc) {
        if (mc.options == null) return;
        fullbright(mc);
        long now = System.currentTimeMillis();
        boolean l = mc.options.attackKey.isPressed();
        boolean r = mc.options.useKey.isPressed();
        if (l && !lastL) LEFT.add(now);
        if (r && !lastR) RIGHT.add(now);
        lastL = l;
        lastR = r;
        while (!LEFT.isEmpty() && now - LEFT.peekFirst() > 1000) LEFT.pollFirst();
        while (!RIGHT.isEmpty() && now - RIGHT.peekFirst() > 1000) RIGHT.pollFirst();
        if (combo > 0 && (now - lastHit > 2000 || (mc.player != null && mc.player.hurtTime > 0))) combo = 0;
    }

    private static boolean fbApplied;

    private static void fullbright(MinecraftClient mc) {
        if (mc.player == null) { fbApplied = false; return; }
        if (KunefeConfig.d.fullbright) {
            net.minecraft.entity.effect.StatusEffectInstance cur = mc.player.getStatusEffect(net.minecraft.entity.effect.StatusEffects.NIGHT_VISION);
            if (cur == null || cur.getDuration() < 400) {
                mc.player.addStatusEffect(new net.minecraft.entity.effect.StatusEffectInstance(
                        net.minecraft.entity.effect.StatusEffects.NIGHT_VISION, 1200, 0, false, false, false));
            }
            fbApplied = true;
        } else if (fbApplied) {
            mc.player.removeStatusEffect(net.minecraft.entity.effect.StatusEffects.NIGHT_VISION);
            fbApplied = false;
        }
    }

    /** Oyuncu bir varlığa vurdu. */
    public static void onAttack() {
        combo++;
        lastHit = System.currentTimeMillis();
    }

    public static int width(MinecraftClient mc, String id) {
        if (id.equals("armor")) return 22;
        if (id.equals("keys")) return 70;
        if (id.equals("potions")) return 120;
        return mc.textRenderer.getWidth(line(mc, id)) + 10;
    }

    public static int height(MinecraftClient mc, String id) {
        if (id.equals("armor")) return 4 * 18 + 4;
        if (id.equals("keys")) return 3 * 22;
        if (id.equals("potions")) return 14 * Math.max(1, effects(mc).size());
        return 14;
    }

    private static List<StatusEffectInstance> effects(MinecraftClient mc) {
        List<StatusEffectInstance> out = new ArrayList<>();
        if (mc.player != null) out.addAll(mc.player.getStatusEffects());
        return out;
    }

    private static String time(int ticks) {
        int s = ticks / 20;
        return String.format("%d:%02d", s / 60, s % 60);
    }

    private static String roman(int amp) {
        String[] r = {"", " II", " III", " IV", " V"};
        return amp >= 0 && amp < r.length ? r[amp] : " " + (amp + 1);
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
                case "cps":
                    return "CPS: " + LEFT.size() + " | " + RIGHT.size();
                case "combo":
                    return "Kombo: " + combo;
                case "target": {
                    HitResult hr = mc.crosshairTarget;
                    if (mc.world != null && hr instanceof BlockHitResult && hr.getType() == HitResult.Type.BLOCK) {
                        return "Blok: " + mc.world.getBlockState(((BlockHitResult) hr).getBlockPos()).getBlock().getName().getString();
                    }
                    if (hr instanceof EntityHitResult) {
                        return "Varlık: " + ((EntityHitResult) hr).getEntity().getName().getString();
                    }
                    return "Hedef: -";
                }
                case "reach": {
                    HitResult hr = mc.crosshairTarget;
                    if (mc.player != null && hr instanceof EntityHitResult) {
                        return String.format("Menzil: %.2f", mc.player.getEyePos().distanceTo(hr.getPos()));
                    }
                    return "Menzil: -";
                }
                case "itemcount": {
                    if (mc.player == null) return "Eşya: -";
                    ItemStack h = mc.player.getMainHandStack();
                    if (h.isEmpty()) return "Eşya: -";
                    int n = 0;
                    for (int i = 0; i < mc.player.getInventory().size(); i++) {
                        ItemStack st = mc.player.getInventory().getStack(i);
                        if (ItemStack.areItemsAndComponentsEqual(st, h)) n += st.getCount();
                    }
                    return h.getName().getString() + ": " + n;
                }
                case "shield":
                    if (mc.player == null) return "Kalkan: -";
                    return "Kalkan: " + (mc.player.isBlocking() ? "AKTİF" : "pasif");
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
        int h = height(mc, id);
        ctx.fill(x, y, x + w, y + h, id.equals("keys") ? 0 : 0x88000000);
        if (!id.equals("keys")) ctx.fill(x, y, x + 2, y + h, ORANGE);
        if (id.equals("armor")) {
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
        if (id.equals("potions")) {
            List<StatusEffectInstance> list = effects(mc);
            if (list.isEmpty()) {
                ctx.drawTextWithShadow(mc.textRenderer, Text.literal("İksir yok"), x + 6, y + 3, 0xFFB0A090);
                return;
            }
            int yy = y + 3;
            for (StatusEffectInstance e : list) {
                String name = e.getEffectType().value().getName().getString() + roman(e.getAmplifier());
                ctx.drawTextWithShadow(mc.textRenderer, Text.literal(name + "  " + time(e.getDuration())), x + 6, yy, WHITE);
                yy += 14;
            }
            return;
        }
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
