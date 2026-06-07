import random, io, os, aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from utils.embeds import CORES, FOOTER

# IDs dos GIFs escolhidos no Tenor para cada ação.
# O bot usa a API do Tenor para transformar o ID em URL direta de GIF.
# Não precisa configurar chave agora: usamos a chave pública de teste como fallback.
TENOR_POST_IDS = {
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
    ],
    'cafune': [
        '2031603864025875578',
        '12375925810041523960',
    ],
    'cafe': [
        '25664210',
        '16932897',
        '25345197',
    ],
    'dancar': [
        '9491878829582494737',
        '27584383',
    ],
}

# Se algum ID falhar, o bot busca por termo.
TENOR_QUERIES = {
    'abracar': 'anime hug',
    'bater': 'anime slap',
    'cafune': 'anime head pat',
    'cafe': 'anime coffee tea',
    'dancar': 'anime dance',
}

# Último fallback estático, só para nunca deixar o comando sem imagem.
ROLEPLAY_GIFS_FALLBACK = {
    'abracar': ['https://media.tenor.com/CzdSfF3Kf6cAAAAC/subaru-rem.gif'],
    'bater': ['https://media.tenor.com/8DUgGLf5KJAAAAAC/anime-hit-slap.gif'],
    'cafune': ['https://media.tenor.com/nxRSlnKOiGoAAAAC/pat-head.gif'],
    'cafe': ['https://media.tenor.com/4DWwI2EQi2sAAAAC/spy-x-family-loid-forger.gif'],
    'dancar': ['https://media.tenor.com/jmP2_KjX7sUAAAAC/oshi-no-ko.gif'],
}

TEXTOS = {
    'abracar': '{autor} abraçou {alvo} bem forte! 💜',
    'bater': '{autor} deu um tapinha de anime em {alvo}! 💥',
    'cafune': '{autor} fez cafuné em {alvo}. 🥺',
    'cafe': '{autor} tomou café/chá com {alvo}. ☕',
    'dancar': '{autor} dançou com {alvo}! ✨',
}

TENOR_API_KEY = os.getenv('TENOR_API_KEY', 'LIVDSRZULELA')

async def _gif_url_from_tenor_item(item: dict) -> str | None:
    """Extrai uma URL direta de GIF de um item retornado pela API v2 do Tenor."""
    formats = item.get('media_formats', {}) or {}
    for fmt in ('gif', 'mediumgif', 'tinygif'):
        url = (formats.get(fmt) or {}).get('url')
        if url:
            return url
    return None


async def _buscar_gif_tenor(acao: str) -> str | None:
    """Busca um GIF no Tenor: primeiro pelos IDs escolhidos, depois por pesquisa."""
    key = TENOR_API_KEY or 'LIVDSRZULELA'
    timeout = aiohttp.ClientTimeout(total=8)
    headers = {'User-Agent': 'IvyBot/2.0 Discord Bot'}
    try:
        async with aiohttp.ClientSession(headers=headers) as s:
            # 1) Usar exatamente os GIFs escolhidos pela Gabi, via data-postid do Tenor.
            ids = TENOR_POST_IDS.get(acao) or []
            if ids:
                gif_id = random.choice(ids)
                params = {'ids': gif_id, 'key': key, 'media_filter': 'gif,mediumgif,tinygif'}
                async with s.get('https://tenor.googleapis.com/v2/posts', params=params, timeout=timeout) as r:
                    if r.status == 200:
                        data = await r.json()
                        results = data.get('results', [])
                        if results:
                            url = await _gif_url_from_tenor_item(results[0])
                            if url:
                                return url

            # 2) Se o ID falhar, busca por termo relacionado à ação.
            query = TENOR_QUERIES.get(acao, acao)
            params = {
                'q': query,
                'key': key,
                'limit': 20,
                'media_filter': 'gif,mediumgif,tinygif',
                'contentfilter': 'medium',
                'locale': 'pt_BR',
            }
            async with s.get('https://tenor.googleapis.com/v2/search', params=params, timeout=timeout) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                results = data.get('results', [])
                if not results:
                    return None
                item = random.choice(results)
                return await _gif_url_from_tenor_item(item)
    except Exception:
        return None
    return None

async def _obter_gif(acao: str) -> str:
    """Obtém GIF do Tenor (se configurado) ou usa fallback local."""
    url = await _buscar_gif_tenor(acao)
    if url:
        return url
    return random.choice(ROLEPLAY_GIFS_FALLBACK[acao])


class Roleplay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def enviar_acao(self, destino, autor, alvo, acao):
        if alvo and alvo.id == autor.id:
            texto = f'{autor.mention} fez `{acao}` consigo mesma(o). Autoamor, né?'
        else:
            texto = TEXTOS[acao].format(autor=autor.mention, alvo=alvo.mention if alvo else 'todo mundo')
        gif_url = await _obter_gif(acao)
        e = discord.Embed(description=texto, color=CORES['roxo'])
        e.set_image(url=gif_url)
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
