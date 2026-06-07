import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import FOOTER

DESAFIOS=[
    {"id":"nacional","nome":"📗 Brasil na Estante","desc":"Leia um livro de autor(a) brasileiro(a).","xp":80},
    {"id":"30dias","nome":"🔥 30 Dias de Leitura","desc":"Registre leitura com `/ler` por 30 dias.","xp":200},
    {"id":"classico","nome":"🏛️ Clássico do Mês","desc":"Leia um clássico da literatura.","xp":100},
    {"id":"fantasia","nome":"🐉 Portal da Fantasia","desc":"Leia um livro de fantasia.","xp":80},
]
class Desafios(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name="desafio", description="🎲 Mostra o desafio de leitura atual")
    async def desafio(self, interaction):
        d=DESAFIOS[0]
        e=discord.Embed(title="🎲 Desafio de Leitura", description=f"**{d['nome']}**\n{d['desc']}", color=discord.Color.green())
        e.add_field(name="🎁 Recompensa", value=f"+{d['xp']} XP", inline=True)
        e.add_field(name="Como participar", value="Use `/estante adicionar` e `/ler` para registrar progresso.", inline=False)
        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e)
    @app_commands.command(name="desafios", description="📚 Lista desafios disponíveis")
    async def desafios(self, interaction):
        e=discord.Embed(title="📚 Desafios disponíveis", color=discord.Color.green())
        for d in DESAFIOS: e.add_field(name=d['nome'], value=f"{d['desc']}\n🎁 +{d['xp']} XP", inline=False)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e, ephemeral=True)
async def setup(bot): await bot.add_cog(Desafios(bot))
