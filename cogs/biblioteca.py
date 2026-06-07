import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros
from utils.embeds import embed_biblioteca, embed_erro, embed_sucesso, estrelas, CORES
from utils.db import get_biblioteca, atualizar_biblioteca, avaliar_livro, get_stats_usuario, get_perfil, atualizar_perfil_visual, add_xp, checkin_leitura, atualizar_pagina_livro
from utils.profile_card import gerar_profile_card, gerar_estante_card

STATUS_CHOICES=[app_commands.Choice(name='📌 Quero Ler',value='quero_ler'),app_commands.Choice(name='📖 Lendo',value='lendo'),app_commands.Choice(name='✅ Lido',value='lido'),app_commands.Choice(name='❤️ Favorito',value='favorito'),app_commands.Choice(name='🗑️ Abandonado',value='abandonado')]

class Biblioteca(commands.Cog):
    def __init__(self, bot): self.bot=bot
    estante=app_commands.Group(name='estante', description='📚 Gerencia sua estante pessoal')
    @estante.command(name='adicionar', description='Adiciona um livro à estante')
    @app_commands.choices(status=STATUS_CHOICES)
    async def adicionar(self, interaction:discord.Interaction, titulo:str, status:str='quero_ler', pagina_atual:int=0):
        await interaction.response.defer(ephemeral=True); r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await interaction.followup.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        atualizar_biblioteca(interaction.user.id, r[0], status, pagina_atual=pagina_atual)
        if status=='lido': add_xp(interaction.user.id, interaction.user.display_name, 50)
        await interaction.followup.send(embed=embed_sucesso(f"**{r[0]['titulo']}** adicionado como **{status.replace('_',' ').title()}**!"))
    @estante.command(name='ver', description='Vê sua estante em imagem')
    @app_commands.choices(status=STATUS_CHOICES)
    async def ver(self, interaction:discord.Interaction, status:str=None):
        await interaction.response.defer(ephemeral=True); itens=get_biblioteca(interaction.user.id,status)
        if itens:
            img=await gerar_estante_card(interaction.user, itens, 'Estante' if not status else status.replace('_',' ').title())
            await interaction.followup.send(file=discord.File(img, filename='estante.png'))
        else:
            await interaction.followup.send(embed=embed_biblioteca(itens, interaction.user.display_name, status or 'todos'))

    @estante.command(name='pagina', description='Atualiza a página em que você está/parou')
    @app_commands.choices(status=STATUS_CHOICES)
    async def pagina(self, interaction:discord.Interaction, titulo:str, pagina_atual:int, status:str=None):
        ok = atualizar_pagina_livro(interaction.user.id, titulo, pagina_atual, status)
        if not ok:
            return await interaction.response.send_message(embed=embed_erro('Não achei esse livro na sua estante. Adicione ele primeiro.'), ephemeral=True)
        extra = f' e status **{status.replace("_", " ").title()}**' if status else ''
        await interaction.response.send_message(embed=embed_sucesso(f'Página atualizada para **{pagina_atual}**{extra}!'), ephemeral=True)

    @commands.command(name='pagina', aliases=['página'])
    async def pagina_prefix(self, ctx, pagina_atual:int=None, *, titulo:str=None):
        if pagina_atual is None or not titulo:
            return await ctx.send(embed=embed_erro('Use: `!pagina <número> <título>`'))
        ok = atualizar_pagina_livro(ctx.author.id, titulo, pagina_atual)
        if not ok:
            return await ctx.send(embed=embed_erro('Não achei esse livro na sua estante. Adicione ele primeiro.'))
        await ctx.send(embed=embed_sucesso(f'Página atualizada para **{pagina_atual}**!'))

    @estante.command(name='stats', description='Estatísticas da sua leitura')
    async def stats(self, interaction:discord.Interaction):
        todos=get_biblioteca(interaction.user.id); stats=get_stats_usuario(interaction.user.id); cont={}
        for i in todos: cont[i['status']]=cont.get(i['status'],0)+1
        e=discord.Embed(title=f'📊 Estatísticas de {interaction.user.display_name}', color=CORES['azul'])
        for k,n in [('📌 Quero Ler','quero_ler'),('📖 Lendo','lendo'),('✅ Lidos','lido'),('❤️ Favoritos','favorito'),('🗑️ Abandonados','abandonado')]: e.add_field(name=k,value=str(cont.get(n,0)),inline=True)
        e.add_field(name='⭐ Média', value=str(stats.get('media_avaliacao',0)), inline=True); e.set_footer(text='Ivy 📚 • Feito pela Gabi 🌷')
        await interaction.response.send_message(embed=e, ephemeral=True)
    @app_commands.command(name='avaliar', description='⭐ Avalia um livro com estrelas e comentário opcional')
    @app_commands.choices(estrelas_n=[app_commands.Choice(name='⭐ 1',value=1),app_commands.Choice(name='⭐⭐ 2',value=2),app_commands.Choice(name='⭐⭐⭐ 3',value=3),app_commands.Choice(name='⭐⭐⭐⭐ 4',value=4),app_commands.Choice(name='⭐⭐⭐⭐⭐ 5',value=5)])
    async def avaliar(self, interaction:discord.Interaction, titulo:str, estrelas_n:int, comentario:str=''):
        await interaction.response.defer(ephemeral=True); r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await interaction.followup.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        avaliar_livro(interaction.user.id, r[0], estrelas_n, comentario); xp=add_xp(interaction.user.id, interaction.user.display_name, 10)
        e=discord.Embed(title='⭐ Avaliação registrada!', color=CORES['dourado']); e.add_field(name='📚 Livro',value=r[0]['titulo'],inline=False); e.add_field(name='Nota',value=estrelas(estrelas_n),inline=True); e.add_field(name='XP',value=f'+10 XP • total {xp}',inline=True)
        if comentario: e.add_field(name='💬 Comentário', value=comentario[:500], inline=False)
        if r[0].get('capa_url'): e.set_thumbnail(url=r[0]['capa_url'])
        await interaction.followup.send(embed=e)
    @app_commands.command(name='ler', description='🔥 Registra leitura diária e mantém streak')
    async def ler(self, interaction:discord.Interaction, minutos:int=15):
        row=checkin_leitura(interaction.user.id, interaction.user.display_name)
        await interaction.response.send_message(embed=embed_sucesso(f"Leitura registrada! 🔥 Streak: **{row['streak']}** dia(s) • +15 XP"), ephemeral=True)
    @app_commands.command(name='perfil', description='👤 Exibe perfil visual')
    async def perfil_cmd(self, interaction:discord.Interaction, usuario:discord.Member=None):
        await interaction.response.defer(); alvo=usuario or interaction.user; perfil=get_perfil(alvo.id)
        if not perfil:
            from utils.db import garantir_perfil
            garantir_perfil(alvo.id, alvo.display_name); perfil=get_perfil(alvo.id)
        img=await gerar_profile_card(alvo, perfil, get_stats_usuario(alvo.id))
        await interaction.followup.send(file=discord.File(img, filename='perfil_ivy.png'))
    @app_commands.command(name='perfil-frase', description='💭 Define sua frase no perfil')
    async def perfil_frase(self, interaction:discord.Interaction, frase:str):
        atualizar_perfil_visual(interaction.user.id, interaction.user.display_name, frase=frase)
        await interaction.response.send_message(embed=embed_sucesso('Frase atualizada!'), ephemeral=True)
    @app_commands.command(name='perfil-wallpaper', description='🖼️ Define URL do wallpaper do perfil')
    async def perfil_wallpaper(self, interaction:discord.Interaction, url:str):
        atualizar_perfil_visual(interaction.user.id, interaction.user.display_name, wallpaper_url=url)
        await interaction.response.send_message(embed=embed_sucesso('Wallpaper atualizado!'), ephemeral=True)
    @app_commands.command(name='perfil-resetar-wallpaper', description='🖼️ Volta para o wallpaper padrão da Ivy')
    async def perfil_reset(self, interaction:discord.Interaction):
        atualizar_perfil_visual(interaction.user.id, interaction.user.display_name, wallpaper_url='')
        await interaction.response.send_message(embed=embed_sucesso('Wallpaper padrão restaurado!'), ephemeral=True)
    async def _add_estante_prefix(self, ctx, status, titulo):
        pagina = 0
        if titulo and '|' in titulo:
            partes = titulo.rsplit('|', 1)
            titulo = partes[0].strip()
            try:
                pagina = int(partes[1].strip())
            except Exception:
                pagina = 0
        if not titulo:
            return await ctx.send(embed=embed_erro(f'Use: `!{status.replace("_", "")} <título>`'))
        r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await ctx.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        atualizar_biblioteca(ctx.author.id, r[0], status, pagina_atual=pagina)
        if status=='lido': add_xp(ctx.author.id, ctx.author.display_name, 50)
        if status=='favorito': add_xp(ctx.author.id, ctx.author.display_name, 15)
        await ctx.send(embed=embed_sucesso(f"**{r[0]['titulo']}** adicionado como **{status.replace('_',' ').title()}**!"))

    @commands.command(name='estante')
    async def estante_prefix(self, ctx, status: str='todos'):
        status = None if status.lower() in ('todos','tudo') else status.lower().replace('quero-ler','quero_ler')
        itens=get_biblioteca(ctx.author.id,status)
        if itens:
            img=await gerar_estante_card(ctx.author, itens, 'Estante' if not status else status.replace('_',' ').title())
            await ctx.send(file=discord.File(img, filename='estante.png'))
        else:
            await ctx.send(embed=embed_biblioteca(itens, ctx.author.display_name, status or 'todos'))

    @commands.command(name='lendo')
    async def lendo_prefix(self, ctx, *, titulo: str=None): await self._add_estante_prefix(ctx, 'lendo', titulo)

    @commands.command(name='lido', aliases=['concluido','concluído'])
    async def lido_prefix(self, ctx, *, titulo: str=None): await self._add_estante_prefix(ctx, 'lido', titulo)

    @commands.command(name='abandonado', aliases=['abandonei','parado','parei'])
    async def abandonado_prefix(self, ctx, *, titulo: str=None):
        # Use: !abandonado Nome do livro | 120  (página onde parou)
        await self._add_estante_prefix(ctx, 'abandonado', titulo)

    @commands.command(name='favorito', aliases=['favoritar'])
    async def favorito_prefix(self, ctx, *, titulo: str=None): await self._add_estante_prefix(ctx, 'favorito', titulo)

    @app_commands.command(name='favorito', description='❤️ Adiciona um livro aos favoritos')
    async def favorito_slash(self, interaction:discord.Interaction, titulo:str):
        await interaction.response.defer(ephemeral=True); r=await buscar_livros(titulo,1,lang='pt')
        if not r: return await interaction.followup.send(embed=embed_erro(f'Livro **{titulo}** não encontrado.'))
        atualizar_biblioteca(interaction.user.id, r[0], 'favorito'); add_xp(interaction.user.id, interaction.user.display_name, 15)
        await interaction.followup.send(embed=embed_sucesso(f"**{r[0]['titulo']}** foi adicionado aos seus **Favoritos**! ❤️ (+15 XP)"))

    @commands.command(name='avaliar')
    async def avaliar_prefix(self, ctx, estrelas_n: int=None, *, titulo_e_comentario: str=None):
        if not estrelas_n or not titulo_e_comentario:
            return await ctx.send(embed=embed_erro('Use: `!avaliar <1-5> <título> | comentário opcional`'))
        if estrelas_n < 1 or estrelas_n > 5:
            return await ctx.send(embed=embed_erro('A nota precisa ser de 1 a 5 estrelas.'))
        titulo, comentario = (titulo_e_comentario.split('|',1)+[''])[:2] if '|' in titulo_e_comentario else (titulo_e_comentario, '')
        r=await buscar_livros(titulo.strip(),1,lang='pt')
        if not r: return await ctx.send(embed=embed_erro(f'Livro **{titulo.strip()}** não encontrado.'))
        avaliar_livro(ctx.author.id, r[0], estrelas_n, comentario.strip()); xp=add_xp(ctx.author.id, ctx.author.display_name, 10)
        e=discord.Embed(title='⭐ Avaliação registrada!', color=CORES['dourado']); e.add_field(name='📚 Livro',value=r[0]['titulo'],inline=False); e.add_field(name='Nota',value=estrelas(estrelas_n),inline=True); e.add_field(name='XP',value=f'+10 XP • total {xp}',inline=True)
        if comentario.strip(): e.add_field(name='💬 Comentário', value=comentario.strip()[:500], inline=False)
        if r[0].get('capa_url'): e.set_thumbnail(url=r[0]['capa_url'])
        await ctx.send(embed=e)

    @commands.command(name='ler')
    async def ler_prefix(self, ctx, minutos:int=15):
        row=checkin_leitura(ctx.author.id, ctx.author.display_name)
        await ctx.send(embed=embed_sucesso(f"Leitura registrada! 🔥 Streak: **{row['streak']}** dia(s) • +15 XP"))

    @commands.command(name='perfil')
    async def perfil_prefix(self, ctx, usuario:discord.Member=None):
        alvo=usuario or ctx.author; perfil=get_perfil(alvo.id)
        if not perfil:
            from utils.db import garantir_perfil
            garantir_perfil(alvo.id, alvo.display_name); perfil=get_perfil(alvo.id)
        img=await gerar_profile_card(alvo, perfil, get_stats_usuario(alvo.id))
        await ctx.send(file=discord.File(img, filename='perfil_ivy.png'))

    @commands.command(name='perfil-frase', aliases=['frase-perfil'])
    async def perfil_frase_prefix(self, ctx, *, frase:str=None):
        if not frase: return await ctx.send(embed=embed_erro('Use: `!perfil-frase <sua frase>`'))
        atualizar_perfil_visual(ctx.author.id, ctx.author.display_name, frase=frase)
        await ctx.send(embed=embed_sucesso('Frase atualizada!'))

    @commands.command(name='perfil-wallpaper', aliases=['wallpaper'])
    async def perfil_wallpaper_prefix(self, ctx, url:str=None):
        if not url: return await ctx.send(embed=embed_erro('Use: `!perfil-wallpaper <url da imagem>`'))
        atualizar_perfil_visual(ctx.author.id, ctx.author.display_name, wallpaper_url=url)
        await ctx.send(embed=embed_sucesso('Wallpaper atualizado!'))

async def setup(bot): await bot.add_cog(Biblioteca(bot))
