import discord
from datetime import datetime

CORES = {
    "azul":     discord.Color.from_rgb(88, 101, 242),
    "verde":    discord.Color.from_rgb(87, 242, 135),
    "vermelho": discord.Color.from_rgb(237, 66, 69),
    "amarelo":  discord.Color.from_rgb(254, 231, 92),
    "roxo":     discord.Color.from_rgb(155, 89, 182),
    "laranja":  discord.Color.from_rgb(230, 126, 34),
    "cinza":    discord.Color.from_rgb(142, 146, 151),
}

def estrelas(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return "⭐" * n + "☆" * (5 - n)

def formato_preco(preco) -> str:
    if preco is None:
        return "Ver na loja"
    return f"R$ {preco:.2f}"

def embed_livro(livro: dict, links: list[dict] = None, cor=None) -> discord.Embed:
    """Embed rico para exibição de um livro"""
    cor = cor or CORES["azul"]
    e = discord.Embed(
        title=f"📚 {livro.get('titulo', 'Sem título')}",
        color=cor,
        timestamp=datetime.utcnow()
    )
    if livro.get("capa_url"):
        e.set_thumbnail(url=livro["capa_url"])

    # Infos principais
    if livro.get("autor"):
        e.add_field(name="✍️ Autor", value=livro["autor"], inline=True)
    if livro.get("editora"):
        e.add_field(name="🏢 Editora", value=livro["editora"], inline=True)
    if livro.get("ano"):
        e.add_field(name="📅 Ano", value=livro["ano"], inline=True)
    if livro.get("paginas"):
        e.add_field(name="📄 Páginas", value=str(livro["paginas"]), inline=True)
    if livro.get("isbn"):
        e.add_field(name="🔢 ISBN", value=livro["isbn"], inline=True)
    if livro.get("generos"):
        generos = livro["generos"]
        if isinstance(generos, list):
            generos = ", ".join(generos[:3])
        e.add_field(name="🏷️ Categorias", value=generos, inline=True)
    if livro.get("avaliacao_google") and livro["avaliacao_google"] > 0:
        av = livro["avaliacao_google"]
        votos = livro.get("votos_google", 0)
        e.add_field(name="⭐ Avaliação Google", value=f"{av}/5 ({votos} votos)", inline=True)
    if livro.get("sinopse"):
        sinopse = livro["sinopse"]
        if len(sinopse) > 400:
            sinopse = sinopse[:397] + "..."
        e.add_field(name="📝 Sinopse", value=sinopse, inline=False)

    # Links de compra
    if links:
        link_text = "\n".join([f"[{l['loja']}]({l['url']})" for l in links[:6]])
        e.add_field(name="🛍️ Onde Comprar", value=link_text, inline=False)

    e.set_footer(text="BookBot 📚 • Use /buscar para pesquisar mais livros")
    return e

def embed_wishlist(items: list, username: str) -> discord.Embed:
    e = discord.Embed(
        title=f"❤️ Lista de Desejos de {username}",
        color=CORES["roxo"],
        timestamp=datetime.utcnow()
    )
    if not items:
        e.description = "Sua lista está vazia! Use `/desejo adicionar <livro>` para começar."
        return e

    for i, item in enumerate(items[:20], 1):
        preco_alvo = f"🎯 Alerta: {formato_preco(item.get('preco_alvo'))}" if item.get("preco_alvo") else ""
        valor = f"✍️ {item.get('autor','')}\n{preco_alvo}" if item.get("autor") else preco_alvo or "—"
        e.add_field(
            name=f"{i}. {item['titulo'][:50]}",
            value=valor or "—",
            inline=True
        )
    e.set_footer(text=f"📚 {len(items)} livro(s) na lista")
    return e

def embed_biblioteca(itens: list, username: str, status_label: str) -> discord.Embed:
    ICONES = {
        "quero_ler": "📌",
        "lendo": "📖",
        "lido": "✅",
        "favorito": "❤️",
        "abandonado": "🗑️",
    }
    icone = ICONES.get(status_label, "📚")
    e = discord.Embed(
        title=f"{icone} Estante de {username} — {status_label.replace('_', ' ').title()}",
        color=CORES["verde"],
        timestamp=datetime.utcnow()
    )
    if not itens:
        e.description = "Nenhum livro nessa categoria ainda."
        return e
    for item in itens[:15]:
        av = f" {estrelas(item.get('avaliacao'))}" if item.get("avaliacao") else ""
        e.add_field(
            name=f"📚 {item['titulo'][:45]}",
            value=f"✍️ {item.get('autor','')}{av}",
            inline=True
        )
    e.set_footer(text=f"{len(itens)} livro(s) • Use /estante para ver tudo")
    return e

def embed_perfil(perfil: dict, stats: dict, username: str, avatar_url: str = None) -> discord.Embed:
    e = discord.Embed(
        title=f"👤 Perfil de {username}",
        color=CORES["azul"],
        timestamp=datetime.utcnow()
    )
    if avatar_url:
        e.set_thumbnail(url=avatar_url)

    generos = perfil.get("generos", [])
    autores = perfil.get("autores", [])
    formato_map = {"todos": "Todos", "fisico": "📚 Físico", "ebook": "📱 Ebook", "audio": "🎧 Audiobook"}

    e.add_field(name="📚 Livros Lidos",      value=str(stats.get("lidos", 0)),          inline=True)
    e.add_field(name="⭐ Média Avaliações",  value=str(stats.get("media_avaliacao", 0)), inline=True)
    e.add_field(name="❤️ Na Wishlist",       value=str(stats.get("wishlist", 0)),        inline=True)
    e.add_field(name="🏷️ Gêneros Favoritos", value=", ".join(generos) or "Não definido", inline=False)
    e.add_field(name="✍️ Autores Favoritos", value=", ".join(autores) or "Não definido", inline=False)
    e.add_field(name="📖 Formato Preferido", value=formato_map.get(perfil.get("formato","todos"), "Todos"), inline=True)
    e.add_field(name="📅 Livros/Ano",        value=perfil.get("livros_ano","1-5"), inline=True)

    e.set_footer(text="Use /perfil editar para atualizar suas preferências")
    return e

def embed_promocao(livro: dict, preco_atual: float, preco_anterior: float,
                   loja: str, url: str) -> discord.Embed:
    desconto = 0
    if preco_anterior and preco_anterior > 0:
        desconto = int((1 - preco_atual / preco_anterior) * 100)

    e = discord.Embed(
        title=f"🔥 PROMOÇÃO: {livro.get('titulo','')[:60]}",
        url=url,
        color=CORES["vermelho"],
        timestamp=datetime.utcnow()
    )
    if livro.get("capa_url"):
        e.set_thumbnail(url=livro["capa_url"])

    e.add_field(name="✍️ Autor",      value=livro.get("autor","—"), inline=True)
    e.add_field(name="🏬 Loja",       value=loja,                    inline=True)
    if desconto > 0:
        e.add_field(name="💸 Desconto", value=f"**{desconto}% OFF**", inline=True)
    if preco_anterior:
        e.add_field(name="💰 De",   value=f"~~R$ {preco_anterior:.2f}~~", inline=True)
    e.add_field(    name="✅ Por",  value=f"**R$ {preco_atual:.2f}**",     inline=True)
    e.add_field(    name="🔗 Link", value=f"[Comprar agora]({url})",       inline=False)

    e.set_footer(text="BookBot 📚 • Use /alerta para criar alertas personalizados")
    return e

def embed_ranking(titulo: str, itens: list, tipo: str = "wishlist") -> discord.Embed:
    e = discord.Embed(title=f"🏆 {titulo}", color=CORES["amarelo"], timestamp=datetime.utcnow())
    medalhas = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    for i, item in enumerate(itens[:10]):
        if tipo == "wishlist":
            valor = f"✍️ {item.get('autor','')}\n👥 {item.get('total',0)} na wishlist"
        else:
            media = item.get("media", 0)
            valor = f"✍️ {item.get('autor','')}\n{estrelas(media)} ({item.get('votos',0)} avaliações)"
        e.add_field(
            name=f"{medalhas[i]} {item['titulo'][:45]}",
            value=valor,
            inline=False
        )
    e.set_footer(text="BookBot 📚 • Rankings atualizados em tempo real")
    return e

def embed_erro(mensagem: str) -> discord.Embed:
    return discord.Embed(title="❌ Erro", description=mensagem, color=CORES["vermelho"])

def embed_sucesso(mensagem: str) -> discord.Embed:
    return discord.Embed(title="✅ Sucesso", description=mensagem, color=CORES["verde"])
