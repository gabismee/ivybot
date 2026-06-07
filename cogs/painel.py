import re
import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import CORES, FOOTER, embed_sucesso, embed_erro

PASTEL_LILAS = 0xD8B4FE

DEFAULT_ROLE_PANEL = [
    ("💖 Romance", 0xF8C8DC),
    ("🐉 Fantasia", 0xD8B4FE),
    ("🚀 Ficção Científica", 0xBDE0FE),
    ("👻 Terror", 0xD8DEE9),
    ("🔎 Mistério", 0xCDEAC0),
    ("📜 Clássicos", 0xFFF1B6),
    ("🎌 Mangás", 0xFFD6A5),
    ("❤️‍🩹 Drama", 0xF8C8DC),
    ("💸 Promoções", 0xFFF1B6),
    ("🎲 Quiz", 0xBDE0FE),
    ("📚 Clube do Livro", 0xCDEAC0),
    ("🌙 Frase do Dia", 0xD8B4FE),
    ("📢 Anúncios", 0xFFD6A5),
]

HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def parse_color(value: str | None, default: int = PASTEL_LILAS) -> discord.Color:
    if not value:
        return discord.Color(default)
    value = value.strip()
    if value.lower() in CORES:
        return CORES[value.lower()]
    if HEX_RE.match(value):
        return discord.Color(int(value.replace('#', ''), 16))
    return discord.Color(default)


def normalize_role_name(role_name: str) -> str:
    return role_name.strip()[:90]


class RolePanelView(discord.ui.View):
    def __init__(self, roles: list[tuple[str, int]] = DEFAULT_ROLE_PANEL):
        super().__init__(timeout=None)
        for index, (role_name, color) in enumerate(roles[:25]):
            label = role_name[:80]
            custom_id = f"ivy_role:{role_name}"
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=custom_id, row=index // 5)
            button.callback = self._make_callback(role_name, color)
            self.add_item(button)

    def _make_callback(self, role_name: str, color: int):
        async def callback(interaction: discord.Interaction):
            await toggle_role(interaction, role_name, color)
        return callback


async def get_or_create_role(guild: discord.Guild, role_name: str, color: int) -> discord.Role:
    role_name = normalize_role_name(role_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        return role
    return await guild.create_role(
        name=role_name,
        color=discord.Color(color),
        reason="Cargo criado pelo painel da Ivy",
        mentionable=False,
    )


async def toggle_role(interaction: discord.Interaction, role_name: str, color: int = PASTEL_LILAS):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Use isso dentro de um servidor.", ephemeral=True)

    if not interaction.guild.me.guild_permissions.manage_roles:
        return await interaction.response.send_message(
            "Eu preciso da permissão **Gerenciar cargos** pra fazer isso.", ephemeral=True
        )

    try:
        role = await get_or_create_role(interaction.guild, role_name, color)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "Não consegui criar o cargo. Meu cargo precisa ficar acima dos cargos que vou gerenciar.", ephemeral=True
        )

    if role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "Não consigo mexer nesse cargo porque ele está acima do meu cargo na hierarquia do Discord.", ephemeral=True
        )

    try:
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Cargo removido pelo painel da Ivy")
            msg = f"Removi o cargo **{role.name}** do seu perfil."
        else:
            await interaction.user.add_roles(role, reason="Cargo adicionado pelo painel da Ivy")
            msg = f"Adicionei o cargo **{role.name}** no seu perfil."
        await interaction.response.send_message(msg, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(
            "Não consegui alterar seu cargo. Confere se o cargo da Ivy está acima desse cargo.", ephemeral=True
        )


class Painel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id") if isinstance(interaction.data, dict) else None
        if not custom_id or not custom_id.startswith("ivy_role:"):
            return
        role_name = custom_id.split(":", 1)[1]
        color = dict(DEFAULT_ROLE_PANEL).get(role_name, PASTEL_LILAS)
        await toggle_role(interaction, role_name, color)

    painel_group = app_commands.Group(
        name="painel",
        description="📌 Cria painéis prontos da Ivy",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @painel_group.command(name="cargos", description="Cria um painel de cargos com botões")
    @app_commands.describe(
        canal="Canal onde o painel será enviado",
        titulo="Título do embed",
        descricao="Texto explicando os cargos",
        cor="Cor do embed. Ex: #D8B4FE",
        imagem="URL de imagem ou GIF para o embed",
    )
    async def painel_cargos_slash(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        titulo: str = "🌷 Escolha seus cargos!",
        descricao: str = "Clique nos botões abaixo para receber ou remover cargos do seu perfil.",
        cor: str = "#D8B4FE",
        imagem: str | None = None,
    ):
        canal = canal or interaction.channel
        embed = self._role_embed(titulo, descricao, cor, imagem)
        await canal.send(embed=embed, view=RolePanelView())
        await interaction.response.send_message(embed=embed_sucesso(f"Painel de cargos enviado em {canal.mention}."), ephemeral=True)

    @commands.group(name="painel", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def painel_prefix(self, ctx: commands.Context):
        await ctx.send(embed=embed_erro("Use `!painel cargos` para criar o painel de cargos."))

    @painel_prefix.command(name="cargos")
    @commands.has_permissions(manage_guild=True)
    async def painel_cargos_prefix(self, ctx: commands.Context, *, args: str = ""):
        """Uso: !painel cargos [#canal] | título | descrição | #D8B4FE | imagem_url"""
        canal = ctx.channel
        if ctx.message.channel_mentions:
            canal = ctx.message.channel_mentions[0]
            args = args.replace(canal.mention, "", 1).strip()
        partes = [p.strip() for p in args.split("|")]
        titulo = partes[0] if len(partes) > 0 and partes[0] else "🌷 Escolha seus cargos!"
        descricao = partes[1] if len(partes) > 1 and partes[1] else "Clique nos botões abaixo para receber ou remover cargos do seu perfil."
        cor = partes[2] if len(partes) > 2 and partes[2] else "#D8B4FE"
        imagem = partes[3] if len(partes) > 3 and partes[3] else None
        embed = self._role_embed(titulo, descricao, cor, imagem)
        await canal.send(embed=embed, view=RolePanelView())
        await ctx.send(embed=embed_sucesso(f"Painel de cargos enviado em {canal.mention}."))

    def _role_embed(self, titulo: str, descricao: str, cor: str, imagem: str | None) -> discord.Embed:
        cargos = "\n".join(f"• {name}" for name, _ in DEFAULT_ROLE_PANEL)
        embed = discord.Embed(
            title=titulo[:256],
            description=f"{descricao[:2500]}\n\n**Cargos disponíveis:**\n{cargos}",
            color=parse_color(cor),
        )
        if imagem:
            embed.set_image(url=imagem)
        embed.set_footer(text=FOOTER)
        return embed


async def setup(bot):
    await bot.add_cog(Painel(bot))
