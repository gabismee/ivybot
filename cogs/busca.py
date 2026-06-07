import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros, gerar_links_compra, livro_aleatorio
from utils.embeds import embed_livro, embed_erro, embed_sucesso, CORES
from utils.db import adicionar_wishlist, atualizar_biblioteca, add_xp

class BotaoLivro(discord.ui.View):
    def __init__(self, livro:dict): super().__init__(timeout=120); self.livro=livro
    @discord.ui.button(label='📌 Quero Ler', style=discord.ButtonStyle.primary)
    async def quero_ler(self, interaction, button):
        ok=adicionar_wishlist(interaction.user.id, self.livro)
        atualizar_biblioteca(interaction.user.id, self.livro, 'quero_ler')
        if ok: add_xp(interaction.user.id, interaction.user.display_name, 5)
        await interaction.response.send_message(f"✅ **{self.livro['titulo']}** foi para **Quero Ler**!", ephemeral=True)
    @discord.ui.button(label='📚 Adicionar à Estante', style=discord.ButtonStyle.secondary)
    async def estante(self, interaction, button):
        atualizar_biblioteca(interaction.user.id, self.livro, 'lendo')
        await interaction.response.send_message(f"✅ **{self.livro['titulo']}** adicionado como **Lendo**.", ephemeral=True)

    @discord.ui.button(label='❤️ Favoritar', style=discord.ButtonStyle.danger)
    async def favoritar(self, interaction, button):
        atualizar_biblioteca(interaction.user.id, self.livro, 'favorito')
        add_xp(interaction.user.id, interaction.user.display_name, 15)
        await interaction.response.send_message(f"❤️ **{self.livro['titulo']}** foi para seus **Favoritos**! (+15 XP)", ephemeral=True)

class SeletorLivro(discord.ui.View):
    def __init__(self, resultados):
        super().__init__(timeout=90); self.resultados=resultados
        opts=[discord.SelectOption(label=r['titulo'][:100], description=f"{r.get('autor','')[:50]} — {r.get('ano','')}", value=str(i)) for i,r in enumerate(resultados[:10])]
        s=discord.ui.Select(placeholder='Escolha um livro...', options=opts); s.callback=self.on_select; self.add_item(s)
    async def on_select(self, interaction):
        livro=self.resultados[int(interaction.data['values'][0])]
        await interaction.response.edit_message(embed=embed_livro(livro, gerar_links_compra(livro)), view=BotaoLivro(livro))

async def _executar_busca(ctx_or_interaction, query, is_slash):
    resultados=await buscar_livros(query, 8, lang='pt')
    if not resultados:
        msg=embed_erro(f"Nenhum livro encontrado para **{query}**.")
        return await (ctx_or_interaction.followup.send(embed=msg) if is_slash else ctx_or_interaction.send(embed=msg))
    embed=discord.Embed(title=f"🔍 Resultados para: {query}", description='Escolha um resultado no menu abaixo.', color=CORES['roxo'])
    await (ctx_or_interaction.followup.send(embed=embed, view=SeletorLivro(resultados)) if is_slash else ctx_or_interaction.send(embed=embed, view=SeletorLivro(resultados)))

class Busca(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name='buscar', description='🔍 Pesquisa vários livros e deixa você escolher')
    async def buscar_slash(self, interaction:discord.Interaction, query:str): await interaction.response.defer(); await _executar_busca(interaction, query, True)
    @app_commands.command(name='livro', description='📚 Mostra detalhes completos do melhor resultado')
    async def livro_slash(self, interaction:discord.Interaction, titulo:str):
        await interaction.response.defer(); r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
        l=r[0]; await interaction.followup.send(embed=embed_livro(l, gerar_links_compra(l)), view=BotaoLivro(l))
    @app_commands.command(name='conhecer', description='🎲 Conheça um livro aleatório')
    async def conhecer(self, interaction:discord.Interaction):
        await interaction.response.defer(); l=await livro_aleatorio()
        if not l: return await interaction.followup.send(embed=embed_erro('Não consegui sortear um livro agora.'))
        await interaction.followup.send(embed=embed_livro(l, gerar_links_compra(l)), view=BotaoLivro(l))
    @commands.command(name='conhecer')
    async def conhecer_prefix(self, ctx):
        l=await livro_aleatorio()
        if not l: return await ctx.send(embed=embed_erro('Não consegui sortear um livro agora.'))
        await ctx.send(embed=embed_livro(l, gerar_links_compra(l)), view=BotaoLivro(l))

    @commands.command(name='buscar', aliases=['b','search'])
    async def buscar_prefix(self, ctx, *, query:str=None):
        if not query: return await ctx.send(embed=embed_erro('Use: `!buscar <título, autor ou tema>`'))
        await _executar_busca(ctx, query, False)
    @commands.command(name='livro')
    async def livro_prefix(self, ctx, *, titulo:str=None):
        if not titulo: return await ctx.send(embed=embed_erro('Use: `!livro <título>`'))
        r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await ctx.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        l=r[0]; await ctx.send(embed=embed_livro(l, gerar_links_compra(l)), view=BotaoLivro(l))

async def setup(bot): await bot.add_cog(Busca(bot))
