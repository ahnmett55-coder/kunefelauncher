package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;
import net.minecraft.util.Util;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;

/** ESC > Özelleştir: KP bakiyesi, sahip olunan kozmetikler ve mağaza. */
public class CosmeticsScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private static final int WHITE = 0xFFFFFFFF;
    private static final int GRAY = 0xFFB0A090;

    private final Screen parent;
    private volatile String status = "Yükleniyor...";
    private volatile int kp = -1;
    private volatile List<String> owned = new ArrayList<>();
    private volatile List<String> shop = new ArrayList<>();
    private boolean started;

    public CosmeticsScreen(Screen parent) {
        super(Text.literal("Özelleştir"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int cx = this.width / 2;
        int y = this.height - 84;
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Kozmetik Menüsünü Aç"), b -> {
            if (this.client != null && this.client.player != null) {
                this.client.player.networkHandler.sendChatCommand("uc menu");
                this.client.setScreen(null);
            }
        }).position(cx - 100, y).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("KP Satın Al / Mağaza (site)"), b -> {
            Util.getOperatingSystem().open(URI.create(KunefeApi.SITE));
        }).position(cx - 100, y + 24).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Geri"), b -> {
            if (this.client != null) this.client.setScreen(this.parent);
        }).position(cx - 100, y + 48).width(200).build());

        if (!started) {
            started = true;
            String name = this.client != null && this.client.player != null ? this.client.player.getName().getString() : "";
            Thread t = new Thread(() -> load(name), "kunefe-menu");
            t.setDaemon(true);
            t.start();
        }
    }

    private void load(String name) {
        try {
            KunefeApi.Me me = KunefeApi.me(name);
            List<String> lines = new ArrayList<>();
            for (KunefeApi.Item it : KunefeApi.catalog()) lines.add(it.name + "  (" + it.type + ")  -  " + it.price + " KP");
            this.owned = me.owned;
            this.shop = lines;
            this.kp = me.kp;
            this.status = "";
        } catch (Exception e) {
            this.status = "Siteye ulaşılamadı. Biraz sonra tekrar dene.";
        }
    }

    @Override
    public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
        super.render(ctx, mouseX, mouseY, delta);
        int cx = this.width / 2;
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("KÜNEFECRAFT - ÖZELLEŞTİR"), cx, 18, ORANGE);
        if (!this.status.isEmpty()) {
            ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal(this.status), cx, 40, GRAY);
        } else {
            ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("KP bakiyen: " + this.kp), cx, 40, WHITE);
        }
        int y = 66;
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Sahip olduklarım"), cx - 150, y, ORANGE);
        y += 14;
        if (this.owned.isEmpty()) {
            ctx.drawTextWithShadow(this.textRenderer, Text.literal("Henüz yok."), cx - 150, y, GRAY);
            y += 12;
        }
        for (String s : this.owned) {
            ctx.drawTextWithShadow(this.textRenderer, Text.literal("- " + s), cx - 150, y, WHITE);
            y += 12;
        }
        y += 10;
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Mağaza (satın almak için siteyi aç)"), cx - 150, y, ORANGE);
        y += 14;
        for (String s : this.shop) {
            if (y > this.height - 92) break;
            ctx.drawTextWithShadow(this.textRenderer, Text.literal("- " + s), cx - 150, y, WHITE);
            y += 12;
        }
    }
}
