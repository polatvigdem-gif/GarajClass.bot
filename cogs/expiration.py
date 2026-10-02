import discord
from discord.ext import commands, tasks
import os
import json
import datetime
import pytz
import config

TZ = pytz.timezone("Europe/Istanbul")
DATA_FILE = "expiration_data.json"

def load_or_init_data():
    now = datetime.datetime.now(TZ)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Data file read error: {e}")
            
    # İlk defa çalıştırıldığında 15 günlük hedef belirle
    end_time = now + datetime.timedelta(days=15)
    data = {
        "start_time": now.isoformat(),
        "end_time": end_time.isoformat(),
        "last_notification_date": ""
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class Expiration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_or_init_data()
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    def get_remaining_time(self):
        now = datetime.datetime.now(TZ)
        end_time = datetime.datetime.fromisoformat(self.data["end_time"])
        if end_time.tzinfo is None:
            end_time = TZ.localize(end_time)
            
        delta = end_time - now
        total_seconds = int(delta.total_seconds())
        
        days = delta.days
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        end_ts = int(end_time.timestamp())
        
        return total_seconds, days, hours, minutes, end_ts

    def build_warning_embed(self, days, hours, minutes, end_ts):
        if days <= 3:
            color = discord.Color.red()
            status_emoji = "🚨"
            urgency_text = "**ACİL VE KRİTİK SEVİYE:** Hizmet süresinin bitimine 3 günden az kalmıştır!"
        elif days <= 7:
            color = discord.Color.orange()
            status_emoji = "⚠️"
            urgency_text = "**YÜKSEK ÖNCELİK:** Son haftaya girilmiştir, gerekli planlamalar yapılmalıdır."
        else:
            color = discord.Color.gold()
            status_emoji = "⏳"
            urgency_text = "**BİLGİLENDİRME:** 15 günlük planlanan takip süreci devam etmektedir."

        embed = discord.Embed(
            title=f"{status_emoji} ÖNEMLİ SİSTEM BİLDİRİMİ: BOT HİZMET SÜRESİ SAYACI",
            description=(
                "Sayın Kurucu ve Sunucu Yönetimi,\n\n"
                "Bu bilgilendirme, **GarajClass Bot** altyapısının aktiflik süresi ve planlanan kapanış "
                "takvimi hakkında sunucu yönetimini haberdar etmek amacıyla otomatik olarak oluşturulmuştur.\n\n"
                f"{urgency_text}"
            ),
            color=color,
            timestamp=datetime.datetime.now(TZ)
        )

        embed.add_field(
            name="⏱️ Kalan Süre Sayacı",
            value=(
                f"• **Kalan Gün:** `{max(0, days)} Gün, {max(0, hours)} Saat, {max(0, minutes)} Dakika`\n"
                f"• **Canlı Geri Sayım:** <t:{end_ts}:R>\n"
                f"• **Hedef Bitiş Tarihi:** <t:{end_ts}:F>"
            ),
            inline=False
        )

        embed.add_field(
            name="📌 Durum ve Önemli Bilgilendirme",
            value=(
                "Botun belirlenen aktif çalışma süresi **15 gün** olarak sınırlandırılmıştır. "
                "Bu sayaç sıfırlandığında bot sunucuda **pasif duruma geçecek** ve tüm otomatik "
                "işlevler sonlanacaktır. Sunucu düzeninin ve üye deneyiminin aksamaması için "
                "bu sürecin yakından takip edilmesi son derece önemlidir."
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Bot Kapanırsa Etkilenecek Sistemler",
            value=(
                "▫️ **Kayıt ve Doğrulama:** Yeni gelenlerin form doldurması ve rol alması durur.\n"
                "▫️ **Bilet (Ticket) & Destek:** Destek talebi açma ve yetkili odaları devre dışı kalır.\n"
                "▫️ **Spam & Güvenlik Koruması:** Hızlı mesaj atma engeli ve susturma işlemleri çalışmaz.\n"
                "▫️ **İstatistik & Loglama:** Yetkili performans takibi ve işlem kayıtları tutulamaz."
            ),
            inline=False
        )

        embed.set_footer(
            text="GarajClass Otomatik Yönetim Takibi • 15 Gün Sonra Bu Modül Kendini İmha Edecektir",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
        )
        return embed

    async def send_daily_warning(self):
        channel = self.bot.get_channel(config.CH_EXPIRATION_WARNING)
        if not channel:
            return

        total_seconds, days, hours, minutes, end_ts = self.get_remaining_time()

        # Süre dolmuşsa
        if total_seconds <= 0:
            await self.handle_expiration(channel)
            return

        embed = self.build_warning_embed(days, hours, minutes, end_ts)
        mention_content = f"<@&{config.ROLE_FOUNDER}>"
        
        await channel.send(content=mention_content, embed=embed)
        
        today_str = datetime.datetime.now(TZ).strftime("%Y-%m-%d")
        self.data["last_notification_date"] = today_str
        save_data(self.data)

    async def handle_expiration(self, channel):
        """15 gün tamamlandığında son mesajı iletip dosyayı imha eder."""
        embed = discord.Embed(
            title="🛑 HİZMET SÜRESİ TAMAMLANDI: BOT PASİF DURUMDA",
            description=(
                "Sayın Kurucu ve Sunucu Yönetimi,\n\n"
                "**GarajClass Bot** için tanımlanan **15 günlük** çalışma süresi resmi olarak dolmuştur.\n\n"
                "Belirtilen süre tamamlandığı için bu uyarı ve sayaç sistemi kendini otomatik olarak "
                "sonlandırmış ve sistem dosyalarını imha etmiştir. Bot hizmetlerinin yeniden "
                "devreye alınması için geliştirici veya sunucu sahibi ile iletişime geçilmesi gerekmektedir."
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.now(TZ)
        )
        embed.set_footer(text="GarajClass • Süre Dolumu Bildirimi ve Otomatik İmha")
        
        try:
            await channel.send(content=f"<@&{config.ROLE_FOUNDER}>", embed=embed)
        except Exception as e:
            print(f"Kapanış mesajı gönderilemedi: {e}")

        # Döngüyü durdur
        self.daily_check.cancel()

        # json dosyasını temizle
        if os.path.exists(DATA_FILE):
            try:
                os.remove(DATA_FILE)
            except Exception as e:
                print(f"Data file remove error: {e}")

        # Bu python dosyasını kendi kendine sil (Self-delete)
        current_file_path = os.path.abspath(__file__)
        try:
            # Cog'u bellekten çıkar
            await self.bot.unload_extension("cogs.expiration")
        except Exception:
            pass

        try:
            if os.path.exists(current_file_path):
                os.remove(current_file_path)
                print(f"Expiration cog deleted itself: {current_file_path}")
        except Exception as e:
            print(f"Dosya silinemedi: {e}")

    @tasks.loop(minutes=30)
    async def daily_check(self):
        """Periyodik kontrol: Her gün bir kez bildirimi gönderir ve süreyi denetler."""
        total_seconds, days, hours, minutes, end_ts = self.get_remaining_time()

        channel = self.bot.get_channel(config.CH_EXPIRATION_WARNING)

        # Süre dolduysa doğrudan imha et
        if total_seconds <= 0:
            if channel:
                await self.handle_expiration(channel)
            return

        today_str = datetime.datetime.now(TZ).strftime("%Y-%m-%d")
        # Eğer bugün bildirim henüz atılmadıysa gönder
        if self.data.get("last_notification_date") != today_str:
            await self.send_daily_warning()

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="botsuresi")
    @commands.has_permissions(administrator=True)
    async def botsuresi(self, ctx):
        """Botun kalan süresini manuel kontrol etmeyi sağlar."""
        total_seconds, days, hours, minutes, end_ts = self.get_remaining_time()
        if total_seconds <= 0:
            await ctx.send("🛑 Botun 15 günlük süresi zaten dolmuş!")
            return
            
        embed = self.build_warning_embed(days, hours, minutes, end_ts)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Expiration(bot))
