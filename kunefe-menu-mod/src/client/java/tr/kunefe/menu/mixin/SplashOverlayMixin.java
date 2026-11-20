package tr.kunefe.menu.mixin;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.SplashOverlay;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(SplashOverlay.class)
public class SplashOverlayMixin {
    private static final String[] NEWS = {
        "• Künefe Menü: nişangah editörü, skin mağazası, HUD modülleri",
        "• El eşyası konumu ayarı",
        "• TAB listesinde KünefeLauncher logosu",
        "• Hazır kaynak paketleri otomatik aktif",
        "• Sadece sayısal IPv4 sunuculara giriş"
    };
    private static final String[] TIPS = {
        "İpucu: ESC > Künefe Ayarları'ndan HUD'u sürükleyerek düzenle.",
        "İpucu: ESC menüsündeki Özelleştir ile KP harca.",
        "İpucu: Nişangahı hedefte kırmızı yapabilirsin.",
        "İpucu: Skin mağazasından istediğin oyuncunun skinini al.",
        "İpucu: Sağ Shift ile HUD ayarlarına hızlı gir (ESC menüsü)."
    };
    private static final String TIP = TIPS[(int) (System.nanoTime() % TIPS.length + TIPS.length) % TIPS.length];

    @Inject(method = "render", at = @At("TAIL"), require = 0)
    private void kunefe$news(DrawContext ctx, int mx, int my, float delta, CallbackInfo ci) {
        try {
            MinecraftClient mc = MinecraftClient.getInstance();
            int w = ctx.getScaledWindowWidth();
            int y = 12;
            ctx.drawCenteredTextWithShadow(mc.textRenderer, "KÜNEFELAUNCHER v2.0 • YENİLİKLER", w / 2, y, 0xFFFF8C00);
            y += 14;
            for (String s : NEWS) {
                ctx.drawCenteredTextWithShadow(mc.textRenderer, s, w / 2, y, 0xFFFFFFFF);
                y += 11;
            }
            ctx.drawCenteredTextWithShadow(mc.textRenderer, TIP, w / 2, ctx.getScaledWindowHeight() - 20, 0xFFFFD27F);
        } catch (Throwable ignored) {}
    }
}
