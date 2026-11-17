package tr.kunefe.menu;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.minecraft.client.gui.screen.GameMenuScreen;
import net.minecraft.client.gui.screen.ingame.InventoryScreen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

/** ESC menüsüne: sağda oyuncunun 3D modeli + altında "Özelleştir" butonu. */
public class KunefeMenuClient implements ClientModInitializer {
    private static final int ORANGE = 0xFFFF8C00;

    @Override
    public void onInitializeClient() {
        HudConfig.load();
        HudRenderCallback.EVENT.register((ctx, tickCounter) -> HudModules.renderAll(ctx));
        ScreenEvents.AFTER_INIT.register((client, screen, w, h) -> {
            if (!(screen instanceof GameMenuScreen)) return;
            try {
                int bw = 110;
                int px = w - bw - 24;
                Screens.getButtons(screen).add(ButtonWidget.builder(Text.literal("Özelleştir"),
                        b -> client.setScreen(new CosmeticsScreen(screen)))
                        .position(px + 7, h / 2 + 76).width(bw).build());
                Screens.getButtons(screen).add(ButtonWidget.builder(Text.literal("HUD Düzenle"),
                        b -> client.setScreen(new HudEditorScreen(screen)))
                        .position(px + 7, h / 2 + 100).width(bw).build());
                ScreenEvents.afterRender(screen).register((s, ctx, mx, my, delta) -> {
                    if (client.player == null) return;
                    int top = h / 2 - 100;
                    int bottom = h / 2 + 70;
                    ctx.fill(px, top, w - 4, bottom, 0x99101012);
                    ctx.fill(px, top, w - 4, top + 1, ORANGE);
                    ctx.fill(px, bottom - 1, w - 4, bottom, ORANGE);
                    ctx.fill(px, top, px + 1, bottom, ORANGE);
                    ctx.fill(w - 5, top, w - 4, bottom, ORANGE);
                    InventoryScreen.drawEntity(ctx, px + 2, top + 14, w - 6, bottom - 4, 48, 0.0625f, mx, my, client.player);
                    ctx.drawCenteredTextWithShadow(client.textRenderer, Text.literal(client.player.getName().getString()),
                            px + (w - 4 - px) / 2, top + 4, ORANGE);
                });
            } catch (Throwable ignored) {
                // hata olursa ESC menüsü vanilla kalır
            }
        });
    }
}
