"""
Busca info de autores via Wikipedia API (pt + en) e Google Books.
Sem chave de API necessária.
"""
import aiohttp, logging, re, urllib.parse

log = logging.getLogger('Ivy.AutorInfo')

# ─── AUTOR ───────────────────────────────────────────────────────────────────

async def buscar_autor(nome: str) -> dict | None:
    """Busca foto, bio, nascimento e obras do autor."""
    info = await _wikipedia_autor(nome, lang='pt')
    if not info:
        info = await _wikipedia_autor(nome, lang='en')
    # Enriquecer obras via Google Books
    obras = await _obras_google(nome)
    if info:
        if obras and not info.get('obras'):
            info['obras'] = obras
        return info
    # Se Wikipedia falhou, monta só com Google Books
    if obras:
        return {
            'nome': nome,
            'bio': '',
            'nascimento': '',
            'foto_url': '',
            'obras': obras,
            'generos': [],
        }
    return None


async def _wikipedia_autor(nome: str, lang: str = 'pt') -> dict | None:
    """Busca autor na Wikipedia em português ou inglês."""
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0 Discord Bot'}) as s:
            # 1. Buscar título da página
            search_url = f'https://{lang}.wikipedia.org/w/api.php'
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': nome,
                'srnamespace': 0,
                'srlimit': 1,
                'format': 'json',
            }
            async with s.get(search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                results = data.get('query', {}).get('search', [])
                if not results:
                    return None
                page_title = results[0]['title']

            # 2. Buscar extrato + imagem
            detail_params = {
                'action': 'query',
                'prop': 'extracts|pageimages|revisions',
                'exintro': True,
                'explaintext': True,
                'exsentences': 5,
                'pithumbsize': 300,
                'titles': page_title,
                'rvprop': 'content',
                'rvsection': 0,
                'format': 'json',
            }
            async with s.get(search_url, params=detail_params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                pages = data.get('query', {}).get('pages', {})
                if not pages:
                    return None
                page = next(iter(pages.values()))

            bio_raw = page.get('extract', '')
            bio = _limpar_bio(bio_raw)[:700]
            foto_url = page.get('thumbnail', {}).get('source', '')

            # Extrai datas do infobox via regex no wikitext (campo revisions)
            nascimento = ''
            rev = ''
            for rv in page.get('revisions', []):
                rev = rv.get('*', '') or rv.get('slots', {}).get('main', {}).get('*', '')
                if rev:
                    break
            m = re.search(r'\|\s*(?:birth_date|data_nascimento)\s*=\s*([^\n|]+)', rev, re.IGNORECASE)
            if m:
                nascimento = re.sub(r'\{\{[^}]+\}\}', '', m.group(1)).strip()
                nascimento = re.sub(r'\s+', ' ', nascimento).strip()

            return {
                'nome': page_title,
                'bio': bio,
                'nascimento': nascimento,
                'foto_url': foto_url,
                'obras': [],
                'generos': [],
            }
    except Exception as e:
        log.error('Erro Wikipedia autor (%s): %s', lang, e)
        return None


async def _obras_google(nome: str) -> list[str]:
    """Busca lista de obras do autor via Google Books."""
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0'}) as s:
            params = {'q': f'inauthor:"{nome}"', 'maxResults': 8, 'printType': 'books', 'country': 'BR'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                obras = []
                vistos = set()
                for item in data.get('items', []):
                    t = item.get('volumeInfo', {}).get('title', '')
                    tn = t.lower().strip()
                    if t and tn not in vistos:
                        vistos.add(tn)
                        obras.append(t)
                return obras[:8]
    except Exception as e:
        log.error('Erro Google Books obras: %s', e)
        return []


# ─── PERSONAGEM ───────────────────────────────────────────────────────────────

async def buscar_personagem(nome: str) -> dict | None:
    """
    Busca info de personagem via Wikipedia primeiro, depois Google Books.
    """
    info = await _wikipedia_personagem(nome, lang='pt')
    if not info:
        info = await _wikipedia_personagem(nome, lang='en')
    if info:
        return info
    return await _personagem_google(nome)


async def _wikipedia_personagem(nome: str, lang: str = 'pt') -> dict | None:
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0 Discord Bot'}) as s:
            search_url = f'https://{lang}.wikipedia.org/w/api.php'
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': f'{nome} personagem fictício',
                'srnamespace': 0,
                'srlimit': 1,
                'format': 'json',
            }
            async with s.get(search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                results = data.get('query', {}).get('search', [])
                if not results:
                    return None
                page_title = results[0]['title']

            detail_params = {
                'action': 'query',
                'prop': 'extracts|pageimages',
                'exintro': True,
                'explaintext': True,
                'exsentences': 4,
                'pithumbsize': 300,
                'titles': page_title,
                'format': 'json',
            }
            async with s.get(search_url, params=detail_params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                pages = data.get('query', {}).get('pages', {})
                page = next(iter(pages.values()))

            bio = _limpar_bio(page.get('extract', ''))[:500]
            foto_url = page.get('thumbnail', {}).get('source', '')
            if not bio or len(bio) < 30:
                return None

            return {
                'nome': page_title,
                'obra': '',
                'autor': '',
                'descricao': bio,
                'capa_url': foto_url,
            }
    except Exception as e:
        log.error('Erro Wikipedia personagem (%s): %s', lang, e)
        return None


async def _personagem_google(nome: str) -> dict | None:
    """Fallback: Google Books para personagens."""
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0'}) as s:
            params = {'q': nome, 'maxResults': 3, 'printType': 'books', 'country': 'BR'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                items = data.get('items', [])
                if not items:
                    return None
                info = items[0].get('volumeInfo', {})
                thumb = (info.get('imageLinks', {}).get('thumbnail') or '').replace('http://', 'https://')
                return {
                    'nome': nome,
                    'obra': info.get('title', ''),
                    'autor': ', '.join(info.get('authors', [])),
                    'descricao': (info.get('description') or '')[:400],
                    'capa_url': thumb,
                }
    except Exception as e:
        log.error('Erro Google Books personagem: %s', e)
        return None


def _limpar_bio(bio: str) -> str:
    bio = re.sub(r'\[\d+\]', '', bio)        # remove [1], [2] etc
    bio = re.sub(r'\[.*?\]', '', bio)         # remove [[wikilinks]]
    bio = re.sub(r'\{.*?\}', '', bio)         # remove {{templates}}
    bio = re.sub(r'<[^>]+>', '', bio)         # remove HTML tags
    bio = re.sub(r'\s+', ' ', bio).strip()
    return bio
