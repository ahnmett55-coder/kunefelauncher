package tr.kunefe.menu.mixin;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.DisconnectedScreen;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.screen.multiplayer.ConnectScreen;
import net.minecraft.client.network.ServerAddress;
import net.minecraft.client.network.ServerInfo;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import tr.kunefe.menu.IpLock;

@Mixin(ConnectScreen.class)
public class ConnectScreenMixin {
    @Inject(method = "connect(Lnet/minecraft/client/gui/screen/Screen;Lnet/minecraft/client/MinecraftClient;Lnet/minecraft/client/network/ServerAddress;Lnet/minecraft/client/network/ServerInfo;ZLnet/minecraft/client/network/CookieStorage;)V",
            at = @At("HEAD"), cancellable = true, require = 0)
    private static void kunefe$lock(Screen parent, MinecraftClient client, ServerAddress address, ServerInfo info, boolean quickPlay,
                                    net.minecraft.client.network.CookieStorage cookies, CallbackInfo ci) {
        try {
            if (!IpLock.allowed(address.getAddress())) {
                ci.cancel();
                client.setScreen(new DisconnectedScreen(parent, Text.literal("KünefeCraft"),
                        Text.literal("Sadece sayısal IPv4 adresli sunuculara girilebilir.")));
            }
        } catch (Throwable ignored) {}
    }
}
