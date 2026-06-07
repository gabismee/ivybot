import os, io, textwrap, aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.xp import nivel_por_xp

ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_BG = os.path.join(ROOT, 'assets', 'default_profile_bg.png')


def _font(size=28, bold=False):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


async def _download_image(url):
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10), headers={'User-Agent': 'IvyBot/1.0'}) as r:
                if r.status != 200:
                    return None
                data = await r.read()
                return Image.open(io.BytesIO(data)).convert('RGB')
    except Exception:
        return None


def _cover(img, size):
    img = img.convert('RGB')
    w, h = img.size
    tw, th = size
    scale = max(tw / w, th / h)
    nw, nh = int(w * scale), int(h * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw - tw) // 2, (nh - th) // 2, (nw + tw) // 2, (nh + th) // 2))


def _wrap_text(draw, text, font, max_width, max_lines=3):
    text = str(text or '')
    words = text.split()
    lines, current = [], ''
    for word in words:
        test = (current + ' ' + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


async def gerar_profile_card(member, perfil, stats):
    W, H = 900, 620
    bg = await _download_image(perfil.get('wallpaper_url'))
    if bg is None:
        bg = Image.open(DEFAULT_BG).convert('RGB') if os.path.exists(DEFAULT_BG) else Image.new('RGB', (W, 260), (54, 35, 86))
    bg = _cover(bg, (W, 260)).filter(ImageFilter.GaussianBlur(0.2))
    canvas = Image.new('RGB', (W, H), (246, 241, 249))
    canvas.paste(bg, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((35, 230, 865, 590), radius=32, fill=(255, 255, 255), outline=(226, 214, 235), width=3)
    avatar = await _download_image(str(member.display_avatar.url))
    if avatar:
        avatar = _cover(avatar, (128, 128)).convert('RGBA')
        mask = Image.new('L', (128, 128), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((0, 0, 128, 128), fill=255)
        canvas.paste(avatar, (70, 270), mask)
        d.ellipse((70, 270, 198, 398), outline=(155, 89, 182), width=5)
    nome = member.display_name[:26]
    frase = perfil.get('frase') or 'Livros são minha fuga favorita.'
    xp = int(perfil.get('xp') or 0)
    nivel, atual, prox = nivel_por_xp(xp)
    d.text((220, 270), nome, font=_font(42, True), fill=(48, 35, 58))
    frase_font = _font(22)
    for i, line in enumerate(_wrap_text(d, f'“{frase}”', frase_font, 610, 2)):
        d.text((220, 322 + i * 26), line, font=frase_font, fill=(97, 76, 112))
    barra_x, barra_y = 220, 382
    barra_w = 560
    pct = min(1, atual / max(1, prox))
    d.rounded_rectangle((barra_x, barra_y, barra_x + barra_w, barra_y + 22), radius=11, fill=(230, 222, 235))
    d.rounded_rectangle((barra_x, barra_y, barra_x + int(barra_w * pct), barra_y + 22), radius=11, fill=(155, 89, 182))
    d.text((barra_x, barra_y + 30), f'Nível {nivel} • XP {xp} ({atual}/{prox})', font=_font(22, True), fill=(75, 55, 86))
    cards = [
        ('Livros lidos', stats.get('lidos', 0)), ('Streak', perfil.get('streak', 0)),
        ('Média', stats.get('media_avaliacao', 0)), ('Quero ler', stats.get('wishlist', 0)),
        ('Cookies', stats.get('cookies', 0)), ('Curtidas', stats.get('curtidas', 0)), ('Cartinhas', stats.get('cartinhas', 0))
    ]
    x, y = 70, 465
    for i, (label, val) in enumerate(cards):
        cx = x + (i % 4) * 200
        cy = y + (i // 4) * 72
        d.rounded_rectangle((cx, cy, cx + 175, cy + 55), radius=16, fill=(248, 244, 251), outline=(228, 218, 236))
        d.text((cx + 14, cy + 8), str(val), font=_font(24, True), fill=(66, 44, 78))
        d.text((cx + 14, cy + 32), label, font=_font(15), fill=(110, 90, 125))
    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio


async def gerar_estante_card(member, itens, titulo='Estante'):
    W, H = 1100, 760
    canvas = Image.new('RGB', (W, H), (246, 241, 249))
    d = ImageDraw.Draw(canvas)
    d.text((40, 30), f'{titulo} de {member.display_name}', font=_font(42, True), fill=(50, 35, 60))
    x, y = 45, 110
    for idx, item in enumerate(itens[:12]):
        col = idx % 4
        row = idx // 4
        cx = x + col * 260
        cy = y + row * 205
        d.rounded_rectangle((cx, cy, cx + 235, cy + 180), radius=18, fill=(255, 255, 255), outline=(226, 214, 235), width=2)
        cover = await _download_image(item.get('capa_url'))
        if cover:
            cover = _cover(cover, (74, 112))
            canvas.paste(cover, (cx + 12, cy + 18))
        title_font = _font(16, True)
        author_font = _font(13)
        tx = cx + 96
        ty = cy + 16
        for line in _wrap_text(d, item.get('titulo', ''), title_font, 125, 3):
            d.text((tx, ty), line, font=title_font, fill=(50, 35, 60))
            ty += 20
        ay = max(ty + 4, cy + 80)
        for line in _wrap_text(d, item.get('autor', ''), author_font, 125, 2):
            d.text((tx, ay), line, font=author_font, fill=(90, 75, 100))
            ay += 17
        nota = int(item.get('avaliacao') or 0)
        if nota:
            d.text((tx, cy + 124), '★' * nota + '☆' * (5 - nota), font=_font(15), fill=(138, 102, 25))
        pagina = int(item.get('pagina_atual') or 0)
        total = int(item.get('total_paginas') or 0)
        if pagina or total:
            prog = f'Pág. {pagina}' + (f'/{total}' if total else '')
            d.text((tx, cy + 148), prog, font=_font(13, True), fill=(105, 72, 124))
    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio
