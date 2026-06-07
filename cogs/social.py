import discord
from discord import app_commands
from discord.ext import commands
from utils.db import registrar_interacao, ja_interagiu_hoje, listar_interacoes, add_xp, ensure_perfil
from utils.embeds import embed_erro, embed_sucesso, FOOTER

class Social(commands.Cog):
    def __init__(self, bot): self.bot=bot

    async def _dar(self, interaction, usuario: discord.Member, tipo: str, emoji: str, xp:int=5):
        if usuario.bot or usuario.id == interaction.user.id:
            return await interaction.response.send_message(embed=embed_erro("Escolha outra pessoa, sem bot e sem você mesma kkk"), ephemeral=True)
        if ja_interagiu_hoje(tipo, interaction.user.id, usuario.id):
            return await interaction.response.send_message(embed=embed_erro(f"Você já deu {tipo} para essa pessoa hoje."), ephemeral=True)
        registrar_interacao(tipo, interaction.user.id, usuario.id)
        ensure_perfil(usuario.id, usuario.display_name)
        add_xp(interaction.user.id, interaction.user.display_name, xp)
        await interaction.response.send_message(embed=embed_sucesso(f"{emoji} {interaction.user.mention} enviou {tipo} para {usuario.mention}! +{xp} XP"))

    @app_commands.command(name="cookie", description="🍪 Dá um cookie para alguém")
    async def cookie(self, interaction, usuario: discord.Member): await self._dar(interaction, usuario, "cookie", "🍪")

    @app_commands.command(name="curtir", description="💜 Dá uma curtida para alguém")
    async def curtir(self, interaction, usuario: discord.Member): await self._dar(interaction, usuario, "curtida", "💜")

    @app_commands.command(name="cartinha", description="💌 Envia uma cartinha para alguém")
    async def cartinha(self, interaction, usuario: discord.Member, mensagem: str):
        if usuario.bot or usuario.id == interaction.user.id:
            return await interaction.response.send_message(embed=embed_erro("Escolha outra pessoa, sem bot e sem você mesma kkk"), ephemeral=True)
        if len(mensagem) > 300:
            return await interaction.response.send_message(embed=embed_erro("A cartinha pode ter no máximo 300 caracteres."), ephemeral=True)
        registrar_interacao("cartinha", interaction.user.id, usuario.id, mensagem)
        ensure_perfil(usuario.id, usuario.display_name)
        add_xp(interaction.user.id, interaction.user.display_name, 15)
        await interaction.response.send_message(embed=embed_sucesso(f"💌 Cartinha enviada para {usuario.mention}! +15 XP"), ephemeral=True)

    async def _listar(self, interaction, tipo: str, titulo: str, emoji: str):
        rows=listar_interacoes(tipo, interaction.user.id, 10)
        e=discord.Embed(title=f"{emoji} {titulo}", color=discord.Color.purple())
        if not rows: e.description="Nada recebido ainda."
        for r in rows:
            user=interaction.guild.get_member(r['remetente_id']) if interaction.guild else None
            nome=user.mention if user else str(r['remetente_id'])
            data=r['criado_em'].strftime('%d/%m/%Y %H:%M') if r.get('criado_em') else 'data desconhecida'
            msg=f"De: {nome}\n📅 {data}"
            if r.get('mensagem'): msg += f"\n💬 {r['mensagem']}"
            e.add_field(name=f"{emoji} Recebido", value=msg, inline=False)
        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="cookies", description="🍪 Veja quem te deu cookies")
    async def cookies(self, interaction): await self._listar(interaction,"cookie","Cookies recebidos","🍪")
    @app_commands.command(name="curtidas", description="💜 Veja quem te curtiu")
    async def curtidas(self, interaction): await self._listar(interaction,"curtida","Curtidas recebidas","💜")
    @app_commands.command(name="cartinhas", description="💌 Leia suas cartinhas")
    async def cartinhas(self, interaction): await self._listar(interaction,"cartinha","Cartinhas recebidas","💌")
async def setup(bot): await bot.add_cog(Social(bot))
