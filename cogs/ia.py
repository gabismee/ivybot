import discord
from discord import app_commands
from discord.ext import commands
from utils.api import recomendar_por_perfil, buscar_livros, gerar_links_compra, buscar_similares
from utils.embeds import embed_livro, embed_erro, CORES
from utils.db import get_perfil, get_biblioteca

class IA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _recomendar_exec(self, destino, usuario):
        perfil = get_perfil(usuario.id)
        if not perfil:
            return await destino.send(embed=discord.Embed(description="Configure seu perfil primeiro com `/configurar`!", color=CORES['laranja']))
        biblioteca = get_biblioteca(usuario.id)
        titulos_lidos = [l["titulo"] for l in biblioteca]
        recomendacoes = await recomendar_por_perfil(perfil, titulos_lidos)
        if not recomendacoes:
            return await destino.send(embed=embed_erro("Não encontrei recomendações agora. Tente mais tarde."))
        embed = discord.Embed(
            title=f"🤖 Recomendações para {usuario.display_name}",
            description=f"Baseado nos seus gostos e no seu histórico.",
            color=CORES['roxo']
        )
        gens = perfil.get('generos', [])[:3]
        if gens:
            embed.add_field(name='Gêneros do perfil', value=', '.join(gens), inline=False)
        for i, livro in enumerate(recomendacoes[:5], 1):
            embed.add_field(
                name=f"{i}. {livro['titulo'][:50]}",
                value=f"✍️ {livro.get('autor','')}\n"
                      f"{'⭐ '+str(livro['avaliacao_google'])+'/5' if livro.get('avaliacao_google') else ''}\n"
                      f"📝 {livro.get('sinopse','')[:100]}...",
                inline=False
            )
        embed.set_footer(text="Use /livro ou !livro para ver detalhes")
        await destino.send(embed=embed, view=VerRecomendacoesView(recomendacoes[:5]))

    @app_commands.command(name="recomendar", description="🤖 Recomendações personalizadas baseadas no seu perfil")
    async def recomendar(self, interaction: discord.Interaction):
        await interaction.response.defer()
        class Dest:
            async def send(_, **kw): return await interaction.followup.send(**kw)
        await self._recomendar_exec(Dest(), interaction.user)

    @commands.command(name='recomendar')
    async def recomendar_prefix(self, ctx):
        await self._recomendar_exec(ctx, ctx.author)

    async def _similar_exec(self, destino, titulo: str):
        similares = await buscar_similares(titulo, 6)
        if not similares:
            return await destino.send(embed=embed_erro("Não encontrei obras semelhantes sem repetir volumes da mesma série."))
        embed = discord.Embed(
            title=f"📚 Obras parecidas com: {titulo[:45]}",
            description="Filtrei para evitar volumes/edições da mesma série quando possível.",
            color=CORES['azul']
        )
        for l in similares[:6]:
            embed.add_field(
                name=f"📖 {l['titulo'][:55]}",
                value=f"✍️ {l.get('autor','—')}\n🏷️ {', '.join(l.get('generos', [])[:2]) if isinstance(l.get('generos'), list) else l.get('generos','')}\n📝 {l.get('sinopse','')[:120]}...",
                inline=False
            )
            if l.get('capa_url') and not embed.thumbnail.url:
                embed.set_thumbnail(url=l['capa_url'])
        embed.set_footer(text="Use /livro ou !livro para ver detalhes")
        await destino.send(embed=embed, view=VerRecomendacoesView(similares[:6]))

    @app_commands.command(name="similar", description="🔍 Encontra obras semelhantes, sem repetir volumes da mesma série")
    @app_commands.describe(titulo="Título do livro/mangá que você gostou")
    async def similar(self, interaction: discord.Interaction, titulo: str):
        await interaction.response.defer()
        class Dest:
            async def send(_, **kw): return await interaction.followup.send(**kw)
        await self._similar_exec(Dest(), titulo)

    @commands.command(name='similar', aliases=['parecido'])
    async def similar_prefix(self, ctx, *, titulo: str = None):
        if not titulo:
            return await ctx.send(embed=embed_erro('Use: `!similar <livro>` ou `!parecido <livro>`'))
        await self._similar_exec(ctx, titulo)

    async def _encontrar_exec(self, destino, tema: str):
        resultados = await buscar_livros(tema, 6, lang='pt')
        if not resultados:
            return await destino.send(embed=embed_erro(f"Não encontrei livros sobre **{tema}**."))
        embed = discord.Embed(title=f"🎯 Livros sobre: {tema}", color=CORES['verde'])
        for l in resultados[:5]:
            embed.add_field(name=f"📚 {l['titulo'][:50]}", value=f"✍️ {l.get('autor','')}\n📝 {l.get('sinopse','')[:100]}...", inline=False)
        embed.set_footer(text="Use /livro ou !livro para ver detalhes e onde comprar")
        await destino.send(embed=embed, view=VerRecomendacoesView(resultados[:5]))

    @app_commands.command(name="encontrar", description="🎯 Encontra livros por objetivo ou tema")
    async def encontrar(self, interaction: discord.Interaction, tema: str):
        await interaction.response.defer()
        class Dest:
            async def send(_, **kw): return await interaction.followup.send(**kw)
        await self._encontrar_exec(Dest(), tema)

    @commands.command(name='encontrar')
    async def encontrar_prefix(self, ctx, *, tema: str = None):
        if not tema:
            return await ctx.send(embed=embed_erro('Use: `!encontrar <tema>`'))
        await self._encontrar_exec(ctx, tema)

class VerRecomendacoesView(discord.ui.View):
    def __init__(self, livros: list):
        super().__init__(timeout=120)
        self.livros = livros
        opcoes = [discord.SelectOption(label=l["titulo"][:100], description=l.get("autor","")[:50], value=str(i), emoji="📚") for i, l in enumerate(livros)]
        s = discord.ui.Select(placeholder="Ver detalhes de um livro...", options=opcoes)
        s.callback = self.on_select
        self.add_item(s)

    async def on_select(self, interaction: discord.Interaction):
        livro = self.livros[int(interaction.data["values"][0])]
        await interaction.response.send_message(embed=embed_livro(livro, gerar_links_compra(livro)), ephemeral=True)

async def setup(bot):
    await bot.add_cog(IA(bot))
