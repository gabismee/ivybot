import discord
from discord import app_commands
from discord.ext import commands
from utils.api import recomendar_por_perfil, buscar_livros, gerar_links_compra
from utils.embeds import embed_livro, embed_erro
from utils.db import get_perfil, get_biblioteca

OBJETIVO_QUERIES = {
    "aprender":      ["melhores livros técnicos", "livros aprender habilidades"],
    "profissional":  ["livros liderança negócios", "livros desenvolvimento profissional"],
    "estudos":       ["livros vestibular enem", "livros estudo"],
    "concurso":      ["livros concurso público", "direito administrativo"],
    "diversao":      ["bestsellers ficção", "livros fantasia aventura"],
}

class IA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="recomendar", description="🤖 Recomendações personalizadas baseadas no seu perfil")
    async def recomendar(self, interaction: discord.Interaction):
        await interaction.response.defer()

        perfil = get_perfil(interaction.user.id)
        if not perfil:
            await interaction.followup.send(embed=discord.Embed(
                description="Configure seu perfil primeiro com `/configurar`!",
                color=discord.Color.orange()
            ))
            return

        # Histórico para evitar repetição
        biblioteca = get_biblioteca(interaction.user.id)
        titulos_lidos = [l["titulo"] for l in biblioteca]

        recomendacoes = await recomendar_por_perfil(perfil, titulos_lidos)

        if not recomendacoes:
            await interaction.followup.send(embed=embed_erro("Não encontrei recomendações agora. Tente mais tarde."))
            return

        embed = discord.Embed(
            title=f"🤖 Recomendações para {interaction.user.display_name}",
            description=f"Baseado nos seus gêneros: **{', '.join(perfil.get('generos', [])[:3])}**",
            color=discord.Color.purple()
        )

        for i, livro in enumerate(recomendacoes[:5], 1):
            embed.add_field(
                name=f"{i}. {livro['titulo'][:50]}",
                value=f"✍️ {livro.get('autor','')}\n"
                      f"{'⭐ '+str(livro['avaliacao_google'])+'/5' if livro.get('avaliacao_google') else ''}\n"
                      f"📝 {livro.get('sinopse','')[:80]}...",
                inline=False
            )
        embed.set_footer(text="Use /buscar <título> para ver detalhes de qualquer livro")

        # Botões para ver detalhes
        view = VerRecomendacoesView(recomendacoes[:5])
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="similar", description="🔍 Encontra livros similares a um que você gostou")
    @app_commands.describe(titulo="Título do livro que você gostou")
    async def similar(self, interaction: discord.Interaction, titulo: str):
        await interaction.response.defer()
        base = await buscar_livros(titulo, 1)
        if not base:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return

        livro_base = base[0]
        queries = []
        if livro_base.get("autor"):
            queries.append(f"autor:{livro_base['autor']}")
        if livro_base.get("generos"):
            g = livro_base["generos"]
            if isinstance(g, list) and g:
                queries.append(f"subject:{g[0]}")

        todos = []
        for q in queries:
            resultados = await buscar_livros(q, 5)
            todos.extend([r for r in resultados if r["titulo"] != livro_base["titulo"]])

        # Remove duplicatas
        vistos, unicos = set(), []
        for l in todos:
            if l["titulo"] not in vistos:
                vistos.add(l["titulo"])
                unicos.append(l)

        if not unicos:
            await interaction.followup.send(embed=embed_erro("Não encontrei similares."))
            return

        embed = discord.Embed(
            title=f"📚 Similares a: {livro_base['titulo'][:40]}",
            color=discord.Color.blue()
        )
        for l in unicos[:5]:
            embed.add_field(
                name=f"📖 {l['titulo'][:50]}",
                value=f"✍️ {l.get('autor','')}\n📝 {l.get('sinopse','')[:80]}...",
                inline=False
            )
        embed.set_footer(text="Use /buscar <título> para ver detalhes")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="encontrar", description="🎯 Encontra livros por objetivo ou tema")
    @app_commands.describe(tema="O que você quer aprender ou ler sobre?")
    async def encontrar(self, interaction: discord.Interaction, tema: str):
        await interaction.response.defer()
        resultados = await buscar_livros(tema, 6)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Não encontrei livros sobre **{tema}**."))
            return

        embed = discord.Embed(
            title=f"🎯 Livros sobre: {tema}",
            color=discord.Color.green()
        )
        for l in resultados[:5]:
            embed.add_field(
                name=f"📚 {l['titulo'][:50]}",
                value=f"✍️ {l.get('autor','')}\n📝 {l.get('sinopse','')[:80]}...",
                inline=False
            )
        embed.set_footer(text="Use /buscar <título> para ver detalhes e onde comprar")
        view = VerRecomendacoesView(resultados[:5])
        await interaction.followup.send(embed=embed, view=view)

class VerRecomendacoesView(discord.ui.View):
    def __init__(self, livros: list):
        super().__init__(timeout=120)
        self.livros = livros
        opcoes = [
            discord.SelectOption(
                label=l["titulo"][:100],
                description=l.get("autor","")[:50],
                value=str(i),
                emoji="📚"
            ) for i, l in enumerate(livros)
        ]
        s = discord.ui.Select(placeholder="Ver detalhes de um livro...", options=opcoes)
        s.callback = self.on_select
        self.add_item(s)

    async def on_select(self, interaction: discord.Interaction):
        idx   = int(interaction.data["values"][0])
        livro = self.livros[idx]
        links = gerar_links_compra(livro)
        embed = embed_livro(livro, links)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(IA(bot))
