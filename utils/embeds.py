import discord
from datetime import datetime

CORES = {
    # Paleta pastel da Ivy
    "azul": discord.Color.from_rgb(189, 224, 254),
    "verde": discord.Color.from_rgb(205, 234, 192),
    "vermelho": discord.Color.from_rgb(255, 179, 186),
    "amarelo": discord.Color.from_rgb(255, 241, 182),
    "roxo": discord.Color.from_rgb(216, 180, 254),
    "laranja": discord.Color.from_rgb(255, 214, 165),
    "rosa": discord.Color.from_rgb(248, 200, 220),
    "cinza": discord.Color.from_rgb(220, 220, 230),
    "dourado": discord.Color.from_rgb(255, 232, 150),
}
FOOTER = "Ivy 📚 • Feito pela Gabi 🌷"

def estrelas(n:int)->str:
    n=max(0,min(5,int(round(float(n or 0))))); return "⭐"*n + "☆"*(5-n)

def formato_preco(preco, moeda='BRL'):
    if preco is None: return "Preço não disponível"
    return f"R$ {float(preco):.2f}".replace('.', ',') if moeda=='BRL' else f"{moeda} {preco}"

def embed_livro(livro:dict, links:list[dict]=None, cor=None):
    e=discord.Embed(title=f"📚 {livro.get('titulo','Sem título')}", color=cor or CORES['azul'], timestamp=datetime.utcnow(), url=livro.get('preview_link') or None)
    if livro.get('subtitulo'): e.description=f"*{livro['subtitulo']}*"
    if livro.get('capa_url'): e.set_thumbnail(url=livro['capa_url'])
    for name,key,inline in [("✍️ Autor","autor",True),("🏢 Editora","editora",True),("📅 Ano","ano",True),("📄 Páginas","paginas",True),("🌎 Idioma","idioma",True),("🔢 ISBN","isbn",True)]:
        if livro.get(key): e.add_field(name=name, value=str(livro[key]), inline=inline)
    if livro.get('avaliacao_google'): e.add_field(name="⭐ Avaliação", value=f"{livro['avaliacao_google']}/5 ({livro.get('votos_google',0)} votos)", inline=True)
    if livro.get('generos'):
        gen=livro['generos']; gen=', '.join(gen[:5]) if isinstance(gen,list) else str(gen); e.add_field(name="🏷️ Gêneros", value=gen[:250], inline=False)
    if livro.get('preco'): e.add_field(name="💰 Preço encontrado", value=formato_preco(livro.get('preco'), livro.get('moeda','BRL')), inline=True)
    if livro.get('idiomas') and isinstance(livro.get('idiomas'), list): e.add_field(name="🌐 Idiomas disponíveis", value=', '.join(map(str, livro['idiomas'][:8])) or 'N/A', inline=True)
    if livro.get('sinopse'):
        sinopse=livro['sinopse']; e.add_field(name="📝 Sinopse", value=(sinopse[:900]+'...') if len(sinopse)>900 else sinopse, inline=False)
    if links:
        parts=[]
        for l in links[:5]:
            preco=f" — {formato_preco(l.get('preco'))}" if l.get('preco') else ""
            parts.append(f"[{l['loja']}]({l['url']}){preco}")
        e.add_field(name="🛍️ Onde comprar", value='\n'.join(parts), inline=False)
    e.set_footer(text=FOOTER); return e

def embed_wishlist(items, username):
    e=discord.Embed(title=f"📌 Quero Ler de {username}", color=CORES['roxo'], timestamp=datetime.utcnow())
    if not items: e.description="Sua lista está vazia! Use `/queroler adicionar <livro>` para começar."; e.set_footer(text=FOOTER); return e
    for i,item in enumerate(items[:20],1):
        preco=f"🎯 Alerta: {formato_preco(item.get('preco_alvo'))}" if item.get('preco_alvo') else ""
        e.add_field(name=f"{i}. {item['titulo'][:50]}", value=f"✍️ {item.get('autor','—')}\n{preco}".strip(), inline=True)
    e.set_footer(text=f"{len(items)} livro(s) • {FOOTER}"); return e

def embed_biblioteca(itens, username, status_label):
    e=discord.Embed(title=f"📚 Estante de {username} — {status_label.replace('_',' ').title()}", color=CORES['verde'], timestamp=datetime.utcnow())
    if not itens: e.description="Nenhum livro nessa categoria ainda."; e.set_footer(text=FOOTER); return e
    for item in itens[:15]:
        av=f" {estrelas(item.get('avaliacao'))}" if item.get('avaliacao') else ""
        com=f"\n💬 {item.get('comentario')[:80]}..." if item.get('comentario') else ""
        e.add_field(name=f"📚 {item['titulo'][:45]}", value=f"✍️ {item.get('autor','')}{av}{com}", inline=True)
    e.set_footer(text=f"{len(itens)} livro(s) • {FOOTER}"); return e

def embed_erro(mensagem): return discord.Embed(title="❌ Erro", description=mensagem, color=CORES['vermelho'])
def embed_sucesso(mensagem):
    e=discord.Embed(title="✅ Sucesso", description=mensagem, color=CORES['verde']); e.set_footer(text=FOOTER); return e
