import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import CORES, FOOTER, embed_sucesso, embed_erro
from cogs.painel import parse_color


class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    embed_group = app_commands.Group(
        name="embed",
        description="🎨 Cria embeds personalizados",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @embed_group.command(name="criar", description="Cria um embed personalizado em um canal")
    @app_commands.describe(
        canal="Canal onde o embed será enviado",
        titulo="Título do embed",
        descricao="Texto principal do embed",
        cor="Cor em hexadecimal ou nome pastel. Ex: #D8B4FE ou rosa",
        imagem="URL de imagem/GIF grande",
        thumbnail="URL da imagem pequena no canto",
        footer="Texto do rodapé",
    )
    async def criar_slash(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        titulo: str = "Mensagem da Ivy",
        descricao: str = "Escreva sua mensagem aqui.",
        cor: str = "#D8B4FE",
        imagem: str | None = None,
        thumbnail: str | None = None,
        footer: str | None = None,
    ):
        canal = canal or interaction.channel
        embed = self.build_embed(titulo, descricao, cor, imagem, thumbnail, footer)
        await canal.send(embed=embed)
        await interaction.response.send_message(embed=embed_sucesso(f"Embed enviado em {canal.mention}."), ephemeral=True)

    @embed_group.command(name="exemplo", description="Mostra um exemplo de uso do comando !embed criar")
    async def exemplo_slash(self, interaction: discord.Interaction):
        texto = (
            "Use assim:\n"
            "`!embed criar #canal | Título | Descrição | #D8B4FE | imagem_url | thumbnail_url | footer`\n\n"
            "Ou use `/embed criar` para preencher os campos pelo Discord."
        )
        await interaction.response.send_message(embed=embed_sucesso(texto), ephemeral=True)

    @commands.group(name="embed", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def embed_prefix(self, ctx: commands.Context):
        await ctx.send(embed=embed_erro("Use `!embed criar #canal | título | descrição | #D8B4FE | imagem | thumbnail | footer`."))

    @embed_prefix.command(name="criar")
    @commands.has_permissions(manage_guild=True)
    async def criar_prefix(self, ctx: commands.Context, *, args: str = ""):
        canal = ctx.channel
        if ctx.message.channel_mentions:
            canal = ctx.message.channel_mentions[0]
            args = args.replace(canal.mention, "", 1).strip()

        partes = [p.strip() for p in args.split("|")]
        if len(partes) < 2:
            return await ctx.send(embed=embed_erro(
                "Formato: `!embed criar #canal | Título | Descrição | #D8B4FE | imagem_url | thumbnail_url | footer`"
            ))

        titulo = partes[0] or "Mensagem da Ivy"
        descricao = partes[1] or " "
        cor = partes[2] if len(partes) > 2 and partes[2] else "#D8B4FE"
        imagem = partes[3] if len(partes) > 3 and partes[3] else None
        thumbnail = partes[4] if len(partes) > 4 and partes[4] else None
        footer = partes[5] if len(partes) > 5 and partes[5] else None

        embed = self.build_embed(titulo, descricao, cor, imagem, thumbnail, footer)
        await canal.send(embed=embed)
        await ctx.send(embed=embed_sucesso(f"Embed enviado em {canal.mention}."))

    @commands.command(name="embedexemplo")
    @commands.has_permissions(manage_guild=True)
    async def embed_exemplo_prefix(self, ctx: commands.Context):
        texto = (
            "Use assim:\n"
            "`!embed criar #canal | Título | Descrição | #D8B4FE | imagem_url | thumbnail_url | footer`\n\n"
            "Exemplo:\n"
            "`!embed criar #comandos | 📖 Central de Comandos | Use !ajuda para ver tudo. | #D8B4FE`"
        )
        await ctx.send(embed=embed_sucesso(texto))

    def build_embed(self, titulo: str, descricao: str, cor: str, imagem: str | None, thumbnail: str | None, footer: str | None):
        embed = discord.Embed(
            title=titulo[:256],
            description=descricao[:4000],
            color=parse_color(cor),
        )
        if imagem:
            embed.set_image(url=imagem)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=(footer[:2048] if footer else FOOTER))
        return embed


async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
