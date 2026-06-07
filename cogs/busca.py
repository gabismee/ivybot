import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros, gerar_links_compra, buscar_precos
from utils.embeds import embed_livro, embed_erro, FOOTER
from utils.db import add_xp

class BotaoWishlist(discord.ui.View):
    def __init__(self, livro):
        super().__init__(timeout=120); self.livro=livro
    @discord.ui.button(label="Adicionar à wishlist", emoji="❤️", style=discord.ButtonStyle.secondary)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.db import adicionar_wishlist
        ok=adicionar_wishlist(interaction.user.id,self.livro)
        await interaction.response.send_message("❤️ Adicionado à wishlist!" if ok else "Esse livro já está na sua wishlist.", ephemeral=True)

class SeletorLivro(discord.ui.View):
    def __init__(self, livros):
        super().__init__(timeout=120); self.livros=livros
        select=discord.ui.Select(placeholder="Escolha um livro para ver detalhes...", options=[discord.SelectOption(label=l['titulo'][:100], description=l.get('autor','')[:50], value=str(i), emoji='📚') for i,l in enumerate(livros[:25])])
        select.callback=self.on_select; self.add_item(select)
    async def on_select(self, interaction):
        livro=self.livros[int(interaction.data['values'][0])]
        links=gerar_links_compra(livro)
        extras=await buscar_precos(livro.get('titulo',''), livro.get('autor',''), livro.get('isbn',''))
        links=extras+links
        if extras and livro.get('preco') is None:
            livro={**livro, 'preco': extras[0]['preco'], 'loja_preco': extras[0]['loja'], 'buy_link': extras[0]['url']}
        await interaction.response.send_message(embed=embed_livro(livro, links), view=BotaoWishlist(livro), ephemeral=True)

async def _executar_busca(ctx, query, is_slash=False):
    resultados=await buscar_livros(query, 8)
    if not resultados:
        msg=embed_erro(f"Nenhum livro encontrado para **{query}**. Tente outro título ou autor.")
        return await (ctx.followup.send(embed=msg) if is_slash else ctx.send(embed=msg))
    embed=discord.Embed(title="🔍 Resultados da busca", description=f"Encontrei **{len(resultados)}** livros. Escolha um abaixo:", color=discord.Color.blurple())
    embed.set_footer(text=FOOTER)
    view=SeletorLivro(resultados)
    await (ctx.followup.send(embed=embed, view=view) if is_slash else ctx.send(embed=embed, view=view))

async def _detalhe_livro(ctx, titulo, is_slash=False):
    resultados=await buscar_livros(titulo, 1)
    if not resultados:
        msg=embed_erro(f"Livro **{titulo}** não encontrado.")
        return await (ctx.followup.send(embed=msg) if is_slash else ctx.send(embed=msg))
    livro=resultados[0]
    extras=await buscar_precos(livro.get('titulo',''), livro.get('autor',''), livro.get('isbn',''))
    links=extras+gerar_links_compra(livro)
    if extras and livro.get('preco') is None:
        livro={**livro, 'preco': extras[0]['preco'], 'loja_preco': extras[0]['loja'], 'buy_link': extras[0]['url']}
    await (ctx.followup.send(embed=embed_livro(livro, links), view=BotaoWishlist(livro)) if is_slash else ctx.send(embed=embed_livro(livro, links), view=BotaoWishlist(livro)))

class Busca(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name="buscar", description="🔍 Pesquisa vários livros e abre um seletor")
    async def buscar_slash(self, interaction:discord.Interaction, query:str):
        await interaction.response.defer(); await _executar_busca(interaction, query, True)
    @app_commands.command(name="livro", description="📚 Mostra detalhes diretos de um livro")
    async def livro_slash(self, interaction:discord.Interaction, titulo:str):
        await interaction.response.defer(); await _detalhe_livro(interaction, titulo, True)
    @commands.command(name="buscar", aliases=["b","search"])
    async def buscar_prefix(self, ctx, *, query:str=None):
        if not query: return await ctx.send(embed=embed_erro("Use: `!buscar <título ou autor>`"))
        msg=await ctx.send("🔍 Buscando..."); await _executar_busca(ctx, query, False); await msg.delete()
    @commands.command(name="livro", aliases=["l"])
    async def livro_prefix(self, ctx, *, titulo:str=None):
        if not titulo: return await ctx.send(embed=embed_erro("Use: `!livro <título>`"))
        msg=await ctx.send("📚 Buscando detalhes..."); await _detalhe_livro(ctx, titulo, False); await msg.delete()
    @commands.command(name="ajuda", aliases=["help","h"])
    async def ajuda_prefix(self, ctx):
        e=discord.Embed(title="📚 Ivy — Comandos", description="Use `/` ou `!` para conversar comigo.", color=discord.Color.blurple())
        e.add_field(name="🔍 Busca", value="`!buscar <termo>` — lista resultados\n`!livro <título>` — detalhe direto", inline=False)
        e.add_field(name="👤 Perfil", value="`/perfil` — cartão visual\n`/perfil-config frase` / `wallpaper`", inline=False)
        e.add_field(name="🎲 Quiz", value="`/quiz iniciar` — quiz literário com ranking", inline=False)
        e.add_field(name="🍪 Social", value="`/cookie`, `/curtir`, `/cartinha`, `/cookies`, `/curtidas`, `/cartinhas`", inline=False)
        e.set_footer(text=FOOTER); await ctx.send(embed=e)
async def setup(bot): await bot.add_cog(Busca(bot))
