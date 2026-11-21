package tr.kunefe.menu.mixin;

import net.minecraft.client.gui.hud.PlayerListHud;
import net.minecraft.client.network.PlayerListEntry;
import net.minecraft.text.MutableText;
import net.minecraft.text.Text;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tr.kunefe.menu.Presence;

@Mixin(PlayerListHud.class)
public class PlayerListHudMixin {
    @Inject(method = "getPlayerName", at = @At("RETURN"), cancellable = true, require = 0)
    private void kunefe$logo(PlayerListEntry entry, CallbackInfoReturnable<Text> cir) {
        try {
            if (Presence.isLauncher(entry.getProfile().getName())) {
                MutableText m = Text.empty();
                m.append(Presence.logo());
                m.append(cir.getReturnValue());
                cir.setReturnValue(m);
            }
        } catch (Throwable ignored) {}
    }
}
