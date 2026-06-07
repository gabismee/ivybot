import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_config, salvar_config
from utils.embeds import CORES, FOOTER, embed_sucesso, embed_erro

DEFAULT_MSG = "📖 Um novo capítulo começou! Bem-vindo(a), {user}, à biblioteca do {server}."
DEFAULT_GIF = "attachment://welcome_default.png"
DEFAULT_COLOR = "#CDB4DB"

def _hex_to_color(value: str):
    try:
        value = (value or DEFAULT_COLOR).strip().replace('#','')
        if len(value) != 6:
            return CORES['roxo']
        return discord.Color(int(value, 16))
    except Exception:
        return CORES['roxo']

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_welcome(self, member: discord.Member):
        cfg = get_config(member.guild.id)
        canal_id = cfg.get('canal_boasvindas') or cfg.get('canal_clube')
        canal = member.guild.get_channel(canal_id) if canal_id else None
        if not canal:
            return
        msg = cfg.get('boasvindas_msg') or DEFAULT_MSG
        msg = msg.replace('{user}', member.mention).replace('{server}', member.guild.name)
        gif = cfg.get('boasvindas_gif') or ''
        cor = _hex_to_color(cfg.get('boasvindas_cor') or DEFAULT_COLOR)
        embed = discord.Embed(title=f"🌷 Bem-vindo(a) ao {member.guild.name}!", description=msg, color=cor)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=FOOTER)
        file = None
        if gif:
            embed.set_image(url=gif)
        else:
            file = discord.File('assets/welcome_default.png', filename='welcome_default.png')
            embed.set_image(url='attachment://welcome_default.png')
        try:
            if file:
                await canal.send(content=member.mention, embed=embed, file=file)
            else:
                await canal.send(content=member.mention, embed=embed)
        except Exception:
            pass

    welcome_group = app_commands.Group(name='boasvindas', description='🌷 Configura as boas-vindas do servidor', default_permissions=discord.Permissions(manage_guild=True))

    @welcome_group.command(name='canal', description='Define o canal de boas-vindas')
    async def set_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        salvar_config(interaction.guild_id, 'canal_boasvindas', canal.id)
        await interaction.response.send_message(embed=embed_sucesso(f'Canal de boas-vindas definido para {canal.mention}.'), ephemeral=True)

    @welcome_group.command(name='mensagem', description='Define a mensagem. Use {user} e {server}.')
    async def set_msg(self, interaction: discord.Interaction, mensagem: str):
        salvar_config(interaction.guild_id, 'boasvindas_msg', mensagem[:900])
        await interaction.response.send_message(embed=embed_sucesso('Mensagem de boas-vindas atualizada.'), ephemeral=True)

    @welcome_group.command(name='gif', description='Define o GIF/imagem de boas-vindas por URL')
    async def set_gif(self, interaction: discord.Interaction, url: str):
        salvar_config(interaction.guild_id, 'boasvindas_gif', url[:500])
        await interaction.response.send_message(embed=embed_sucesso('GIF/imagem de boas-vindas atualizado.'), ephemeral=True)

    @welcome_group.command(name='cor', description='Define a cor do embed em hexadecimal. Ex: #CDB4DB')
    async def set_cor(self, interaction: discord.Interaction, cor: str):
        if not cor.startswith('#') or len(cor) != 7:
            return await interaction.response.send_message(embed=embed_erro('Use uma cor no formato `#CDB4DB`.'), ephemeral=True)
        salvar_config(interaction.guild_id, 'boasvindas_cor', cor)
        await interaction.response.send_message(embed=embed_sucesso(f'Cor definida para `{cor}`.'), ephemeral=True)

    @welcome_group.command(name='testar', description='Testa a mensagem de boas-vindas')
    async def testar(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embed_sucesso('Enviando teste no canal configurado...'), ephemeral=True)
        await self.send_welcome(interaction.user)

    @commands.group(name='boasvindas', invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def boasvindas_prefix(self, ctx):
        await ctx.send('Use: `!boasvindas canal #canal`, `!boasvindas mensagem ...`, `!boasvindas gif <url>`, `!boasvindas cor #CDB4DB`, `!boasvindas testar`.')

    @boasvindas_prefix.command(name='canal')
    @commands.has_permissions(manage_guild=True)
    async def bw_canal(self, ctx, canal: discord.TextChannel):
        salvar_config(ctx.guild.id, 'canal_boasvindas', canal.id)
        await ctx.send(embed=embed_sucesso(f'Canal de boas-vindas definido para {canal.mention}.'))

    @boasvindas_prefix.command(name='mensagem')
    @commands.has_permissions(manage_guild=True)
    async def bw_msg(self, ctx, *, mensagem: str):
        salvar_config(ctx.guild.id, 'boasvindas_msg', mensagem[:900])
        await ctx.send(embed=embed_sucesso('Mensagem de boas-vindas atualizada.'))

    @boasvindas_prefix.command(name='gif')
    @commands.has_permissions(manage_guild=True)
    async def bw_gif(self, ctx, *, url: str):
        salvar_config(ctx.guild.id, 'boasvindas_gif', url[:500])
        await ctx.send(embed=embed_sucesso('GIF/imagem de boas-vindas atualizado.'))

    @boasvindas_prefix.command(name='cor')
    @commands.has_permissions(manage_guild=True)
    async def bw_cor(self, ctx, cor: str):
        salvar_config(ctx.guild.id, 'boasvindas_cor', cor)
        await ctx.send(embed=embed_sucesso(f'Cor definida para `{cor}`.'))

    @boasvindas_prefix.command(name='testar')
    @commands.has_permissions(manage_guild=True)
    async def bw_testar(self, ctx):
        await self.send_welcome(ctx.author)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
