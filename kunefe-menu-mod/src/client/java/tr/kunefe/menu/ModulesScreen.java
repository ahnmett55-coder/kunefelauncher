package tr.kunefe.menu;

import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.List;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

/** Aesir tarzı modül listesi: her modül için aç/kapat. Çalışanlar etkin, gelecek olanlar "Yakında". */
public class ModulesScreen extends Screen {
    private static final int ORANGE = 0xFFFF8C00;
    private static final int PER_PAGE = 12;

    private static final class Entry {
        final String title, desc;
        final BooleanSupplier get;
        final Consumer<Boolean> set;

        Entry(String title, String desc, BooleanSupplier get, Consumer<Boolean> set) {
            this.title = title;
            this.desc = desc;
            this.get = get;
            this.set = set;
        }
    }

    private final Screen parent;
    private final List<Entry> entries = new ArrayList<>();
    private int page;

    public ModulesScreen(Screen parent) {
        super(Text.literal("Modüller"));
        this.parent = parent;
        hud("Zırh Göstergesi", "Giydiğin zırhları gösterir", "armor");
        hud("Kalkan Durumu", "Kalkan aktif mi gösterir", "shield");
        hud("Koordinatlar", "Konum bilgilerini gösterir", "coords");
        hud("Eşya Sayacı", "Elindeki eşyadan envanterde kaç tane var", "itemcount");
        hud("FPS", "FPS değerini gösterir", "fps");
        hud("Blok Bilgisi", "Baktığın bloğun/varlığın adı", "target");
        hud("Ping", "Sunucu gecikmesini gösterir", "ping");
        hud("Yön", "Baktığın yönü gösterir", "direction");
        hud("Saat", "Sistem saatini gösterir", "clock");
        hud("İksir Göstergesi", "Aktif iksir efektlerini gösterir", "potions");
        hud("CPS", "Saniyedeki tıklamaları gösterir", "cps");
        hud("Kombo Sayacı", "Art arda vuruş sayısını gösterir", "combo");
        hud("Vuruş Menzili", "Hedefe olan mesafeyi gösterir", "reach");
        hud("Tuş Vuruşları", "WASD ve zıplama tuşlarını gösterir", "keys");
        entries.add(new Entry("Tam Parlaklık", "Sürekli gece görüşü", () -> KunefeConfig.d.fullbright, v -> KunefeConfig.d.fullbright = v));
        entries.add(new Entry("Nişangah", "Özel nişangah (Nişangah sayfasında ayarla)", () -> KunefeConfig.d.crossOn, v -> KunefeConfig.d.crossOn = v));
        entries.add(new Entry("El Item Pozisyonu", "Birinci şahısta eldeki eşyanın konumu", () -> KunefeConfig.d.handOn, v -> KunefeConfig.d.handOn = v));
        String[] soon = {"Yaratık Canları", "Özel Can Çubukları", "MMORPG Araçları", "Alev Efekti", "Eşya Görünümü", "Vuruş Rengi",
                "Hareket Bulanıklığı", "Kristal Ayarları", "Vuruş Kutuları", "Koşu Kilidi", "İsim Etiketleri", "Blok Çerçevesi",
                "Skor Tablosu", "Eşya Fiziği", "Yakınlaştırma", "Serbest Görüş", "Mini Harita", "TPS", "Zaman Değiştirici",
                "Hava Durumu Değiştirici", "Yayın Bildirimleri", "Yeni Kozmetik Bildirimleri", "Maç Açılışı"};
        for (String s : soon) entries.add(new Entry(s, "Yakında", null, null));
    }

    private void hud(String title, String desc, String id) {
        entries.add(new Entry(title, desc, () -> HudConfig.MODS.get(id).on, v -> {
            HudConfig.MODS.get(id).on = v;
            HudConfig.save();
        }));
    }

    private int pages() {
        return (entries.size() + PER_PAGE - 1) / PER_PAGE;
    }

    @Override
    protected void init() {
        int colW = 150;
        int x0 = this.width / 2 - colW - 3;
        int start = page * PER_PAGE;
        for (int i = 0; i < PER_PAGE && start + i < entries.size(); i++) {
            Entry e = entries.get(start + i);
            int x = x0 + (i % 2) * (colW + 6);
            int y = 34 + (i / 2) * 26;
            ButtonWidget b = ButtonWidget.builder(label(e), btn -> {
                if (e.get == null) return;
                e.set.accept(!e.get.getAsBoolean());
                KunefeConfig.save();
                btn.setMessage(label(e));
            }).position(x, y).width(colW).tooltip(net.minecraft.client.gui.tooltip.Tooltip.of(Text.literal(e.desc))).build();
            b.active = e.get != null;
            this.addDrawableChild(b);
        }
        int by = this.height - 28;
        this.addDrawableChild(ButtonWidget.builder(Text.literal("<"), b -> { page = (page + pages() - 1) % pages(); this.clearAndInit(); })
                .position(this.width / 2 - 100, by).width(40).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal("Bitti"), b -> this.close())
                .position(this.width / 2 - 50, by).width(100).build());
        this.addDrawableChild(ButtonWidget.builder(Text.literal(">"), b -> { page = (page + 1) % pages(); this.clearAndInit(); })
                .position(this.width / 2 + 60, by).width(40).build());
    }

    private static Text label(Entry e) {
        if (e.get == null) return Text.literal(e.title + ": Yakında");
        return Text.literal(e.title + ": " + (e.get.getAsBoolean() ? "AÇIK" : "KAPALI"));
    }

    @Override
    public void render(DrawContext ctx, int mx, int my, float d) {
        super.render(ctx, mx, my, d);
        int on = 0;
        for (Entry e : entries) if (e.get != null && e.get.getAsBoolean()) on++;
        ctx.drawCenteredTextWithShadow(this.textRenderer, Text.literal("Modüller  " + on + "/" + entries.size()
                + "   (sayfa " + (page + 1) + "/" + pages() + ")"), this.width / 2, 14, ORANGE);
    }

    @Override
    public void close() {
        KunefeConfig.save();
        if (this.client != null) this.client.setScreen(parent);
    }
}
