import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import embed_ranking
from utils.db import get_ranking_wishlist, get_ranking_avaliacoes, get_ranking_xp

class Ranking(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name='ranking', description='🏆 Rankings da comunidade')
    @app_commands.choices(tipo=[app_commands.Choice(name='🌱 XP',value='xp'),app_commands.Choice(name='❤️ Mais desejados',value='wishlist'),app_commands.Choice(name='⭐ Mais bem avaliados',value='avaliacoes')])
    async def ranking(self, interaction, tipo:str='xp'):
        if tipo=='wishlist': itens=get_ranking_wishlist(10); titulo='Livros Mais Desejados'
        elif tipo=='avaliacoes': itens=get_ranking_avaliacoes(10); titulo='Livros Mais Bem Avaliados'
        else: itens=get_ranking_xp(10); titulo='Leitores com Mais XP'
        if not itens: return await interaction.response.send_message(embed=discord.Embed(description='Ainda não há dados suficientes.', color=discord.Color.orange()))
        await interaction.response.send_message(embed=embed_ranking(titulo,itens,tipo))
async def setup(bot): await bot.add_cog(Ranking(bot))
