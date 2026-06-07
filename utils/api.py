import aiohttp
import logging
import random
from urllib.parse import quote_plus

log = logging.getLogger("Ivy.API")
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

def _brl(valor):
    return f"R$ {float(valor):.2f}".replace('.', ',')

async def buscar_livros(query, max_results=5, lang="pt"):
    # Google primeiro porque traz preço, avaliação, sinopse e idioma com mais consistência.
    resultado = await _buscar_google(query, max_results, lang=lang)
    if resultado:
        return resultado
    return await buscar_open_library(query, max_results)

async def buscar_open_library(query, max_results=5):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "limit": max_results, "language": "por"}
            async with s.get(OPEN_LIBRARY_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200: return []
                data = await r.json(); docs = data.get("docs", [])
                return [_parse_open_library(d) for d in docs[:max_results]]
    except Exception as e:
        log.error("Erro Open Library: %s", e); return []

async def _buscar_google(query, max_results=5, lang="pt"):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "maxResults": max_results, "printType": "books", "country": "BR"}
            if lang: params["langRestrict"] = lang
            async with s.get(GOOGLE_BOOKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200: return []
                data = await r.json(); return [_parse_google_book(i) for i in data.get("items", [])]
    except Exception as e:
        log.error("Erro Google Books: %s", e); return []

async def buscar_volume_google(google_id):
    if not google_id: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{GOOGLE_BOOKS_URL}/{google_id}", params={"country":"BR"}, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200: return None
                return _parse_google_book(await r.json())
    except Exception:
        return None

def _parse_open_library(doc):
    isbn_list = doc.get("isbn", []); isbn = isbn_list[0] if isbn_list else (doc.get('key','') or doc.get('title',''))
    cover_id = doc.get("cover_i"); capa = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
    autores = doc.get("author_name", ["Autor desconhecido"]); ano = str(doc.get("first_publish_year", ""))
    return {"titulo": doc.get("title", "Título desconhecido"), "autor": ", ".join(autores[:3]), "editora": ", ".join(doc.get("publisher", [])[:1]), "ano": ano, "paginas": doc.get("number_of_pages_median", 0), "generos": doc.get("subject", [])[:5], "sinopse": "Primeira edição: " + ano if ano else "Sinopse não disponível.", "isbn": isbn, "capa_url": capa, "idioma": "pt/indefinido", "idiomas": doc.get('language', [])[:8], "avaliacao_google": 0, "votos_google": 0, "google_id": "", "preco": None, "moeda": "BRL", "buy_link": ""}

def _parse_google_book(item):
    info = item.get("volumeInfo", {}); sale = item.get("saleInfo", {})
    isbn = ""
    for id_obj in info.get("industryIdentifiers", []):
        if id_obj.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = id_obj.get("identifier", ""); break
    thumb = info.get("imageLinks", {}).get("thumbnail", "") or info.get("imageLinks", {}).get("smallThumbnail", "")
    thumb = thumb.replace("http://", "https://") if thumb else ""
    price_obj = sale.get("retailPrice") or sale.get("listPrice") or {}
    preco = price_obj.get("amount")
    moeda = price_obj.get("currencyCode", "BRL")
    return {"titulo": info.get("title", "Título desconhecido"), "subtitulo": info.get('subtitle',''), "autor": ", ".join(info.get("authors", ["Autor desconhecido"])), "editora": info.get("publisher", ""), "ano": info.get("publishedDate", "")[:4] if info.get("publishedDate") else "", "paginas": info.get("pageCount", 0), "generos": info.get("categories", []), "sinopse": (info.get("description") or "Sem sinopse disponível.")[:1200], "isbn": isbn or item.get('id',''), "capa_url": thumb, "idioma": info.get("language", "N/A"), "idiomas": [info.get("language", "N/A")], "avaliacao_google": info.get("averageRating", 0), "votos_google": info.get("ratingsCount", 0), "google_id": item.get("id", ""), "preco": preco, "moeda": moeda, "buy_link": sale.get("buyLink", ""), "preview_link": info.get('previewLink','')}

def gerar_links_compra(livro):
    titulo = livro.get("titulo", ""); isbn = livro.get("isbn", ""); query = quote_plus(isbn or titulo); nome = quote_plus(titulo)
    links=[]
    if livro.get('buy_link'): links.append({"loja":"Google Play Livros", "url":livro['buy_link'], "preco": livro.get('preco')})
    links.extend([
        {"loja":"Amazon BR", "url":"https://www.amazon.com.br/s?k=" + query + "&i=stripbooks"},
        {"loja":"Estante Virtual", "url":"https://www.estantevirtual.com.br/busca?q=" + nome},
        {"loja":"Mercado Livre", "url":"https://lista.mercadolivre.com.br/livro-" + nome},
    ])
    return links

async def buscar_precos(titulo, autor="", isbn=""):
    livros = await buscar_livros(isbn or titulo, 3, lang="pt")
    achados=[]
    for l in livros:
        if l.get('preco'):
            achados.append({"loja":"Google Play Livros", "url": l.get('buy_link') or l.get('preview_link'), "preco": l.get('preco'), "capa_url": l.get('capa_url'), "titulo": l.get('titulo'), "autor": l.get('autor')})
    if achados: return achados
    return gerar_links_compra({"titulo": titulo, "isbn": isbn})

async def recomendar_por_perfil(perfil, historico_titulos):
    generos = perfil.get("generos", []) or []; autores = perfil.get("autores", []) or []
    queries = autores[:1] + generos[:2] + [perfil.get('objetivo','livros em português'), 'romance fantasia livros em português']
    todos=[]
    for q in queries[:4]:
        for l in await buscar_livros(q, 6, lang="pt"):
            if l['titulo'] not in historico_titulos: todos.append(l)
    vistos=set(); unicos=[]
    for l in todos:
        k=l['titulo'].lower()
        if k not in vistos:
            vistos.add(k); unicos.append(l)
    return unicos[:5]

async def livro_aleatorio():
    termos = ["literatura brasileira", "fantasia juvenil", "romance brasileiro", "ficção científica português", "clássicos da literatura", "mangá português"]
    livros = await buscar_livros(random.choice(termos), 10, lang="pt")
    return random.choice(livros) if livros else None

# --- Similaridade melhorada: evita devolver volumes/edições da mesma série ---
def _normalizar_titulo(txt: str) -> str:
    import unicodedata, re
    txt = unicodedata.normalize('NFKD', txt or '').encode('ascii', 'ignore').decode('ascii').lower()
    txt = re.sub(r'[^a-z0-9\s]', ' ', txt)
    txt = re.sub(r'\b(vol|volume|livro|book|box|edicao|edition|parte|tomo|colecao|saga)\b', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

_SERIES_BLOQUEIO = {
    'harry potter': ['harry potter', 'hogwarts'],
    'percy jackson': ['percy jackson', 'olimpianos', 'herois do olimpo'],
    'jogos vorazes': ['jogos vorazes', 'hungers games', 'hunger games'],
    'senhor dos aneis': ['senhor dos aneis', 'lord of the rings'],
    'o hobbit': ['hobbit', 'senhor dos aneis', 'lord of the rings'],
    'crepusculo': ['crepusculo', 'twilight'],
    'narnia': ['narnia'],
    'naruto': ['naruto'],
    'one piece': ['one piece'],
}

_SIMILARES_CURADOS = {
    'harry potter': ['Percy Jackson e o Ladrão de Raios', 'As Crônicas de Nárnia', 'Eragon', 'Artemis Fowl', 'A Bússola de Ouro', 'A Escola do Bem e do Mal', 'O Nome do Vento'],
    'jogos vorazes': ['Divergente', 'Maze Runner', 'Legend', 'A Rainha Vermelha', 'Battle Royale', 'Feios'],
    'percy jackson': ['Harry Potter', 'As Crônicas de Nárnia', 'A Bússola de Ouro', 'Eragon', 'Magnus Chase'],
    'crepusculo': ['Diários do Vampiro', 'Sussurro', 'Cidade dos Ossos', 'Academia de Vampiros'],
    'naruto': ['Bleach', 'One Piece', 'Black Clover', 'Hunter x Hunter', 'Jujutsu Kaisen', 'My Hero Academia'],
    'one piece': ['Naruto', 'Fairy Tail', 'Hunter x Hunter', 'Dragon Ball', 'Black Clover'],
}

async def buscar_similares(titulo: str, max_results: int = 5):
    base_norm = _normalizar_titulo(titulo)
    chave = next((k for k in _SIMILARES_CURADOS if k in base_norm), None)
    candidatos = []
    if chave:
        for q in _SIMILARES_CURADOS[chave]:
            candidatos.extend(await buscar_livros(q, 2, lang='pt'))
    else:
        base = await buscar_livros(titulo, 1, lang='pt')
        if not base:
            return []
        livro_base = base[0]
        generos = livro_base.get('generos') or []
        if isinstance(generos, str):
            generos = [generos]
        queries = []
        for g in generos[:3]:
            queries.append(f'{g} livros em português')
        if livro_base.get('sinopse'):
            queries.append(f"{titulo} livros parecidos fantasia aventura romance jovem")
        if not queries:
            queries = [f'livros parecidos com {titulo} em português']
        for q in queries[:4]:
            candidatos.extend(await buscar_livros(q, 8, lang='pt'))

    bloqueios = set()
    for serie, termos in _SERIES_BLOQUEIO.items():
        if serie in base_norm:
            bloqueios.update(termos)
    # também bloqueia palavras principais do título quando for muito característico
    palavras_base = [p for p in base_norm.split() if len(p) >= 5]
    vistos, unicos = set(), []
    for l in candidatos:
        nt = _normalizar_titulo(l.get('titulo',''))
        if not nt or nt in vistos:
            continue
        if nt == base_norm:
            continue
        if any(_normalizar_titulo(b) in nt for b in bloqueios):
            continue
        # evita volumes que repetem o título-base quase inteiro
        overlap = sum(1 for p in palavras_base if p in nt)
        if len(palavras_base) >= 2 and overlap >= min(2, len(palavras_base)):
            continue
        vistos.add(nt)
        unicos.append(l)
        if len(unicos) >= max_results:
            break
    return unicos
