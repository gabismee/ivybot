import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from utils.api import buscar_livros
from utils.embeds import embed_promocao
from utils.db import get_config, get_db, registrar_preco
import asyncio
from datetime import datetime

# Livros populares para monitorar promoções (pode ser expandido)
LIVROS_MONITORADOS = [
    "Clean Code",
    "O Poder do Hábito",
    "Sapiens",
    "Harry Potter",
    "Duna",
    "O Senhor dos Anéis",
    "Pai Rico Pai Pobre",
    "O Alquimista",
    "1984",
    "Corte de Espinhos e Rosas",
]

class Promocoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificar_promocoes.start()

    def cog_unload(self):
        self.verificar_promocoes.cancel()

    @tasks.loop(hours=6)
    async def verificar_promocoes(self):
        """Verifica promoções a cada 6 horas e posta nos canais configurados"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            cfg = get_config(guild.id)
            canal_id = cfg.get("canal_promocoes")
            if not canal_id:
                continue
            canal = guild.get_channel(canal_id)
            if not canal:
                continue
            await self._postar_promocoes(canal)

    async def _postar_promocoes(self, canal: discord.TextChannel):
        """Busca e posta top promoções no canal"""
        embed = discord.Embed(
            title="🔥 Promoções de Livros — Atualização",
            description="Aqui estão os livros em destaque agora:",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        # Busca alguns livros populares para exibir como destaque
        for titulo in LIVROS_MONITORADOS[:5]:
            try:
                resultados = await buscar_livros(titulo, 1)
                if resultados:
                    l = resultados[0]
                    from utils.api import gerar_links_compra
                    links = gerar_links_compra(l)
                    amazon_url = next((lk["url"] for lk in links if "amazon" in lk["loja"].lower()), links[0]["url"])
                    embed.add_field(
                        name=f"📚 {l['titulo'][:45]}",
                        value=f"✍️ {l.get('autor','')}\n"
                              f"[🛒 Ver na Amazon]({amazon_url}) | "
                              f"[📚 Cultura]({links[1]['url'] if len(links)>1 else amazon_url})",
                        inline=False
                    )
                await asyncio.sleep(1)  # Rate limit gentil
            except Exception:
                continue

        embed.set_footer(text="BookBot 📚 • Use /alerta para criar alertas personalizados")
        try:
            await canal.send(embed=embed)
        except discord.Forbidden:
            pass

    # ─── Comandos ─────────────────────────────────────────────────────────────
    @app_commands.command(name="promocoes", description="🔥 Mostra promoções de livros agora")
    @app_commands.describe(genero="Filtrar por gênero (opcional)")
    async def promocoes(self, interaction: discord.Interaction, genero: str = ""):
        await interaction.response.defer()
        query = f"{genero} livros" if genero else "livros bestsellers"
        resultados = await buscar_livros(query, 8)

        if not resultados:
            await interaction.followup.send(
                embed=discord.Embed(description="Não encontrei promoções no momento.", color=discord.Color.orange())
            )
            return

        embed = discord.Embed(
            title=f"🔥 Livros em Destaque{' — '+genero if genero else ''}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        from utils.api import gerar_links_compra
        for l in resultados[:6]:
            links = gerar_links_compra(l)
            amazon = next((lk["url"] for lk in links if "amazon" in lk["loja"].lower()), links[0]["url"])
            embed.add_field(
                name=f"📚 {l['titulo'][:45]}",
                value=f"✍️ {l.get('autor','')}\n[Ver preços 🛒]({amazon})",
                inline=True
            )
        embed.set_footer(text="BookBot 📚 • Use /alerta para monitorar um livro específico")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="gratuitos", description="📱 Livros gratuitos em domínio público")
    async def gratuitos(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Livros Gratuitos — Domínio Público",
            description="Acesse gratuitamente clássicos da literatura:",
            color=discord.Color.green()
        )
        fontes = [
            ("📖 Domínio Público (Gov BR)",   "http://www.dominiopublico.gov.br",    "Portal oficial do governo com obras clássicas"),
            ("🌐 Project Gutenberg",           "https://www.gutenberg.org",           "60k+ ebooks gratuitos (maioria em inglês)"),
            ("🗄️ Internet Archive",            "https://archive.org/details/texts",   "Enorme acervo digital gratuito"),
            ("🎓 Brasiliana USP",              "https://www.brasiliana.usp.br",       "Obras históricas e literárias brasileiras"),
            ("📱 Amazon Kindle Grátis",        "https://www.amazon.com.br/b?node=16340791011", "Ebooks gratuitos na Amazon"),
            ("🔬 Scielo Books",                "https://books.scielo.org",            "Livros acadêmicos gratuitos"),
        ]
        for nome, url, desc in fontes:
            embed.add_field(name=nome, value=f"[Acessar]({url})\n{desc}", inline=True)
        embed.set_footer(text="BookBot 📚 • Todos os links são de fontes confiáveis e gratuitas")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Promocoes(bot))
