package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.text.Text;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Oyun içi skin mağazası: bir oyuncu adının skinini indir ve/veya sunucuda uygula. */
public class SkinStoreScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private final Screen parent;
    private TextFieldWidget field;
    private volatile String status = "Bir oyuncu adı yaz veya listeden seç.";

    public SkinStoreScreen(Screen parent) {
        super(Text.literal("Skin Mağazası"));
        this.parent = parent;
    }

    private String name() {
        return field == null ? "" : field.getText().trim().replaceAll("[^A-Za-z0-9_]", "");
    }

    private void apply(String n) {
        if (n.isEmpty() || this.client == null || this.client.player == null) {
            status = "Skin uygulamak için sunucuda olmalısın.";
            return;
        }
        this.client.player.networkHandler.sendChatCommand("skin set " + n);
        status = n + " skini uygulandı (sunucu).";
    }

    private void download(String n) {
        if (n.isEmpty()) { status = "Önce bir ad yaz."; return; }
        status = "İndiriliyor...";
        Thread t = new Thread(() -> {
            try {
                byte[] b = KunefeApi.getBytes("https://minotar.net/skin/" + n);
                Path dir = this.client.runDirectory.toPath().resolve("kunefe_skins");
                Files.createDirectories(dir);
                Files.write(dir.resolve(n + ".png"), b);
                status = "Kaydedildi: kunefe_skins/" + n + ".png";
            } catch (Throwable e) {
                status = "İndirilemedi.";
            }
        }, "kunefe-skin");
        t.setDaemon(true);
        t.start();
    }

    @Override
    protected void init() {
        int cx = this.width / 2;
        field = new TextFieldWidget(this.textRenderer, cx - 100, 36, 200, 20, Text.literal("Oyuncu adı"));
        field.setMaxLength(16);
        this.addDrawableChild(field);
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Uygula"), b -> apply(name())).position(cx - 100, 62).width(98).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("İndir"), b -> download(name())).position(cx + 2, 62).width(98).build());
        List<String> feat = KunefeApi.featuredSkins();
        int i = 0;
        for (String n : feat) {
            if (i >= 12) break;
            int col = i % 3, row = i / 3;
            this.addDrawableChild(ButtonWidget.builder(Text.literal(n), b -> { field.setText(n); status = n + " seçildi."; })
                    .position(cx - 150 + col * 100, 110 + row * 24).width(98).build());
            i++;
        }
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), b -> this.close()).position(cx - 100, this.height - 28).width(200).build());
    }

    @Override
    public void render(DrawContext ctx, int mx, int my, float d) {
        super.render(ctx, mx, my, d);
        int cx = this.width / 2;
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Skin Mağazası"), cx, 14, ORANGE);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Öne çıkanlar"), cx, 98, 0xFFB0A090);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal(status), cx, this.height - 44, 0xFFFFFFFF);
    }

    @Override
    public void close() {
        if (this.client != null) this.client.setScreen(parent);
    }
}
