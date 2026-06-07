import psycopg2
import psycopg2.extras
import json
from contextlib import contextmanager
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.nvxahdngihjzbjkcdcvb:f8gIFDuUaohPky5T@aws-1-us-east-1.pooler.supabase.com:6543/postgres")

@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS perfis (
            user_id BIGINT PRIMARY KEY, username TEXT, generos TEXT DEFAULT '[]', autores TEXT DEFAULT '[]',
            formato TEXT DEFAULT 'todos', orcamento TEXT DEFAULT 'ate_50', objetivo TEXT DEFAULT 'diversao',
            livros_ano TEXT DEFAULT '1-5', frase TEXT DEFAULT '', wallpaper_url TEXT DEFAULT '', xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0, ultimo_checkin DATE, criado_em TIMESTAMP DEFAULT NOW(), atualizado TIMESTAMP DEFAULT NOW()
        );
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS frase TEXT DEFAULT '';
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS wallpaper_url TEXT DEFAULT '';
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS streak INTEGER DEFAULT 0;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS ultimo_checkin DATE;

        CREATE TABLE IF NOT EXISTS wishlist (
            id SERIAL PRIMARY KEY, user_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT,
            preco_alvo REAL, formato TEXT DEFAULT 'qualquer', adicionado TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn)
        );
        CREATE TABLE IF NOT EXISTS biblioteca (
            id SERIAL PRIMARY KEY, user_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT,
            status TEXT DEFAULT 'quero_ler', avaliacao INTEGER, comentario TEXT, adicionado TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn)
        );
        ALTER TABLE biblioteca ADD COLUMN IF NOT EXISTS comentario TEXT;
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id SERIAL PRIMARY KEY, user_id BIGINT, isbn TEXT, titulo TEXT, autor TEXT, estrelas INTEGER,
            comentario TEXT, avaliado_em TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn)
        );
        CREATE TABLE IF NOT EXISTS historico_precos (id SERIAL PRIMARY KEY, isbn TEXT, loja TEXT, preco REAL, url TEXT, registrado TIMESTAMP DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS clube_livros (id SERIAL PRIMARY KEY, guild_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT, iniciado TIMESTAMP DEFAULT NOW(), encerrado TIMESTAMP, ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS clube_progresso (id SERIAL PRIMARY KEY, clube_id INTEGER, user_id BIGINT, pagina_atual INTEGER DEFAULT 0, total_paginas INTEGER DEFAULT 0, atualizado TIMESTAMP DEFAULT NOW(), UNIQUE(clube_id, user_id));
        CREATE TABLE IF NOT EXISTS clube_votos (id SERIAL PRIMARY KEY, guild_id BIGINT, isbn TEXT, titulo TEXT, user_id BIGINT, votado_em TIMESTAMP DEFAULT NOW(), UNIQUE(guild_id, user_id));
        CREATE TABLE IF NOT EXISTS config_guild (guild_id BIGINT PRIMARY KEY, canal_promocoes BIGINT, canal_ebooks BIGINT, canal_clube BIGINT, canal_ranking BIGINT, alertas_ativos INTEGER DEFAULT 1, horario_promocoes TEXT DEFAULT '09:00');
        CREATE TABLE IF NOT EXISTS cache_livros (isbn TEXT PRIMARY KEY, dados TEXT, cached_em TIMESTAMP DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS interacoes_sociais (id SERIAL PRIMARY KEY, guild_id BIGINT, tipo TEXT, remetente_id BIGINT, destinatario_id BIGINT, mensagem TEXT, criado_em TIMESTAMP DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS quiz_records (guild_id BIGINT, channel_id BIGINT, pontos INTEGER DEFAULT 0, criado_em TIMESTAMP DEFAULT NOW(), PRIMARY KEY(guild_id, channel_id));
        CREATE TABLE IF NOT EXISTS desafios_usuario (id SERIAL PRIMARY KEY, user_id BIGINT, desafio TEXT, concluido INTEGER DEFAULT 0, criado_em TIMESTAMP DEFAULT NOW(), concluido_em TIMESTAMP);
        """)
    print("✅ Banco de dados PostgreSQL inicializado")

def _json(v):
    if not v: return []
    if isinstance(v, list): return v
    try: return json.loads(v)
    except Exception: return []

def garantir_perfil(user_id:int, username:str=""):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO perfis (user_id, username) VALUES (%s,%s) ON CONFLICT(user_id) DO UPDATE SET username=COALESCE(NULLIF(EXCLUDED.username,''), perfis.username)", (user_id, username))

def get_perfil(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM perfis WHERE user_id=%s", (user_id,)); row=cur.fetchone()
        if row:
            d=dict(row); d['generos']=_json(d.get('generos')); d['autores']=_json(d.get('autores')); return d
    return None

def salvar_perfil(user_id:int, username:str, dados:dict):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""
        INSERT INTO perfis (user_id, username, generos, autores, formato, orcamento, objetivo, livros_ano, atualizado)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username, generos=EXCLUDED.generos, autores=EXCLUDED.autores,
        formato=EXCLUDED.formato, orcamento=EXCLUDED.orcamento, objetivo=EXCLUDED.objetivo, livros_ano=EXCLUDED.livros_ano, atualizado=NOW()
        """, (user_id, username, json.dumps(dados.get('generos', [])), json.dumps(dados.get('autores', [])), dados.get('formato','todos'), dados.get('orcamento','ate_50'), dados.get('objetivo','diversao'), dados.get('livros_ano','1-5')))

def atualizar_perfil_visual(user_id:int, username:str, frase=None, wallpaper_url=None):
    garantir_perfil(user_id, username)
    with get_db() as conn:
        cur=conn.cursor()
        if frase is not None: cur.execute("UPDATE perfis SET frase=%s, atualizado=NOW() WHERE user_id=%s", (frase[:120], user_id))
        if wallpaper_url is not None: cur.execute("UPDATE perfis SET wallpaper_url=%s, atualizado=NOW() WHERE user_id=%s", (wallpaper_url[:500], user_id))

def add_xp(user_id:int, username:str, quantidade:int):
    garantir_perfil(user_id, username)
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("UPDATE perfis SET xp=COALESCE(xp,0)+%s, atualizado=NOW() WHERE user_id=%s RETURNING xp", (quantidade, user_id)); return int(cur.fetchone()['xp'])

def checkin_leitura(user_id:int, username:str):
    garantir_perfil(user_id, username)
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""
        UPDATE perfis SET streak = CASE WHEN ultimo_checkin = CURRENT_DATE - INTERVAL '1 day' THEN COALESCE(streak,0)+1 WHEN ultimo_checkin = CURRENT_DATE THEN COALESCE(streak,0) ELSE 1 END,
        ultimo_checkin=CURRENT_DATE, xp=COALESCE(xp,0)+15 WHERE user_id=%s RETURNING streak, xp
        """, (user_id,)); return dict(cur.fetchone())

def get_wishlist(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM wishlist WHERE user_id=%s ORDER BY adicionado DESC", (user_id,)); return [dict(r) for r in cur.fetchall()]

def adicionar_wishlist(user_id:int, livro:dict, preco_alvo:float=None):
    try:
        with get_db() as conn:
            cur=conn.cursor(); cur.execute("""INSERT INTO wishlist (user_id,titulo,autor,isbn,capa_url,preco_alvo,formato) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,isbn) DO NOTHING""", (user_id, livro['titulo'], livro.get('autor',''), livro.get('isbn') or livro['titulo'], livro.get('capa_url',''), preco_alvo, livro.get('formato','qualquer'))); return cur.rowcount>0
    except Exception: return False

def remover_wishlist(user_id:int, isbn:str):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("DELETE FROM wishlist WHERE user_id=%s AND (isbn=%s OR titulo=%s)", (user_id,isbn,isbn)); return cur.rowcount>0

def get_biblioteca(user_id:int, status:str=None):
    with get_db() as conn:
        cur=conn.cursor();
        if status: cur.execute("SELECT * FROM biblioteca WHERE user_id=%s AND status=%s ORDER BY adicionado DESC", (user_id,status))
        else: cur.execute("SELECT * FROM biblioteca WHERE user_id=%s ORDER BY adicionado DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]

def atualizar_biblioteca(user_id:int, livro:dict, status:str):
    try:
        with get_db() as conn:
            cur=conn.cursor(); cur.execute("""INSERT INTO biblioteca (user_id,titulo,autor,isbn,capa_url,status) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,isbn) DO UPDATE SET status=EXCLUDED.status, capa_url=EXCLUDED.capa_url, adicionado=NOW()""", (user_id, livro['titulo'], livro.get('autor',''), livro.get('isbn') or livro['titulo'], livro.get('capa_url',''), status)); return True
    except Exception: return False

def avaliar_livro(user_id:int, livro:dict, estrelas:int, comentario:str=""):
    try:
        with get_db() as conn:
            isbn=livro.get('isbn') or livro['titulo']; cur=conn.cursor(); cur.execute("""INSERT INTO avaliacoes (user_id,isbn,titulo,autor,estrelas,comentario) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,isbn) DO UPDATE SET estrelas=EXCLUDED.estrelas, comentario=EXCLUDED.comentario, avaliado_em=NOW()""", (user_id,isbn,livro['titulo'],livro.get('autor',''),estrelas,comentario[:500])); cur.execute("""INSERT INTO biblioteca (user_id,titulo,autor,isbn,capa_url,status,avaliacao,comentario) VALUES (%s,%s,%s,%s,%s,'lido',%s,%s) ON CONFLICT(user_id,isbn) DO UPDATE SET avaliacao=EXCLUDED.avaliacao, comentario=EXCLUDED.comentario, status='lido'""", (user_id,livro['titulo'],livro.get('autor',''),isbn,livro.get('capa_url',''),estrelas,comentario[:500])); return True
    except Exception: return False

def registrar_preco(isbn, loja, preco, url):
    with get_db() as conn:
        conn.cursor().execute("INSERT INTO historico_precos (isbn, loja, preco, url) VALUES (%s,%s,%s,%s)", (isbn,loja,preco,url))

def get_historico_precos(isbn):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM historico_precos WHERE isbn=%s ORDER BY registrado DESC LIMIT 60", (isbn,)); return [dict(r) for r in cur.fetchall()]

def get_menor_preco(isbn):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT MIN(preco) menor FROM historico_precos WHERE isbn=%s", (isbn,)); row=cur.fetchone(); return row['menor'] if row else None

def get_config(guild_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM config_guild WHERE guild_id=%s", (guild_id,)); row=cur.fetchone(); return dict(row) if row else {}

def salvar_config(guild_id:int, chave:str, valor):
    permitidas={'canal_promocoes','canal_ebooks','canal_clube','canal_ranking','alertas_ativos','horario_promocoes'}
    if chave not in permitidas: raise ValueError('Config inválida')
    with get_db() as conn:
        conn.cursor().execute(f"INSERT INTO config_guild (guild_id,{chave}) VALUES (%s,%s) ON CONFLICT(guild_id) DO UPDATE SET {chave}=EXCLUDED.{chave}", (guild_id,valor))

def get_cache_livro(isbn): return None
def salvar_cache_livro(isbn,dados): pass

def get_ranking_wishlist(limit:int=10):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT titulo, autor, isbn, COUNT(*) total FROM wishlist GROUP BY isbn,titulo,autor ORDER BY total DESC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def get_ranking_avaliacoes(limit:int=10):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT titulo, autor, isbn, AVG(estrelas) media, COUNT(*) votos FROM avaliacoes GROUP BY isbn,titulo,autor ORDER BY media DESC, votos DESC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def get_ranking_xp(limit:int=10):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT user_id, username, xp, streak FROM perfis ORDER BY xp DESC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def get_top_livros_lidos(limit:int=50):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT titulo, autor, COUNT(*) total FROM biblioteca WHERE status='lido' GROUP BY titulo,autor ORDER BY total DESC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def get_stats_usuario(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT COUNT(*) n FROM biblioteca WHERE user_id=%s AND status='lido'", (user_id,)); lidos=cur.fetchone()['n']; cur.execute("SELECT AVG(estrelas) m FROM avaliacoes WHERE user_id=%s", (user_id,)); media=cur.fetchone()['m']; cur.execute("SELECT COUNT(*) n FROM wishlist WHERE user_id=%s", (user_id,)); wish=cur.fetchone()['n']; cur.execute("SELECT COUNT(*) n FROM interacoes_sociais WHERE destinatario_id=%s AND tipo='cookie'", (user_id,)); cookies=cur.fetchone()['n']; cur.execute("SELECT COUNT(*) n FROM interacoes_sociais WHERE destinatario_id=%s AND tipo='curtida'", (user_id,)); curtidas=cur.fetchone()['n']; cur.execute("SELECT COUNT(*) n FROM interacoes_sociais WHERE destinatario_id=%s AND tipo='cartinha'", (user_id,)); cartinhas=cur.fetchone()['n']; return {'lidos':lidos,'media_avaliacao':round(float(media or 0),1),'wishlist':wish,'cookies':cookies,'curtidas':curtidas,'cartinhas':cartinhas}

def registrar_interacao(guild_id:int, tipo:str, remetente_id:int, destinatario_id:int, mensagem:str=""):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT criado_em FROM interacoes_sociais WHERE guild_id=%s AND tipo=%s AND remetente_id=%s AND destinatario_id=%s AND criado_em::date=CURRENT_DATE", (guild_id,tipo,remetente_id,destinatario_id));
        if tipo in ('cookie','curtida') and cur.fetchone(): return False
        cur.execute("INSERT INTO interacoes_sociais (guild_id,tipo,remetente_id,destinatario_id,mensagem) VALUES (%s,%s,%s,%s,%s)", (guild_id,tipo,remetente_id,destinatario_id,mensagem[:300])); return True

def listar_interacoes(user_id:int, tipo:str, limit:int=15):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM interacoes_sociais WHERE destinatario_id=%s AND tipo=%s ORDER BY criado_em DESC LIMIT %s", (user_id,tipo,limit)); return [dict(r) for r in cur.fetchall()]

def get_quiz_record(guild_id:int, channel_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT pontos FROM quiz_records WHERE guild_id=%s AND channel_id=%s", (guild_id,channel_id)); row=cur.fetchone(); return int(row['pontos']) if row else 0

def salvar_quiz_record(guild_id:int, channel_id:int, pontos:int):
    atual=get_quiz_record(guild_id, channel_id)
    if pontos <= atual: return False
    with get_db() as conn:
        conn.cursor().execute("INSERT INTO quiz_records (guild_id,channel_id,pontos) VALUES (%s,%s,%s) ON CONFLICT(guild_id,channel_id) DO UPDATE SET pontos=EXCLUDED.pontos, criado_em=NOW()", (guild_id,channel_id,pontos)); return True

def criar_desafio(user_id:int, desafio:str):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO desafios_usuario (user_id, desafio) VALUES (%s,%s) RETURNING id", (user_id,desafio)); return cur.fetchone()['id']

def listar_desafios(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM desafios_usuario WHERE user_id=%s ORDER BY criado_em DESC LIMIT 10", (user_id,)); return [dict(r) for r in cur.fetchall()]

def concluir_desafio(user_id:int, desafio_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("UPDATE desafios_usuario SET concluido=1, concluido_em=NOW() WHERE user_id=%s AND id=%s AND concluido=0", (user_id,desafio_id)); return cur.rowcount>0

# --- Recursos adicionados: boas-vindas, lembretes e avisos de promoções ---
def _ensure_extra_tables():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        ALTER TABLE config_guild ADD COLUMN IF NOT EXISTS canal_boasvindas BIGINT;
        ALTER TABLE config_guild ADD COLUMN IF NOT EXISTS boasvindas_msg TEXT;
        ALTER TABLE config_guild ADD COLUMN IF NOT EXISTS boasvindas_gif TEXT;
        ALTER TABLE config_guild ADD COLUMN IF NOT EXISTS boasvindas_cor TEXT DEFAULT '#CDB4DB';
        CREATE TABLE IF NOT EXISTS lembretes (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            mensagem TEXT NOT NULL,
            lembrar_em TIMESTAMP NOT NULL,
            concluido INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS wishlist_notificacoes (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            isbn TEXT,
            titulo TEXT,
            preco REAL,
            url TEXT,
            enviado_em TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, isbn, preco)
        );
        """)

# envolve init_db original para garantir colunas novas mesmo em bancos já criados
_old_init_db = init_db
def init_db():
    _old_init_db()
    _ensure_extra_tables()

# amplia configs permitidas sem quebrar chamadas antigas
def salvar_config(guild_id:int, chave:str, valor):
    permitidas={'canal_promocoes','canal_ebooks','canal_clube','canal_ranking','alertas_ativos','horario_promocoes','canal_boasvindas','boasvindas_msg','boasvindas_gif','boasvindas_cor'}
    if chave not in permitidas: raise ValueError('Config inválida')
    with get_db() as conn:
        conn.cursor().execute(f"INSERT INTO config_guild (guild_id,{chave}) VALUES (%s,%s) ON CONFLICT(guild_id) DO UPDATE SET {chave}=EXCLUDED.{chave}", (guild_id,valor))

def criar_lembrete(user_id:int, mensagem:str, lembrar_em):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO lembretes (user_id,mensagem,lembrar_em) VALUES (%s,%s,%s) RETURNING id", (user_id,mensagem,lembrar_em)); return cur.fetchone()['id']

def lembretes_pendentes(limit:int=30):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM lembretes WHERE concluido=0 AND lembrar_em<=NOW() ORDER BY lembrar_em ASC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def concluir_lembrete(lembrete_id:int):
    with get_db() as conn:
        conn.cursor().execute("UPDATE lembretes SET concluido=1 WHERE id=%s", (lembrete_id,))

def wishlist_com_alerta(limit:int=200):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM wishlist WHERE preco_alvo IS NOT NULL ORDER BY adicionado DESC LIMIT %s", (limit,)); return [dict(r) for r in cur.fetchall()]

def registrar_notificacao_wishlist(user_id:int, isbn:str, titulo:str, preco:float, url:str):
    try:
        with get_db() as conn:
            cur=conn.cursor(); cur.execute("INSERT INTO wishlist_notificacoes (user_id,isbn,titulo,preco,url) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (user_id,isbn,titulo,preco,url)); return cur.rowcount>0
    except Exception:
        return False
