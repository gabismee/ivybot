import os, io, textwrap, aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.xp import nivel_por_xp

ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_BG = os.path.join(ROOT, 'assets', 'default_profile_bg.png')

# Usar apenas ASCII/texto nos ícones para evitar quadrados em sistemas sem emoji font
ICON_LIVROS   = '[Lidos]'
ICON_STREAK   = '[Streak]'
ICON_MEDIA    = '[Media]'
ICON_QUERO    = '[Quer ler]'
ICON_COOKIES  = '[Cookies]'
ICON_CURTIDAS = '[Curtidas]'
ICON_CARTAS   = '[Cartas]'


def _font(size=28, bold=False):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf' if bold else '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
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
    return lines[:max_lines]


async def gerar_profile_card(member, perfil, stats):
    W, H = 900, 640

    # ── Wallpaper (topo, altura fixa 220px) ──
    WALL_H = 220
    bg = await _download_image(perfil.get('wallpaper_url'))
    if bg is None:
        bg = Image.open(DEFAULT_BG).convert('RGB') if os.path.exists(DEFAULT_BG) else Image.new('RGB', (W, WALL_H), (54, 35, 86))
    bg = _cover(bg, (W, WALL_H)).filter(ImageFilter.GaussianBlur(0.5))

    canvas = Image.new('RGB', (W, H), (246, 241, 249))
    canvas.paste(bg, (0, 0))  # wallpaper no topo, sem sobrepor info

    d = ImageDraw.Draw(canvas)

    # ── Card de informações (abaixo do wallpaper) ──
    CARD_Y = WALL_H + 10
    d.rounded_rectangle((30, CARD_Y, W - 30, H - 20), radius=28, fill=(255, 255, 255), outline=(226, 214, 235), width=2)

    # ── Avatar (posicionado na borda do wallpaper/card) ──
    avatar = await _download_image(str(member.display_avatar.url))
    AV_SIZE = 110
    AV_X, AV_Y = 55, WALL_H - AV_SIZE // 2  # metade sobre o wallpaper, metade no card
    if avatar:
        avatar = _cover(avatar, (AV_SIZE, AV_SIZE)).convert('RGBA')
        mask = Image.new('L', (AV_SIZE, AV_SIZE), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((0, 0, AV_SIZE, AV_SIZE), fill=255)
        # Borda branca antes do avatar
        d.ellipse((AV_X - 4, AV_Y - 4, AV_X + AV_SIZE + 4, AV_Y + AV_SIZE + 4), fill=(255, 255, 255))
        d.ellipse((AV_X - 2, AV_Y - 2, AV_X + AV_SIZE + 2, AV_Y + AV_SIZE + 2), outline=(155, 89, 182), width=4)
        canvas.paste(avatar, (AV_X, AV_Y), mask)

    # ── Nome e frase ──
    INFO_X = AV_X + AV_SIZE + 20
    INFO_Y = CARD_Y + 18
    nome = member.display_name[:28]
    frase = perfil.get('frase') or 'Livros sao minha fuga favorita.'
    # Remove emojis que causam quadrados — mantém apenas ASCII e caracteres latinos
    import re
    frase_safe = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', frase).strip() or 'Livros sao minha fuga favorita.'
    nome_safe  = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', nome).strip() or member.name[:28]

    d.text((INFO_X, INFO_Y), nome_safe, font=_font(36, True), fill=(48, 35, 58))
    frase_font = _font(20)
    for i, line in enumerate(_wrap_text(d, f'"{frase_safe}"', frase_font, W - INFO_X - 60, 2)):
        d.text((INFO_X, INFO_Y + 44 + i * 24), line, font=frase_font, fill=(97, 76, 112))

    # ── Barra de XP ──
    xp = int(perfil.get('xp') or 0)
    nivel, atual, prox = nivel_por_xp(xp)
    BAR_X = 55
    BAR_Y = CARD_Y + 130
    BAR_W = W - 110
    pct = min(1, atual / max(1, prox))
    d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + 18), radius=9, fill=(230, 222, 235))
    if pct > 0:
        d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + int(BAR_W * pct), BAR_Y + 18), radius=9, fill=(155, 89, 182))
    d.text((BAR_X, BAR_Y + 24), f'Nivel {nivel}  •  XP {xp}  ({atual}/{prox})', font=_font(19, True), fill=(75, 55, 86))

    # ── Cards de estatísticas ──
    cards = [
        (ICON_LIVROS,  stats.get('lidos', 0)),
        (ICON_STREAK,  perfil.get('streak', 0)),
        (ICON_MEDIA,   stats.get('media_avaliacao', 0)),
        (ICON_QUERO,   stats.get('wishlist', 0)),
        (ICON_COOKIES, stats.get('cookies', 0)),
        (ICON_CURTIDAS,stats.get('curtidas', 0)),
        (ICON_CARTAS,  stats.get('cartinhas', 0)),
    ]
    STAT_Y = CARD_Y + 185
    CARD_W = 180
    CARD_H = 58
    GAP = 12
    cols = 4
    for i, (label, val) in enumerate(cards):
        col = i % cols
        row = i // cols
        cx = 55 + col * (CARD_W + GAP)
        cy = STAT_Y + row * (CARD_H + GAP)
        d.rounded_rectangle((cx, cy, cx + CARD_W, cy + CARD_H), radius=14, fill=(248, 244, 251), outline=(228, 218, 236))
        d.text((cx + 12, cy + 6),  str(val),  font=_font(22, True), fill=(66, 44, 78))
        d.text((cx + 12, cy + 32), label,     font=_font(13),       fill=(110, 90, 125))

    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio


async def gerar_estante_card(member, itens, titulo='Estante'):
    W, H = 1100, 760
    canvas = Image.new('RGB', (W, H), (246, 241, 249))
    d = ImageDraw.Draw(canvas)
    import re
    titulo_safe = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', titulo).strip() or titulo
    nome_safe   = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', member.display_name).strip() or member.name
    d.text((40, 30), f'{titulo_safe} de {nome_safe}', font=_font(38, True), fill=(50, 35, 60))

    x, y = 45, 110
    CARD_W, CARD_H = 240, 185
    GAP_X, GAP_Y = 18, 18
    cols = 4

    for idx, item in enumerate(itens[:12]):
        col = idx % cols
        row = idx // cols
        cx = x + col * (CARD_W + GAP_X)
        cy = y + row * (CARD_H + GAP_Y)
        d.rounded_rectangle((cx, cy, cx + CARD_W, cy + CARD_H), radius=16, fill=(255, 255, 255), outline=(226, 214, 235), width=2)

        cover = await _download_image(item.get('capa_url'))
        if cover:
            cover = _cover(cover, (68, 100))
            canvas.paste(cover, (cx + 10, cy + 14))

        # Texto à direita da capa
        tx = cx + 88
        ty = cy + 14
        title_font = _font(14, True)
        author_font = _font(12)
        max_text_w = CARD_W - 88 - 10  # largura disponível para texto

        titulo_livro = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', item.get('titulo', '')).strip()
        autor_livro  = re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', item.get('autor', '')).strip()

        for line in _wrap_text(d, titulo_livro, title_font, max_text_w, 3):
            d.text((tx, ty), line, font=title_font, fill=(50, 35, 60))
            ty += 18

        ay = max(ty + 4, cy + 74)
        for line in _wrap_text(d, autor_livro, author_font, max_text_w, 2):
            d.text((tx, ay), line, font=author_font, fill=(90, 75, 100))
            ay += 15

        nota = int(item.get('avaliacao') or 0)
        if nota:
            d.text((tx, cy + 124), '*' * nota + '-' * (5 - nota), font=_font(14), fill=(138, 102, 25))

        pagina = int(item.get('pagina_atual') or 0)
        total  = int(item.get('total_paginas') or 0)
        if pagina or total:
            prog = f'Pag. {pagina}' + (f'/{total}' if total else '')
            d.text((tx, cy + 148), prog, font=_font(12, True), fill=(105, 72, 124))

    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio
