import discord
from discord import app_commands
from discord.ext import commands
from utils.api import buscar_livros
from utils.embeds import embed_biblioteca, embed_perfil, embed_erro, embed_sucesso, estrelas
from utils.db import get_biblioteca, atualizar_biblioteca, avaliar_livro, get_stats_usuario, get_perfil, add_xp, registrar_leitura, ensure_perfil, atualizar_personalizacao
from utils.profile_card import gerar_profile_card

STATUS_CHOICES=[app_commands.Choice(name="📌 Quero Ler",value="quero_ler"),app_commands.Choice(name="📖 Lendo",value="lendo"),app_commands.Choice(name="✅ Lido",value="lido"),app_commands.Choice(name="❤️ Favorito",value="favorito"),app_commands.Choice(name="🗑️ Abandonado",value="abandonado")]

class Biblioteca(commands.Cog):
    def __init__(self,bot): self.bot=bot
    estante=app_commands.Group(name="estante", description="📚 Gerencia sua biblioteca pessoal")
    perfil_config=app_commands.Group(name="perfil-config", description="🎴 Personaliza seu perfil")

    @estante.command(name="adicionar", description="Adiciona um livro à sua estante")
    @app_commands.choices(status=STATUS_CHOICES)
    async def adicionar(self, interaction, titulo:str, status:str="quero_ler"):
        await interaction.response.defer(ephemeral=True); res=await buscar_livros(titulo,1)
        if not res: return await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
        atualizar_biblioteca(interaction.user.id,res[0],status)
        xp=50 if status=="lido" else 5; add_xp(interaction.user.id, interaction.user.display_name, xp)
        await interaction.followup.send(embed=embed_sucesso(f"**{res[0]['titulo']}** adicionado! +{xp} XP"))

    @estante.command(name="ver", description="Vê sua estante por status")
    @app_commands.choices(status=STATUS_CHOICES)
    async def ver(self, interaction, status:str=None):
        await interaction.response.send_message(embed=embed_biblioteca(get_biblioteca(interaction.user.id,status), interaction.user.display_name, status or "todos"), ephemeral=True)

    @estante.command(name="stats", description="Estatísticas da sua leitura")
    async def stats(self, interaction):
        p=get_perfil(interaction.user.id) or {}; s=get_stats_usuario(interaction.user.id)
        await interaction.response.send_message(embed=embed_perfil(p,s,interaction.user.display_name,str(interaction.user.display_avatar.url)), ephemeral=True)

    @app_commands.command(name="avaliar", description="⭐ Avalia um livro")
    @app_commands.choices(estrelas_n=[app_commands.Choice(name=f"{'⭐'*i} {i}", value=i) for i in range(1,6)])
    async def avaliar(self, interaction, titulo:str, estrelas_n:int, comentario:str=""):
        await interaction.response.defer(ephemeral=True); res=await buscar_livros(titulo,1)
        if not res: return await interaction.followup.send(embed=embed_erro(f"Livro **{titulo}** não encontrado."))
        avaliar_livro(interaction.user.id,res[0],estrelas_n,comentario); add_xp(interaction.user.id, interaction.user.display_name, 10)
        e=discord.Embed(title="⭐ Avaliação registrada!", color=discord.Color.gold())
        e.add_field(name="📚 Livro",value=res[0]['titulo'],inline=False); e.add_field(name="⭐ Nota",value=estrelas(estrelas_n),inline=True)
        if comentario: e.add_field(name="💬 Comentário",value=comentario[:500],inline=False)
        if res[0].get('capa_url'): e.set_thumbnail(url=res[0]['capa_url'])
        await interaction.followup.send(embed=e)

    @app_commands.command(name="ler", description="🔥 Registra minutos de leitura e mantém streak")
    async def ler(self, interaction, minutos:int):
        if minutos <= 0: return await interaction.response.send_message(embed=embed_erro("Minutos precisa ser maior que zero."), ephemeral=True)
        streak=registrar_leitura(interaction.user.id, interaction.user.display_name, minutos)
        await interaction.response.send_message(embed=embed_sucesso(f"Leitura registrada! 🔥 Streak atual: **{streak}** dia(s). +15 XP"), ephemeral=True)

    @app_commands.command(name="perfil", description="🎴 Exibe seu cartão visual de leitor")
    async def perfil_cmd(self, interaction, usuario:discord.Member=None):
        await interaction.response.defer()
        alvo=usuario or interaction.user; ensure_perfil(alvo.id, alvo.display_name)
        perfil=get_perfil(alvo.id); stats=get_stats_usuario(alvo.id)
        img=await gerar_profile_card(alvo, perfil, stats)
        await interaction.followup.send(file=discord.File(img, filename="perfil_ivy.png"))

    @perfil_config.command(name="frase", description="Define sua frase do perfil")
    async def frase(self, interaction, texto:str):
        atualizar_personalizacao(interaction.user.id, interaction.user.display_name, frase=texto)
        await interaction.response.send_message(embed=embed_sucesso("Frase atualizada!"), ephemeral=True)

    @perfil_config.command(name="wallpaper", description="Define o papel de parede do perfil por URL")
    async def wallpaper(self, interaction, url:str):
        atualizar_personalizacao(interaction.user.id, interaction.user.display_name, wallpaper_url=url)
        await interaction.response.send_message(embed=embed_sucesso("Wallpaper atualizado!"), ephemeral=True)

    @perfil_config.command(name="resetar", description="Volta para o wallpaper padrão da Ivy")
    async def resetar(self, interaction):
        atualizar_personalizacao(interaction.user.id, interaction.user.display_name, reset_wallpaper=True)
        await interaction.response.send_message(embed=embed_sucesso("Wallpaper padrão restaurado!"), ephemeral=True)
async def setup(bot): await bot.add_cog(Biblioteca(bot))
