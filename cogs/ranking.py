import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import embed_ranking
from utils.db import get_ranking_wishlist, get_ranking_avaliacoes

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ranking", description="🏆 Rankings da comunidade")
    @app_commands.describe(tipo="Tipo de ranking")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="❤️ Mais desejados", value="wishlist"),
        app_commands.Choice(name="⭐ Mais bem avaliados", value="avaliacoes"),
    ])
    async def ranking(self, interaction: discord.Interaction, tipo: str = "wishlist"):
        if tipo == "wishlist":
            itens = get_ranking_wishlist(10)
            titulo = "Livros Mais Desejados da Comunidade"
        else:
            itens = get_ranking_avaliacoes(10)
            titulo = "Livros Mais Bem Avaliados"

        if not itens:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Ainda não há dados suficientes. Comece adicionando livros!",
                    color=discord.Color.orange()
                )
            )
            return

        embed = embed_ranking(titulo, itens, tipo)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top-promocoes", description="🔥 Maiores descontos da semana")
    async def top_promocoes(self, interaction: discord.Interaction):
        from utils.db import get_db
        with get_db() as conn:
            rows = conn.execute("""
                SELECT h.isbn, h.loja, h.preco, h.url,
                    (SELECT MAX(preco) FROM historico_precos WHERE isbn=h.isbn) as preco_max
                FROM historico_precos h
                WHERE h.registrado > datetime('now', '-7 days')
                GROUP BY h.isbn
                HAVING preco_max > h.preco
                ORDER BY (preco_max - h.preco) / preco_max DESC
                LIMIT 10
            """).fetchall()

        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Nenhuma promoção registrada ainda esta semana.",
                    color=discord.Color.orange()
                )
            )
            return

        embed = discord.Embed(title="🔥 Top Promoções da Semana", color=discord.Color.red())
        for i, row in enumerate(rows, 1):
            desconto = int((row["preco_max"] - row["preco"]) / row["preco_max"] * 100)
            embed.add_field(
                name=f"{i}. ISBN: {row['isbn'][:13]}",
                value=f"🏬 {row['loja']}\n💸 **{desconto}% OFF** — R$ {row['preco']:.2f}\n[Ver]({row['url']})",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ranking(bot))
