import aiohttp
import logging

log = logging.getLogger("BookBot.API")

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


async def buscar_livros(query, max_results=5):
    resultado = await buscar_open_library(query, max_results)
    if resultado:
        return resultado
    return await _buscar_google(query, max_results)


async def buscar_open_library(query, max_results=5):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "limit": max_results}
            async with s.get(OPEN_LIBRARY_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                docs = data.get("docs", [])
                return [_parse_open_library(d) for d in docs[:max_results]]
    except Exception as e:
        log.error("Erro Open Library: " + str(e))
        return []


async def _buscar_google(query, max_results=5):
    try:
        async with aiohttp.ClientSession() as s:
            params = {"q": query, "maxResults": max_results, "printType": "books"}
            async with s.get(GOOGLE_BOOKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                items = data.get("items", [])
                return [_parse_google_book(i) for i in items]
    except Exception as e:
        log.error("Erro Google Books: " + str(e))
        return []


def _parse_open_library(doc):
    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else ""
    cover_id = doc.get("cover_i")
    if cover_id:
        capa = "https://covers.openlibrary.org/b/id/" + str(cover_id) + "-L.jpg"
    else:
        capa = ""
    autores = doc.get("author_name", ["Autor desconhecido"])
    ano = str(doc.get("first_publish_year", ""))
    return {
        "titulo": doc.get("title", "Titulo desconhecido"),
        "autor": ", ".join(autores[:3]),
        "editora": ", ".join(doc.get("publisher", [])[:1]),
        "ano": ano,
        "paginas": doc.get("number_of_pages_median", 0),
        "generos": doc.get("subject", [])[:3],
        "sinopse": "Primeira edicao: " + ano,
        "isbn": isbn,
        "capa_url": capa,
        "idioma": "N/A",
        "avaliacao_google": 0,
        "votos_google": 0,
        "google_id": "",
    }


def _parse_google_book(item):
    info = item.get("volumeInfo", {})
    isbn = ""
    for id_obj in info.get("industryIdentifiers", []):
        if id_obj.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = id_obj["identifier"]
            break
    thumb = info.get("imageLinks", {}).get("thumbnail", "")
    if thumb:
        thumb = thumb.replace("http://", "https://")
    desc = info.get("description", "Sem sinopse.")
    return {
        "titulo": info.get("title", "Titulo desconhecido"),
        "autor": ", ".join(info.get("authors", ["Autor desconhecido"])),
        "editora": info.get("publisher", ""),
        "ano": info.get("publishedDate", "")[:4] if info.get("publishedDate") else "",
        "paginas": info.get("pageCount", 0),
        "generos": info.get("categories", []),
        "sinopse": desc[:500],
        "isbn": isbn,
        "capa_url": thumb,
        "idioma": info.get("language", "N/A"),
        "avaliacao_google": info.get("averageRating", 0),
        "votos_google": info.get("ratingsCount", 0),
        "google_id": item.get("id", ""),
    }


def gerar_links_compra(livro):
    titulo = livro.get("titulo", "")
    isbn = livro.get("isbn", "")
    query = (isbn or titulo).replace(" ", "+")
    nome = titulo.replace(" ", "+")
    return [
        {"loja": "Amazon BR", "url": "https://www.amazon.com.br/s?k=" + query},
        {"loja": "Estante Virtual", "url": "https://www.estantevirtual.com.br/busca?q=" + nome},
        {"loja": "Mercado Livre", "url": "https://lista.mercadolivre.com.br/" + nome},
        {"loja": "Google Play Livros", "url": "https://play.google.com/store/search?q=" + nome + "&c=books"},
    ]


async def buscar_precos(titulo, autor="", isbn=""):
    return gerar_links_compra({"titulo": titulo, "isbn": isbn})


def get_cache_livro(isbn):
    return None


def salvar_cache_livro(isbn, dados):
    pass


async def recomendar_por_perfil(perfil, historico_titulos):
    generos = perfil.get("generos", [])
    autores = perfil.get("autores", [])
    queries = []
    if autores:
        queries.append(autores[0])
    if generos:
        queries.append(generos[0])
    if not queries:
        queries.append("bestseller")

    todos = []
    for q in queries[:2]:
        livros = await buscar_livros(q, 8)
        for l in livros:
            if l["titulo"] not in historico_titulos:
                todos.append(l)

    vistos = set()
    unicos = []
    for l in todos:
        if l["titulo"] not in vistos:
            vistos.add(l["titulo"])
            unicos.append(l)
    return unicos[:5]
