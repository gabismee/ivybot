import os, io, textwrap, aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.xp import nivel_por_xp

ROOT=os.path.dirname(os.path.dirname(__file__))
DEFAULT_BG=os.path.join(ROOT,'assets','default_profile_bg.png')

def _font(size=28, bold=False):
    paths=[
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'
    ]
    for p in paths:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

async def _download_image(url):
    if not url: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200: return None
                data=await r.read(); return Image.open(io.BytesIO(data)).convert('RGB')
    except Exception: return None

def _cover(img, size):
    img=img.convert('RGB'); w,h=img.size; tw,th=size; scale=max(tw/w, th/h); nw,nh=int(w*scale), int(h*scale); img=img.resize((nw,nh), Image.LANCZOS); return img.crop(((nw-tw)//2,(nh-th)//2,(nw+tw)//2,(nh+th)//2))

async def gerar_profile_card(member, perfil, stats):
    W,H=900,620
    bg=await _download_image(perfil.get('wallpaper_url'))
    if bg is None:
        bg=Image.open(DEFAULT_BG).convert('RGB') if os.path.exists(DEFAULT_BG) else Image.new('RGB',(W,260),(54,35,86))
    bg=_cover(bg,(W,260)).filter(ImageFilter.GaussianBlur(0.2))
    canvas=Image.new('RGB',(W,H),(246,241,249)); canvas.paste(bg,(0,0))
    d=ImageDraw.Draw(canvas)
    # painel info embaixo para preservar wallpaper
    d.rounded_rectangle((35,230,865,590), radius=32, fill=(255,255,255), outline=(226,214,235), width=3)
    # avatar
    avatar=await _download_image(str(member.display_avatar.url))
    if avatar:
        avatar=_cover(avatar,(128,128)).convert('RGBA')
        mask=Image.new('L',(128,128),0); md=ImageDraw.Draw(mask); md.ellipse((0,0,128,128), fill=255)
        canvas.paste(avatar,(70,270),mask); d.ellipse((70,270,198,398), outline=(155,89,182), width=5)
    nome=member.display_name[:26]
    frase=perfil.get('frase') or 'Livros são minha fuga favorita.'
    xp=int(perfil.get('xp') or 0); nivel, atual, prox=nivel_por_xp(xp)
    d.text((220,270), nome, font=_font(42,True), fill=(48,35,58))
    d.text((220,322), f'"{frase[:90]}"', font=_font(24), fill=(97,76,112))
    barra_x, barra_y=220,370; barra_w=560; pct=min(1, atual/max(1,prox))
    d.rounded_rectangle((barra_x,barra_y,barra_x+barra_w,barra_y+22), radius=11, fill=(230,222,235))
    d.rounded_rectangle((barra_x,barra_y,barra_x+int(barra_w*pct),barra_y+22), radius=11, fill=(155,89,182))
    d.text((barra_x,barra_y+30), f'Nível {nivel} • XP {xp} ({atual}/{prox})', font=_font(22,True), fill=(75,55,86))
    cards=[('Livros lidos',stats.get('lidos',0)),('Streak',perfil.get('streak',0)),('Média',stats.get('media_avaliacao',0)),('Quero ler',stats.get('wishlist',0)),('Cookies',stats.get('cookies',0)),('Curtidas',stats.get('curtidas',0)),('Cartinhas',stats.get('cartinhas',0))]
    x,y=70,455
    for i,(label,val) in enumerate(cards):
        cx=x+(i%4)*200; cy=y+(i//4)*72
        d.rounded_rectangle((cx,cy,cx+175,cy+55), radius=16, fill=(248,244,251), outline=(228,218,236))
        d.text((cx+14,cy+8), str(val), font=_font(24,True), fill=(66,44,78))
        d.text((cx+14,cy+32), label, font=_font(15), fill=(110,90,125))
    bio=io.BytesIO(); canvas.save(bio,'PNG'); bio.seek(0); return bio

async def gerar_estante_card(member, itens, titulo='Estante'):
    W,H=1000,700; canvas=Image.new('RGB',(W,H),(246,241,249)); d=ImageDraw.Draw(canvas)
    d.text((40,30), f'{titulo} de {member.display_name}', font=_font(42,True), fill=(50,35,60))
    x,y=45,110
    for idx,item in enumerate(itens[:12]):
        col=idx%4; row=idx//4; cx=x+col*235; cy=y+row*180
        d.rounded_rectangle((cx,cy,cx+210,cy+155), radius=18, fill=(255,255,255), outline=(226,214,235), width=2)
        cover=await _download_image(item.get('capa_url'))
        if cover:
            cover=_cover(cover,(70,105)); canvas.paste(cover,(cx+12,cy+18))
        d.text((cx+92,cy+18), textwrap.shorten(item.get('titulo',''), width=22), font=_font(17,True), fill=(50,35,60))
        d.text((cx+92,cy+50), textwrap.shorten(item.get('autor',''), width=24), font=_font(14), fill=(90,75,100))
        nota=int(item.get('avaliacao') or 0); d.text((cx+92,cy+84), '★'*nota+'☆'*(5-nota), font=_font(17), fill=(138,102,25))
    bio=io.BytesIO(); canvas.save(bio,'PNG'); bio.seek(0); return bio
