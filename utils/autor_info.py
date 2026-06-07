"""
Utilitário para buscar informações de autores e personagens via Open Library + Google Books.
"""
import aiohttp
import logging
import re

log = logging.getLogger('Ivy.AutorInfo')

async def buscar_autor(nome: str) -> dict | None:
    """
    Busca informações completas de um autor:
    - Foto, bio, gêneros literários, obras principais.
    Usa Open Library como fonte principal.
    """
    result = await _buscar_open_library_autor(nome)
    if not result:
        result = await _buscar_google_autor(nome)
    return result


async def _buscar_open_library_autor(nome: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as s:
            # Buscar autor pelo nome
            params = {'q': nome, 'type': '/type/author', 'limit': 1}
            async with s.get('https://openlibrary.org/search/authors.json', params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                docs = data.get('docs', [])
                if not docs:
                    return None
                autor = docs[0]
                key = autor.get('key', '')  # ex: OL23919A

            # Buscar detalhes do autor
            if not key:
                return None
            async with s.get(f'https://openlibrary.org/authors/{key}.json', timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                det = await r.json()

            # Buscar obras do autor
            obras = []
            async with s.get(f'https://openlibrary.org/authors/{key}/works.json', params={'limit': 10}, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    wdata = await r.json()
                    for w in wdata.get('entries', [])[:8]:
                        t = w.get('title', '')
                        if t:
                            obras.append(t)

            nome_real = det.get('name', nome)
            # Bio pode ser string ou dict {'type':..., 'value':...}
            bio_raw = det.get('bio', '')
            if isinstance(bio_raw, dict):
                bio_raw = bio_raw.get('value', '')
            bio = _limpar_bio(str(bio_raw))[:700] if bio_raw else ''

            # Data de nascimento
            nascimento = det.get('birth_date', '')
            morte = det.get('death_date', '')
            datas = ''
            if nascimento:
                datas = f'{nascimento}'
                if morte:
                    datas += f' — {morte}'

            # Foto
            foto_url = ''
            fotos = det.get('photos', [])
            if fotos and fotos[0] > 0:
                foto_url = f'https://covers.openlibrary.org/a/id/{fotos[0]}-L.jpg'

            # Gêneros/assuntos das obras — tentar pegar dos subject_places/subjects
            generos = list(set(det.get('subjects', [])[:5]))

            return {
                'nome': nome_real,
                'bio': bio,
                'nascimento': datas,
                'foto_url': foto_url,
                'obras': obras,
                'generos': generos,
                'fonte': 'Open Library',
            }
    except Exception as e:
        log.error('Erro ao buscar autor no Open Library: %s', e)
        return None


async def _buscar_google_autor(nome: str) -> dict | None:
    """Fallback: usa Google Books para listar obras do autor."""
    try:
        async with aiohttp.ClientSession() as s:
            params = {'q': f'inauthor:"{nome}"', 'maxResults': 8, 'printType': 'books', 'country': 'BR'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                items = data.get('items', [])
                if not items:
                    return None

        obras = []
        generos = set()
        for item in items[:8]:
            info = item.get('volumeInfo', {})
            t = info.get('title', '')
            if t:
                obras.append(t)
            for g in info.get('categories', []):
                generos.add(g)

        return {
            'nome': nome,
            'bio': '',
            'nascimento': '',
            'foto_url': '',
            'obras': obras,
            'generos': list(generos)[:5],
            'fonte': 'Google Books',
        }
    except Exception as e:
        log.error('Erro ao buscar autor no Google Books: %s', e)
        return None


async def buscar_personagem(nome: str) -> dict | None:
    """
    Busca informações de um personagem via Open Library / Google Books.
    Retorna: nome, obra, descrição, imagem da obra (capa).
    """
    try:
        async with aiohttp.ClientSession() as s:
            # Tenta buscar livros relacionados ao personagem
            params = {'q': f'"{nome}" character', 'maxResults': 5, 'printType': 'books', 'country': 'BR'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                items = data.get('items', [])
                if not items:
                    return None

        # Pegar o livro mais relevante
        item = items[0]
        info = item.get('volumeInfo', {})
        titulo = info.get('title', '')
        autores = ', '.join(info.get('authors', ['Autor desconhecido']))
        sinopse = info.get('description', '')[:500]
        thumb = (info.get('imageLinks', {}).get('thumbnail') or info.get('imageLinks', {}).get('smallThumbnail') or '').replace('http://', 'https://')

        return {
            'nome': nome,
            'obra': titulo,
            'autor': autores,
            'descricao': sinopse,
            'capa_url': thumb,
            'fonte': 'Google Books',
        }
    except Exception as e:
        log.error('Erro ao buscar personagem: %s', e)
        return None


def _limpar_bio(bio: str) -> str:
    """Remove marcações wiki/markup da bio."""
    bio = re.sub(r'\[.*?\]', '', bio)
    bio = re.sub(r'\s+', ' ', bio).strip()
    return bio
