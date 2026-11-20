package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

import java.util.Map;

/** HUD düzenleyici: modülleri sürükleyip bırak, sağdaki butonlarla aç/kapat. */
public class HudEditorScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private final Screen parent;
    private String hovered;
    private String dragging;

    public HudEditorScreen(Screen parent) {
        super(Text.literal("HUD Düzenle"));
        this.parent = parent;
    }

    private Text label(String id) {
        return Text.literal(HudModules.title(id) + ": " + (HudConfig.MODS.get(id).on ? "AÇIK" : "KAPALI"));
    }

    @Override
    protected void init() {
        int colW = 128;
        int bx = this.width - colW * 2 - 8;
        int i = 0;
        for (String id : HudConfig.MODS.keySet()) {
            int col = i % 2;
            int row = i / 2;
            this.addDrawableChild(ButtonWidget.builder(label(id), btn -> {
                HudConfig.Mod m = HudConfig.MODS.get(id);
                m.on = !m.on;
                btn.setMessage(label(id));
                HudConfig.save();
            }).position(bx + col * (colW + 2), 28 + row * 22).width(colW).build());
            i++;
        }
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), btn -> this.close())
                .position(this.width - 130, this.height - 28).width(120).build());
    }

    @Override
    public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
        super.render(ctx, mouseX, mouseY, delta);
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Modülleri sürükleyerek yerleştir"), this.width / 2, 8, ORANGE);
        hovered = null;
        for (Map.Entry<String, HudConfig.Mod> e : HudConfig.MODS.entrySet()) {
            if (!e.getValue().on) continue;
            String id = e.getKey();
            HudConfig.Mod m = e.getValue();
            HudModules.draw(ctx, this.client, id, m.x, m.y);
            int w = HudModules.width(this.client, id);
            int h = HudModules.height(this.client, id);
            boolean over = mouseX >= m.x && mouseX <= m.x + w && mouseY >= m.y && mouseY <= m.y + h;
            if (over) hovered = id;
            int c = (id.equals(dragging) || over) ? 0xFFFFFFFF : ORANGE;
            ctx.fill(m.x - 1, m.y - 1, m.x + w + 1, m.y, c);
            ctx.fill(m.x - 1, m.y + h, m.x + w + 1, m.y + h + 1, c);
            ctx.fill(m.x - 1, m.y, m.x, m.y + h, c);
            ctx.fill(m.x + w, m.y, m.x + w + 1, m.y + h, c);
        }
    }

    @Override
    public boolean mouseClicked(double mx, double my, int button) {
        if (super.mouseClicked(mx, my, button)) return true;
        if (hovered != null) {
            dragging = hovered;
            return true;
        }
        return false;
    }

    @Override
    public boolean mouseDragged(double mx, double my, int button, double dx, double dy) {
        if (dragging != null) {
            HudConfig.Mod m = HudConfig.MODS.get(dragging);
            int w = HudModules.width(this.client, dragging);
            int h = HudModules.height(this.client, dragging);
            m.x = Math.max(0, Math.min(this.width - w, m.x + (int) Math.round(dx)));
            m.y = Math.max(0, Math.min(this.height - h, m.y + (int) Math.round(dy)));
            return true;
        }
        return super.mouseDragged(mx, my, button, dx, dy);
    }

    @Override
    public boolean mouseReleased(double mx, double my, int button) {
        if (dragging != null) {
            dragging = null;
            HudConfig.save();
            return true;
        }
        return super.mouseReleased(mx, my, button);
    }

    @Override
    public void close() {
        HudConfig.save();
        if (this.client != null) this.client.setScreen(this.parent);
    }
}
