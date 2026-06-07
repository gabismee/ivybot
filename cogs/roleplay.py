import random, io
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from utils.embeds import CORES, FOOTER
from utils.media import tenor_gif_from_id, tenor_search_gif

ROLEPLAY_GIFS = {
    'abracar': [
        '5299348585618231224',
        '4606955245193927037',
        '4492243580644690368',
        '12099486736811549373',
        '6816284113184970956',
    ],
    'bater': [
        '17655624',
        '10475156973113460459',
        '26038183',
        '16268549',
        '11426619910221365543',
    ],
    'cafune': [
        '2031603864025875578',
        '5711182',
        '17907437',
        '12375925810041523960',
        '3422144103984916185',
    ],
    'cafe': [
        '25664210',
        '25510963',
        '2735753108991467875',
        '25345197',
        '16932897',
    ],
    'dancar': [
        '4547293782133915583',
        '9999828832175336605',
        '20808263',
        '27584383',
        '9491878829582494737',
    ],
}

ROLEPLAY_SEARCH_TERMS = {
    'abracar': 'anime hug',
    'bater': 'anime slap',
    'cafune': 'anime head pat',
    'cafe': 'anime coffee anime tea',
    'dancar': 'anime dance',
}
TEXTOS = {
    'abracar': '{autor} abraçou {alvo} bem forte! 💜',
    'bater': '{autor} deu um tapinha de anime em {alvo}! 💥',
    'cafune': '{autor} fez cafuné em {alvo}. 🥺',
    'cafe': '{autor} tomou café/chá com {alvo}. ☕',
    'dancar': '{autor} dançou com {alvo}! ✨'
}

class Roleplay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def enviar_acao(self, destino, autor, alvo, acao):
        if alvo and alvo.id == autor.id:
            texto = f'{autor.mention} fez `{acao}` consigo mesma(o). Autoamor, né?'
        else:
            texto = TEXTOS[acao].format(autor=autor.mention, alvo=alvo.mention if alvo else 'todo mundo')
        # Busca o GIF direto pela API do Tenor usando o ID escolhido.
        # A função usa TENOR_API_KEY do Render ou a chave de teste LIVDSRZULELA.
        gif_id = random.choice(ROLEPLAY_GIFS[acao])
        gif_url = await tenor_gif_from_id(gif_id)

        # Se algum ID falhar, tenta busca por termo como plano B.
        if not gif_url:
            gif_url = await tenor_search_gif(ROLEPLAY_SEARCH_TERMS.get(acao, 'anime reaction'))

        e = discord.Embed(description=texto, color=CORES['roxo'])
        if gif_url:
            e.set_image(url=gif_url)
        else:
            e.add_field(
                name='GIF indisponível',
                value='Não consegui carregar o GIF agora. Tenta de novo em alguns segundos.',
                inline=False,
            )
        e.set_footer(text=FOOTER)
        if hasattr(destino, 'response'):
            await destino.response.send_message(embed=e)
        else:
            await destino.send(embed=e)

    @app_commands.command(name='abracar', description='💜 Abraça alguém')
    async def abracar(self, interaction, usuario: discord.Member): await self.enviar_acao(interaction, interaction.user, usuario, 'abracar')
    @app_commands.command(name='bater', description='💥 Bate em alguém no estilo anime')
    async def bater(self, interaction, usuario: discord.Member): await self.enviar_acao(interaction, interaction.user, usuario, 'bater')
    @app_commands.command(name='cafune', description='🥺 Faz cafuné em alguém')
    async def cafune(self, interaction, usuario: discord.Member): await self.enviar_acao(interaction, interaction.user, usuario, 'cafune')
    @app_commands.command(name='cafe', description='☕ Toma café/chá com alguém')
    async def cafe(self, interaction, usuario: discord.Member): await self.enviar_acao(interaction, interaction.user, usuario, 'cafe')
    @app_commands.command(name='dancar', description='✨ Dança com alguém')
    async def dancar(self, interaction, usuario: discord.Member): await self.enviar_acao(interaction, interaction.user, usuario, 'dancar')

    @commands.command(name='abracar', aliases=['abraçar','hug'])
    async def abracar_p(self, ctx, usuario: discord.Member=None): await self.enviar_acao(ctx, ctx.author, usuario, 'abracar')
    @commands.command(name='bater', aliases=['hit','tapa'])
    async def bater_p(self, ctx, usuario: discord.Member=None): await self.enviar_acao(ctx, ctx.author, usuario, 'bater')
    @commands.command(name='cafune', aliases=['cafuné','pat'])
    async def cafune_p(self, ctx, usuario: discord.Member=None): await self.enviar_acao(ctx, ctx.author, usuario, 'cafune')
    @commands.command(name='cafe', aliases=['café','cha','chá'])
    async def cafe_p(self, ctx, usuario: discord.Member=None): await self.enviar_acao(ctx, ctx.author, usuario, 'cafe')
    @commands.command(name='dancar', aliases=['dançar','dance'])
    async def dancar_p(self, ctx, usuario: discord.Member=None): await self.enviar_acao(ctx, ctx.author, usuario, 'dancar')

    async def _ship_image(self, user1, user2, label):
        bg = Image.new('RGB', (800, 300), '#1b102b')
        draw = ImageDraw.Draw(bg)
        try: font_big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 42)
        except Exception: font_big = None
        for i,u in enumerate([user1,user2]):
            data = await u.display_avatar.with_size(256).read()
            av = Image.open(io.BytesIO(data)).convert('RGBA').resize((170,170))
            mask = Image.new('L', (170,170), 0); ImageDraw.Draw(mask).ellipse((0,0,170,170), fill=255)
            x = 85 if i==0 else 545
            bg.paste(av, (x,55), mask)
        pct=random.randint(1,100)
        draw.text((360,85), '💜', font=font_big, fill='#f8c8dc')
        draw.text((320,145), f'{pct}%', font=font_big, fill='#d8b4fe')
        draw.text((230,230), label[:28], font=font_big, fill='#ffffff')
        out=io.BytesIO(); bg.save(out, 'PNG'); out.seek(0)
        return out, pct

    @app_commands.command(name='ship', description='💜 Faz ship entre dois usuários')
    async def ship(self, interaction, usuario1: discord.Member, usuario2: discord.Member):
        await interaction.response.defer()
        img,pct=await self._ship_image(usuario1, usuario2, 'Ship literário')
        await interaction.followup.send(content=f'💜 Ship de {usuario1.mention} + {usuario2.mention}: **{pct}%**', file=discord.File(img, 'ship.png'))

    @commands.command(name='ship')
    async def ship_p(self, ctx, usuario1: discord.Member=None, usuario2: discord.Member=None):
        usuario1 = usuario1 or ctx.author
        usuario2 = usuario2 or ctx.author
        img,pct=await self._ship_image(usuario1, usuario2, 'Ship literário')
        await ctx.send(content=f'💜 Ship de {usuario1.mention} + {usuario2.mention}: **{pct}%**', file=discord.File(img, 'ship.png'))

    @app_commands.command(name='ship-personagem', description='📚 Faz ship com personagens literários')
    async def ship_personagem(self, interaction, personagem1: str, personagem2: str):
        pct=random.randint(1,100)
        e=discord.Embed(title='💜 Ship Literário', description=f'**{personagem1}** + **{personagem2}**\nCompatibilidade: **{pct}%**', color=CORES['rosa'])
        await interaction.response.send_message(embed=e)

    @commands.command(name='ship-personagem', aliases=['shippersonagem'])
    async def ship_personagem_p(self, ctx, personagem1: str=None, *, personagem2: str=None):
        if not personagem1 or not personagem2: return await ctx.send('Use: `!ship-personagem Hermione Draco`')
        pct=random.randint(1,100)
        e=discord.Embed(title='💜 Ship Literário', description=f'**{personagem1}** + **{personagem2}**\nCompatibilidade: **{pct}%**', color=CORES['rosa'])
        await ctx.send(embed=e)

    @app_commands.command(name='duelo', description='⚔️ Duelo literário rápido')
    async def duelo(self, interaction, usuario: discord.Member):
        frases=['citou Machado de Assis e venceu no argumento','invocou um plot twist absurdo','abriu um livro mágico e ganhou +10 de sabedoria','perdeu porque confundiu autor com personagem']
        vencedor=random.choice([interaction.user, usuario])
        perdedor=usuario if vencedor.id==interaction.user.id else interaction.user
        e=discord.Embed(title='⚔️ Duelo Literário', description=f'{interaction.user.mention} desafiou {usuario.mention}!\n\n🏆 {vencedor.mention} venceu: {random.choice(frases)}.\n😵 {perdedor.mention} foi derrotado(a).', color=CORES['dourado'])
        await interaction.response.send_message(embed=e)

    @commands.command(name='duelo')
    async def duelo_p(self, ctx, usuario: discord.Member=None):
        if not usuario: return await ctx.send('Use: `!duelo @pessoa`')
        vencedor=random.choice([ctx.author, usuario]); perdedor=usuario if vencedor.id==ctx.author.id else ctx.author
        e=discord.Embed(title='⚔️ Duelo Literário', description=f'{ctx.author.mention} desafiou {usuario.mention}!\n\n🏆 {vencedor.mention} venceu o duelo literário.\n😵 {perdedor.mention} perdeu.', color=CORES['dourado'])
        await ctx.send(embed=e)

async def setup(bot): await bot.add_cog(Roleplay(bot))
