import discord, asyncio
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from utils.api import buscar_livros, gerar_links_compra, buscar_precos
from utils.embeds import FOOTER, formato_preco
from utils.db import get_config, registrar_preco

LIVROS_MONITORADOS=["Harry Potter","Duna","1984","A Menina que Roubava Livros","Jogos Vorazes","O Pequeno Príncipe","Coraline","Dom Casmurro"]

class Promocoes(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.verificar_promocoes.start()
    def cog_unload(self): self.verificar_promocoes.cancel()

    @tasks.loop(hours=6)
    async def verificar_promocoes(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            cfg=get_config(guild.id); canal_id=cfg.get('canal_promocoes')
            if canal_id and (canal:=guild.get_channel(canal_id)): await self._postar_promocoes(canal)

    async def _postar_promocoes(self, canal):
        e=discord.Embed(title='🔥 Promoções/Livros em destaque — Ivy', description='Preços quando encontrados via APIs gratuitas.', color=discord.Color.red(), timestamp=datetime.utcnow())
        for titulo in LIVROS_MONITORADOS[:5]:
            try:
                res=await buscar_livros(titulo,1)
                if not res: continue
                l=res[0]; precos=await buscar_precos(l.get('titulo',''), l.get('autor',''), l.get('isbn',''))
                links=precos+gerar_links_compra(l); melhor=precos[0] if precos else ({'preco':l.get('preco'),'url':l.get('buy_link'),'loja':l.get('loja_preco') or 'Google Books'} if l.get('preco') else None)
                if melhor and melhor.get('preco') and l.get('isbn'): registrar_preco(l.get('isbn'), melhor.get('loja','Loja'), melhor['preco'], melhor.get('url',''))
                price=f"💰 **{formato_preco(melhor['preco'])}** — {melhor.get('loja')}\n[Comprar]({melhor.get('url')})" if melhor and melhor.get('preco') else f"💰 Preço não encontrado\n[Ver opções]({links[0]['url']})"
                e.add_field(name=f"📚 {l['titulo'][:45]}", value=f"✍️ {l.get('autor','')}\n{price}", inline=False)
                await asyncio.sleep(1)
            except Exception: continue
        e.set_footer(text=FOOTER)
        try: await canal.send(embed=e)
        except discord.Forbidden: pass

    @app_commands.command(name='promocoes', description='🔥 Mostra livros em destaque com preço quando disponível')
    async def promocoes(self, interaction, genero:str=''):
        await interaction.response.defer(); query=f'{genero} livros' if genero else 'livros bestsellers'
        resultados=await buscar_livros(query,8)
        if not resultados: return await interaction.followup.send(embed=discord.Embed(description='Não encontrei promoções agora.', color=discord.Color.orange()))
        e=discord.Embed(title=f"🔥 Livros em Destaque{' — '+genero if genero else ''}", color=discord.Color.red(), timestamp=datetime.utcnow())
        for l in resultados[:6]:
            precos=await buscar_precos(l.get('titulo',''), l.get('autor',''), l.get('isbn',''))
            links=precos+gerar_links_compra(l)
            melhor=precos[0] if precos else ({'preco':l.get('preco'),'url':l.get('buy_link'),'loja':l.get('loja_preco') or 'Google Books'} if l.get('preco') else None)
            texto=f"✍️ {l.get('autor','')}\n"
            if melhor and melhor.get('preco'): texto+=f"💰 **{formato_preco(melhor['preco'])}** — {melhor.get('loja')}\n[Comprar]({melhor.get('url')})"
            else: texto+=f"[Ver preços 🛒]({links[0]['url']})"
            e.add_field(name=f"📚 {l['titulo'][:45]}", value=texto, inline=True)
        e.set_footer(text=FOOTER); await interaction.followup.send(embed=e)

    @app_commands.command(name='gratuitos', description='📱 Livros gratuitos em domínio público')
    async def gratuitos(self, interaction):
        e=discord.Embed(title='📚 Livros Gratuitos — Domínio Público', description='Fontes gratuitas e confiáveis:', color=discord.Color.green())
        for nome,url,desc in [("📖 Domínio Público","http://www.dominiopublico.gov.br","Obras clássicas"),("🌐 Project Gutenberg","https://www.gutenberg.org","Ebooks gratuitos"),("🗄️ Internet Archive","https://archive.org/details/texts","Acervo digital")]:
            e.add_field(name=nome,value=f"[Acessar]({url})\n{desc}",inline=True)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e)
async def setup(bot): await bot.add_cog(Promocoes(bot))
