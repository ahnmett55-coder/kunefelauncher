package tr.kunefe.menu;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.entity.Entity;
import net.minecraft.util.hit.EntityHitResult;
import net.minecraft.util.hit.HitResult;

/** Özel nişangah çizimi (oyun içi ve ayar ekranındaki önizleme). */
public final class CrosshairRenderer {
    private CrosshairRenderer() {}

    /** Oyun içi: ekran ortasına çizer. */
    public static void drawInGame(DrawContext ctx) {
        MinecraftClient mc = MinecraftClient.getInstance();
        if (mc.options == null || !mc.options.getPerspective().isFirstPerson()) return;
        int color = KunefeConfig.CROSS_COLORS[Math.floorMod(KunefeConfig.d.crossColor, KunefeConfig.CROSS_COLORS.length)];
        if (KunefeConfig.d.crossRedOnTarget) {
            HitResult hr = mc.crosshairTarget;
            if (hr instanceof EntityHitResult) {
                Entity e = ((EntityHitResult) hr).getEntity();
                if (e != null) color = 0xFFFF3030;
            }
        }
        draw(ctx, ctx.getScaledWindowWidth() / 2, ctx.getScaledWindowHeight() / 2, color);
    }

    public static void draw(DrawContext ctx, int cx, int cy, int color) {
        KunefeConfig.Data d = KunefeConfig.d;
        int s = Math.max(1, d.crossSize);
        int g = Math.max(0, d.crossGap);
        int t = Math.max(1, d.crossThick);
        int half = t / 2;
        switch (d.crossStyle) {
            case 1: // nokta
                ctx.fill(cx - t, cy - t, cx + t + 1, cy + t + 1, color);
                break;
            case 2: { // kare
                int r = s + g;
                ctx.fill(cx - r, cy - r, cx + r + 1, cy - r + t, color);
                ctx.fill(cx - r, cy + r + 1 - t, cx + r + 1, cy + r + 1, color);
                ctx.fill(cx - r, cy - r, cx - r + t, cy + r + 1, color);
                ctx.fill(cx + r + 1 - t, cy - r, cx + r + 1, cy + r + 1, color);
                break;
            }
            case 3: // T (üst kol yok)
                ctx.fill(cx - g - s, cy - half, cx - g, cy - half + t, color);
                ctx.fill(cx + g + 1, cy - half, cx + g + s + 1, cy - half + t, color);
                ctx.fill(cx - half, cy + g + 1, cx - half + t, cy + g + s + 1, color);
                break;
            default: // artı
                ctx.fill(cx - g - s, cy - half, cx - g, cy - half + t, color);
                ctx.fill(cx + g + 1, cy - half, cx + g + s + 1, cy - half + t, color);
                ctx.fill(cx - half, cy - g - s, cx - half + t, cy - g, color);
                ctx.fill(cx - half, cy + g + 1, cx - half + t, cy + g + s + 1, color);
        }
    }
}
