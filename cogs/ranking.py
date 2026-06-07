import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_ranking_wishlist, get_ranking_avaliacoes, get_ranking_xp, get_top_livros_lidos
from utils.embeds import estrelas, CORES

class Ranking(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name='ranking', description='🏆 Rankings da comunidade')
    @app_commands.choices(tipo=[app_commands.Choice(name='📌 Quero Ler',value='wishlist'),app_commands.Choice(name='⭐ Avaliações',value='avaliacoes'),app_commands.Choice(name='🌱 XP/Níveis',value='xp'),app_commands.Choice(name='📚 Mais lidos do servidor',value='lidos')])
    async def ranking(self, interaction, tipo:str='xp'):
        e=discord.Embed(title='🏆 Ranking', color=CORES['dourado'])
        if tipo=='wishlist': rows=get_ranking_wishlist(10); e.title='📌 Livros mais desejados'
        elif tipo=='avaliacoes': rows=get_ranking_avaliacoes(10); e.title='⭐ Mais bem avaliados'
        elif tipo=='lidos': rows=get_top_livros_lidos(10); e.title='📚 Mais lidos do servidor'
        else: rows=get_ranking_xp(10); e.title='🌱 Ranking de XP'
        if not rows: e.description='Ainda não há dados.'
        for i,r in enumerate(rows,1):
            if tipo=='xp': val=f"XP: **{r.get('xp',0)}** • Streak: {r.get('streak',0)}"; nome=r.get('username') or str(r.get('user_id'))
            elif tipo=='avaliacoes': nome=r['titulo']; val=f"✍️ {r.get('autor','')}\n{estrelas(r.get('media',0))} ({r.get('votos',0)} avaliações)"
            else: nome=r['titulo']; val=f"✍️ {r.get('autor','')}\nTotal: **{r.get('total',0)}**"
            e.add_field(name=f'{i}. {nome}'[:256], value=val, inline=False)
        e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷'); await interaction.response.send_message(embed=e)
    @commands.command(name='ranking', aliases=['rank'])
    async def ranking_prefix(self, ctx, tipo:str='xp'):
        e=discord.Embed(title='🏆 Ranking', color=CORES['dourado'])
        if tipo in ('wishlist','queroler','quero_ler'): rows=get_ranking_wishlist(10); e.title='📌 Livros mais desejados'
        elif tipo in ('avaliacoes','avaliações','notas'): rows=get_ranking_avaliacoes(10); e.title='⭐ Mais bem avaliados'
        elif tipo in ('lidos','livros'): rows=get_top_livros_lidos(10); e.title='📚 Mais lidos do servidor'
        else: rows=get_ranking_xp(10); e.title='🌱 Ranking de XP'; tipo='xp'
        if not rows: e.description='Ainda não há dados.'
        for i,r in enumerate(rows,1):
            if tipo=='xp': val=f"XP: **{r.get('xp',0)}** • Streak: {r.get('streak',0)}"; nome=r.get('username') or str(r.get('user_id'))
            elif tipo in ('avaliacoes','avaliações','notas'): nome=r['titulo']; val=f"✍️ {r.get('autor','')}\n{estrelas(r.get('media',0))} ({r.get('votos',0)} avaliações)"
            else: nome=r['titulo']; val=f"✍️ {r.get('autor','')}\nTotal: **{r.get('total',0)}**"
            e.add_field(name=f'{i}. {nome}'[:256], value=val, inline=False)
        e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷'); await ctx.send(embed=e)

async def setup(bot): await bot.add_cog(Ranking(bot))
