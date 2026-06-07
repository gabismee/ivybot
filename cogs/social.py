import discord
from discord import app_commands
from discord.ext import commands
from utils.db import registrar_interacao, listar_interacoes, add_xp
from utils.embeds import embed_sucesso, embed_erro

class Social(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _dar(self, interaction, membro, tipo, mensagem=''):
        if membro.bot or membro.id==interaction.user.id: return await interaction.response.send_message(embed=embed_erro('Escolha outra pessoa.'), ephemeral=True)
        ok=registrar_interacao(interaction.guild_id or 0, tipo, interaction.user.id, membro.id, mensagem)
        if not ok: return await interaction.response.send_message(embed=embed_erro(f'Você já enviou {tipo} para essa pessoa hoje.'), ephemeral=True)
        add_xp(interaction.user.id, interaction.user.display_name, 5)
        await interaction.response.send_message(embed=embed_sucesso(f'{interaction.user.mention} enviou **{tipo}** para {membro.mention}!'))
    @app_commands.command(name='cookie', description='🍪 Dá um cookie para alguém')
    async def cookie(self, interaction, membro:discord.Member): await self._dar(interaction,membro,'cookie')
    @app_commands.command(name='curtir', description='💜 Dá uma curtida para alguém')
    async def curtir(self, interaction, membro:discord.Member): await self._dar(interaction,membro,'curtida')
    @app_commands.command(name='cartinha', description='💌 Envia uma cartinha de até 300 caracteres')
    async def cartinha(self, interaction, membro:discord.Member, mensagem:str):
        if len(mensagem)>300: return await interaction.response.send_message(embed=embed_erro('A cartinha pode ter no máximo 300 caracteres.'), ephemeral=True)
        await self._dar(interaction,membro,'cartinha',mensagem)
    @app_commands.command(name='cookies', description='🍪 Ver cookies recebidos')
    async def cookies(self, interaction, usuario:discord.Member=None): await self._listar(interaction, usuario or interaction.user, 'cookie')
    @app_commands.command(name='curtidas', description='💜 Ver curtidas recebidas')
    async def curtidas(self, interaction, usuario:discord.Member=None): await self._listar(interaction, usuario or interaction.user, 'curtida')
    @app_commands.command(name='cartinhas', description='💌 Ver cartinhas recebidas')
    async def cartinhas(self, interaction, usuario:discord.Member=None): await self._listar(interaction, usuario or interaction.user, 'cartinha')
    async def _listar(self, interaction, usuario, tipo):
        rows=listar_interacoes(usuario.id,tipo,15); e=discord.Embed(title=f'{tipo.title()}s de {usuario.display_name}', color=__import__('utils.embeds', fromlist=['CORES']).CORES['rosa'])
        if not rows: e.description='Nada recebido ainda.'
        for r in rows:
            remetente=interaction.guild.get_member(r['remetente_id']) if interaction.guild else None
            nome=remetente.display_name if remetente else str(r['remetente_id'])
            data=str(r['criado_em'])[:16]
            val=f'De: **{nome}**\nData: {data}'
            if tipo=='cartinha': val += f"\n💬 {r.get('mensagem','')}"
            e.add_field(name='—', value=val, inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
    async def _dar_prefix(self, ctx, membro, tipo, mensagem=''):
        if not membro or membro.bot or membro.id==ctx.author.id:
            return await ctx.send(embed=embed_erro('Escolha outra pessoa.'))
        ok=registrar_interacao(ctx.guild.id if ctx.guild else 0, tipo, ctx.author.id, membro.id, mensagem)
        if not ok: return await ctx.send(embed=embed_erro(f'Você já enviou {tipo} para essa pessoa hoje.'))
        add_xp(ctx.author.id, ctx.author.display_name, 5)
        await ctx.send(embed=embed_sucesso(f'{ctx.author.mention} enviou **{tipo}** para {membro.mention}!'))

    @commands.command(name='cookie')
    async def cookie_prefix(self, ctx, membro:discord.Member=None): await self._dar_prefix(ctx,membro,'cookie')
    @commands.command(name='curtir', aliases=['curtida'])
    async def curtir_prefix(self, ctx, membro:discord.Member=None): await self._dar_prefix(ctx,membro,'curtida')
    @commands.command(name='cartinha')
    async def cartinha_prefix(self, ctx, membro:discord.Member=None, *, mensagem:str=''):
        if len(mensagem)>300: return await ctx.send(embed=embed_erro('A cartinha pode ter no máximo 300 caracteres.'))
        if not mensagem: return await ctx.send(embed=embed_erro('Use: `!cartinha @pessoa mensagem`'))
        await self._dar_prefix(ctx,membro,'cartinha',mensagem)
    @commands.command(name='cookies')
    async def cookies_prefix(self, ctx, usuario:discord.Member=None): await self._listar_prefix(ctx, usuario or ctx.author, 'cookie')
    @commands.command(name='curtidas')
    async def curtidas_prefix(self, ctx, usuario:discord.Member=None): await self._listar_prefix(ctx, usuario or ctx.author, 'curtida')
    @commands.command(name='cartinhas')
    async def cartinhas_prefix(self, ctx, usuario:discord.Member=None): await self._listar_prefix(ctx, usuario or ctx.author, 'cartinha')
    async def _listar_prefix(self, ctx, usuario, tipo):
        rows=listar_interacoes(usuario.id,tipo,15); e=discord.Embed(title=f'{tipo.title()}s de {usuario.display_name}', color=__import__('utils.embeds', fromlist=['CORES']).CORES['rosa'])
        if not rows: e.description='Nada recebido ainda.'
        for r in rows:
            remetente=ctx.guild.get_member(r['remetente_id']) if ctx.guild else None
            nome=remetente.display_name if remetente else str(r['remetente_id'])
            data=str(r['criado_em'])[:16]
            val=f'De: **{nome}**\nData: {data}'
            if tipo=='cartinha': val += f"\n💬 {r.get('mensagem','')}"
            e.add_field(name='—', value=val, inline=False)
        await ctx.send(embed=e)

async def setup(bot): await bot.add_cog(Social(bot))
