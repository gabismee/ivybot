import os
import re
import random
import aiohttp
from urllib.parse import quote_plus

DIRECT_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
TENOR_API_KEY = os.getenv('TENOR_API_KEY') or 'LIVDSRZULELA'
TENOR_V2_BASE = 'https://tenor.googleapis.com/v2'

async def tenor_gif_from_id(post_id: str | int | None) -> str | None:
    """Busca a URL direta do GIF no Tenor usando o ID do post.

    Usa TENOR_API_KEY do Render quando existir; se não existir, usa a chave
    pública de teste da documentação: LIVDSRZULELA.
    """
    if not post_id:
        return None
    post_id = str(post_id).strip()
    if not post_id:
        return None

    params = {
        'ids': post_id,
        'key': TENOR_API_KEY,
        'media_filter': 'gif,tinygif',
        'locale': 'pt_BR',
        'client_key': 'ivybot',
    }
    headers = {'User-Agent': 'IvyBot/1.0'}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f'{TENOR_V2_BASE}/posts',
                params=params,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        results = data.get('results') or []
        if not results:
            return None
        media = results[0].get('media_formats') or {}
        return (
            (media.get('gif') or {}).get('url')
            or (media.get('tinygif') or {}).get('url')
        )
    except Exception:
        return None

async def tenor_search_gif(term: str, limit: int = 20) -> str | None:
    """Busca um GIF aleatório no Tenor por termo, caso algum comando queira usar busca."""
    if not term:
        return None
    params = {
        'q': term,
        'key': TENOR_API_KEY,
        'limit': max(1, min(int(limit or 20), 50)),
        'media_filter': 'gif,tinygif',
        'locale': 'pt_BR',
        'contentfilter': 'medium',
        'client_key': 'ivybot',
    }
    headers = {'User-Agent': 'IvyBot/1.0'}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f'{TENOR_V2_BASE}/search',
                params=params,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        results = data.get('results') or []
        if not results:
            return None
        picked = random.choice(results)
        media = picked.get('media_formats') or {}
        return (
            (media.get('gif') or {}).get('url')
            or (media.get('tinygif') or {}).get('url')
        )
    except Exception:
        return None

async def resolve_tenor_url(url: str | None) -> str | None:
    """Converte página/embed do Tenor em URL direta de GIF/imagem quando possível."""
    if not url:
        return None
    url = str(url).strip().strip('<>')

    # Se receber HTML embed do Tenor, extrai o data-postid e usa API.
    post_id = extract_tenor_post_id(url)
    if post_id:
        api_url = await tenor_gif_from_id(post_id)
        if api_url:
            return api_url

    if 'media.tenor.com' in url or url.lower().split('?')[0].endswith(DIRECT_EXTS):
        return url
    if 'tenor.com' not in url:
        return url

    # Fallback: tenta pegar og:image da página, caso a API não responda.
    try:
        headers = {'User-Agent': 'Mozilla/5.0 IvyBot'}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=12), allow_redirects=True) as resp:
                html = await resp.text()
        post_id = extract_tenor_post_id(html)
        if post_id:
            api_url = await tenor_gif_from_id(post_id)
            if api_url:
                return api_url
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'https://media\.tenor\.com/[^"\'<>\s]+?\.(?:gif|webp|png)',
        ]
        for pat in patterns:
            m = re.search(pat, html, flags=re.I)
            if m:
                found = m.group(1) if m.groups() else m.group(0)
                return found.replace('&amp;', '&')
    except Exception:
        return url
    return url

def extract_tenor_post_id(value: str | None) -> str | None:
    """Extrai ID de links do Tenor ou de embeds HTML com data-postid."""
    if not value:
        return None
    value = str(value)
    patterns = [
        r'data-postid=["\'](\d+)["\']',
        r'tenor\.com/(?:pt-BR/)?view/[^\s"\']*?-(\d+)(?:[?\s"\']|$)',
        r'tenor\.com/view/[^\s"\']*?-(\d+)(?:[?\s"\']|$)',
        r'gif-(\d+)(?:[?\s"\']|$)',
    ]
    for pat in patterns:
        m = re.search(pat, value, flags=re.I)
        if m:
            return m.group(1)
    if value.strip().isdigit():
        return value.strip()
    return None

async def normalize_media_url(url: str | None) -> str | None:
    if not url:
        return None
    return await resolve_tenor_url(url)

async def wikipedia_summary(term: str, lang: str = 'pt') -> dict | None:
    """Busca resumo simples na Wikipédia, com imagem quando tiver."""
    if not term:
        return None
    headers = {'User-Agent': 'IvyBot/1.0'}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            search_url = f'https://{lang}.wikipedia.org/w/api.php'
            params = {
                'action': 'query', 'list': 'search', 'srsearch': term,
                'format': 'json', 'srlimit': 1, 'utf8': 1,
            }
            async with session.get(search_url, params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
            results = data.get('query', {}).get('search', [])
            if not results:
                return None
            title = results[0]['title']
            summary_url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title)}'
            async with session.get(summary_url, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    return None
                s = await r.json()
            return {
                'title': s.get('title') or title,
                'extract': s.get('extract') or '',
                'image': (s.get('thumbnail') or {}).get('source') or (s.get('originalimage') or {}).get('source') or '',
                'url': (s.get('content_urls') or {}).get('desktop', {}).get('page') or '',
            }
    except Exception:
        return None
