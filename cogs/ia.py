import discord
from discord import app_commands
from discord.ext import commands
from utils.api import recomendar_por_perfil, buscar_livros, gerar_links_compra, buscar_precos
from utils.embeds import embed_livro, embed_erro, FOOTER
from utils.db import get_perfil, get_biblioteca, ensure_perfil

class IA(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @app_commands.command(name='recomendar', description='🤖 Recomendações personalizadas ou populares')
    async def recomendar(self, interaction):
        await interaction.response.defer()
        ensure_perfil(interaction.user.id, interaction.user.display_name)
        perfil=get_perfil(interaction.user.id) or {'generos':[], 'autores':[], 'objetivo':'diversao'}
        hist=[l['titulo'] for l in get_biblioteca(interaction.user.id)]
        recs=await recomendar_por_perfil(perfil,hist)
        if not recs: return await interaction.followup.send(embed=embed_erro('Não encontrei recomendações agora.'))
        e=discord.Embed(title=f'🤖 Recomendações para {interaction.user.display_name}', description='Baseado no seu perfil e leituras. Se ainda não configurou, usei populares.', color=discord.Color.purple())
        for i,l in enumerate(recs[:5],1): e.add_field(name=f'{i}. {l["titulo"][:50]}', value=f"✍️ {l.get('autor','')}\n📝 {l.get('sinopse','')[:100]}...", inline=False)
        e.set_footer(text=FOOTER); await interaction.followup.send(embed=e, view=VerRecomendacoesView(recs[:5]))
    @app_commands.command(name='similar', description='🔍 Encontra livros similares')
    async def similar(self, interaction, titulo:str):
        await interaction.response.defer(); base=await buscar_livros(titulo,1)
        if not base: return await interaction.followup.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        q=base[0].get('autor') or (base[0].get('generos') or ['bestseller'])[0]
        res=[r for r in await buscar_livros(q,6) if r['titulo'] != base[0]['titulo']]
        if not res: return await interaction.followup.send(embed=embed_erro('Não encontrei similares.'))
        e=discord.Embed(title=f'📚 Similares a: {base[0]["titulo"][:40]}', color=discord.Color.blue())
        for l in res[:5]: e.add_field(name=f'📖 {l["titulo"][:50]}', value=f"✍️ {l.get('autor','')}", inline=False)
        e.set_footer(text=FOOTER); await interaction.followup.send(embed=e, view=VerRecomendacoesView(res[:5]))
    @app_commands.command(name='encontrar', description='🎯 Encontra livros por tema')
    async def encontrar(self, interaction, tema:str):
        await interaction.response.defer(); res=await buscar_livros(tema,6)
        if not res: return await interaction.followup.send(embed=embed_erro(f'Não encontrei livros sobre **{tema}**.'))
        e=discord.Embed(title=f'🎯 Livros sobre: {tema}', color=discord.Color.green())
        for l in res[:5]: e.add_field(name=f'📚 {l["titulo"][:50]}', value=f"✍️ {l.get('autor','')}\n📝 {l.get('sinopse','')[:80]}...", inline=False)
        e.set_footer(text=FOOTER); await interaction.followup.send(embed=e, view=VerRecomendacoesView(res[:5]))
class VerRecomendacoesView(discord.ui.View):
    def __init__(self, livros):
        super().__init__(timeout=120); self.livros=livros
        s=discord.ui.Select(placeholder='Ver detalhes de um livro...', options=[discord.SelectOption(label=l['titulo'][:100], description=l.get('autor','')[:50], value=str(i), emoji='📚') for i,l in enumerate(livros)])
        s.callback=self.on_select; self.add_item(s)
    async def on_select(self, interaction):
        livro=self.livros[int(interaction.data['values'][0])]; extras=await buscar_precos(livro.get('titulo',''), livro.get('autor',''), livro.get('isbn',''))
        links=extras+gerar_links_compra(livro)
        if extras and livro.get('preco') is None: livro={**livro,'preco':extras[0]['preco'],'loja_preco':extras[0]['loja'],'buy_link':extras[0]['url']}
        await interaction.response.send_message(embed=embed_livro(livro,links), ephemeral=True)
async def setup(bot): await bot.add_cog(IA(bot))
