import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros
from utils.embeds import embed_erro, embed_sucesso
from utils.db import get_db, get_config

class Clube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    clube = app_commands.Group(name="clube", description="📖 Clube do Livro do servidor")

    def _clube_ativo(self, guild_id: int) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM clube_livros WHERE guild_id = ? AND ativo = 1 ORDER BY iniciado DESC LIMIT 1",
                (guild_id,)
            ).fetchone()
            return dict(row) if row else None

    @clube.command(name="criar", description="Cria um clube do livro no servidor")
    @app_commands.describe(titulo="Título do livro para o clube")
    @app_commands.default_permissions(manage_guild=True)
    async def criar(self, interaction: discord.Interaction, titulo: str):
        await interaction.response.defer()
        atual = self._clube_ativo(interaction.guild_id)
        if atual:
            await interaction.followup.send(embed=embed_erro(
                f"Já existe um clube ativo: **{atual['titulo']}**\n"
                "Use `/clube encerrar` antes de criar um novo."
            ))
            return

        resultados = await buscar_livros(titulo, 1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return

        livro = resultados[0]
        with get_db() as conn:
            conn.execute(
                "INSERT INTO clube_livros (guild_id, titulo, autor, isbn, capa_url) VALUES (?,?,?,?,?)",
                (interaction.guild_id, livro["titulo"], livro.get("autor",""),
                 livro.get("isbn",""), livro.get("capa_url",""))
            )

        embed = discord.Embed(
            title="📖 Clube do Livro Iniciado!",
            color=discord.Color.green()
        )
        embed.add_field(name="📚 Livro", value=livro["titulo"], inline=False)
        embed.add_field(name="✍️ Autor", value=livro.get("autor","—"), inline=True)
        if livro.get("paginas"):
            embed.add_field(name="📄 Páginas", value=str(livro["paginas"]), inline=True)
        if livro.get("capa_url"):
            embed.set_thumbnail(url=livro["capa_url"])
        embed.add_field(
            name="📋 Comandos disponíveis",
            value="`/clube progresso` — Atualizar sua página\n"
                  "`/clube ranking` — Ver progresso do grupo\n"
                  "`/clube encerrar` — Encerrar o clube",
            inline=False
        )
        embed.set_footer(text="Boa leitura a todos! 📚")
        await interaction.followup.send(embed=embed)

    @clube.command(name="status", description="Exibe o livro atual do clube")
    async def status(self, interaction: discord.Interaction):
        atual = self._clube_ativo(interaction.guild_id)
        if not atual:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum clube ativo. Use `/clube criar` para começar!"),
                ephemeral=True
            )
            return

        with get_db() as conn:
            membros = conn.execute(
                "SELECT COUNT(*) as n FROM clube_progresso WHERE clube_id = ?", (atual["id"],)
            ).fetchone()["n"]
            progresso_medio = conn.execute(
                "SELECT AVG(CASE WHEN total_paginas > 0 THEN CAST(pagina_atual AS REAL)/total_paginas ELSE 0 END) as m "
                "FROM clube_progresso WHERE clube_id = ?", (atual["id"],)
            ).fetchone()["m"] or 0

        embed = discord.Embed(title="📖 Clube do Livro", color=discord.Color.blurple())
        embed.add_field(name="📚 Livro",          value=atual["titulo"],     inline=False)
        embed.add_field(name="✍️ Autor",          value=atual.get("autor","—"), inline=True)
        embed.add_field(name="👥 Participantes",  value=str(membros),        inline=True)
        embed.add_field(name="📊 Progresso Médio",value=f"{progresso_medio*100:.0f}%", inline=True)
        embed.add_field(name="📅 Iniciado em",    value=atual["iniciado"][:10], inline=True)
        if atual.get("capa_url"):
            embed.set_thumbnail(url=atual["capa_url"])
        await interaction.response.send_message(embed=embed)

    @clube.command(name="progresso", description="Atualiza sua página atual no livro do clube")
    @app_commands.describe(pagina="Página que você está", total="Total de páginas (opcional)")
    async def progresso(self, interaction: discord.Interaction,
                        pagina: int, total: int = 0):
        atual = self._clube_ativo(interaction.guild_id)
        if not atual:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum clube ativo no momento."), ephemeral=True
            )
            return

        with get_db() as conn:
            conn.execute("""
                INSERT INTO clube_progresso (clube_id, user_id, pagina_atual, total_paginas)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clube_id, user_id) DO UPDATE SET
                    pagina_atual=excluded.pagina_atual,
                    total_paginas=CASE WHEN excluded.total_paginas > 0
                        THEN excluded.total_paginas ELSE total_paginas END,
                    atualizado=datetime('now')
            """, (atual["id"], interaction.user.id, pagina, total))

        pct = f" ({pagina}/{total} — {pagina/total*100:.0f}%)" if total > 0 else ""
        await interaction.response.send_message(
            embed=embed_sucesso(f"Progresso atualizado! Você está na página **{pagina}**{pct}"),
            ephemeral=True
        )

    @clube.command(name="ranking", description="Ranking de progresso do clube")
    async def ranking(self, interaction: discord.Interaction):
        atual = self._clube_ativo(interaction.guild_id)
        if not atual:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum clube ativo."), ephemeral=True
            )
            return

        with get_db() as conn:
            rows = conn.execute("""
                SELECT user_id, pagina_atual, total_paginas
                FROM clube_progresso WHERE clube_id = ?
                ORDER BY pagina_atual DESC LIMIT 10
            """, (atual["id"],)).fetchall()

        if not rows:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum membro atualizou o progresso ainda."), ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🏆 Ranking do Clube — {atual['titulo'][:40]}",
            color=discord.Color.gold()
        )
        medalhas = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        for i, row in enumerate(rows):
            user = self.bot.get_user(row["user_id"])
            nome = user.display_name if user else f"Usuário {row['user_id']}"
            total = row["total_paginas"]
            pg    = row["pagina_atual"]
            pct   = f" ({pg/total*100:.0f}%)" if total > 0 else ""
            embed.add_field(
                name=f"{medalhas[i]} {nome}",
                value=f"Página **{pg}**{pct}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @clube.command(name="votar", description="Vote no próximo livro do clube")
    @app_commands.describe(titulo="Título que você quer sugerir/votar")
    async def votar(self, interaction: discord.Interaction, titulo: str):
        await interaction.response.defer(ephemeral=True)
        resultados = await buscar_livros(titulo, 1)
        if not resultados:
            await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
            return

        livro = resultados[0]
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO clube_votos (guild_id, isbn, titulo, user_id) VALUES (?,?,?,?)",
                    (interaction.guild_id, livro.get("isbn",""), livro["titulo"], interaction.user.id)
                )
            await interaction.followup.send(embed=embed_sucesso(
                f"Voto registrado em **{livro['titulo']}**!"
            ))
        except Exception:
            await interaction.followup.send(embed=embed_erro("Você já votou nesta rodada!"))

    @clube.command(name="votos", description="Exibe a contagem de votos para o próximo livro")
    async def votos(self, interaction: discord.Interaction):
        with get_db() as conn:
            rows = conn.execute("""
                SELECT titulo, isbn, COUNT(*) as votos
                FROM clube_votos WHERE guild_id = ?
                GROUP BY isbn ORDER BY votos DESC LIMIT 10
            """, (interaction.guild_id,)).fetchall()

        if not rows:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum voto ainda. Use `/clube votar` para sugerir um livro!"),
                ephemeral=True
            )
            return

        embed = discord.Embed(title="🗳️ Votos — Próximo Livro do Clube", color=discord.Color.purple())
        medalhas = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4, 11)]
        for i, row in enumerate(rows):
            embed.add_field(
                name=f"{medalhas[i]} {row['titulo'][:45]}",
                value=f"🗳️ {row['votos']} voto(s)",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @clube.command(name="encerrar", description="Encerra o clube do livro atual")
    @app_commands.default_permissions(manage_guild=True)
    async def encerrar(self, interaction: discord.Interaction):
        atual = self._clube_ativo(interaction.guild_id)
        if not atual:
            await interaction.response.send_message(
                embed=embed_erro("Nenhum clube ativo para encerrar."), ephemeral=True
            )
            return

        with get_db() as conn:
            conn.execute(
                "UPDATE clube_livros SET ativo=0, encerrado=datetime('now') WHERE id=?",
                (atual["id"],)
            )
        await interaction.response.send_message(embed=embed_sucesso(
            f"Clube do livro **{atual['titulo']}** encerrado!\n"
            "Use `/clube criar` para iniciar um novo."
        ))

async def setup(bot):
    await bot.add_cog(Clube(bot))
