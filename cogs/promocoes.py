import discord, asyncio
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from utils.api import buscar_livros, gerar_links_compra
from utils.db import get_config, wishlist_com_alerta, registrar_notificacao_wishlist
from utils.embeds import formato_preco, CORES

LIVROS_MONITORADOS=['romance brasileiro','fantasia em português','literatura brasileira','young adult português','mangá português','clássicos brasileiros','ficção científica português']

class Promocoes(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.verificar_promocoes.start()
    def cog_unload(self): self.verificar_promocoes.cancel()
    @tasks.loop(hours=6)
    async def verificar_promocoes(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            cid=get_config(guild.id).get('canal_promocoes')
            canal=guild.get_channel(cid) if cid else None
            if canal: await self._postar_promocoes(canal)
        await self._avisar_wishlist_promocoes()

    async def _avisar_wishlist_promocoes(self):
        # Verifica alertas de preço da lista Quero Ler. Depende da API retornar preço.
        for item in wishlist_com_alerta():
            try:
                resultados = await buscar_livros(item['titulo'], 3, lang='pt')
                alvo = float(item.get('preco_alvo') or 0)
                for livro in resultados:
                    preco = livro.get('preco')
                    if not preco or float(preco) > alvo:
                        continue
                    isbn = item.get('isbn') or livro.get('isbn') or item['titulo']
                    url = livro.get('buy_link') or gerar_links_compra(livro)[0]['url']
                    if not registrar_notificacao_wishlist(item['user_id'], isbn, livro.get('titulo') or item['titulo'], float(preco), url):
                        continue
                    user = self.bot.get_user(item['user_id']) or await self.bot.fetch_user(item['user_id'])
                    e = discord.Embed(
                        title='🔔 Livro da sua lista entrou no preço!',
                        description=f"**{livro.get('titulo', item['titulo'])}**\n💰 {formato_preco(preco, livro.get('moeda','BRL'))}\n🎯 Seu alerta: {formato_preco(alvo)}\n[Ver/Comprar]({url})",
                        color=CORES['rosa'],
                        timestamp=datetime.utcnow()
                    )
                    if livro.get('capa_url'):
                        e.set_thumbnail(url=livro['capa_url'])
                    e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷')
                    try: await user.send(embed=e)
                    except Exception: pass
                    break
            except Exception:
                continue

    async def _postar_promocoes(self, canal):
        e=await self._montar_embed('livros em português', '')
        try: await canal.send(embed=e)
        except discord.Forbidden: pass
    async def _montar_embed(self, query, limite):
        livros=await buscar_livros(query,10,lang='pt')
        e=discord.Embed(title='🔥 Promoções/Livros em português', description='Separado por faixas de preço quando a API retorna preço. Quando não retorna, deixo link de busca BR.', color=CORES['laranja'], timestamp=datetime.utcnow())
        grupos={'Até R$30':[], 'Até R$50':[], 'Até R$100':[], 'Sem preço na API':[]}
        for l in livros:
            p=l.get('preco')
            item=f"**{l['titulo'][:45]}**\n✍️ {l.get('autor','—')[:45]}"
            if p: item += f"\n💰 {formato_preco(p,l.get('moeda','BRL'))}"
            links=gerar_links_compra(l); item += f"\n[Ver/Comprar]({(l.get('buy_link') or links[0]['url'])})"
            if p and p<=30: grupos['Até R$30'].append(item)
            elif p and p<=50: grupos['Até R$50'].append(item)
            elif p and p<=100: grupos['Até R$100'].append(item)
            else: grupos['Sem preço na API'].append(item)
            if l.get('capa_url') and not e.thumbnail.url: e.set_thumbnail(url=l['capa_url'])
        for nome,items in grupos.items():
            if items: e.add_field(name=nome, value='\n\n'.join(items[:3])[:1000], inline=False)
        e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷'); return e
    @app_commands.command(name='promocoes', description='🔥 Livros em português por faixa de preço')
    @app_commands.choices(faixa=[app_commands.Choice(name='Até R$30',value='30'),app_commands.Choice(name='Até R$50',value='50'),app_commands.Choice(name='Até R$100',value='100')])
    async def promocoes(self, interaction, genero:str='', faixa:str=''):
        await interaction.response.defer(); q=(genero+' livros em português') if genero else 'livros em português brasileiros'
        await interaction.followup.send(embed=await self._montar_embed(q, faixa))
    @app_commands.command(name='gratuitos', description='📱 Livros gratuitos em domínio público')
    async def gratuitos(self, interaction):
        e=discord.Embed(title='📚 Livros gratuitos em português', description='Fontes confiáveis para achar livros gratuitos:', color=CORES['verde'])
        fontes=[('Domínio Público (Gov BR)','http://www.dominiopublico.gov.br'),('Brasiliana USP','https://www.brasiliana.usp.br'),('Scielo Books','https://books.scielo.org'),('Biblioteca Nacional Digital','https://bndigital.bn.gov.br')]
        for n,u in fontes: e.add_field(name=n,value=f'[Acessar]({u})',inline=True)
        await interaction.response.send_message(embed=e)
    @commands.command(name='promocoes', aliases=['promoções'])
    async def promocoes_prefix(self, ctx, faixa:str='', *, genero:str=''):
        # Ex.: !promocoes 30 fantasia / !promocoes romance
        if faixa and not faixa.isdigit():
            genero = (faixa + ' ' + genero).strip(); faixa=''
        q=(genero+' livros em português') if genero else 'livros em português brasileiros'
        await ctx.send(embed=await self._montar_embed(q, faixa))
    @commands.command(name='gratuitos')
    async def gratuitos_prefix(self, ctx):
        e=discord.Embed(title='📚 Livros gratuitos em português', description='Fontes confiáveis para achar livros gratuitos:', color=CORES['verde'])
        fontes=[('Domínio Público (Gov BR)','http://www.dominiopublico.gov.br'),('Brasiliana USP','https://www.brasiliana.usp.br'),('Scielo Books','https://books.scielo.org'),('Biblioteca Nacional Digital','https://bndigital.bn.gov.br')]
        for n,u in fontes: e.add_field(name=n,value=f'[Acessar]({u})',inline=True)
        await ctx.send(embed=e)

async def setup(bot): await bot.add_cog(Promocoes(bot))
