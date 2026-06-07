import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros, gerar_links_compra
from utils.embeds import embed_wishlist, embed_livro, embed_erro, embed_sucesso
from utils.db import get_wishlist, adicionar_wishlist, remover_wishlist, atualizar_biblioteca, add_xp

class RemoverView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=60); self.items=items
        opts=[discord.SelectOption(label=i['titulo'][:100], description=i.get('autor','')[:50], value=i.get('isbn') or i['titulo']) for i in items[:25]]
        s=discord.ui.Select(placeholder='Escolha um livro para remover...', options=opts); s.callback=self.on_select; self.add_item(s)
    async def on_select(self, interaction):
        v=interaction.data['values'][0]; ok=remover_wishlist(interaction.user.id, v)
        await interaction.response.send_message(embed=embed_sucesso('Removido da lista Quero Ler.') if ok else embed_erro('Não consegui remover.'), ephemeral=True)

class Wishlist(commands.Cog):
    def __init__(self, bot): self.bot=bot
    queroler=app_commands.Group(name='queroler', description='📌 Gerencia sua lista Quero Ler')
    desejo=app_commands.Group(name='desejo', description='📌 Atalho antigo para Quero Ler')
    async def _adicionar(self, interaction, titulo, preco_alvo=None):
        await interaction.response.defer(ephemeral=True); r=await buscar_livros(titulo,3,lang='pt')
        if not r: return await interaction.followup.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        ok=adicionar_wishlist(interaction.user.id, r[0], preco_alvo); atualizar_biblioteca(interaction.user.id, r[0], 'quero_ler')
        if ok: add_xp(interaction.user.id, interaction.user.display_name, 5)
        await interaction.followup.send(embed=embed_sucesso(f"**{r[0]['titulo']}** adicionado em **Quero Ler**!" if ok else 'Esse livro já está na sua lista.'))
    @queroler.command(name='adicionar', description='Adiciona livro em Quero Ler')
    async def adicionar_q(self, interaction:discord.Interaction, titulo:str, preco_alvo:float=None): await self._adicionar(interaction,titulo,preco_alvo)
    @desejo.command(name='adicionar', description='Adiciona livro em Quero Ler')
    async def adicionar_d(self, interaction:discord.Interaction, titulo:str, preco_alvo:float=None): await self._adicionar(interaction,titulo,preco_alvo)
    @queroler.command(name='listar', description='Ver sua lista Quero Ler')
    async def listar_q(self, interaction): await interaction.response.send_message(embed=embed_wishlist(get_wishlist(interaction.user.id), interaction.user.display_name), ephemeral=True)
    @desejo.command(name='listar', description='Ver sua lista Quero Ler')
    async def listar_d(self, interaction): await self.listar_q(interaction)
    @queroler.command(name='remover', description='Remove livro de Quero Ler')
    async def remover_q(self, interaction):
        items=get_wishlist(interaction.user.id)
        if not items: return await interaction.response.send_message(embed=embed_erro('Sua lista Quero Ler está vazia.'), ephemeral=True)
        await interaction.response.send_message('Escolha qual livro remover:', view=RemoverView(items), ephemeral=True)
    @desejo.command(name='remover', description='Remove livro de Quero Ler')
    async def remover_d(self, interaction): await self.remover_q(interaction)
    @queroler.command(name='ver', description='Ver detalhes de um item da lista')
    async def ver_q(self, interaction):
        items=get_wishlist(interaction.user.id)
        if not items: return await interaction.response.send_message(embed=embed_erro('Sua lista está vazia.'), ephemeral=True)
        opts=[discord.SelectOption(label=i['titulo'][:100], description=i.get('autor','')[:50], value=str(n)) for n,i in enumerate(items[:25])]
        class V(discord.ui.View):
            def __init__(self): super().__init__(timeout=60); s=discord.ui.Select(placeholder='Escolha...', options=opts); s.callback=self.sel; self.add_item(s)
            async def sel(self2, inter):
                item=items[int(inter.data['values'][0])]; livro=dict(item); await inter.response.edit_message(embed=embed_livro(livro, gerar_links_compra(livro)), view=None)
        await interaction.response.send_message('Escolha um livro:', view=V(), ephemeral=True)
    @desejo.command(name='ver', description='Ver detalhes de um item da lista')
    async def ver_d(self, interaction): await self.ver_q(interaction)
    @commands.group(name='queroler', aliases=['quero-ler','desejo'], invoke_without_command=True)
    async def queroler_prefix(self, ctx, *, titulo:str=None):
        if titulo:
            r=await buscar_livros(titulo,3,lang='pt')
            if not r: return await ctx.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
            ok=adicionar_wishlist(ctx.author.id, r[0]); atualizar_biblioteca(ctx.author.id, r[0], 'quero_ler')
            if ok: add_xp(ctx.author.id, ctx.author.display_name, 5)
            return await ctx.send(embed=embed_sucesso(f"**{r[0]['titulo']}** adicionado em **Quero Ler**!" if ok else 'Esse livro já está na sua lista.'))
        await ctx.send(embed=embed_wishlist(get_wishlist(ctx.author.id), ctx.author.display_name))

    @queroler_prefix.command(name='adicionar')
    async def queroler_adicionar_prefix(self, ctx, *, titulo:str=None):
        if not titulo: return await ctx.send(embed=embed_erro('Use: `!queroler adicionar <livro>`'))
        r=await buscar_livros(titulo,3,lang='pt')
        if not r: return await ctx.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        ok=adicionar_wishlist(ctx.author.id, r[0]); atualizar_biblioteca(ctx.author.id, r[0], 'quero_ler')
        if ok: add_xp(ctx.author.id, ctx.author.display_name, 5)
        await ctx.send(embed=embed_sucesso(f"**{r[0]['titulo']}** adicionado em **Quero Ler**!" if ok else 'Esse livro já está na sua lista.'))

    @queroler_prefix.command(name='listar')
    async def queroler_listar_prefix(self, ctx):
        await ctx.send(embed=embed_wishlist(get_wishlist(ctx.author.id), ctx.author.display_name))

    @queroler_prefix.command(name='remover')
    async def queroler_remover_prefix(self, ctx, *, isbn_ou_titulo:str=None):
        if not isbn_ou_titulo: return await ctx.send(embed=embed_erro('Use: `!queroler remover <isbn ou título>`'))
        ok=remover_wishlist(ctx.author.id, isbn_ou_titulo)
        await ctx.send(embed=embed_sucesso('Removido da lista Quero Ler.') if ok else embed_erro('Não encontrei esse item na sua lista.'))

async def setup(bot): await bot.add_cog(Wishlist(bot))
