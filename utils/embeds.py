import discord
from datetime import datetime

CORES = {
    "azul": discord.Color.from_rgb(88, 101, 242),
    "verde": discord.Color.from_rgb(87, 242, 135),
    "vermelho": discord.Color.from_rgb(237, 66, 69),
    "amarelo": discord.Color.from_rgb(254, 231, 92),
    "roxo": discord.Color.from_rgb(155, 89, 182),
    "laranja": discord.Color.from_rgb(230, 126, 34),
    "cinza": discord.Color.from_rgb(142, 146, 151),
}
FOOTER = "Ivy 📚 • Feito pela Gabi 🌷"

def estrelas(n:int)->str:
    n=max(0,min(5,int(n or 0))); return "⭐"*n + "☆"*(5-n)

def formato_preco(preco)->str:
    return "Preço indisponível" if preco is None else f"R$ {float(preco):.2f}".replace('.', ',')

def embed_livro(livro:dict, links:list[dict]=None, cor=None)->discord.Embed:
    e=discord.Embed(title=f"📚 {livro.get('titulo','Sem título')}", color=cor or CORES["azul"], timestamp=datetime.utcnow())
    if livro.get("capa_url"): e.set_thumbnail(url=livro["capa_url"])
    for nome,chave,inline in [("✍️ Autor","autor",True),("🏢 Editora","editora",True),("📅 Ano","ano",True),("📄 Páginas","paginas",True),("🔢 ISBN","isbn",True)]:
        if livro.get(chave): e.add_field(name=nome,value=str(livro[chave]),inline=inline)
    if livro.get("generos"):
        g=livro["generos"]; e.add_field(name="🏷️ Categorias", value=", ".join(g[:3]) if isinstance(g,list) else str(g), inline=True)
    if livro.get("preco") is not None:
        loja=livro.get("loja_preco") or "Google Books"
        valor=f"**{formato_preco(livro.get('preco'))}**\nFonte: {loja}"
        if livro.get("buy_link"): valor += f"\n[Comprar]({livro['buy_link']})"
        e.add_field(name="💰 Preço", value=valor, inline=True)
    if livro.get("avaliacao_google"):
        e.add_field(name="⭐ Avaliação Google", value=f"{livro['avaliacao_google']}/5 ({livro.get('votos_google',0)} votos)", inline=True)
    if livro.get("sinopse"):
        sinopse=livro["sinopse"]
        if len(sinopse)>400: sinopse=sinopse[:397]+"..."
        e.add_field(name="📝 Sinopse", value=sinopse, inline=False)
    if links:
        texto=[]
        for l in links[:6]:
            p=f" — {formato_preco(l.get('preco'))}" if l.get('preco') else ""
            texto.append(f"[{l['loja']}]({l['url']}){p}")
        e.add_field(name="🛍️ Onde Comprar", value="\n".join(texto), inline=False)
    e.set_footer(text=FOOTER)
    return e

def embed_wishlist(items, username):
    e=discord.Embed(title=f"❤️ Lista de Desejos de {username}", color=CORES["roxo"], timestamp=datetime.utcnow())
    if not items: e.description="Sua lista está vazia! Use `/desejo adicionar <livro>` para começar."; return e
    for i,item in enumerate(items[:20],1):
        alvo=f"🎯 Alerta: {formato_preco(item.get('preco_alvo'))}" if item.get('preco_alvo') else "—"
        e.add_field(name=f"{i}. {item['titulo'][:50]}", value=f"✍️ {item.get('autor','')}\n{alvo}", inline=True)
    e.set_footer(text=f"{len(items)} livro(s) • {FOOTER}"); return e

def embed_biblioteca(itens, username, status_label):
    ic={"quero_ler":"📌","lendo":"📖","lido":"✅","favorito":"❤️","abandonado":"🗑️"}.get(status_label,"📚")
    e=discord.Embed(title=f"{ic} Estante de {username} — {status_label.replace('_',' ').title()}", color=CORES["verde"], timestamp=datetime.utcnow())
    if not itens: e.description="Nenhum livro nessa categoria ainda."; return e
    for item in itens[:15]:
        av=f" {estrelas(item.get('avaliacao'))}" if item.get('avaliacao') else ""
        e.add_field(name=f"📚 {item['titulo'][:45]}", value=f"✍️ {item.get('autor','')}{av}", inline=True)
    e.set_footer(text=f"{len(itens)} livro(s) • {FOOTER}"); return e

def embed_perfil(perfil, stats, username, avatar_url=None):
    e=discord.Embed(title=f"👤 Perfil de {username}", color=CORES["azul"], timestamp=datetime.utcnow())
    if avatar_url: e.set_thumbnail(url=avatar_url)
    e.add_field(name="📚 Livros Lidos", value=str(stats.get("lidos",0)), inline=True)
    e.add_field(name="⭐ Média", value=str(stats.get("media_avaliacao",0)), inline=True)
    e.add_field(name="🔥 Streak", value=str(perfil.get("streak",0)), inline=True)
    e.add_field(name="🌱 XP", value=str(perfil.get("xp",0)), inline=True)
    e.add_field(name="🍪 Cookies", value=str(stats.get("cookies",0)), inline=True)
    e.add_field(name="💜 Curtidas", value=str(stats.get("curtidas",0)), inline=True)
    e.add_field(name="💌 Cartinhas", value=str(stats.get("cartinhas",0)), inline=True)
    if perfil.get("frase"): e.add_field(name="💭 Frase", value=perfil["frase"], inline=False)
    if perfil.get("generos"): e.add_field(name="🏷️ Gêneros", value=", ".join(perfil["generos"][:5]), inline=False)
    e.set_footer(text=FOOTER); return e

def embed_promocao(livro, preco_atual, preco_anterior=None, loja="Loja", url=""):
    e=discord.Embed(title=f"🔥 {livro.get('titulo','Promoção de livro')}", color=CORES["vermelho"], timestamp=datetime.utcnow())
    e.add_field(name="💰 Preço", value=f"**{formato_preco(preco_atual)}**", inline=True)
    if preco_anterior: e.add_field(name="Antes", value=formato_preco(preco_anterior), inline=True)
    if livro.get("autor"): e.add_field(name="✍️ Autor", value=livro["autor"], inline=True)
    if url: e.add_field(name="🛒 Link", value=f"[Comprar em {loja}]({url})", inline=False)
    if livro.get("capa_url"): e.set_thumbnail(url=livro["capa_url"])
    e.set_footer(text=FOOTER); return e

def embed_ranking(titulo, itens, tipo="wishlist"):
    e=discord.Embed(title=f"🏆 {titulo}", color=CORES["amarelo"], timestamp=datetime.utcnow())
    if not itens: e.description="Ainda não há dados suficientes."; return e
    for i,item in enumerate(itens[:10],1):
        if tipo=="avaliacoes": val=f"⭐ {round(float(item.get('media') or 0),1)}/5 • {item.get('votos',0)} votos"
        elif tipo=="xp": val=f"🌱 {item.get('xp',0)} XP • 🔥 {item.get('streak',0)} dias"
        else: val=f"❤️ {item.get('total',0)} pessoas"
        e.add_field(name=f"{i}. {item.get('titulo') or item.get('username') or item.get('user_id')}", value=val, inline=False)
    e.set_footer(text=FOOTER); return e

def embed_erro(mensagem):
    return discord.Embed(description=f"❌ {mensagem}", color=CORES["vermelho"])
def embed_sucesso(mensagem):
    e=discord.Embed(description=f"✅ {mensagem}", color=CORES["verde"]); e.set_footer(text=FOOTER); return e
