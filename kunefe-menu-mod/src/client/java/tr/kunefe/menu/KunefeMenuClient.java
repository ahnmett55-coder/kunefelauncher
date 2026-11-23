package tr.kunefe.menu;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.message.v1.ClientSendMessageEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.minecraft.client.gui.screen.GameMenuScreen;
import net.minecraft.client.gui.screen.TitleScreen;
import net.minecraft.client.gui.screen.ingame.InventoryScreen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.network.ServerInfo;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;

public class KunefeMenuClient implements ClientModInitializer {
    private static final int ORANGE = 0xFFFF8C00;
    private static boolean autoDone;
    private static int loginIn = -1;
    private static String loginPw;

    @Override
    public void onInitializeClient() {
        KunefeConfig.load();
        HudConfig.load();
        // Hazır doku paketleri mod içinde gömülü: sürüm denetimine takılmadan her zaman etkin
        try {
            net.fabricmc.loader.api.FabricLoader.getInstance().getModContainer("kunefemenu").ifPresent(mc -> {
                String[][] packs = {{"dark_gold_gui", "Dark Gold GUI"}, {"orange_pvp", "Orange PVP"}};
                for (String[] pk : packs) {
                    try {
                        net.fabricmc.fabric.api.resource.ResourceManagerHelper.registerBuiltinResourcePack(
                                net.minecraft.util.Identifier.of("kunefemenu", pk[0]), mc, Text.literal(pk[1]),
                                net.fabricmc.fabric.api.resource.ResourcePackActivationType.ALWAYS_ENABLED);
                    } catch (Throwable ignored) {}
                }
            });
        } catch (Throwable ignored) {}
        HudRenderCallback.EVENT.register((ctx, tc) -> HudModules.renderAll(ctx));
        ClientTickEvents.END_CLIENT_TICK.register(mc -> {
            try { HudModules.tick(mc); Presence.tick(mc); } catch (Throwable ignored) {}
            try {
                if (loginIn > 0 && --loginIn == 0 && loginPw != null && mc.getNetworkHandler() != null) {
                    mc.getNetworkHandler().sendChatCommand("login " + loginPw);
                    loginPw = null;
                }
            } catch (Throwable ignored) {}
        });
        AttackEntityCallback.EVENT.register((p, w, h, e, hit) -> {
            if (w.isClient) HudModules.onAttack();
            return ActionResult.PASS;
        });

        // İkinci katman: sayısal IPv4 dışı sunucudan at.
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> {
            try {
                ServerInfo si = client.getCurrentServerEntry();
                if (si == null || client.isInSingleplayer()) return;
                if (KunefeApi.SERVER_IP.equals(si.address)) {
                    java.nio.file.Path lf = net.fabricmc.loader.api.FabricLoader.getInstance().getGameDir().resolve("kunefe_login.txt");
                    if (java.nio.file.Files.exists(lf)) {
                        String pw = java.nio.file.Files.readString(lf, java.nio.charset.StandardCharsets.UTF_8).trim();
                        if (!pw.isEmpty()) { loginPw = pw; loginIn = 40; }
                    }
                }
                if (!IpLock.allowed(IpLock.hostOf(si.address))) {
                    client.execute(() -> {
                        if (client.world != null) client.world.disconnect();
                        client.disconnect();
                        client.setScreen(new net.minecraft.client.gui.screen.DisconnectedScreen(new TitleScreen(),
                                Text.translatable("connect.failed"), Text.literal("Connection refused: getsockopt")));
                    });
                }
            } catch (Throwable ignored) {}
        });

        // Launcher'ın yazdığı kunefe_packs.txt: hazır doku paketlerini garanti etkinleştir.
        net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents.CLIENT_STARTED.register(client -> {
            try {
                java.nio.file.Path f = net.fabricmc.loader.api.FabricLoader.getInstance().getGameDir().resolve("kunefe_packs.txt");
                if (!java.nio.file.Files.exists(f)) return;
                net.minecraft.resource.ResourcePackManager mgr = client.getResourcePackManager();
                mgr.scanPacks();
                boolean ch = false;
                for (String id : java.nio.file.Files.readAllLines(f, java.nio.charset.StandardCharsets.UTF_8)) {
                    id = id.trim();
                    if (id.isEmpty() || !mgr.getIds().contains(id) || mgr.getEnabledIds().contains(id)) continue;
                    ch |= mgr.enable(id);
                }
                if (ch) client.options.refreshResourcePacks(mgr);
            } catch (Throwable ignored) {}
        });

        ScreenEvents.AFTER_INIT.register((client, screen, w, h) -> {
            try {
                if (screen instanceof TitleScreen && !autoDone) {
                    autoDone = true;
                    java.nio.file.Path af = net.fabricmc.loader.api.FabricLoader.getInstance().getGameDir().resolve("kunefe_autojoin.txt");
                    if (java.nio.file.Files.exists(af)) {
                        String ip = java.nio.file.Files.readString(af, java.nio.charset.StandardCharsets.UTF_8).trim();
                        java.nio.file.Files.deleteIfExists(af);
                        if (IpLock.allowed(IpLock.hostOf(ip))) {
                            client.execute(() -> {
                                net.minecraft.client.network.ServerAddress addr = net.minecraft.client.network.ServerAddress.parse(ip);
                                ServerInfo si = new ServerInfo("KünefeCraft", ip, ServerInfo.ServerType.OTHER);
                                net.minecraft.client.gui.screen.multiplayer.ConnectScreen.connect(screen, client, addr, si, false, null);
                            });
                        }
                    }
                }
                if (screen instanceof TitleScreen) {
                    Screens.getButtons(screen).add(ButtonWidget.builder(Text.literal("KünefeCraft'a Katıl"), b -> {
                        net.minecraft.client.network.ServerAddress addr = net.minecraft.client.network.ServerAddress.parse(KunefeApi.SERVER_IP);
                        ServerInfo si = new ServerInfo("KünefeCraft", KunefeApi.SERVER_IP, ServerInfo.ServerType.OTHER);
                        net.minecraft.client.gui.screen.multiplayer.ConnectScreen.connect(screen, client, addr, si, false, null);
                    }).position(w / 2 - 100, 40).width(200).build());
                    ScreenEvents.afterRender(screen).register((s, ctx, mx, my, d) ->
                            ctx.drawCenteredTextWithShadow(client.textRenderer, Text.literal("KÜNEFECRAFT"), w / 2, 26, ORANGE));
                } else if (screen instanceof GameMenuScreen) {
                    int bw = 110;
                    int px = w - bw - 24;
                    Screens.getButtons(screen).add(ButtonWidget.builder(Text.literal("Özelleştir"),
                            b -> client.setScreen(new CosmeticsScreen(screen))).position(px + 7, h / 2 + 76).width(bw).build());
                    Screens.getButtons(screen).add(ButtonWidget.builder(Text.literal("Künefe Ayarları"),
                            b -> client.setScreen(new SettingsScreen(screen))).position(px + 7, h / 2 + 100).width(bw).build());
                    ScreenEvents.afterRender(screen).register((s, ctx, mx, my, d) -> {
                        if (client.player == null) return;
                        int top = h / 2 - 100, bottom = h / 2 + 70;
                        ctx.fill(px, top, w - 4, bottom, 0x99101012);
                        ctx.fill(px, top, w - 4, top + 1, ORANGE);
                        ctx.fill(px, bottom - 1, w - 4, bottom, ORANGE);
                        ctx.fill(px, top, px + 1, bottom, ORANGE);
                        ctx.fill(w - 5, top, w - 4, bottom, ORANGE);
                        InventoryScreen.drawEntity(ctx, px + 2, top + 14, w - 6, bottom - 4, 48, 0.0625f, mx, my, client.player);
                        ctx.drawCenteredTextWithShadow(client.textRenderer, Text.literal(client.player.getName().getString()),
                                px + (w - 4 - px) / 2, top + 4, ORANGE);
                    });
                }
            } catch (Throwable ignored) {}
        });
    }
}
