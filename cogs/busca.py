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
        self.escolha = None

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

class Busca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="buscar", description="🔍 Pesquisa um livro pelo título, autor ou ISBN")
    @app_commands.describe(
        query="Título, autor, ISBN ou palavras-chave",
        formato="Filtrar por formato (opcional)"
    )
    @app_commands.choices(formato=[
        app_commands.Choice(name="Todos", value="todos"),
        app_commands.Choice(name="📚 Físico", value="fisico"),
        app_commands.Choice(name="📱 Ebook", value="ebook"),
        app_commands.Choice(name="🎧 Audiobook", value="audio"),
    ])
    async def buscar(self, interaction: discord.Interaction, query: str, formato: str = "todos"):
        await interaction.response.defer()

        resultados = await buscar_livros(query, max_results=8)

        if not resultados:
            await interaction.followup.send(embed=embed_erro(
                f"Nenhum livro encontrado para **{query}**.\nTente outro título ou autor."
            ))
            return

        if len(resultados) == 1:
            livro = resultados[0]
            links = gerar_links_compra(livro)
            embed = embed_livro(livro, links)
            view  = BotaoWishlist(livro)
            await interaction.followup.send(embed=embed, view=view)
        else:
            embed = discord.Embed(
                title=f"🔍 Resultados para: {query}",
                description=f"Encontrei **{len(resultados)}** livros. Escolha um abaixo:",
                color=discord.Color.blurple()
            )
            view = SeletorLivro(resultados)
            await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="livro", description="📚 Exibe detalhes completos de um livro")
    @app_commands.describe(titulo="Título do livro")
    async def livro(self, interaction: discord.Interaction, titulo: str):
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

async def setup(bot):
    await bot.add_cog(Busca(bot))
