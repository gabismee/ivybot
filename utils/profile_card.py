import io, os, textwrap
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.db import get_nivel

DEFAULT_BG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "profile_default.png")

def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

async def _fetch_image(url):
    if not url: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200: return None
                if int(r.headers.get("Content-Length", "0") or 0) > 5_000_000: return None
                return Image.open(io.BytesIO(await r.read())).convert("RGBA")
    except Exception:
        return None

def _cover(im, size):
    im = im.convert("RGBA")
    w,h=im.size; tw,th=size
    scale=max(tw/w, th/h); nw,nh=int(w*scale),int(h*scale)
    im=im.resize((nw,nh), Image.LANCZOS)
    return im.crop(((nw-tw)//2,(nh-th)//2,(nw+tw)//2,(nh+th)//2))

def _rounded_mask(size, radius):
    mask=Image.new("L", size, 0); d=ImageDraw.Draw(mask); d.rounded_rectangle((0,0,*size), radius, fill=255); return mask

async def gerar_profile_card(member, perfil, stats):
    W,H=980,520
    bg = await _fetch_image(perfil.get("wallpaper_url"))
    if bg is None:
        bg=Image.open(DEFAULT_BG).convert("RGBA")
    bg=_cover(bg,(W,H)).filter(ImageFilter.GaussianBlur(0.6))
    overlay=Image.new("RGBA",(W,H),(9,7,24,95)); img=Image.alpha_composite(bg,overlay)
    draw=ImageDraw.Draw(img)
    draw.rounded_rectangle((24,24,W-24,H-24), radius=32, outline=(190,120,255,200), width=3, fill=(10,8,28,90))

    avatar=await _fetch_image(str(member.display_avatar.url))
    if avatar:
        avatar=_cover(avatar,(150,150)); mask=_rounded_mask((150,150),75); img.paste(avatar,(58,70),mask)
        draw.ellipse((58,70,208,220), outline=(198,120,255,255), width=5)

    title=_font(46, True); mid=_font(25, True); small=_font(20); tiny=_font(17)
    nivel=get_nivel(perfil.get("xp",0))
    draw.text((235,85), member.display_name[:24], font=title, fill=(255,255,255,255))
    draw.text((238,145), f"Nível {nivel['nivel']}  •  {perfil.get('xp',0)} XP", font=mid, fill=(218,170,255,255))
    # XP bar
    bx,by,bw,bh=238,185,430,18
    draw.rounded_rectangle((bx,by,bx+bw,by+bh), radius=9, fill=(35,28,64,230))
    frac=min(1, nivel['atual_no_nivel']/max(1,nivel['necessario_nivel']))
    draw.rounded_rectangle((bx,by,bx+int(bw*frac),by+bh), radius=9, fill=(180,96,255,240))

    cards=[("📚",stats.get('lidos',0),"Livros lidos"),("🔥",perfil.get('streak',0),"Streak"),("⭐",stats.get('media_avaliacao',0),"Média"),("🍪",stats.get('cookies',0),"Cookies"),("💜",stats.get('curtidas',0),"Curtidas"),("💌",stats.get('cartinhas',0),"Cartinhas")]
    x0,y0=58,265
    for i,(ico,num,label) in enumerate(cards):
        x=x0+(i%3)*285; y=y0+(i//3)*86
        draw.rounded_rectangle((x,y,x+250,y+64), radius=16, fill=(15,13,38,190), outline=(126,83,184,150))
        draw.text((x+18,y+12), f"{ico} {num}", font=mid, fill=(255,255,255,255))
        draw.text((x+18,y+40), label, font=tiny, fill=(215,205,230,255))

    frase=perfil.get("frase") or "Livros são minha fuga favorita. 💜"
    wrapped="\n".join(textwrap.wrap(f'“{frase}”', width=42)[:3])
    draw.rounded_rectangle((58,438,922,485), radius=18, fill=(15,13,38,190), outline=(126,83,184,120))
    draw.text((82,450), wrapped, font=small, fill=(245,238,255,255))
    out=io.BytesIO(); img.convert("RGB").save(out, format="PNG", quality=95); out.seek(0); return out
