import discord, random
from discord import app_commands
from discord.ext import commands
from data.literary_data import frase_aleatoria, poesia_aleatoria, GENEROS, PERSONAGENS, TOP50
from utils.api import buscar_livros
from utils.embeds import CORES, embed_erro

FOOTER='Ivy 📚 • Feito pela Gabi 🌷'

class Literario(commands.Cog):
    def __init__(self, bot): self.bot=bot

    def _frase_embed(self):
        f,obra,autor=frase_aleatoria(); e=discord.Embed(title='📜 Frase literária', description=f'“{f}”', color=CORES['roxo']); e.add_field(name='Obra',value=obra,inline=True); e.add_field(name='Autor',value=autor,inline=True); e.set_footer(text=FOOTER); return e
    @app_commands.command(name='frase', description='📜 Sorteia uma frase literária')
    async def frase(self, interaction): await interaction.response.send_message(embed=self._frase_embed())
    @commands.command(name='frase')
    async def frase_prefix(self, ctx): await ctx.send(embed=self._frase_embed())

    def _poesia_embed(self):
        titulo,autor,txt=poesia_aleatoria(); e=discord.Embed(title=f'🌙 {titulo}', description=txt, color=CORES['rosa']); e.add_field(name='Autor', value=autor); e.set_footer(text=FOOTER); return e
    @app_commands.command(name='poesia', description='🌙 Sorteia uma poesia/trecho')
    async def poesia(self, interaction): await interaction.response.send_message(embed=self._poesia_embed())
    @commands.command(name='poesia', aliases=['poema'])
    async def poesia_prefix(self, ctx): await ctx.send(embed=self._poesia_embed())

    def _genero_embed(self, nome):
        key=nome.lower().strip(); data=GENEROS.get(key)
        if not data: return None
        e=discord.Embed(title=f'🏷️ {key.title()}', description=data['desc'], color=CORES['azul']); e.add_field(name='Autores principais', value='\n'.join(data['autores']), inline=True); e.add_field(name='Obras principais', value='\n'.join(data['obras']), inline=True); e.set_footer(text=FOOTER); return e
    @app_commands.command(name='genero', description='🏷️ Explica um gênero literário')
    async def genero(self, interaction, nome:str):
        e=self._genero_embed(nome)
        if not e: return await interaction.response.send_message('Não achei esse gênero. Tente: romance, ficção científica, fantasia, terror, mangá ou mistério.', ephemeral=True)
        await interaction.response.send_message(embed=e)
    @commands.command(name='genero', aliases=['gênero'])
    async def genero_prefix(self, ctx, *, nome:str=None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!genero <nome>`'))
        e=self._genero_embed(nome)
        if not e: return await ctx.send(embed=embed_erro('Não achei esse gênero. Tente: romance, ficção científica, fantasia, terror, mangá ou mistério.'))
        await ctx.send(embed=e)

    def _personagem_embed(self, nome):
        p=PERSONAGENS.get(nome.lower().strip())
        if not p: return None
        title,obra,autor,desc=p; e=discord.Embed(title=f'🔎 {title}', description=desc, color=CORES['verde']); e.add_field(name='Obra', value=obra); e.add_field(name='Autor', value=autor); e.set_footer(text=FOOTER); return e
    @app_commands.command(name='personagem', description='🔎 Pesquisa um personagem literário/mangá')
    async def personagem(self, interaction, nome:str):
        e=self._personagem_embed(nome)
        if e: return await interaction.response.send_message(embed=e)
        await interaction.response.send_message('Ainda não tenho esse personagem cadastrado.', ephemeral=True)
    @commands.command(name='personagem')
    async def personagem_prefix(self, ctx, *, nome:str=None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!personagem <nome>`'))
        e=self._personagem_embed(nome)
        if e: return await ctx.send(embed=e)
        await ctx.send(embed=embed_erro('Ainda não tenho esse personagem cadastrado.'))

    async def _autor_exec(self, destino, nome):
        livros=await buscar_livros(f'inauthor:{nome}',5,lang='pt')
        e=discord.Embed(title=f'✍️ {nome}', description='Obras encontradas em português:', color=CORES['laranja'])
        if not livros: e.description='Não encontrei obras desse autor agora.'
        for l in livros[:5]: e.add_field(name=l['titulo'][:60], value=f"{l.get('ano','')} • {l.get('editora','') or 'Editora não informada'}", inline=False)
        e.set_footer(text=FOOTER); await destino.send(embed=e)
    @app_commands.command(name='autor', description='✍️ Pesquisa um autor pelo nome')
    async def autor(self, interaction, nome:str):
        await interaction.response.defer()
        class Dest:
            async def send(_, **kw): return await interaction.followup.send(**kw)
        await self._autor_exec(Dest(), nome)
    @commands.command(name='autor')
    async def autor_prefix(self, ctx, *, nome:str=None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!autor <nome>`'))
        await self._autor_exec(ctx, nome)

    def _top_embed(self):
        texto='\n'.join([f'**{i}.** {t}' for i,t in enumerate(TOP50,1)])
        e=discord.Embed(title='📚 Top 50 livros conhecidos/mais lidos', description=texto[:3900], color=CORES['dourado']); e.set_footer(text=FOOTER); return e
    @app_commands.command(name='toplivros', description='📚 Exibe 50 livros muito lidos/conhecidos')
    async def toplivros(self, interaction): await interaction.response.send_message(embed=self._top_embed())
    @commands.command(name='toplivros', aliases=['top-livros'])
    async def toplivros_prefix(self, ctx): await ctx.send(embed=self._top_embed())

    async def _animal_send(self, destino, tipo):
        urls={'gato':'https://cataas.com/cat?width=600&height=500','cachorro':'https://placedog.net/600/500?id='+str(random.randint(1,999))}
        url=urls.get(tipo) or random.choice(list(urls.values()))
        e=discord.Embed(title=f'🐾 {tipo.title()} fofo', color=CORES['rosa']); e.set_image(url=url); e.set_footer(text=FOOTER); await destino.send(embed=e)
    @app_commands.command(name='gato', description='🐱 Gera imagem de gato fofo')
    async def gato(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), 'gato')
    @app_commands.command(name='cachorro', description='🐶 Gera imagem de cachorro fofo')
    async def cachorro(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), 'cachorro')
    @app_commands.command(name='animalfofo', description='🐾 Gera imagem de animal fofo aleatório')
    async def animalfofo(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), random.choice(['gato','cachorro']))
    @commands.command(name='gato')
    async def gato_prefix(self, ctx): await self._animal_send(ctx, 'gato')
    @commands.command(name='cachorro')
    async def cachorro_prefix(self, ctx): await self._animal_send(ctx, 'cachorro')
    @commands.command(name='animalfofo', aliases=['animal'])
    async def animalfofo_prefix(self, ctx): await self._animal_send(ctx, random.choice(['gato','cachorro']))

async def setup(bot): await bot.add_cog(Literario(bot))
