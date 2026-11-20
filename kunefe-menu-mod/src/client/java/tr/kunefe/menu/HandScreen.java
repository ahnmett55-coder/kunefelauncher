package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

/** Birinci şahıs el eşyası konumu: X (yatay), Y (dikey), Z (derinlik). */
public class HandScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private final Screen parent;

    public HandScreen(Screen parent) {
        super(Text.literal("El Eşyası Konumu"));
        this.parent = parent;
    }

    private Text toggleLabel() {
        return Text.literal("El eşyası konumu: " + (KunefeConfig.d.handOn ? "AÇIK" : "KAPALI"));
    }

    private void axis(int y, java.util.function.IntSupplier get, java.util.function.IntConsumer set) {
        this.addDrawableChild(ButtonWidget.builder(Text.literal("-"), b -> {
            set.accept(Math.max(-60, get.getAsInt() - 2));
            KunefeConfig.save();
        }).position(this.width / 2 + 10, y).width(24).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("+"), b -> {
            set.accept(Math.min(60, get.getAsInt() + 2));
            KunefeConfig.save();
        }).position(this.width / 2 + 38, y).width(24).build());
    }

    @Override
    protected void init() {
        KunefeConfig.Data d = KunefeConfig.d;
        int cx = this.width / 2;
        this.addDrawableChild(ButtonWidget.builder(toggleLabel(), b -> {
            d.handOn = !d.handOn;
            b.setMessage(toggleLabel());
            KunefeConfig.save();
        }).position(cx - 100, 36).width(200).build());
        axis(70, () -> d.handX, v -> d.handX = v);
        axis(96, () -> d.handY, v -> d.handY = v);
        axis(122, () -> d.handZ, v -> d.handZ = v);
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Sıfırla"), b -> {
            d.handX = 0;
            d.handY = 0;
            d.handZ = 0;
            KunefeConfig.save();
        }).position(cx - 100, 154).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), b -> this.close())
                .position(cx - 100, this.height - 28).width(200).build());
    }

    @Override
    public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
        super.render(ctx, mouseX, mouseY, delta);
        KunefeConfig.Data d = KunefeConfig.d;
        int cx = this.width / 2;
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Birinci Şahıs El Eşyası Konumu"), cx, 12, ORANGE);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Sağ / Sol: " + d.handX), cx - 100, 76, 0xFFFFFFFF);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Yukarı / Aşağı: " + d.handY), cx - 100, 102, 0xFFFFFFFF);
        ctx.drawTextWithShadow(this.textRenderer, Text.literal("Yakın / Uzak: " + d.handZ), cx - 100, 128, 0xFFFFFFFF);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Değişikliği oyunda elinde bir eşya tutarak gör."), cx, 182, 0xFFB0A090);
    }

    @Override
    public void close() {
        KunefeConfig.save();
        if (this.client != null) this.client.setScreen(this.parent);
    }
}
