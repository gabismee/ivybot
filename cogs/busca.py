import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros, gerar_links_compra
from utils.embeds import embed_livro, embed_erro
from utils.db import adicionar_wishlist

class BotaoWishlist(discord.ui.View):
    def __init__(self, livro: dict):
        super().__init__(timeout=120)
        self.livro = livro

    @discord.ui.button(label="❤️ Adicionar à Wishlist", style=discord.ButtonStyle.primary)
    async def add_wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = adicionar_wishlist(interaction.user.id, self.livro)
        if ok:
            await interaction.response.send_message(
                f"✅ **{self.livro['titulo']}** adicionado à sua wishlist!", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Livro já está na wishlist.", ephemeral=True)

    @discord.ui.button(label="📚 Adicionar à Estante", style=discord.ButtonStyle.secondary)
    async def add_estante(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.db import atualizar_biblioteca
        atualizar_biblioteca(interaction.user.id, self.livro, "quero_ler")
        await interaction.response.send_message(
            f"✅ **{self.livro['titulo']}** adicionado à estante como 'Quero Ler'!", ephemeral=True
        )

class SeletorLivro(discord.ui.View):
    def __init__(self, resultados: list[dict]):
        super().__init__(timeout=60)
        self.resultados = resultados

        opcoes = [
            discord.SelectOption(
                label=r["titulo"][:100],
                description=f"{r.get('autor','')[:50]} — {r.get('ano','')}",
                value=str(i),
                emoji="📚"
            )
            for i, r in enumerate(resultados[:10])
        ]
        select = discord.ui.Select(placeholder="Escolha um livro...", options=opcoes)
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        idx = int(interaction.data["values"][0])
        livro = self.resultados[idx]
        links = gerar_links_compra(livro)
        embed = embed_livro(livro, links)
        view  = BotaoWishlist(livro)
        await interaction.response.edit_message(embed=embed, view=view)

async def _executar_busca(ctx_or_interaction, query: str, is_slash: bool):
    """Lógica compartilhada entre slash e prefixo"""
    resultados = await buscar_livros(query, max_results=8)

    if not resultados:
        erro = embed_erro(f"Nenhum livro encontrado para **{query}**.\nTente outro título ou autor.")
        if is_slash:
            await ctx_or_interaction.followup.send(embed=erro)
        else:
            await ctx_or_interaction.send(embed=erro)
        return

    if len(resultados) == 1:
        livro = resultados[0]
        links = gerar_links_compra(livro)
        embed = embed_livro(livro, links)
        view  = BotaoWishlist(livro)
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)
    else:
        embed = discord.Embed(
            title=f"🔍 Resultados para: {query}",
            description=f"Encontrei **{len(resultados)}** livros. Escolha um abaixo:",
            color=discord.Color.blurple()
        )
        view = SeletorLivro(resultados)
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

class Busca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Slash command ──────────────────────────────────────────────────────────
    @app_commands.command(name="buscar", description="🔍 Pesquisa um livro pelo título, autor ou ISBN")
    @app_commands.describe(query="Título, autor, ISBN ou palavras-chave")
    async def buscar_slash(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        await _executar_busca(interaction, query, is_slash=True)

    @app_commands.command(name="livro", description="📚 Exibe detalhes completos de um livro")
    @app_commands.describe(titulo="Título do livro")
    async def livro_slash(self, interaction: discord.Interaction, titulo: str):
        await interaction.response.defer()
        resultados = await buscar_livros(titulo, max_results=1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return
        livro = resultados[0]
        links = gerar_links_compra(livro)
        embed = embed_livro(livro, links)
        view  = BotaoWishlist(livro)
        await interaction.followup.send(embed=embed, view=view)

    # ── Prefixo ! ──────────────────────────────────────────────────────────────
    @commands.command(name="buscar", aliases=["b", "livro", "search"])
    async def buscar_prefix(self, ctx: commands.Context, *, query: str = None):
        """🔍 Pesquisa um livro. Uso: !buscar harry potter"""
        if not query:
            await ctx.send(embed=embed_erro("Use: `!buscar <título ou autor>`\nExemplo: `!buscar Harry Potter`"))
            return
        msg = await ctx.send("🔍 Buscando...")
        await _executar_busca(ctx, query, is_slash=False)
        await msg.delete()

    @commands.command(name="ajuda", aliases=["help", "h"])
    async def ajuda_prefix(self, ctx: commands.Context):
        """📚 Lista todos os comandos"""
        embed = discord.Embed(
            title="📚 BookBot — Comandos",
            description="Use `/` para slash commands ou `!` para comandos de texto.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="🔍 Busca", value="`!buscar <livro>` — Pesquisa livros\n`!livro <título>` — Detalhes de um livro", inline=False)
        embed.add_field(name="📚 Estante", value="`/estante` — Sua biblioteca pessoal", inline=False)
        embed.add_field(name="❤️ Wishlist", value="`/desejo` — Lista de desejos", inline=False)
        embed.add_field(name="🤖 IA", value="`/recomendar` — Recomendações personalizadas", inline=False)
        embed.add_field(name="⚙️ Perfil", value="`/configurar` — Configura seu perfil\n`/perfil` — Ver seu perfil", inline=False)
        embed.set_footer(text="BookBot 📚 • Feito com ❤️ para amantes de livros")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Busca(bot))
