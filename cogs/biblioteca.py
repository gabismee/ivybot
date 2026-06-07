import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros
from utils.embeds import embed_biblioteca, embed_perfil, embed_erro, embed_sucesso, estrelas
from utils.db import (get_biblioteca, atualizar_biblioteca, avaliar_livro,
                      get_stats_usuario, get_perfil)

STATUS_CHOICES = [
    app_commands.Choice(name="📌 Quero Ler",   value="quero_ler"),
    app_commands.Choice(name="📖 Lendo",        value="lendo"),
    app_commands.Choice(name="✅ Lido",         value="lido"),
    app_commands.Choice(name="❤️ Favorito",    value="favorito"),
    app_commands.Choice(name="🗑️ Abandonado",  value="abandonado"),
]

class Biblioteca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    estante = app_commands.Group(name="estante", description="📚 Gerencia sua biblioteca pessoal")

    @estante.command(name="adicionar", description="Adiciona um livro à sua estante")
    @app_commands.describe(titulo="Título do livro", status="Status de leitura")
    @app_commands.choices(status=STATUS_CHOICES)
    async def adicionar(self, interaction: discord.Interaction, titulo: str,
                        status: str = "quero_ler"):
        await interaction.response.defer(ephemeral=True)
        resultados = await buscar_livros(titulo, 1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return
        livro = resultados[0]
        atualizar_biblioteca(interaction.user.id, livro, status)
        labels = {
            "quero_ler": "📌 Quero Ler", "lendo": "📖 Lendo",
            "lido": "✅ Lido", "favorito": "❤️ Favorito", "abandonado": "🗑️ Abandonado"
        }
        await interaction.followup.send(embed=embed_sucesso(
            f"**{livro['titulo']}** adicionado como **{labels.get(status, status)}**!"
        ))

    @estante.command(name="ver", description="Vê sua estante por status")
    @app_commands.describe(status="Filtrar por status (opcional)")
    @app_commands.choices(status=STATUS_CHOICES)
    async def ver(self, interaction: discord.Interaction, status: str = None):
        itens = get_biblioteca(interaction.user.id, status)
        label = status or "todos"
        embed = embed_biblioteca(itens, interaction.user.display_name, label)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @estante.command(name="stats", description="Estatísticas da sua leitura")
    async def stats(self, interaction: discord.Interaction):
        uid  = interaction.user.id
        todos = get_biblioteca(uid)
        contagem = {}
        for item in todos:
            s = item["status"]
            contagem[s] = contagem.get(s, 0) + 1

        embed = discord.Embed(
            title=f"📊 Estatísticas de {interaction.user.display_name}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📌 Quero Ler",   value=str(contagem.get("quero_ler", 0)),  inline=True)
        embed.add_field(name="📖 Lendo",        value=str(contagem.get("lendo", 0)),       inline=True)
        embed.add_field(name="✅ Lidos",        value=str(contagem.get("lido", 0)),        inline=True)
        embed.add_field(name="❤️ Favoritos",   value=str(contagem.get("favorito", 0)),    inline=True)
        embed.add_field(name="🗑️ Abandonados", value=str(contagem.get("abandonado", 0)),  inline=True)
        embed.add_field(name="📚 Total",        value=str(len(todos)),                     inline=True)

        stats = get_stats_usuario(uid)
        if stats.get("media_avaliacao"):
            embed.add_field(
                name="⭐ Média de Avaliações",
                value=f"{stats['media_avaliacao']}/5",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="avaliar", description="⭐ Avalia um livro que você leu")
    @app_commands.describe(
        titulo="Título do livro",
        estrelas_n="Nota de 1 a 5",
        comentario="Comentário opcional"
    )
    @app_commands.choices(estrelas_n=[
        app_commands.Choice(name="⭐ 1 estrela",      value=1),
        app_commands.Choice(name="⭐⭐ 2 estrelas",   value=2),
        app_commands.Choice(name="⭐⭐⭐ 3 estrelas", value=3),
        app_commands.Choice(name="⭐⭐⭐⭐ 4 estrelas",  value=4),
        app_commands.Choice(name="⭐⭐⭐⭐⭐ 5 estrelas", value=5),
    ])
    async def avaliar(self, interaction: discord.Interaction, titulo: str,
                      estrelas_n: int, comentario: str = ""):
        await interaction.response.defer(ephemeral=True)
        resultados = await buscar_livros(titulo, 1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return
        livro = resultados[0]
        avaliar_livro(interaction.user.id, livro, estrelas_n, comentario)

        embed = discord.Embed(
            title="⭐ Avaliação Registrada!",
            color=discord.Color.gold()
        )
        embed.add_field(name="📚 Livro",     value=livro["titulo"], inline=False)
        embed.add_field(name="⭐ Nota",      value=estrelas(estrelas_n),   inline=True)
        if comentario:
            embed.add_field(name="💬 Comentário", value=comentario, inline=False)
        if livro.get("capa_url"):
            embed.set_thumbnail(url=livro["capa_url"])
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="perfil", description="👤 Exibe seu perfil de leitor")
    @app_commands.describe(usuario="Ver perfil de outro usuário (opcional)")
    async def perfil_cmd(self, interaction: discord.Interaction,
                         usuario: discord.Member = None):
        alvo = usuario or interaction.user
        perfil = get_perfil(alvo.id)
        stats  = get_stats_usuario(alvo.id)

        if not perfil:
            if alvo == interaction.user:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="Você ainda não tem perfil! Use `/configurar` para criar.",
                        color=discord.Color.orange()
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=embed_erro(f"{alvo.display_name} ainda não configurou o perfil."),
                    ephemeral=True
                )
            return

        embed = embed_perfil(perfil, stats, alvo.display_name, str(alvo.display_avatar.url))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Biblioteca(bot))
