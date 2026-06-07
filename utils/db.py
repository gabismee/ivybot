import os, json
from contextlib import contextmanager
from datetime import datetime, date
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.nvxahdngihjzbjkcdcvb:f8gIFDuUaohPky5T@aws-1-us-east-1.pooler.supabase.com:6543/postgres")

@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS perfis (
            user_id BIGINT PRIMARY KEY, username TEXT, generos TEXT DEFAULT '[]', autores TEXT DEFAULT '[]',
            formato TEXT DEFAULT 'todos', orcamento TEXT DEFAULT 'ate_50', objetivo TEXT DEFAULT 'diversao',
            livros_ano TEXT DEFAULT '1-5', frase TEXT DEFAULT 'Livros são minha fuga favorita. 💜',
            wallpaper_url TEXT, xp INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, ultimo_registro_leitura DATE,
            meta_anual INTEGER DEFAULT 0, criado_em TIMESTAMP DEFAULT NOW(), atualizado TIMESTAMP DEFAULT NOW()
        );
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS frase TEXT DEFAULT 'Livros são minha fuga favorita. 💜';
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS wallpaper_url TEXT;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS streak INTEGER DEFAULT 0;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS ultimo_registro_leitura DATE;
        ALTER TABLE perfis ADD COLUMN IF NOT EXISTS meta_anual INTEGER DEFAULT 0;

        CREATE TABLE IF NOT EXISTS wishlist (id SERIAL PRIMARY KEY, user_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT, preco_alvo REAL, formato TEXT DEFAULT 'qualquer', adicionado TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn));
        CREATE TABLE IF NOT EXISTS biblioteca (id SERIAL PRIMARY KEY, user_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT, status TEXT DEFAULT 'quero_ler', avaliacao INTEGER, comentario TEXT, adicionado TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn));
        CREATE TABLE IF NOT EXISTS historico_precos (id SERIAL PRIMARY KEY, isbn TEXT, loja TEXT, preco REAL, url TEXT, registrado TIMESTAMP DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS clube_livros (id SERIAL PRIMARY KEY, guild_id BIGINT, titulo TEXT, autor TEXT, isbn TEXT, capa_url TEXT, iniciado TIMESTAMP DEFAULT NOW(), encerrado TIMESTAMP, ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS clube_progresso (id SERIAL PRIMARY KEY, clube_id INTEGER, user_id BIGINT, pagina_atual INTEGER DEFAULT 0, total_paginas INTEGER DEFAULT 0, atualizado TIMESTAMP DEFAULT NOW(), UNIQUE(clube_id, user_id));
        CREATE TABLE IF NOT EXISTS clube_votos (id SERIAL PRIMARY KEY, guild_id BIGINT, isbn TEXT, titulo TEXT, user_id BIGINT, votado_em TIMESTAMP DEFAULT NOW(), UNIQUE(guild_id, user_id));
        CREATE TABLE IF NOT EXISTS avaliacoes (id SERIAL PRIMARY KEY, user_id BIGINT, isbn TEXT, titulo TEXT, autor TEXT, estrelas INTEGER, comentario TEXT, avaliado_em TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, isbn));
        CREATE TABLE IF NOT EXISTS config_guild (guild_id BIGINT PRIMARY KEY, canal_promocoes BIGINT, canal_ebooks BIGINT, canal_clube BIGINT, canal_ranking BIGINT, alertas_ativos INTEGER DEFAULT 1, horario_promocoes TEXT DEFAULT '09:00');
        CREATE TABLE IF NOT EXISTS cache_livros (isbn TEXT PRIMARY KEY, dados TEXT, cached_em TIMESTAMP DEFAULT NOW());

        CREATE TABLE IF NOT EXISTS social_interacoes (id SERIAL PRIMARY KEY, tipo TEXT NOT NULL, remetente_id BIGINT NOT NULL, destinatario_id BIGINT NOT NULL, mensagem TEXT, criado_em TIMESTAMP DEFAULT NOW());
        CREATE TABLE IF NOT EXISTS quiz_scores (id SERIAL PRIMARY KEY, guild_id BIGINT, user_id BIGINT, pontos INTEGER DEFAULT 0, acertos INTEGER DEFAULT 0, partidas INTEGER DEFAULT 0, atualizado TIMESTAMP DEFAULT NOW(), UNIQUE(guild_id, user_id));
        CREATE TABLE IF NOT EXISTS desafios_usuario (id SERIAL PRIMARY KEY, user_id BIGINT, desafio_id TEXT, progresso INTEGER DEFAULT 0, concluido INTEGER DEFAULT 0, atualizado TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, desafio_id));
        """)
    print("✅ Banco PostgreSQL inicializado")

def _safe_json(v):
    if isinstance(v, list): return v
    try: return json.loads(v or "[]")
    except Exception: return []

def ensure_perfil(user_id:int, username:str=""):
    with get_db() as conn:
        cur=conn.cursor()
        cur.execute("""INSERT INTO perfis (user_id, username) VALUES (%s,%s)
        ON CONFLICT(user_id) DO UPDATE SET username=COALESCE(NULLIF(EXCLUDED.username,''), perfis.username), atualizado=NOW()""", (user_id, username or ""))

def get_perfil(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM perfis WHERE user_id=%s",(user_id,)); row=cur.fetchone()
        if not row: return None
        d=dict(row); d["generos"]=_safe_json(d.get("generos")); d["autores"]=_safe_json(d.get("autores")); return d

def salvar_perfil(user_id:int, username:str, dados:dict):
    ensure_perfil(user_id, username)
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""UPDATE perfis SET username=%s, generos=%s, autores=%s, formato=%s, orcamento=%s, objetivo=%s, livros_ano=%s, atualizado=NOW() WHERE user_id=%s""",
        (username, json.dumps(dados.get("generos",[])), json.dumps(dados.get("autores",[])), dados.get("formato","todos"), dados.get("orcamento","ate_50"), dados.get("objetivo","diversao"), dados.get("livros_ano","1-5"), user_id))

def atualizar_personalizacao(user_id:int, username:str, frase=None, wallpaper_url=None, reset_wallpaper=False):
    ensure_perfil(user_id, username)
    sets=[]; vals=[]
    if frase is not None: sets.append("frase=%s"); vals.append(frase[:160])
    if wallpaper_url is not None: sets.append("wallpaper_url=%s"); vals.append(wallpaper_url)
    if reset_wallpaper: sets.append("wallpaper_url=NULL")
    if not sets: return
    vals.append(user_id)
    with get_db() as conn:
        cur=conn.cursor(); cur.execute(f"UPDATE perfis SET {', '.join(sets)}, atualizado=NOW() WHERE user_id=%s", vals)

def add_xp(user_id:int, username:str, amount:int):
    ensure_perfil(user_id, username)
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("UPDATE perfis SET xp=COALESCE(xp,0)+%s, atualizado=NOW() WHERE user_id=%s", (amount, user_id))

def get_nivel(xp:int):
    xp=int(xp or 0); nivel=1; need=100
    while xp >= need:
        nivel += 1; need += 100 + nivel*50
    anterior = need - (100 + nivel*50) if nivel > 1 else 0
    return {"nivel": nivel, "xp": xp, "proximo": need, "atual_no_nivel": max(0, xp-anterior), "necessario_nivel": need-anterior}

def registrar_leitura(user_id:int, username:str, minutos:int):
    ensure_perfil(user_id, username)
    hoje=date.today()
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT ultimo_registro_leitura, streak FROM perfis WHERE user_id=%s", (user_id,)); row=cur.fetchone() or {}
        ultimo=row.get("ultimo_registro_leitura"); streak=int(row.get("streak") or 0)
        if ultimo == hoje: novo=streak
        elif ultimo and (hoje-ultimo).days == 1: novo=streak+1
        else: novo=1
        cur.execute("UPDATE perfis SET streak=%s, ultimo_registro_leitura=%s, xp=COALESCE(xp,0)+15 WHERE user_id=%s", (novo, hoje, user_id))
    return novo

# Wishlist/Biblioteca/Avaliações
def get_wishlist(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM wishlist WHERE user_id=%s ORDER BY adicionado DESC",(user_id,)); return [dict(r) for r in cur.fetchall()]

def adicionar_wishlist(user_id:int, livro:dict, preco_alvo:float=None):
    try:
        with get_db() as conn:
            cur=conn.cursor(); cur.execute("""INSERT INTO wishlist (user_id,titulo,autor,isbn,capa_url,preco_alvo,formato) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,isbn) DO NOTHING""", (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn") or livro["titulo"], livro.get("capa_url",""), preco_alvo, livro.get("formato","qualquer")))
            return cur.rowcount>0
    except Exception: return False

def remover_wishlist(user_id:int, isbn:str):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("DELETE FROM wishlist WHERE user_id=%s AND (isbn=%s OR titulo=%s)",(user_id,isbn,isbn)); return cur.rowcount>0

def get_biblioteca(user_id:int, status:str=None):
    with get_db() as conn:
        cur=conn.cursor();
        if status: cur.execute("SELECT * FROM biblioteca WHERE user_id=%s AND status=%s ORDER BY adicionado DESC",(user_id,status))
        else: cur.execute("SELECT * FROM biblioteca WHERE user_id=%s ORDER BY adicionado DESC",(user_id,))
        return [dict(r) for r in cur.fetchall()]

def atualizar_biblioteca(user_id:int, livro:dict, status:str):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""INSERT INTO biblioteca (user_id,titulo,autor,isbn,capa_url,status) VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT(user_id,isbn) DO UPDATE SET status=EXCLUDED.status, adicionado=NOW()""",(user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn") or livro["titulo"], livro.get("capa_url",""), status))
    return True

def avaliar_livro(user_id:int, livro:dict, estrelas:int, comentario:str=""):
    isbn=livro.get("isbn") or livro["titulo"]
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""INSERT INTO avaliacoes (user_id,isbn,titulo,autor,estrelas,comentario) VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT(user_id,isbn) DO UPDATE SET estrelas=EXCLUDED.estrelas, comentario=EXCLUDED.comentario, avaliado_em=NOW()""",(user_id,isbn,livro["titulo"],livro.get("autor",""),estrelas,comentario))
        cur.execute("""INSERT INTO biblioteca (user_id,titulo,autor,isbn,capa_url,status,avaliacao,comentario) VALUES (%s,%s,%s,%s,%s,'lido',%s,%s)
        ON CONFLICT(user_id,isbn) DO UPDATE SET avaliacao=EXCLUDED.avaliacao, comentario=EXCLUDED.comentario, status='lido'""",(user_id,livro["titulo"],livro.get("autor",""),isbn,livro.get("capa_url",""),estrelas,comentario))
    return True

def get_stats_usuario(user_id:int):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT COUNT(*) n FROM biblioteca WHERE user_id=%s AND status='lido'",(user_id,)); lidos=cur.fetchone()["n"]
        cur.execute("SELECT AVG(estrelas) m FROM avaliacoes WHERE user_id=%s",(user_id,)); media=cur.fetchone()["m"]
        cur.execute("SELECT COUNT(*) n FROM wishlist WHERE user_id=%s",(user_id,)); wishlist=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM social_interacoes WHERE destinatario_id=%s AND tipo='cookie'",(user_id,)); cookies=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM social_interacoes WHERE destinatario_id=%s AND tipo='curtida'",(user_id,)); curtidas=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) n FROM social_interacoes WHERE destinatario_id=%s AND tipo='cartinha'",(user_id,)); cartinhas=cur.fetchone()["n"]
    return {"lidos":lidos,"media_avaliacao":round(float(media or 0),1),"wishlist":wishlist,"cookies":cookies,"curtidas":curtidas,"cartinhas":cartinhas}

# preços/config/cache/ranking legado
def registrar_preco(isbn, loja, preco, url):
    with get_db() as conn: conn.cursor().execute("INSERT INTO historico_precos (isbn,loja,preco,url) VALUES (%s,%s,%s,%s)",(isbn,loja,preco,url))
def get_historico_precos(isbn):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT * FROM historico_precos WHERE isbn=%s ORDER BY registrado DESC LIMIT 60",(isbn,)); return [dict(r) for r in cur.fetchall()]
def get_menor_preco(isbn):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT MIN(preco) menor FROM historico_precos WHERE isbn=%s",(isbn,)); row=cur.fetchone(); return row["menor"] if row else None
def get_config(guild_id):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT * FROM config_guild WHERE guild_id=%s",(guild_id,)); row=cur.fetchone(); return dict(row) if row else {}
def salvar_config(guild_id,chave,valor):
    permitido={"canal_promocoes","canal_ebooks","canal_clube","canal_ranking","alertas_ativos","horario_promocoes"}
    if chave not in permitido: raise ValueError("Config inválida")
    with get_db() as conn: conn.cursor().execute(f"INSERT INTO config_guild (guild_id,{chave}) VALUES (%s,%s) ON CONFLICT(guild_id) DO UPDATE SET {chave}=EXCLUDED.{chave}",(guild_id,valor))
def get_cache_livro(isbn): return None
def salvar_cache_livro(isbn,dados): pass

def get_ranking_wishlist(limit=10):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT titulo,autor,isbn,COUNT(*) total FROM wishlist GROUP BY isbn,titulo,autor ORDER BY total DESC LIMIT %s",(limit,)); return [dict(r) for r in cur.fetchall()]
def get_ranking_avaliacoes(limit=10):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT titulo,autor,isbn,AVG(estrelas) media,COUNT(*) votos FROM avaliacoes GROUP BY isbn,titulo,autor ORDER BY media DESC,votos DESC LIMIT %s",(limit,)); return [dict(r) for r in cur.fetchall()]
def get_ranking_xp(limit=10):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT user_id,username,xp,streak FROM perfis ORDER BY xp DESC LIMIT %s",(limit,)); return [dict(r) for r in cur.fetchall()]

# Social
def registrar_interacao(tipo, remetente_id, destinatario_id, mensagem=None):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO social_interacoes (tipo,remetente_id,destinatario_id,mensagem) VALUES (%s,%s,%s,%s)",(tipo,remetente_id,destinatario_id,mensagem))

def ja_interagiu_hoje(tipo, remetente_id, destinatario_id):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT 1 FROM social_interacoes WHERE tipo=%s AND remetente_id=%s AND destinatario_id=%s AND criado_em::date=CURRENT_DATE LIMIT 1",(tipo,remetente_id,destinatario_id)); return cur.fetchone() is not None

def listar_interacoes(tipo, destinatario_id, limit=10):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("SELECT * FROM social_interacoes WHERE tipo=%s AND destinatario_id=%s ORDER BY criado_em DESC LIMIT %s",(tipo,destinatario_id,limit)); return [dict(r) for r in cur.fetchall()]

# Quiz
def atualizar_quiz_score(guild_id,user_id,pontos,acertos=0,partida=False):
    with get_db() as conn:
        cur=conn.cursor(); cur.execute("""INSERT INTO quiz_scores (guild_id,user_id,pontos,acertos,partidas) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT(guild_id,user_id) DO UPDATE SET pontos=quiz_scores.pontos+EXCLUDED.pontos, acertos=quiz_scores.acertos+EXCLUDED.acertos, partidas=quiz_scores.partidas+EXCLUDED.partidas, atualizado=NOW()""",(guild_id,user_id,pontos,acertos,1 if partida else 0))
def get_quiz_ranking(guild_id,limit=10):
    with get_db() as conn: cur=conn.cursor(); cur.execute("SELECT * FROM quiz_scores WHERE guild_id=%s ORDER BY pontos DESC,acertos DESC LIMIT %s",(guild_id,limit)); return [dict(r) for r in cur.fetchall()]
