import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros
from utils.embeds import embed_erro, embed_sucesso
from utils.db import get_wishlist, adicionar_wishlist

class Alertas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alerta", description="🔔 Cria alerta de preço para um livro")
    @app_commands.describe(
        livro="Título do livro",
        preco="Preço desejado (ex: 29.90)"
    )
    async def alerta(self, interaction: discord.Interaction, livro: str, preco: float):
        await interaction.response.defer(ephemeral=True)

        if preco <= 0:
            await interaction.followup.send(embed=embed_erro("O preço deve ser maior que zero."))
            return

        resultados = await buscar_livros(livro, max_results=1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{livro}** não encontrado."))
            return

        l = resultados[0]
        adicionar_wishlist(interaction.user.id, l, preco_alvo=preco)

        embed = discord.Embed(
            title="🔔 Alerta Criado!",
            color=discord.Color.green()
        )
        embed.add_field(name="📚 Livro",         value=l["titulo"],  inline=False)
        embed.add_field(name="✍️ Autor",         value=l.get("autor","—"), inline=True)
        embed.add_field(name="🎯 Preço Alvo",    value=f"R$ {preco:.2f}",  inline=True)
        embed.set_footer(text="Você receberá uma DM quando o preço baixar!")
        if l.get("capa_url"):
            embed.set_thumbnail(url=l["capa_url"])

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="meus-alertas", description="📋 Lista seus alertas de preço ativos")
    async def meus_alertas(self, interaction: discord.Interaction):
        items = get_wishlist(interaction.user.id)
        alertas = [i for i in items if i.get("preco_alvo")]

        if not alertas:
            await interaction.response.send_message(
                embed=embed_erro("Você não tem alertas ativos.\nUse `/alerta` para criar um!"),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🔔 Seus Alertas de Preço ({len(alertas)})",
            color=discord.Color.orange()
        )
        for item in alertas[:15]:
            embed.add_field(
                name=f"📚 {item['titulo'][:45]}",
                value=f"✍️ {item.get('autor','')}\n🎯 Alerta: **R$ {item['preco_alvo']:.2f}**",
                inline=True
            )
        embed.set_footer(text="Use /desejo remover para cancelar um alerta")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def verificar_alertas(self, isbn: str, preco_atual: float, loja: str, url: str):
        """Verifica e dispara alertas quando um preço cai — chamado pelo cog de promoções"""
        from utils.db import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM wishlist WHERE isbn = ? AND preco_alvo IS NOT NULL AND preco_alvo >= ?",
                (isbn, preco_atual)
            ).fetchall()

        for row in rows:
            user = self.bot.get_user(row["user_id"])
            if not user:
                try:
                    user = await self.bot.fetch_user(row["user_id"])
                except Exception:
                    continue
            try:
                embed = discord.Embed(
                    title="🔥 Alerta de Preço Disparado!",
                    description=f"**{row['titulo']}** atingiu seu preço alvo!",
                    color=discord.Color.red(),
                    url=url
                )
                embed.add_field(name="🎯 Seu alerta",    value=f"R$ {row['preco_alvo']:.2f}", inline=True)
                embed.add_field(name="✅ Preço atual",   value=f"**R$ {preco_atual:.2f}**",   inline=True)
                embed.add_field(name="🏬 Loja",         value=loja,                           inline=True)
                embed.add_field(name="🔗 Comprar",      value=f"[Clique aqui]({url})",        inline=False)
                embed.set_footer(text="BookBot 📚")
                if row.get("capa_url"):
                    embed.set_thumbnail(url=row["capa_url"])
                await user.send(embed=embed)
            except discord.Forbidden:
                pass  # DMs desativadas

async def setup(bot):
    await bot.add_cog(Alertas(bot))
