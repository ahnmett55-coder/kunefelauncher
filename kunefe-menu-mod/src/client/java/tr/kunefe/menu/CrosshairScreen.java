package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

import java.util.function.Supplier;

/** Nişangah editörü: stil, renk, boyut, aralık, kalınlık. Ortada canlı önizleme. */
public class CrosshairScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private final Screen parent;

    public CrosshairScreen(Screen parent) {
        super(Text.literal("Nişangah"));
        this.parent = parent;
    }

    private void add(int y, Supplier<String> label, Runnable action) {
        int x = 20;
        ButtonWidget[] ref = new ButtonWidget[1];
        ref[0] = ButtonWidget.builder(Text.literal(label.get()), b -> {
            action.run();
            b.setMessage(Text.literal(label.get()));
            KunefeConfig.save();
        }).position(x, y).width(170).build();
        this.addDrawableChild(ref[0]);
    }

    private void pair(int y, String name, java.util.function.IntSupplier get, java.util.function.IntConsumer set, int min, int max) {
        this.addDrawableChild(ButtonWidget.builder(Text.literal("-"), b -> {
            set.accept(Math.max(min, get.getAsInt() - 1));
            KunefeConfig.save();
        }).position(196, y).width(20).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("+"), b -> {
            set.accept(Math.min(max, get.getAsInt() + 1));
            KunefeConfig.save();
        }).position(218, y).width(20).build());
    }

    @Override
    protected void init() {
        KunefeConfig.Data d = KunefeConfig.d;
        add(30, () -> "Özel nişangah: " + (d.crossOn ? "AÇIK" : "KAPALI"), () -> d.crossOn = !d.crossOn);
        add(54, () -> "Stil: " + KunefeConfig.CROSS_STYLES[Math.floorMod(d.crossStyle, KunefeConfig.CROSS_STYLES.length)],
                () -> d.crossStyle = (d.crossStyle + 1) % KunefeConfig.CROSS_STYLES.length);
        add(78, () -> "Renk: " + KunefeConfig.CROSS_COLOR_NAMES[Math.floorMod(d.crossColor, KunefeConfig.CROSS_COLOR_NAMES.length)],
                () -> d.crossColor = (d.crossColor + 1) % KunefeConfig.CROSS_COLORS.length);
        add(102, () -> "Hedefte kırmızı: " + (d.crossRedOnTarget ? "EVET" : "HAYIR"), () -> d.crossRedOnTarget = !d.crossRedOnTarget);
        pair(130, "Boyut", () -> d.crossSize, v -> d.crossSize = v, 1, 12);
        pair(154, "Aralık", () -> d.crossGap, v -> d.crossGap = v, 0, 10);
        pair(178, "Kalınlık", () -> d.crossThick, v -> d.crossThick = v, 1, 4);
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), b -> this.close())
                .position(20, this.height - 28).width(170).build());
    }

    @Override
    public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
        super.render(ctx, mouseX, mouseY, delta);
        KunefeConfig.Data d = KunefeConfig.d;
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Nişangah Düzenle"), this.width / 2, 8, ORANGE);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Boyut: " + d.crossSize), 244, 136, 0xFFFFFFFF);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Aralık: " + d.crossGap), 244, 160, 0xFFFFFFFF);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Kalınlık: " + d.crossThick), 244, 184, 0xFFFFFFFF);
        int px = this.width - 110;
        int py = this.height / 2;
        ctx.fill(px - 60, py - 60, px + 60, py + 60, 0x99101012);
        ctx.fill(px - 60, py - 60, px + 60, py - 59, ORANGE);
        ctx.fill(px - 60, py + 59, px + 60, py + 60, ORANGE);
        ctx.fill(px - 60, py - 60, px - 59, py + 60, ORANGE);
        ctx.fill(px + 59, py - 60, px + 60, py + 60, ORANGE);
        CrosshairRenderer.draw(ctx, px, py, KunefeConfig.CROSS_COLORS[Math.floorMod(d.crossColor, KunefeConfig.CROSS_COLORS.length)]);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Önizleme"), px, py + 66, 0xFFB0A090);
    }

    @Override
    public void close() {
        KunefeConfig.save();
        if (this.client != null) this.client.setScreen(this.parent);
    }
}
