.class public Lcom/OM7753/gold/PinLockActivity;
.super Lcom/instagram/base/activity/IgFragmentActivity;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Lcom/instagram/base/activity/IgFragmentActivity;-><init>()V
    return-void
.end method

.method public A1b()LX/2lY;
    .locals 1
    const/4 v0, 0x0
    return-object v0
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 3
    invoke-super {p0, p1}, Lcom/instagram/base/activity/IgFragmentActivity;->onCreate(Landroid/os/Bundle;)V
    new-instance v0, Landroid/content/Intent;
    const-class v1, Lcom/instagram/mainactivity/InstagramMainActivity;
    invoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V
    const v2, 0x14004000
    invoke-virtual {v0, v2}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    move-result-object v0
    invoke-virtual {p0, v0}, Lcom/OM7753/gold/PinLockActivity;->startActivity(Landroid/content/Intent;)V
    return-void
.end method
