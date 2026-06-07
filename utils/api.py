import aiohttp
import logging
from urllib.parse import quote_plus

log = logging.getLogger("Ivy.API")
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
MERCADO_LIVRE_URL = "https://api.mercadolibre.com/sites/MLB/search"

async def buscar_livros(query, max_results=5):
    # Google primeiro porque pode trazer preço/link de compra.
    google = await _buscar_google(query, max_results)
    if google:
        return google
    return await buscar_open_library(query, max_results)

async def buscar_open_library(query, max_results=5):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "limit": max_results}
            async with s.get(OPEN_LIBRARY_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return [_parse_open_library(d) for d in data.get("docs", [])[:max_results]]
    except Exception as e:
        log.error("Erro Open Library: %s", e)
        return []

async def _buscar_google(query, max_results=5):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "maxResults": max_results, "printType": "books"}
            async with s.get(GOOGLE_BOOKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return [_parse_google_book(i) for i in data.get("items", [])]
    except Exception as e:
        log.error("Erro Google Books: %s", e)
        return []

def _parse_open_library(doc):
    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else ""
    cover_id = doc.get("cover_i")
    capa = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
    autores = doc.get("author_name", ["Autor desconhecido"])
    ano = str(doc.get("first_publish_year", ""))
    return {
        "titulo": doc.get("title", "Título desconhecido"), "autor": ", ".join(autores[:3]),
        "editora": ", ".join(doc.get("publisher", [])[:1]), "ano": ano,
        "paginas": doc.get("number_of_pages_median", 0), "generos": doc.get("subject", [])[:3],
        "sinopse": "Primeira edição: " + ano if ano else "Sem sinopse.", "isbn": isbn,
        "capa_url": capa, "idioma": "N/A", "avaliacao_google": 0, "votos_google": 0,
        "google_id": "", "preco": None, "moeda": "", "buy_link": "", "loja_preco": ""
    }

def _parse_google_book(item):
    info = item.get("volumeInfo", {})
    sale = item.get("saleInfo", {})
    isbn = ""
    for id_obj in info.get("industryIdentifiers", []):
        if id_obj.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = id_obj.get("identifier", "")
            break
    thumb = info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
    preco_obj = sale.get("retailPrice") or sale.get("listPrice") or {}
    preco = preco_obj.get("amount")
    return {
        "titulo": info.get("title", "Título desconhecido"),
        "autor": ", ".join(info.get("authors", ["Autor desconhecido"])),
        "editora": info.get("publisher", ""), "ano": info.get("publishedDate", "")[:4],
        "paginas": info.get("pageCount", 0), "generos": info.get("categories", []),
        "sinopse": info.get("description", "Sem sinopse.")[:700], "isbn": isbn,
        "capa_url": thumb, "idioma": info.get("language", "N/A"),
        "avaliacao_google": info.get("averageRating", 0), "votos_google": info.get("ratingsCount", 0),
        "google_id": item.get("id", ""), "preco": float(preco) if preco is not None else None,
        "moeda": preco_obj.get("currencyCode", ""), "buy_link": sale.get("buyLink", ""),
        "loja_preco": "Google Books" if preco is not None else ""
    }

def gerar_links_compra(livro):
    titulo = livro.get("titulo", "")
    isbn = livro.get("isbn", "")
    q = quote_plus(isbn or titulo)
    nome = quote_plus(titulo)
    links = []
    if livro.get("buy_link"):
        links.append({"loja": "Google Books", "url": livro["buy_link"], "preco": livro.get("preco")})
    links += [
        {"loja": "Amazon BR", "url": "https://www.amazon.com.br/s?k=" + q},
        {"loja": "Estante Virtual", "url": "https://www.estantevirtual.com.br/busca?q=" + nome},
        {"loja": "Mercado Livre", "url": "https://lista.mercadolivre.com.br/" + nome},
        {"loja": "Google Play Livros", "url": "https://play.google.com/store/search?q=" + nome + "&c=books"},
    ]
    return links

async def buscar_preco_mercado_livre(titulo, autor=""):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": f"livro {titulo} {autor}".strip(), "limit": 5, "category": "MLB1196"}
            async with s.get(MERCADO_LIVRE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                results = data.get("results", [])
                if not results:
                    return None
                item = min(results, key=lambda x: float(x.get("price") or 999999))
                return {"loja": "Mercado Livre", "preco": float(item.get("price", 0)), "url": item.get("permalink", "")}
    except Exception as e:
        log.error("Erro Mercado Livre: %s", e)
        return None

async def buscar_precos(titulo, autor="", isbn=""):
    precos = []
    ml = await buscar_preco_mercado_livre(titulo, autor)
    if ml:
        precos.append(ml)
    return precos

async def recomendar_por_perfil(perfil, historico_titulos):
    generos = perfil.get("generos") or []
    autores = perfil.get("autores") or []
    objetivo = perfil.get("objetivo") or "diversao"
    queries = autores[:2] + generos[:2]
    if objetivo == "aprender": queries.append("livros desenvolvimento pessoal")
    elif objetivo == "estudos": queries.append("livros enem vestibular")
    elif objetivo == "profissional": queries.append("livros carreira negócios")
    else: queries.append("bestsellers ficção fantasia romance")
    todos = []
    historico = {t.lower() for t in historico_titulos}
    for q in queries:
        for l in await buscar_livros(q, 6):
            if l["titulo"].lower() not in historico:
                todos.append(l)
    vistos, unicos = set(), []
    for l in todos:
        k = l["titulo"].lower()
        if k not in vistos:
            vistos.add(k); unicos.append(l)
    return unicos[:5]
