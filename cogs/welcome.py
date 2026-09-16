import discord
from discord.ext import commands
import config
import datetime

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != config.GUILD_ID:
            return
            
        # Give unverified role
        unverified_role = member.guild.get_role(config.ROLE_UNVERIFIED)
        if unverified_role:
            await member.add_roles(unverified_role)

        # Welcome message, let's send it to a general channel or a welcome channel?
        # The user didn't specify the welcome channel ID, so we'll just assume they have a system channel
        # or we could send it to CH_KAYIT_OL (Register channel) or CH_KURALLAR?
        # I'll just use the system channel or Kayıt Ol if system is None.
        channel = member.guild.system_channel
        if not channel:
            channel = member.guild.get_channel(config.CH_KAYIT_OL)
            
        if channel:
            join_date = member.joined_at.strftime("%d/%m/%Y")
            
            embed = discord.Embed(
                title="✨ Sunucumuza Hoş Geldin!",
                description=f"Merhaba {member.mention}\n\n**{member.guild.name}** ailesine katıldığın için çok mutluyuz.\nSeninle birlikte artık **{member.guild.member_count}** kişiyiz!\n\n📜 [Kuralları okumayı unutma](https://discord.com/channels/1275120691863355487/1520419754509205535)\n💬 Sohbete katılmaktan çekinme\n🎮 İyi eğlenceler dileriz!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Katılma tarihi: {join_date}", icon_url=member.guild.icon.url if member.guild.icon else None)
            
            await channel.send(content=member.mention, embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
