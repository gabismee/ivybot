import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils.embeds import FOOTER

EVENTOS={
    1:("🎯 Ano Novo Literário","Defina sua meta e comece uma leitura nova.","+50 XP bônus em metas"),
    6:("🌽 Arraiá Literário","Leia autores nacionais e clássicos brasileiros.","Cargo/evento do servidor"),
    10:("🎃 Halloween Literário","Leituras de arrepiar: terror, mistério e suspense.","+XP em desafios sombrios"),
    12:("🎄 Natal Literário","Livros confortáveis para fechar o ano.","Conquista especial"),
}
class Eventos(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name="evento", description="🎁 Mostra o evento sazonal atual")
    async def evento(self, interaction):
        nome,desc,recomp=EVENTOS.get(datetime.now().month,("🌙 Temporada Livre","Sem evento especial neste mês, mas a leitura segue valendo.","XP normal"))
        e=discord.Embed(title=nome, description=desc, color=discord.Color.purple())
        e.add_field(name="🎁 Recompensa", value=recomp, inline=False)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e)
async def setup(bot): await bot.add_cog(Eventos(bot))
