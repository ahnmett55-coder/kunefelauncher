package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

/** Künefe Ayarları merkezi. */
public class SettingsScreen extends Screen {
    private final Screen parent;

    public SettingsScreen(Screen parent) {
        super(Text.literal("Künefe Ayarları"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int cx = this.width / 2;
        int y = 40;
        this.addDrawableChild(ButtonWidget.builder(Text.literal("HUD Düzenle"), b -> this.client.setScreen(new HudEditorScreen(this))).position(cx - 100, y).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Nişangah"), b -> this.client.setScreen(new CrosshairScreen(this))).position(cx - 100, y + 26).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("El Eşyası Konumu"), b -> this.client.setScreen(new HandScreen(this))).position(cx - 100, y + 52).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Skin Mağazası"), b -> this.client.setScreen(new SkinStoreScreen(this))).position(cx - 100, y + 78).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Kozmetikler (KP)"), b -> this.client.setScreen(new CosmeticsScreen(this))).position(cx - 100, y + 104).width(200).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), b -> this.close()).position(cx - 100, this.height - 28).width(200).build());
    }

    @Override
    public void render(DrawContext ctx, int mx, int my, float d) {
        super.render(ctx, mx, my, d);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("KünefeCraft Ayarları"), this.width / 2, 16, 0xFFFF8C00);
    }

    @Override
    public void close() {
        if (this.client != null) this.client.setScreen(parent);
    }
}
