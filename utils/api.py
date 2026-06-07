import aiohttp
import asyncio
import logging
from utils.db import get_cache_livro, salvar_cache_livro

log = logging.getLogger("BookBot.API")

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_WORKS = "https://openlibrary.org"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

async def buscar_livros(query: str, max_results: int = 5) -> list[dict]:
    resultado = await buscar_open_library(query, max_results)
    if resultado:
        return resultado
    return await _buscar_google(query, max_results)

async def buscar_open_library(query: str, max_results: int = 5) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                OPEN_LIBRARY_URL,
                params={"q": query, "limit": max_results, "language": "por,eng"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status != 200:
                    log.error(f"Open Library status: {r.status}")
                    return []
                data = await r.json()
                docs = data.get("docs", [])
                if not docs:
                    return []
                return [_parse_open_library(d) for d in docs[:max_results]]
    except Exception as e:
        log.error(f"Erro Open Library: {e}")
        return []

async def _buscar_google(query: str, max_results: int = 5) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                GOOGLE_BOOKS_URL,
                params={"q": query, "maxResults": max_results, "printType": "books"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status != 200:
                    log.error(f"Google Books status: {r.status}")
                    return []
                data = await r.json()
                items = data.get("items", [])
                return [_parse_google_book(i) for i in items]
    except Exception as e:
        log.error(f"Erro Google Books: {e}")
        return []

def _parse_open_library(doc: dict) -> dict:
    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else ""
    cover_id = doc.get("cover_i")
    capa = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
    autores = doc.get("author_name", ["Autor desconhecido"])
    return {
        "titulo": doc.get("title", "Título desconhecido"),
        "autor": ", ".join(autores[:3]),
        "editora": ", ".join(doc.get("publisher", [])[:1]),
        "ano": str(doc.get("first_publish_year", "")),
        "paginas": doc.get("number_of_pages_median", 0),
        "generos": doc.get("subject", [])[:3],
        "sinopse": f"Primeira edição: {doc.get('first_publish_year', 'N/A')} | Edições: {doc.get('edition_count', 1)}",
        "isbn": isbn,
        "capa_url": capa,
        "idioma": ", ".join(doc.get("language", ["N/A"])[:2]),
        "avaliacao_google": 0,
        "votos_google": 0,
        "google_id": "",
    }

def _parse_google_book(item: dict) -> dict:
    info = item.get("volumeInfo", {})
    isbn = ""
    for id_obj in info.get("industryIdentifiers", []):
        if id_obj.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = id_obj["identifier"]
            break
    thumb = info.get("imageLinks", {}).get("thumbnail", "")
    if thumb:
        thumb = thumb.replace("http://", "https://").replace("zoom=1", "zoom=2")
    return {
        "titulo": info.get("title", "Título desconhecido"),
        "autor": ", ".join(info.get("authors", ["Autor desconhecido"])),
        "editora": info.get("publisher", ""),
        "ano": info.get("publishedDate", "")[:4] if info.get("publishedDate") else "",
        "paginas": info.get("pageCount", 0),
        "generos": info.get("categories", []),
        "sinopse": info.get("description", "Sem sinopse disponível.")[:500],
        "isbn": isbn,
        "capa_url": thumb,
        "idioma": info.get("language", "N/A"),
        "avaliacao_google": info.get("averageRating", 0),
        "votos_google": info.get("ratingsCount", 0),
        "google_id": item.get("id", ""),
    }

async def buscar_precos(titulo: str, autor: str = "", isbn: str = "") -> list[dict]:
    return gerar_links_compra({"titulo": titulo, "isbn": isbn})

async def _preco_amazon(titulo: str, isbn: str = "") -> list[dict]:
    query = isbn if isbn else titulo
    url = f"https://www.amazon.com.br/s?k={query.replace(' ', '+')}"
    return [{"loja": "Amazon BR", "preco": None, "url": url, "url_busca": True, "emoji": "🛒", "confiavel": True}]

async def _preco_estante(titulo: str, autor: str = "") -> list[dict]:
    query = f"{titulo} {autor}".strip().replace(" ", "+")
    url = f"https://www.estantevirtual.com.br/busca?q={query}"
    return [{"loja": "Estante Virtual", "preco": None, "url": url, "url_busca": True, "emoji": "📖", "confiavel": True}]

def gerar_links_compra(livro: dict) -> list[dict]:
    titulo = livro.get("titulo", "")
    isbn   = livro.get("isbn", "")
    query  = (isbn or titulo).replace(" ", "+")
    nome   = titulo.replace(" ", "+")
    return [
        {"loja": "🛒 Amazon BR",         "url": f"https://www.amazon.com.br/s?k={query}"},
        {"loja": "📚 Livraria Cultura",   "url": f"https://www.livrariacultura.com.br/busca?q={nome}"},
        {"loja": "📖 Estante Virtual",    "url": f"https://www.estantevirtual.com.br/busca?q={nome}"},
        {"loja": "🏬 Saraiva",            "url": f"https://www.saraiva.com.br/busca?q={nome}"},
        {"loja": "🟡 Mercado Livre",      "url": f"https://lista.mercadolivre.com.br/{nome}"},
        {"loja": "📱 Google Play Livros", "url": f"https://play.google.com/store/search?q={nome}&c=books"},
    ]

async def recomendar_por_perfil(perfil: dict, historico_ti
