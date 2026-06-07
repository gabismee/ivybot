import discord, random
from discord import app_commands
from discord.ext import commands
from utils.db import criar_desafio, listar_desafios, concluir_desafio, add_xp
from utils.embeds import embed_sucesso, embed_erro, CORES

DESAFIOS=['Ler 20 páginas hoje','Ler um livro nacional','Ler um conto ou crônica','Ler por 15 minutos antes de dormir','Começar um livro fora da sua zona de conforto','Avaliar um livro que você já terminou','Adicionar 3 livros em Quero Ler']
EVENTOS={1:('🎯 Janeiro das Metas','Monte sua meta literária do ano.'),2:('💕 Fevereiro Romântico','Leia romances ou histórias com relações marcantes.'),6:('🔥 Junho Brasileiro','Valorize autores nacionais.'),10:('🎃 Halloween Literário','Terror, suspense e mistério.'),12:('🎄 Natal Literário','Leituras confortáveis e emocionantes.')}
class Desafios(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name='desafio', description='🎲 Recebe um desafio de leitura')
    async def desafio(self, interaction):
        d=random.choice(DESAFIOS); idd=criar_desafio(interaction.user.id,d)
        await interaction.response.send_message(embed=embed_sucesso(f'Desafio #{idd}: **{d}**\nAo concluir use `/desafio-concluir {idd}`.'))
    @app_commands.command(name='desafios', description='📋 Lista seus desafios')
    async def desafios(self, interaction):
        rows=listar_desafios(interaction.user.id); e=discord.Embed(title='📋 Seus desafios', color=CORES['verde'])
        if not rows: e.description='Nenhum desafio ainda. Use `/desafio`.'
        for r in rows: e.add_field(name=f"#{r['id']} {'✅' if r['concluido'] else '⏳'}", value=r['desafio'], inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
    @app_commands.command(name='desafio-concluir', description='✅ Conclui desafio e ganha XP')
    async def desafio_concluir(self, interaction, id:int):
        if concluir_desafio(interaction.user.id,id):
            add_xp(interaction.user.id, interaction.user.display_name, 150)
            await interaction.response.send_message(embed=embed_sucesso('Desafio concluído! +150 XP'))
        else: await interaction.response.send_message(embed=embed_erro('Desafio não encontrado ou já concluído.'), ephemeral=True)
    @app_commands.command(name='evento', description='🎁 Mostra evento sazonal atual')
    async def evento(self, interaction):
        import datetime
        nome,desc=EVENTOS.get(datetime.datetime.now().month,('📚 Temporada Livre','Sem evento especial este mês. Aproveite para ler algo novo!'))
        e=discord.Embed(title=nome, description=desc, color=CORES['roxo']); e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷'); await interaction.response.send_message(embed=e)
    @commands.command(name='desafio')
    async def desafio_prefix(self, ctx):
        d=random.choice(DESAFIOS); idd=criar_desafio(ctx.author.id,d)
        await ctx.send(embed=embed_sucesso(f'Desafio #{idd}: **{d}**\nAo concluir use `!desafio-concluir {idd}`.'))
    @commands.command(name='desafios')
    async def desafios_prefix(self, ctx):
        rows=listar_desafios(ctx.author.id); e=discord.Embed(title='📋 Seus desafios', color=CORES['verde'])
        if not rows: e.description='Nenhum desafio ainda. Use `!desafio`.'
        for r in rows: e.add_field(name=f"#{r['id']} {'✅' if r['concluido'] else '⏳'}", value=r['desafio'], inline=False)
        await ctx.send(embed=e)
    @commands.command(name='desafio-concluir')
    async def desafio_concluir_prefix(self, ctx, id:int=None):
        if not id: return await ctx.send(embed=embed_erro('Use: `!desafio-concluir <id>`'))
        if concluir_desafio(ctx.author.id,id):
            add_xp(ctx.author.id, ctx.author.display_name, 150)
            await ctx.send(embed=embed_sucesso('Desafio concluído! +150 XP'))
        else: await ctx.send(embed=embed_erro('Desafio não encontrado ou já concluído.'))
    @commands.command(name='evento')
    async def evento_prefix(self, ctx):
        import datetime
        nome,desc=EVENTOS.get(datetime.datetime.now().month,('📚 Temporada Livre','Sem evento especial este mês. Aproveite para ler algo novo!'))
        e=discord.Embed(title=nome, description=desc, color=CORES['roxo']); e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷'); await ctx.send(embed=e)

async def setup(bot): await bot.add_cog(Desafios(bot))
