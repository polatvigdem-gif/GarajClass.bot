import discord
from discord.ext import commands
import config
import aiohttp
import re

class RegistrationModal(discord.ui.Modal, title='Kayıt Formu'):
    nickname = discord.ui.TextInput(
        label='Takma Ad',
        placeholder='Oyundaki takma adınız...',
        required=True
    )
    
    roblox_url = discord.ui.TextInput(
        label='Roblox Profil Linki',
        style=discord.TextStyle.short,
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
        
        view = ApprovalView(user_id=interaction.user.id, nickname=self.nickname.value, roblox_url=self.roblox_url.value)
        await approval_channel.send(content=f"<@&{config.ROLE_REGISTRATION_MANAGER}>", embed=embed, view=view)
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
    def __init__(self, user_id: int, nickname: str, roblox_url: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.nickname = nickname
        self.roblox_url = roblox_url

    async def get_roblox_username(self, text):
        text = text.strip()
        # Linkten veya direkt girilen metinden ID çıkarma
        match = re.search(r"(?:users/|/u/)(\d+)", text)
        
        user_id = None
        if match:
            user_id = match.group(1)
        elif text.isdigit():
            user_id = text
            
        async with aiohttp.ClientSession() as session:
            if user_id:
                try:
                    async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("name") # veya displayName
                except Exception:
                    pass
            else:
                # Eğer ID veya link değilse, direkt kullanıcı adı girilmiş olabilir
                # Kullanıcı adı ile arama yapalım
                try:
                    async with session.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [text], "excludeBannedUsers": False}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("data") and len(data["data"]) > 0:
                                return data["data"][0].get("name")
                except Exception:
                    pass
        return None

    @discord.ui.button(label="ONAYLA", style=discord.ButtonStyle.success, custom_id="btn_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.followup.send("Kullanıcı sunucuda bulunamadı.", ephemeral=True)
            return
            
        unverified_role = interaction.guild.get_role(config.ROLE_UNVERIFIED)
        verified_role = interaction.guild.get_role(config.ROLE_VERIFIED)
        
        if unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        if verified_role:
            await member.add_roles(verified_role)
            
        roblox_username = await self.get_roblox_username(self.roblox_url)
        if roblox_username:
            new_nick = f"{self.nickname} | {roblox_username}"
        else:
            new_nick = f"{self.nickname} | (Bulunamadı)"
            
        # Discord limit: 32 chars
        new_nick = new_nick[:32]
        
        try:
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            pass # Yetki yetersizliği
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        
        content = f"{interaction.user.mention} tarafından Onaylandı."
        await interaction.message.edit(content=content, embed=embed, view=None)
        await interaction.followup.send("Onaylandı.", ephemeral=True)

    @discord.ui.button(label="REDDET", style=discord.ButtonStyle.danger, custom_id="btn_reject")
    async def reject_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RejectModal(self.user_id, interaction.message))

class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(RegistrationView())

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
