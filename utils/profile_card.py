import os, io, re, aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.xp import nivel_por_xp

ROOT        = os.path.dirname(os.path.dirname(__file__))
DEFAULT_BG  = os.path.join(ROOT, 'assets', 'default_profile_bg.png')

# Paleta do card inferior (escuro)
COR_CARD_BG      = (28, 24, 36)    # cinza-roxo quase preto
COR_CARD_BORDA   = (58, 50, 72)
COR_TEXTO_NOME   = (245, 240, 255) # branco levemente roxo
COR_TEXTO_FRASE  = (190, 175, 210) # cinza lavanda
COR_BARRA_BG     = (55, 48, 65)
COR_BARRA_FILL   = (155, 89, 182)  # roxo
COR_BARRA_TEXTO  = (210, 195, 225)
COR_STAT_BG      = (42, 36, 54)
COR_STAT_BORDA   = (72, 62, 88)
COR_STAT_VAL     = (245, 235, 255)
COR_STAT_LABEL   = (150, 135, 170)
COR_AV_BORDA     = (155, 89, 182)

# Labels das estatísticas (sem emoji para evitar quadrados)
STAT_LABELS = [
    ('Livros lidos', 'lidos'),
    ('Streak',       'streak_perfil'),   # vem do perfil
    ('Media',        'media_avaliacao'),
    ('Quer ler',     'wishlist'),
    ('Cookies',      'cookies'),
    ('Curtidas',     'curtidas'),
    ('Cartas',       'cartinhas'),
]


def _font(size=28, bold=False):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'    if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'     if bold else '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    ]
    for p in paths:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()


async def _download_image(url):
    if not url: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10), headers={'User-Agent': 'IvyBot/2.0'}) as r:
                if r.status != 200: return None
                return Image.open(io.BytesIO(await r.read())).convert('RGB')
    except Exception:
        return None


def _cover(img, size):
    img = img.convert('RGB')
    w, h = img.size; tw, th = size
    scale = max(tw/w, th/h)
    nw, nh = int(w*scale), int(h*scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw-tw)//2, (nh-th)//2, (nw+tw)//2, (nh+th)//2))


def _safe(text):
    """Remove caracteres fora do range latino (evita quadrados em imgs)."""
    return re.sub(r'[^\x00-\x7FÀ-ÿ ]', '', str(text or '')).strip()


def _wrap(draw, text, font, max_w, max_lines=2):
    words = text.split(); lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
        if len(lines) >= max_lines: break
    if cur and len(lines) < max_lines: lines.append(cur)
    return lines[:max_lines]


async def gerar_profile_card(member, perfil, stats):
    W, H      = 900, 640
    WALL_H    = 210   # wallpaper ocupa só o topo
    AV_SIZE   = 112
    CARD_Y    = WALL_H + 8

    # ── 1. Wallpaper ──────────────────────────────────────────────────────────
    bg = await _download_image(perfil.get('wallpaper_url'))
    if bg is None:
        bg = Image.open(DEFAULT_BG).convert('RGB') if os.path.exists(DEFAULT_BG) \
             else Image.new('RGB', (W, WALL_H), (54, 35, 86))
    bg = _cover(bg, (W, WALL_H)).filter(ImageFilter.GaussianBlur(0.3))

    # ── 2. Canvas ─────────────────────────────────────────────────────────────
    canvas = Image.new('RGB', (W, H), COR_CARD_BG)
    canvas.paste(bg, (0, 0))  # wallpaper colado no topo

    d = ImageDraw.Draw(canvas)

    # Card inferior escuro (do fim do wallpaper até embaixo)
    d.rounded_rectangle(
        (0, CARD_Y, W, H),
        radius=0,
        fill=COR_CARD_BG,
    )
    # Linha divisória sutil no topo do card
    d.line([(0, CARD_Y), (W, CARD_Y)], fill=COR_CARD_BORDA, width=2)

    # ── 3. Avatar (metade no wallpaper, metade no card) ───────────────────────
    AV_X = 48
    AV_Y = WALL_H - AV_SIZE // 2

    avatar = await _download_image(str(member.display_avatar.url))
    if avatar:
        avatar = _cover(avatar, (AV_SIZE, AV_SIZE)).convert('RGBA')
        mask   = Image.new('L', (AV_SIZE, AV_SIZE), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, AV_SIZE, AV_SIZE), fill=255)
        # borda escura + roxo
        d.ellipse((AV_X-5, AV_Y-5, AV_X+AV_SIZE+5, AV_Y+AV_SIZE+5), fill=COR_CARD_BG)
        d.ellipse((AV_X-3, AV_Y-3, AV_X+AV_SIZE+3, AV_Y+AV_SIZE+3), outline=COR_AV_BORDA, width=4)
        canvas.paste(avatar, (AV_X, AV_Y), mask)

    # ── 4. Nome e frase ───────────────────────────────────────────────────────
    INFO_X = AV_X + AV_SIZE + 18
    INFO_Y = CARD_Y + 14

    nome_safe  = _safe(member.display_name)[:28] or member.name[:28]
    frase_safe = _safe(perfil.get('frase') or 'Livros sao minha fuga favorita.')

    d.text((INFO_X, INFO_Y), nome_safe, font=_font(38, True), fill=COR_TEXTO_NOME)

    f_font = _font(20)
    for i, line in enumerate(_wrap(d, f'"{frase_safe}"', f_font, W - INFO_X - 50, 2)):
        d.text((INFO_X, INFO_Y + 46 + i * 24), line, font=f_font, fill=COR_TEXTO_FRASE)

    # ── 5. Barra de XP ────────────────────────────────────────────────────────
    xp = int(perfil.get('xp') or 0)
    nivel, atual, prox = nivel_por_xp(xp)
    BAR_X = 48
    BAR_Y = CARD_Y + 132
    BAR_W = W - 96
    pct   = min(1.0, atual / max(1, prox))

    d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + 16), radius=8, fill=COR_BARRA_BG)
    if pct > 0:
        d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + int(BAR_W * pct), BAR_Y + 16), radius=8, fill=COR_BARRA_FILL)
    d.text((BAR_X, BAR_Y + 22), f'Nivel {nivel}  |  XP {xp}  ({atual}/{prox})', font=_font(18, True), fill=COR_BARRA_TEXTO)

    # ── 6. Cards de estatísticas ──────────────────────────────────────────────
    # streak vem do perfil, o resto de stats
    combined = dict(stats)
    combined['streak_perfil'] = perfil.get('streak', 0)

    STAT_Y   = CARD_Y + 178
    CARD_W   = 182
    CARD_H   = 58
    GAP      = 10
    cols     = 4

    for i, (label, key) in enumerate(STAT_LABELS):
        col = i % cols
        row = i // cols
        cx  = 48 + col * (CARD_W + GAP)
        cy  = STAT_Y + row * (CARD_H + GAP)
        d.rounded_rectangle((cx, cy, cx + CARD_W, cy + CARD_H), radius=12,
                             fill=COR_STAT_BG, outline=COR_STAT_BORDA, width=1)
        val = combined.get(key, 0)
        d.text((cx + 12, cy + 6),  str(val), font=_font(22, True), fill=COR_STAT_VAL)
        d.text((cx + 12, cy + 32), label,    font=_font(13),       fill=COR_STAT_LABEL)

    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio


async def gerar_estante_card(member, itens, titulo='Estante'):
    W, H = 1100, 760
    canvas = Image.new('RGB', (W, H), COR_CARD_BG)
    d      = ImageDraw.Draw(canvas)

    titulo_safe = _safe(titulo) or titulo
    nome_safe   = _safe(member.display_name) or member.name
    d.text((40, 28), f'{titulo_safe} de {nome_safe}', font=_font(36, True), fill=COR_TEXTO_NOME)

    CARD_W, CARD_H = 244, 188
    GAP_X,  GAP_Y  = 16,  16
    x, y, cols     = 40, 100, 4

    for idx, item in enumerate(itens[:12]):
        col = idx % cols
        row = idx // cols
        cx  = x + col * (CARD_W + GAP_X)
        cy  = y + row * (CARD_H + GAP_Y)
        d.rounded_rectangle((cx, cy, cx + CARD_W, cy + CARD_H), radius=14,
                             fill=COR_STAT_BG, outline=COR_STAT_BORDA, width=1)

        # Capa
        cover = await _download_image(item.get('capa_url'))
        if cover:
            cover = _cover(cover, (66, 100))
            canvas.paste(cover, (cx + 10, cy + 12))

        # Textos ao lado da capa
        tx, ty  = cx + 86, cy + 12
        max_w   = CARD_W - 86 - 8
        t_font  = _font(13, True)
        a_font  = _font(12)
        titulo_l = _safe(item.get('titulo', ''))
        autor_l  = _safe(item.get('autor', ''))

        for line in _wrap(d, titulo_l, t_font, max_w, 3):
            d.text((tx, ty), line, font=t_font, fill=COR_TEXTO_NOME); ty += 17
        ay = max(ty + 4, cy + 72)
        for line in _wrap(d, autor_l, a_font, max_w, 2):
            d.text((tx, ay), line, font=a_font, fill=COR_TEXTO_FRASE); ay += 15

        nota = int(item.get('avaliacao') or 0)
        if nota:
            d.text((tx, cy + 126), '*' * nota + '-' * (5 - nota), font=_font(13), fill=(200, 160, 60))

        pag = int(item.get('pagina_atual') or 0)
        tot = int(item.get('total_paginas') or 0)
        if pag or tot:
            prog = f'Pag. {pag}' + (f'/{tot}' if tot else '')
            d.text((tx, cy + 148), prog, font=_font(12, True), fill=COR_STAT_LABEL)

    bio = io.BytesIO()
    canvas.save(bio, 'PNG')
    bio.seek(0)
    return bio
