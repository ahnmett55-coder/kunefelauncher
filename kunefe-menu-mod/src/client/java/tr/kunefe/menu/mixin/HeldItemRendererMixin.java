package tr.kunefe.menu.mixin;

import net.minecraft.client.network.AbstractClientPlayerEntity;
import net.minecraft.client.render.VertexConsumerProvider;
import net.minecraft.client.render.item.HeldItemRenderer;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.item.ItemStack;
import net.minecraft.util.Arm;
import net.minecraft.util.Hand;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import tr.kunefe.menu.KunefeConfig;

@Mixin(HeldItemRenderer.class)
public class HeldItemRendererMixin {
    @Inject(method = "renderFirstPersonItem", at = @At("HEAD"), require = 0)
    private void kunefe$hand(AbstractClientPlayerEntity player, float tickDelta, float pitch, Hand hand, float swing,
                             ItemStack stack, float equip, MatrixStack m, VertexConsumerProvider vcp, int light, CallbackInfo ci) {
        try {
            KunefeConfig.Data d = KunefeConfig.d;
            if (!d.handOn) return;
            boolean left = (hand == Hand.MAIN_HAND) == (player.getMainArm() == Arm.LEFT);
            float x = d.handX * 0.01f * (left ? -1 : 1);
            m.translate(x, d.handY * 0.01f, d.handZ * 0.01f);
        } catch (Throwable ignored) {}
    }
}
