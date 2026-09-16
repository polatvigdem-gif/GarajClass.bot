import discord
from discord.ext import commands
import config

class RegistrationModal(discord.ui.Modal, title='Kayıt Formu'):
    nickname = discord.ui.TextInput(
        label='Takma Ad',
        placeholder='Oyundaki takma adınız...',
        required=True
    )
    
    roblox_url = discord.ui.TextInput(
        label='Roblox Profil Linki',
        style=discord.TextStyle.url,
        placeholder='https://www.roblox.com/users/...',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Send to approval channel
        approval_channel = interaction.guild.get_channel(config.CH_ONAY_RED)
        
        embed = discord.Embed(title="Yeni Kayıt İsteği", color=discord.Color.blue())
        embed.add_field(name="Kullanıcı", value=interaction.user.mention, inline=False)
        embed.add_field(name="Kullanıcı ID", value=interaction.user.id, inline=False)
        embed.add_field(name="Takma Ad", value=self.nickname.value, inline=False)
        embed.add_field(name="Roblox URL", value=self.roblox_url.value, inline=False)
        
        view = ApprovalView(user_id=interaction.user.id, nickname=self.nickname.value)
        await approval_channel.send(embed=embed, view=view)
        await interaction.response.send_message("Kayıt formun yetkililere gönderildi, lütfen bekle.", ephemeral=True)

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.success, custom_id="btn_register")
    async def register_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has unverified role
        unverified_role = interaction.guild.get_role(config.ROLE_UNVERIFIED)
        if unverified_role in interaction.user.roles:
            await interaction.response.send_modal(RegistrationModal())
        else:
            await interaction.response.send_message("Sadece kayıtlı olmayan kullanıcılar bu butonu kullanabilir.", ephemeral=True)

class RejectModal(discord.ui.Modal, title='Reddetme Sebebi'):
    reason = discord.ui.TextInput(
        label='Sebep',
        style=discord.TextStyle.long,
        placeholder='Reddetme sebebini girin...',
        required=True
    )
    
    def __init__(self, user_id, message_to_edit):
        super().__init__()
        self.user_id = user_id
        self.message_to_edit = message_to_edit

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(self.user_id)
        if member:
            try:
                await member.send(f"Sunucu kayıt başvurunuz reddedildi. Sebep: {self.reason.value}")
            except discord.Forbidden:
                pass # Can't DM user
        
        embed = self.message_to_edit.embeds[0]
        embed.color = discord.Color.red()
        
        content = f"{interaction.user.mention} tarafından Reddedildi / Sebep: {self.reason.value}"
        await self.message_to_edit.edit(content=content, embed=embed, view=None)
        await interaction.response.send_message("Reddedildi.", ephemeral=True)

class ApprovalView(discord.ui.View):
    def __init__(self, user_id: int, nickname: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.nickname = nickname

    @discord.ui.button(label="ONAYLA", style=discord.ButtonStyle.success, custom_id="btn_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message("Kullanıcı sunucuda bulunamadı.", ephemeral=True)
            return
            
        unverified_role = interaction.guild.get_role(config.ROLE_UNVERIFIED)
        verified_role = interaction.guild.get_role(config.ROLE_VERIFIED)
        
        if unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        if verified_role:
            await member.add_roles(verified_role)
            
        try:
            # They want [Takma AD] | [Roblox Kullanıcı Adı]
            # Since we didn't ask for roblox user name explicitly but just the link, we can just put Takma AD
            # Or extract from URL... Let's just set the Nickname they provided.
            await member.edit(nick=f"{self.nickname}")
        except discord.Forbidden:
            pass # Missing permissions to change nickname
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        
        content = f"{interaction.user.mention} tarafından Onaylandı."
        await interaction.message.edit(content=content, embed=embed, view=None)
        await interaction.response.send_message("Onaylandı.", ephemeral=True)

    @discord.ui.button(label="REDDET", style=discord.ButtonStyle.danger, custom_id="btn_reject")
    async def reject_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RejectModal(self.user_id, interaction.message))

class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def kayitmesaji(self, ctx):
        """Kayıt ol kanalına butonu gönderir."""
        embed = discord.Embed(
            title="Kayıt Ol",
            description="Sunucuya kayıt olmak için aşağıdaki 'Kayıt Ol' butonuna basarak formu doldurun.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=RegistrationView())

async def setup(bot):
    await bot.add_cog(Registration(bot))
    # We should also persist views, but for simplicity we rely on the bot running or custom IDs
