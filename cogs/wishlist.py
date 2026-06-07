import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros, gerar_links_compra
from utils.embeds import embed_wishlist, embed_livro, embed_erro, embed_sucesso
from utils.db import get_wishlist, adicionar_wishlist, remover_wishlist

class RemoverView(discord.ui.View):
    def __init__(self, items: list):
        super().__init__(timeout=60)
        self.items = items

        opcoes = [
            discord.SelectOption(
                label=item["titulo"][:100],
                description=item.get("autor","")[:50],
                value=item["isbn"] or item["titulo"],
                emoji="🗑️"
            )
            for item in items[:25]
        ]
        select = discord.ui.Select(placeholder="Escolha um livro para remover...", options=opcoes)
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        isbn = interaction.data["values"][0]
        titulo = next((i["titulo"] for i in self.items if (i["isbn"] or i["titulo"]) == isbn), isbn)
        ok = remover_wishlist(interaction.user.id, isbn)
        if ok:
            await interaction.response.send_message(
                embed=embed_sucesso(f"**{titulo}** removido da sua wishlist."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embed_erro("Não foi possível remover."), ephemeral=True
            )

class Wishlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    desejo = app_commands.Group(name="desejo", description="❤️ Gerencia sua lista de desejos")

    @desejo.command(name="adicionar", description="Adiciona um livro à sua wishlist")
    @app_commands.describe(titulo="Título do livro", preco_alvo="Preço desejado para alerta (ex: 29.90)")
    async def adicionar(self, interaction: discord.Interaction, titulo: str, preco_alvo: float = None):
        await interaction.response.defer(ephemeral=True)
        resultados = await buscar_livros(titulo, max_results=3)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return

        livro = resultados[0]
        ok = adicionar_wishlist(interaction.user.id, livro, preco_alvo)
        if ok:
            msg = f"✅ **{livro['titulo']}** adicionado à wishlist!"
            if preco_alvo:
                msg += f"\n🔔 Você será avisado quando o preço cair abaixo de **R$ {preco_alvo:.2f}**"
            await interaction.followup.send(embed=embed_sucesso(msg))
        else:
            await interaction.followup.send(embed=embed_erro("Livro já está na sua wishlist."))

    @desejo.command(name="remover", description="Remove um livro da sua wishlist")
    async def remover(self, interaction: discord.Interaction):
        items = get_wishlist(interaction.user.id)
        if not items:
            await interaction.response.send_message(
                embed=embed_erro("Sua wishlist está vazia!"), ephemeral=True
            )
            return
        view = RemoverView(items)
        await interaction.response.send_message(
            "Escolha qual livro remover:", view=view, ephemeral=True
        )

    @desejo.command(name="listar", description="Exibe sua lista de desejos")
    async def listar(self, interaction: discord.Interaction):
        items = get_wishlist(interaction.user.id)
        embed = embed_wishlist(items, interaction.user.display_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @desejo.command(name="ver", description="Ver um livro específico da sua wishlist")
    async def ver(self, interaction: discord.Interaction):
        items = get_wishlist(interaction.user.id)
        if not items:
            await interaction.response.send_message(
                embed=embed_erro("Sua wishlist está vazia!"), ephemeral=True
            )
            return
        opcoes = [
            discord.SelectOption(
                label=item["titulo"][:100],
                description=item.get("autor","")[:50],
                value=str(i),
                emoji="📚"
            ) for i, item in enumerate(items[:25])
        ]

        class VerView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                select = discord.ui.Select(placeholder="Escolha um livro...", options=opcoes)
                select.callback = self.on_select
                self.add_item(select)

            async def on_select(self2, inter: discord.Interaction):
                idx  = int(inter.data["values"][0])
                item = items[idx]
                livro = {
                    "titulo":   item["titulo"],
                    "autor":    item.get("autor",""),
                    "isbn":     item.get("isbn",""),
                    "capa_url": item.get("capa_url",""),
                }
                links = gerar_links_compra(livro)
                embed = embed_livro(livro, links)
                await inter.response.edit_message(embed=embed, view=None)

        await interaction.response.send_message("Escolha um livro:", view=VerView(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Wishlist(bot))
