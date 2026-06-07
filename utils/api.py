import aiohttp
import asyncio
import re
import logging
from typing import Optional
from utils.db import get_cache_livro, salvar_cache_livro

log = logging.getLogger("BookBot.API")

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"

# ─── Google Books ─────────────────────────────────────────────────────────────
async def buscar_livros(query: str, max_results: int = 5) -> list[dict]:
    """Busca livros via Google Books API (gratuita, sem chave)"""
    params = {
        "q": query,
        "maxResults": max_results,
        "langRestrict": "pt",
        "printType": "books",
        "orderBy": "relevance"
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(GOOGLE_BOOKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                items = data.get("items", [])
                return [_parse_google_book(i) for i in items]
    except Exception as e:
        log.error(f"Erro na busca Google Books: {e}")
        # Tenta Open Library como fallback
        return await buscar_open_library(query, max_results)

async def buscar_open_library(query: str, max_results: int = 5) -> list[dict]:
    """Fallback: Open Library API"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(OPEN_LIBRARY_URL, params={"q": query, "limit": max_results},
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                docs = data.get("docs", [])
                return [_parse_open_library(d) for d in docs[:max_results]]
    except Exception as e:
        log.error(f"Erro Open Library: {e}")
        return []

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
        "idioma": info.get("language", "pt"),
        "avaliacao_google": info.get("averageRating", 0),
        "votos_google": info.get("ratingsCount", 0),
        "google_id": item.get("id", ""),
    }

def _parse_open_library(doc: dict) -> dict:
    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else ""
    cover_id = doc.get("cover_i")
    capa = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
    return {
        "titulo": doc.get("title", "Título desconhecido"),
        "autor": ", ".join(doc.get("author_name", ["Autor desconhecido"])),
        "editora": ", ".join(doc.get("publisher", [])[:1]),
        "ano": str(doc.get("first_publish_year", "")),
        "paginas": doc.get("number_of_pages_median", 0),
        "generos": doc.get("subject", [])[:3],
        "sinopse": "Veja mais na Open Library.",
        "isbn": isbn,
        "capa_url": capa,
        "idioma": "pt",
        "avaliacao_google": 0,
        "votos_google": 0,
        "google_id": "",
    }

# ─── Preços nas lojas ─────────────────────────────────────────────────────────
async def buscar_precos(titulo: str, autor: str = "", isbn: str = "") -> list[dict]:
    """Busca preços em lojas confiáveis via scraping leve"""
    tasks_list = [
        _preco_amazon(titulo, isbn),
        _preco_estante(titulo, autor),
    ]
    resultados = await asyncio.gather(*tasks_list, return_exceptions=True)
    precos = []
    for r in resultados:
        if isinstance(r, list):
            precos.extend(r)
        elif isinstance(r, dict):
            precos.append(r)
    precos.sort(key=lambda x: x.get("preco", 9999))
    return precos

async def _preco_amazon(titulo: str, isbn: str = "") -> list[dict]:
    """Gera link de busca Amazon BR (sem scraping direto para respeitar TOS)"""
    query = isbn if isbn else titulo
    url = f"https://www.amazon.com.br/s?k={query.replace(' ', '+')}"
    # Retorna link de busca — o usuário clica para ver o preço real
    return [{
        "loja": "Amazon BR",
        "preco": None,
        "url": url,
        "url_busca": True,
        "emoji": "🛒",
        "confiavel": True,
    }]

async def _preco_estante(titulo: str, autor: str = "") -> list[dict]:
    query = f"{titulo} {autor}".strip().replace(" ", "+")
    url = f"https://www.estantevirtual.com.br/busca?q={query}"
    return [{
        "loja": "Estante Virtual",
        "preco": None,
        "url": url,
        "url_busca": True,
        "emoji": "📖",
        "confiavel": True,
    }]

def gerar_links_compra(livro: dict) -> list[dict]:
    """Gera links diretos de busca para todas as lojas confiáveis"""
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

# ─── Recomendações por IA (usando perfil) ─────────────────────────────────────
async def recomendar_por_perfil(perfil: dict, historico_titulos: list[str]) -> list[dict]:
    """Busca recomendações baseadas no perfil do usuário"""
    generos = perfil.get("generos", [])
    autores = perfil.get("autores", [])

    queries = []
    if autores:
        queries.append(f"autor:{autores[0]}")
    if generos:
        queries.append(f"subject:{generos[0]}")
    if not queries:
        queries.append("bestseller")

    todos = []
    for q in queries[:2]:
        livros = await buscar_livros(q, 8)
        for l in livros:
            if l["titulo"] not in historico_titulos:
                todos.append(l)

    # Remove duplicatas
    vistos = set()
    unicos = []
    for l in todos:
        if l["titulo"] not in vistos:
            vistos.add(l["titulo"])
            unicos.append(l)

    return unicos[:5]
