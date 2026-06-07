import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from contextlib import contextmanager
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:f8gIFDuUaohPky5T@db.nvxahdngihjzbjkcdcvb.supabase.co:5432/postgres"
)

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
            user_id     BIGINT PRIMARY KEY,
            username    TEXT,
            generos     TEXT DEFAULT '[]',
            autores     TEXT DEFAULT '[]',
            formato     TEXT DEFAULT 'todos',
            orcamento   TEXT DEFAULT 'ate_50',
            objetivo    TEXT DEFAULT 'diversao',
            livros_ano  TEXT DEFAULT '1-5',
            criado_em   TIMESTAMP DEFAULT NOW(),
            atualizado  TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS wishlist (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            preco_alvo  REAL,
            formato     TEXT DEFAULT 'qualquer',
            adicionado  TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, isbn)
        );

        CREATE TABLE IF NOT EXISTS biblioteca (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            status      TEXT DEFAULT 'quero_ler',
            avaliacao   INTEGER,
            comentario  TEXT,
            adicionado  TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, isbn)
        );

        CREATE TABLE IF NOT EXISTS historico_precos (
            id          SERIAL PRIMARY KEY,
            isbn        TEXT,
            loja        TEXT,
            preco       REAL,
            url         TEXT,
            registrado  TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS clube_livros (
            id          SERIAL PRIMARY KEY,
            guild_id    BIGINT,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            iniciado    TIMESTAMP DEFAULT NOW(),
            encerrado   TIMESTAMP,
            ativo       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS clube_progresso (
            id            SERIAL PRIMARY KEY,
            clube_id      INTEGER,
            user_id       BIGINT,
            pagina_atual  INTEGER DEFAULT 0,
            total_paginas INTEGER DEFAULT 0,
            atualizado    TIMESTAMP DEFAULT NOW(),
            UNIQUE(clube_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS clube_votos (
            id        SERIAL PRIMARY KEY,
            guild_id  BIGINT,
            isbn      TEXT,
            titulo    TEXT,
            user_id   BIGINT,
            votado_em TIMESTAMP DEFAULT NOW(),
            UNIQUE(guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS avaliacoes (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT,
            isbn        TEXT,
            titulo      TEXT,
            autor       TEXT,
            estrelas    INTEGER,
            comentario  TEXT,
            avaliado_em TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, isbn)
        );

        CREATE TABLE IF NOT EXISTS config_guild (
            guild_id          BIGINT PRIMARY KEY,
            canal_promocoes   BIGINT,
            canal_ebooks      BIGINT,
            canal_clube       BIGINT,
            canal_ranking     BIGINT,
            alertas_ativos    INTEGER DEFAULT 1,
            horario_promocoes TEXT DEFAULT '09:00'
        );

        CREATE TABLE IF NOT EXISTS cache_livros (
            isbn      TEXT PRIMARY KEY,
            dados     TEXT,
            cached_em TIMESTAMP DEFAULT NOW()
        );
        """)
    print("✅ Banco de dados PostgreSQL inicializado")

# ─── Perfil ────────────────────────────────────────────────────────────────────
def get_perfil(user_id: int) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM perfis WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["generos"] = json.loads(d["generos"])
            d["autores"] = json.loads(d["autores"])
            return d
    return None

def salvar_perfil(user_id: int, username: str, dados: dict):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO perfis (user_id, username, generos, autores, formato, orcamento, objetivo, livros_ano, atualizado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT(user_id) DO UPDATE SET
                username=EXCLUDED.username, generos=EXCLUDED.generos, autores=EXCLUDED.autores,
                formato=EXCLUDED.formato, orcamento=EXCLUDED.orcamento, objetivo=EXCLUDED.objetivo,
                livros_ano=EXCLUDED.livros_ano, atualizado=NOW()
        """, (
            user_id, username,
            json.dumps(dados.get("generos", [])),
            json.dumps(dados.get("autores", [])),
            dados.get("formato", "todos"),
            dados.get("orcamento", "ate_50"),
            dados.get("objetivo", "diversao"),
            dados.get("livros_ano", "1-5"),
        ))

# ─── Wishlist ─────────────────────────────────────────────────────────────────
def get_wishlist(user_id: int) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM wishlist WHERE user_id = %s ORDER BY adicionado DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]

def adicionar_wishlist(user_id: int, livro: dict, preco_alvo: float = None) -> bool:
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO wishlist (user_id, titulo, autor, isbn, capa_url, preco_alvo, formato)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, isbn) DO NOTHING
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), preco_alvo, livro.get("formato","qualquer")))
        return True
    except Exception:
        return False

def remover_wishlist(user_id: int, isbn: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wishlist WHERE user_id = %s AND isbn = %s", (user_id, isbn))
        return cur.rowcount > 0

# ─── Biblioteca ───────────────────────────────────────────────────────────────
def get_biblioteca(user_id: int, status: str = None) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM biblioteca WHERE user_id = %s AND status = %s ORDER BY adicionado DESC", (user_id, status))
        else:
            cur.execute("SELECT * FROM biblioteca WHERE user_id = %s ORDER BY adicionado DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]

def atualizar_biblioteca(user_id: int, livro: dict, status: str) -> bool:
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO biblioteca (user_id, titulo, autor, isbn, capa_url, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, isbn) DO UPDATE SET status=EXCLUDED.status, adicionado=NOW()
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), status))
        return True
    except Exception:
        return False

def avaliar_livro(user_id: int, livro: dict, estrelas: int, comentario: str = "") -> bool:
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO avaliacoes (user_id, isbn, titulo, autor, estrelas, comentario)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, isbn) DO UPDATE SET estrelas=EXCLUDED.estrelas,
                    comentario=EXCLUDED.comentario, avaliado_em=NOW()
            """, (user_id, livro.get("isbn",""), livro["titulo"], livro.get("autor",""), estrelas, comentario))
            cur.execute("""
                INSERT INTO biblioteca (user_id, titulo, autor, isbn, capa_url, status, avaliacao, comentario)
                VALUES (%s, %s, %s, %s, %s, 'lido', %s, %s)
                ON CONFLICT(user_id, isbn) DO UPDATE SET avaliacao=EXCLUDED.avaliacao,
                    comentario=EXCLUDED.comentario, status='lido'
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), estrelas, comentario))
        return True
    except Exception:
        return False

# ─── Histórico de preços ──────────────────────────────────────────────────────
def registrar_preco(isbn: str, loja: str, preco: float, url: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO historico_precos (isbn, loja, preco, url) VALUES (%s, %s, %s, %s)",
                    (isbn, loja, preco, url))

def get_historico_precos(isbn: str) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM historico_precos WHERE isbn = %s ORDER BY registrado DESC LIMIT 60", (isbn,))
        return [dict(r) for r in cur.fetchall()]

def get_menor_preco(isbn: str) -> float | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(preco) as menor FROM historico_precos WHERE isbn = %s", (isbn,))
        row = cur.fetchone()
        return row["menor"] if row else None

# ─── Config guild ─────────────────────────────────────────────────────────────
def get_config(guild_id: int) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM config_guild WHERE guild_id = %s", (guild_id,))
        row = cur.fetchone()
        return dict(row) if row else {}

def salvar_config(guild_id: int, chave: str, valor):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO config_guild (guild_id, {chave}) VALUES (%s, %s)
            ON CONFLICT(guild_id) DO UPDATE SET {chave}=EXCLUDED.{chave}
        """, (guild_id, valor))

# ─── Cache de livros ──────────────────────────────────────────────────────────
def get_cache_livro(isbn: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT dados FROM cache_livros WHERE isbn = %s AND cached_em > NOW() - INTERVAL '1 day'", (isbn,))
        row = cur.fetchone()
        return json.loads(row["dados"]) if row else None

def salvar_cache_livro(isbn: str, dados: dict):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO cache_livros (isbn, dados) VALUES (%s, %s) ON CONFLICT(isbn) DO UPDATE SET dados=EXCLUDED.dados, cached_em=NOW()",
                    (isbn, json.dumps(dados)))

# ─── Ranking ──────────────────────────────────────────────────────────────────
def get_ranking_wishlist(limit: int = 10) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT titulo, autor, isbn, COUNT(*) as total
            FROM wishlist GROUP BY isbn, titulo, autor ORDER BY total DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

def get_ranking_avaliacoes(limit: int = 10) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT titulo, autor, isbn, AVG(estrelas) as media, COUNT(*) as votos
            FROM avaliacoes GROUP BY isbn, titulo, autor HAVING COUNT(*) >= 2
            ORDER BY media DESC, votos DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

def get_stats_usuario(user_id: int) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as n FROM biblioteca WHERE user_id = %s AND status = 'lido'", (user_id,))
        lidos = cur.fetchone()["n"]
        cur.execute("SELECT AVG(estrelas) as m FROM avaliacoes WHERE user_id = %s", (user_id,))
        media = cur.fetchone()["m"]
        cur.execute("SELECT COUNT(*) as n FROM wishlist WHERE user_id = %s", (user_id,))
        wishlist = cur.fetchone()["n"]
        return {"lidos": lidos, "media_avaliacao": round(float(media or 0), 1), "wishlist": wishlist}
