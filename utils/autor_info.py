"""
Busca info de autores/personagens usando Wikipedia REST + Google Books.
Não precisa de chave. Também tem uma base curta para nomes famosos, porque
Wikipedia pode falhar em algumas consultas ou retornar páginas genéricas.
"""
import aiohttp, logging, re, urllib.parse

log = logging.getLogger('Ivy.AutorInfo')

AUTORES_FIXOS = {
    'machado de assis': {
        'nome': 'Machado de Assis',
        'bio': 'Joaquim Maria Machado de Assis foi um escritor brasileiro, considerado um dos maiores nomes da literatura em língua portuguesa. Escreveu romances, contos, crônicas, poesias e peças, sendo um dos fundadores da Academia Brasileira de Letras.',
        'generos': ['Realismo', 'Romance', 'Conto', 'Crônica', 'Poesia'],
        'obras': ['Dom Casmurro', 'Memórias Póstumas de Brás Cubas', 'Quincas Borba', 'O Alienista', 'Esaú e Jacó'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Machado_de_Assis_1904.jpg/330px-Machado_de_Assis_1904.jpg',
        'nascimento': '1839–1908',
    },
    'clarice lispector': {
        'nome': 'Clarice Lispector',
        'bio': 'Clarice Lispector foi uma escritora e jornalista brasileira, conhecida por sua escrita introspectiva, psicológica e profundamente poética. É uma das autoras mais importantes da literatura brasileira do século XX.',
        'generos': ['Romance', 'Conto', 'Ficção psicológica', 'Literatura modernista'],
        'obras': ['A Hora da Estrela', 'Perto do Coração Selvagem', 'Laços de Família', 'A Paixão Segundo G.H.', 'Água Viva'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Clarice_Lispector_%28cropped%29.jpg/330px-Clarice_Lispector_%28cropped%29.jpg',
        'nascimento': '1920–1977',
    },
    'j k rowling': {
        'nome': 'J. K. Rowling',
        'bio': 'J. K. Rowling é uma escritora britânica conhecida mundialmente pela série Harry Potter, uma das sagas literárias mais populares da história recente.',
        'generos': ['Fantasia', 'Infantojuvenil', 'Aventura'],
        'obras': ['Harry Potter e a Pedra Filosofal', 'Harry Potter e a Câmara Secreta', 'Harry Potter e o Prisioneiro de Azkaban', 'Morte Súbita'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/J._K._Rowling_2010.jpg/330px-J._K._Rowling_2010.jpg',
        'nascimento': '1965–',
    },
    'j. k. rowling': 'j k rowling',
    'jk rowling': 'j k rowling',
    'rick riordan': {
        'nome': 'Rick Riordan',
        'bio': 'Rick Riordan é um escritor norte-americano conhecido por misturar mitologia, aventura e humor em séries juvenis, especialmente Percy Jackson e os Olimpianos.',
        'generos': ['Fantasia', 'Mitologia', 'Infantojuvenil', 'Aventura'],
        'obras': ['Percy Jackson e o Ladrão de Raios', 'O Mar de Monstros', 'Os Heróis do Olimpo', 'As Crônicas dos Kane', 'Magnus Chase'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Rick_Riordan_%2847616144121%29_%28cropped%29.jpg/330px-Rick_Riordan_%2847616144121%29_%28cropped%29.jpg',
        'nascimento': '1964–',
    },
    'j r r tolkien': {
        'nome': 'J. R. R. Tolkien',
        'bio': 'J. R. R. Tolkien foi um escritor, filólogo e professor britânico, famoso por criar a Terra-média e obras fundamentais da fantasia moderna.',
        'generos': ['Fantasia', 'Alta fantasia', 'Aventura', 'Mitologia fictícia'],
        'obras': ['O Hobbit', 'O Senhor dos Anéis', 'O Silmarillion', 'Contos Inacabados'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/J._R._R._Tolkien%2C_1940s.jpg/330px-J._R._R._Tolkien%2C_1940s.jpg',
        'nascimento': '1892–1973',
    },
    'tolkien': 'j r r tolkien',
    'stephen king': {
        'nome': 'Stephen King',
        'bio': 'Stephen King é um escritor norte-americano conhecido por romances de terror, suspense e fantasia sombria, com forte presença na cultura popular.',
        'generos': ['Terror', 'Suspense', 'Fantasia sombria', 'Ficção sobrenatural'],
        'obras': ['It: A Coisa', 'Carrie', 'Misery', 'O Iluminado', 'A Torre Negra'],
        'foto_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Stephen_King%2C_Comicon.jpg/330px-Stephen_King%2C_Comicon.jpg',
        'nascimento': '1947–',
    },
}

PERSONAGENS_FIXOS = {
    'harry potter': {
        'nome': 'Harry Potter', 'obra': 'Harry Potter', 'autor': 'J. K. Rowling',
        'descricao': 'Harry Potter é um jovem bruxo que descobre seu passado mágico e passa a estudar em Hogwarts. A saga acompanha sua amizade com Rony e Hermione e sua luta contra Lord Voldemort.',
        'capa_url': 'https://upload.wikimedia.org/wikipedia/en/d/d7/Harry_Potter_character_poster.jpg',
    },
    'hermione granger': {
        'nome': 'Hermione Granger', 'obra': 'Harry Potter', 'autor': 'J. K. Rowling',
        'descricao': 'Hermione Granger é uma das melhores amigas de Harry Potter, conhecida por sua inteligência, dedicação aos estudos e coragem.',
        'capa_url': 'https://upload.wikimedia.org/wikipedia/en/d/d3/Hermione_Granger_poster.jpg',
    },
    'frodo': {
        'nome': 'Frodo Bolseiro', 'obra': 'O Senhor dos Anéis', 'autor': 'J. R. R. Tolkien',
        'descricao': 'Frodo Bolseiro é o hobbit encarregado de levar o Um Anel até Mordor para destruí-lo, enfrentando uma jornada difícil e transformadora.',
        'capa_url': 'https://upload.wikimedia.org/wikipedia/en/4/4e/Elijah_Wood_as_Frodo_Baggins.png',
    },
    'frodo bolseiro': 'frodo',
    'katniss': {
        'nome': 'Katniss Everdeen', 'obra': 'Jogos Vorazes', 'autor': 'Suzanne Collins',
        'descricao': 'Katniss Everdeen é a protagonista de Jogos Vorazes. Forte, estratégica e protetora, ela se torna símbolo de resistência contra a Capital.',
        'capa_url': 'https://upload.wikimedia.org/wikipedia/en/6/63/Katniss_Everdeen.jpg',
    },
    'katniss everdeen': 'katniss',
    'capitu': {
        'nome': 'Capitu', 'obra': 'Dom Casmurro', 'autor': 'Machado de Assis',
        'descricao': 'Capitu é uma das personagens mais famosas da literatura brasileira, lembrada por sua personalidade marcante e pela ambiguidade em torno da narrativa de Bentinho.',
        'capa_url': '',
    },
}


def _norm(s: str) -> str:
    s = (s or '').strip().lower()
    s = re.sub(r'[.]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def _resolve_fixo(base: dict, nome: str):
    key = _norm(nome)
    val = base.get(key)
    if isinstance(val, str):
        val = base.get(val)
    return dict(val) if isinstance(val, dict) else None


async def buscar_autor(nome: str) -> dict | None:
    fixo = _resolve_fixo(AUTORES_FIXOS, nome)
    if fixo:
        return fixo

    info = await _wikipedia_summary(nome, kind='autor', lang='pt')
    if not info:
        info = await _wikipedia_summary(nome, kind='author', lang='en')

    obras = await _obras_google(nome)
    if info:
        info['obras'] = obras or info.get('obras', [])
        if not info.get('generos'):
            info['generos'] = _inferir_generos(info.get('bio', ''))
        return info

    if obras:
        return {'nome': nome, 'bio': 'Biografia não encontrada automaticamente, mas encontrei obras relacionadas a esse nome.', 'nascimento': '', 'foto_url': '', 'obras': obras, 'generos': []}
    return None


async def buscar_personagem(nome: str) -> dict | None:
    fixo = _resolve_fixo(PERSONAGENS_FIXOS, nome)
    if fixo:
        return fixo

    consultas = [f'{nome} personagem', f'{nome} personagem fictício', f'{nome} fictional character', nome]
    for lang in ('pt', 'en'):
        for q in consultas:
            info = await _wikipedia_summary(q, kind='personagem', lang=lang)
            if info and info.get('descricao'):
                return info
    return await _personagem_google(nome)


async def _wikipedia_summary(query: str, kind: str, lang: str = 'pt') -> dict | None:
    """Busca página por opensearch e lê summary REST."""
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0 Discord Bot'}) as s:
            api = f'https://{lang}.wikipedia.org/w/api.php'
            params = {'action': 'opensearch', 'search': query, 'limit': 1, 'namespace': 0, 'format': 'json'}
            async with s.get(api, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                titles = data[1] if len(data) > 1 else []
                if not titles:
                    return None
                title = titles[0]

            encoded = urllib.parse.quote(title.replace(' ', '_'))
            url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}'
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()

            extract = _limpar_bio(data.get('extract', ''))
            if not extract or len(extract) < 35:
                return None
            thumb = (data.get('thumbnail') or {}).get('source') or (data.get('originalimage') or {}).get('source') or ''
            page_title = data.get('title') or title

            if kind == 'personagem':
                return {'nome': page_title, 'obra': '', 'autor': '', 'descricao': extract[:650], 'capa_url': thumb}
            return {
                'nome': page_title,
                'bio': extract[:850],
                'nascimento': '',
                'foto_url': thumb,
                'obras': [],
                'generos': _inferir_generos(extract),
            }
    except Exception as e:
        log.error('Erro Wikipedia summary (%s/%s): %s', lang, kind, e)
        return None


async def _obras_google(nome: str) -> list[str]:
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0'}) as s:
            params = {'q': f'inauthor:"{nome}"', 'maxResults': 10, 'printType': 'books', 'country': 'BR', 'langRestrict': 'pt'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                obras, vistos = [], set()
                for item in data.get('items', []):
                    t = (item.get('volumeInfo', {}) or {}).get('title', '')
                    tn = _norm(t)
                    if t and tn not in vistos:
                        vistos.add(tn); obras.append(t)
                return obras[:10]
    except Exception as e:
        log.error('Erro Google Books obras: %s', e)
        return []


async def _personagem_google(nome: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0'}) as s:
            params = {'q': f'"{nome}" personagem livro', 'maxResults': 5, 'printType': 'books', 'country': 'BR', 'langRestrict': 'pt'}
            async with s.get('https://www.googleapis.com/books/v1/volumes', params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                items = data.get('items', [])
                if not items:
                    return None
                info = items[0].get('volumeInfo', {})
                thumb = (info.get('imageLinks', {}).get('thumbnail') or '').replace('http://', 'https://')
                desc = info.get('description') or 'Encontrei uma obra relacionada a esse nome, mas não achei uma descrição específica do personagem.'
                return {'nome': nome, 'obra': info.get('title', ''), 'autor': ', '.join(info.get('authors', [])), 'descricao': desc[:500], 'capa_url': thumb}
    except Exception as e:
        log.error('Erro Google Books personagem: %s', e)
        return None


def _inferir_generos(texto: str) -> list[str]:
    t = _norm(texto)
    generos = []
    regras = [
        ('fantasia', 'Fantasia'), ('terror', 'Terror'), ('suspense', 'Suspense'), ('mistério', 'Mistério'),
        ('romance', 'Romance'), ('poesia', 'Poesia'), ('conto', 'Conto'), ('crônica', 'Crônica'),
        ('ficção científica', 'Ficção científica'), ('infantojuvenil', 'Infantojuvenil'), ('jornalista', 'Crônica/Jornalismo'),
    ]
    for chave, nome in regras:
        if chave in t and nome not in generos:
            generos.append(nome)
    return generos[:6]


def _limpar_bio(bio: str) -> str:
    bio = re.sub(r'\[\d+\]', '', bio)
    bio = re.sub(r'\s+', ' ', bio).strip()
    return bio
