import discord
from discord import app_commands
from discord.ext import commands
from utils.db import salvar_config, get_config
from utils.embeds import embed_sucesso, embed_erro

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    config_cmd = app_commands.Group(
        name="config",
        description="⚙️ Configurações do bot no servidor",
        default_permissions=discord.Permissions(manage_guild=True)
    )

    @config_cmd.command(name="canal-promocoes", description="Define o canal de promoções automáticas")
    @app_commands.describe(canal="Canal onde as promoções serão postadas")
    async def canal_promocoes(self, interaction: discord.Interaction, canal: discord.TextChannel):
        salvar_config(interaction.guild_id, "canal_promocoes", canal.id)
        await interaction.response.send_message(
            embed=embed_sucesso(f"Canal de promoções definido para {canal.mention}!"),
            ephemeral=True
        )

    @config_cmd.command(name="canal-ebooks", description="Define o canal de ebooks gratuitos")
    @app_commands.describe(canal="Canal para ebooks gratuitos")
    async def canal_ebooks(self, interaction: discord.Interaction, canal: discord.TextChannel):
        salvar_config(interaction.guild_id, "canal_ebooks", canal.id)
        await interaction.response.send_message(
            embed=embed_sucesso(f"Canal de ebooks definido para {canal.mention}!"),
            ephemeral=True
        )

    @config_cmd.command(name="canal-clube", description="Define o canal do clube do livro")
    @app_commands.describe(canal="Canal para o clube do livro")
    async def canal_clube(self, interaction: discord.Interaction, canal: discord.TextChannel):
        salvar_config(interaction.guild_id, "canal_clube", canal.id)
        await interaction.response.send_message(
            embed=embed_sucesso(f"Canal do clube definido para {canal.mention}!"),
            ephemeral=True
        )

    @config_cmd.command(name="ver", description="Mostra as configurações atuais do servidor")
    async def ver_config(self, interaction: discord.Interaction):
        cfg = get_config(interaction.guild_id)

        embed = discord.Embed(title="⚙️ Configurações do Servidor", color=discord.Color.blurple())

        def canal_str(cid):
            if not cid:
                return "❌ Não configurado"
            ch = interaction.guild.get_channel(cid)
            return ch.mention if ch else f"ID: {cid} (não encontrado)"

        embed.add_field(name="🔥 Canal Promoções", value=canal_str(cfg.get("canal_promocoes")), inline=False)
        embed.add_field(name="📱 Canal Ebooks",    value=canal_str(cfg.get("canal_ebooks")),    inline=False)
        embed.add_field(name="📖 Canal Clube",     value=canal_str(cfg.get("canal_clube")),     inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ajuda", description="📋 Lista todos os comandos disponíveis")
    async def ajuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Ivy — Comandos",
            description="Sua bot literária gratuita no Discord!",
            color=discord.Color.blurple()
        )
        comandos = {
            "🔍 Pesquisa": [
                "`/buscar [query]` — Pesquisa livros",
                "`/livro [título]` — Detalhes de um livro",
                "`/encontrar [tema]` — Livros por tema ou objetivo",
                "`/similar [título]` — Livros similares",
            ],
            "📌 Quero Ler": [
                "`/queroler adicionar [livro]` — Adiciona em Quero Ler",
                "`/queroler remover` — Remove de Quero Ler",
                "`/queroler listar` — Ver sua lista",
                "`/queroler ver` — Ver detalhes de um item",
            ],
            "🔔 Alertas": [
                "`/alerta [livro] [preço]` — Alerta de preço",
                "`/meus-alertas` — Ver alertas ativos",
            ],
            "📚 Estante": [
                "`/estante adicionar [livro]` — Adiciona livro",
                "`/estante ver` — Ver sua estante",
                "`/estante stats` — Estatísticas de leitura",
                "`/avaliar [livro] [nota]` — Avalia um livro",
            ],
            "🤖 IA": [
                "`/recomendar` — Recomendações personalizadas",
                "`/encontrar [tema]` — Buscar por objetivo",
            ],
            "📖 Clube": [
                "`/clube criar [livro]` — Inicia clube (admin)",
                "`/clube status` — Ver livro atual",
                "`/clube progresso [página]` — Atualizar progresso",
                "`/clube ranking` — Ranking do grupo",
                "`/clube votar [livro]` — Votar no próximo livro",
                "`/clube votos` — Ver votos",
            ],
            "🏆 Rankings": [
                "`/ranking` — Rankings da comunidade",
                "`/top-promocoes` — Maiores descontos",
            ],
            "🔥 Promoções": [
                "`/promocoes` — Ver livros em português por preço",
                "`/gratuitos` — Livros gratuitos",
            ],
            "👤 Perfil": [
                "`/configurar` — Configura seu perfil",
                "`/perfil` — Ver perfil visual",
                "`/perfil-frase` — Personaliza frase",
                "`/perfil-wallpaper` — Personaliza wallpaper",
            ],
            "⚙️ Admin": [
                "`/config canal-promocoes` — Define canal",
                "`/config canal-clube` — Canal do clube",
                "`/config ver` — Ver configurações",
            ],
        }
        for categoria, cmds in comandos.items():
            embed.add_field(name=categoria, value="\n".join(cmds), inline=False)
        embed.set_footer(text="Ivy 📚 • Feito pela Gabi 🌷")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="cor", description="🎨 Escolha a cor do seu nome no servidor")
    @app_commands.describe(cor="Cor em hexadecimal. Ex: #CDB4DB")
    async def cor_nome(self, interaction: discord.Interaction, cor: str):
        if not interaction.guild:
            return await interaction.response.send_message(embed=embed_erro("Use esse comando em um servidor."), ephemeral=True)
        if not cor.startswith('#') or len(cor) != 7:
            return await interaction.response.send_message(embed=embed_erro("Use uma cor no formato `#CDB4DB`."), ephemeral=True)
        try:
            color = discord.Color(int(cor.replace('#',''), 16))
        except Exception:
            return await interaction.response.send_message(embed=embed_erro("Cor inválida."), ephemeral=True)
        role_name = f"Ivy Cor {cor.upper()}"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role is None:
            role = await interaction.guild.create_role(name=role_name, color=color, reason="Cor personalizada da Ivy")
        # remove cores antigas da Ivy
        antigas = [r for r in interaction.user.roles if r.name.startswith('Ivy Cor ')]
        if antigas:
            await interaction.user.remove_roles(*antigas, reason="Troca de cor da Ivy")
        await interaction.user.add_roles(role, reason="Cor personalizada da Ivy")
        await interaction.response.send_message(embed=embed_sucesso(f"Sua cor foi definida como `{cor}`. Se não aparecer, coloque o cargo da Ivy acima dos cargos coloridos."), ephemeral=True)

    @commands.command(name='cor')
    async def cor_nome_prefix(self, ctx, cor: str=None):
        if not cor or not cor.startswith('#') or len(cor) != 7:
            return await ctx.send(embed=embed_erro("Use: `!cor #CDB4DB`."))
        try:
            color = discord.Color(int(cor.replace('#',''), 16))
        except Exception:
            return await ctx.send(embed=embed_erro("Cor inválida."))
        role_name = f"Ivy Cor {cor.upper()}"
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            role = await ctx.guild.create_role(name=role_name, color=color, reason="Cor personalizada da Ivy")
        antigas = [r for r in ctx.author.roles if r.name.startswith('Ivy Cor ')]
        if antigas:
            await ctx.author.remove_roles(*antigas, reason="Troca de cor da Ivy")
        await ctx.author.add_roles(role, reason="Cor personalizada da Ivy")
        await ctx.send(embed=embed_sucesso(f"Sua cor foi definida como `{cor}`. Se não aparecer, coloque o cargo da Ivy acima dos cargos coloridos."))

async def setup(bot):
    await bot.add_cog(Admin(bot))
