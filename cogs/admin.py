import discord
from discord import app_commands
from discord.ext import commands
from utils.db import salvar_config, get_config
from utils.embeds import embed_sucesso, FOOTER

class Admin(commands.Cog):
    def __init__(self, bot): self.bot=bot
    config_cmd=app_commands.Group(name='config', description='⚙️ Configurações do bot no servidor', default_permissions=discord.Permissions(manage_guild=True))
    @config_cmd.command(name='canal-promocoes', description='Define o canal de promoções automáticas')
    async def canal_promocoes(self, interaction, canal:discord.TextChannel):
        salvar_config(interaction.guild_id,'canal_promocoes',canal.id); await interaction.response.send_message(embed=embed_sucesso(f'Canal de promoções definido para {canal.mention}!'), ephemeral=True)
    @config_cmd.command(name='canal-ebooks', description='Define o canal de ebooks gratuitos')
    async def canal_ebooks(self, interaction, canal:discord.TextChannel):
        salvar_config(interaction.guild_id,'canal_ebooks',canal.id); await interaction.response.send_message(embed=embed_sucesso(f'Canal de ebooks definido para {canal.mention}!'), ephemeral=True)
    @config_cmd.command(name='canal-clube', description='Define o canal do clube do livro')
    async def canal_clube(self, interaction, canal:discord.TextChannel):
        salvar_config(interaction.guild_id,'canal_clube',canal.id); await interaction.response.send_message(embed=embed_sucesso(f'Canal do clube definido para {canal.mention}!'), ephemeral=True)
    @config_cmd.command(name='ver', description='Mostra configurações atuais')
    async def ver_config(self, interaction):
        cfg=get_config(interaction.guild_id); e=discord.Embed(title='⚙️ Configurações do Servidor', color=discord.Color.blurple())
        def c(cid):
            if not cid: return '❌ Não configurado'
            ch=interaction.guild.get_channel(cid); return ch.mention if ch else f'ID: {cid}'
        e.add_field(name='🔥 Canal Promoções', value=c(cfg.get('canal_promocoes')), inline=False)
        e.add_field(name='📱 Canal Ebooks', value=c(cfg.get('canal_ebooks')), inline=False)
        e.add_field(name='📖 Canal Clube', value=c(cfg.get('canal_clube')), inline=False)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e, ephemeral=True)
    @app_commands.command(name='ajuda', description='📋 Lista comandos disponíveis')
    async def ajuda(self, interaction):
        e=discord.Embed(title='📚 Ivy — Comandos', description='Seu bot literário gratuito no Discord.', color=discord.Color.blurple())
        categorias={
            '🔍 Pesquisa':['`/buscar` — lista resultados','`/livro` — detalhe direto com preço quando disponível','`/recomendar` — recomendações'],
            '👤 Perfil':['`/perfil` — cartão visual','`/perfil-config frase`','`/perfil-config wallpaper`','`/perfil-config resetar`'],
            '📚 Estante':['`/estante adicionar`','`/estante ver`','`/avaliar`','`/ler`'],
            '🎲 Quiz':['`/quiz iniciar`','`/quiz ranking`'],
            '🍪 Social':['`/cookie`','`/curtir`','`/cartinha`','`/cookies`','`/curtidas`','`/cartinhas`'],
            '🎁 Extras':['`/desafio`','`/desafios`','`/evento`','`/promocoes`','`/ranking`'],
            '⚙️ Admin':['`/config canal-promocoes`','`/config canal-clube`','`/config ver`']}
        for cat, cmds in categorias.items(): e.add_field(name=cat, value='\n'.join(cmds), inline=False)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e, ephemeral=True)
async def setup(bot): await bot.add_cog(Admin(bot))
