import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bookbot.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
        -- Perfis de usuário
        CREATE TABLE IF NOT EXISTS perfis (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            generos     TEXT DEFAULT '[]',
            autores     TEXT DEFAULT '[]',
            formato     TEXT DEFAULT 'todos',
            orcamento   TEXT DEFAULT 'ate_50',
            objetivo    TEXT DEFAULT 'diversao',
            livros_ano  TEXT DEFAULT '1-5',
            criado_em   TEXT DEFAULT (datetime('now')),
            atualizado  TEXT DEFAULT (datetime('now'))
        );

        -- Wishlist
        CREATE TABLE IF NOT EXISTS wishlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            preco_alvo  REAL,
            formato     TEXT DEFAULT 'qualquer',
            adicionado  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, isbn)
        );

        -- Biblioteca pessoal (estante)
        CREATE TABLE IF NOT EXISTS biblioteca (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            status      TEXT DEFAULT 'quero_ler',
            avaliacao   INTEGER,
            comentario  TEXT,
            adicionado  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, isbn)
        );

        -- Histórico de preços
        CREATE TABLE IF NOT EXISTS historico_precos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn        TEXT,
            loja        TEXT,
            preco       REAL,
            url         TEXT,
            registrado  TEXT DEFAULT (datetime('now'))
        );

        -- Clube do livro
        CREATE TABLE IF NOT EXISTS clube_livros (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER,
            titulo      TEXT,
            autor       TEXT,
            isbn        TEXT,
            capa_url    TEXT,
            iniciado    TEXT DEFAULT (datetime('now')),
            encerrado   TEXT,
            ativo       INTEGER DEFAULT 1
        );

        -- Progresso no clube
        CREATE TABLE IF NOT EXISTS clube_progresso (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            clube_id    INTEGER,
            user_id     INTEGER,
            pagina_atual INTEGER DEFAULT 0,
            total_paginas INTEGER DEFAULT 0,
            atualizado  TEXT DEFAULT (datetime('now')),
            UNIQUE(clube_id, user_id)
        );

        -- Votos no clube
        CREATE TABLE IF NOT EXISTS clube_votos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER,
            isbn        TEXT,
            titulo      TEXT,
            user_id     INTEGER,
            votado_em   TEXT DEFAULT (datetime('now')),
            UNIQUE(guild_id, user_id)
        );

        -- Avaliações
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            isbn        TEXT,
            titulo      TEXT,
            autor       TEXT,
            estrelas    INTEGER,
            comentario  TEXT,
            avaliado_em TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, isbn)
        );

        -- Config por servidor
        CREATE TABLE IF NOT EXISTS config_guild (
            guild_id            INTEGER PRIMARY KEY,
            canal_promocoes     INTEGER,
            canal_ebooks        INTEGER,
            canal_clube         INTEGER,
            canal_ranking       INTEGER,
            alertas_ativos      INTEGER DEFAULT 1,
            horario_promocoes   TEXT DEFAULT '09:00'
        );

        -- Cache de livros da API
        CREATE TABLE IF NOT EXISTS cache_livros (
            isbn        TEXT PRIMARY KEY,
            dados       TEXT,
            cached_em   TEXT DEFAULT (datetime('now'))
        );
        """)
    print("✅ Banco de dados inicializado")

# ─── Perfil ────────────────────────────────────────────────────────────────────
def get_perfil(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM perfis WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            d = dict(row)
            d["generos"] = json.loads(d["generos"])
            d["autores"] = json.loads(d["autores"])
            return d
    return None

def salvar_perfil(user_id: int, username: str, dados: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO perfis (user_id, username, generos, autores, formato, orcamento, objetivo, livros_ano, atualizado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username, generos=excluded.generos, autores=excluded.autores,
                formato=excluded.formato, orcamento=excluded.orcamento, objetivo=excluded.objetivo,
                livros_ano=excluded.livros_ano, atualizado=datetime('now')
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
        return [dict(r) for r in conn.execute(
            "SELECT * FROM wishlist WHERE user_id = ? ORDER BY adicionado DESC", (user_id,)
        ).fetchall()]

def adicionar_wishlist(user_id: int, livro: dict, preco_alvo: float = None) -> bool:
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO wishlist (user_id, titulo, autor, isbn, capa_url, preco_alvo, formato)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), preco_alvo, livro.get("formato","qualquer")))
        return True
    except Exception:
        return False

def remover_wishlist(user_id: int, isbn: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM wishlist WHERE user_id = ? AND isbn = ?", (user_id, isbn))
        return cur.rowcount > 0

# ─── Biblioteca ───────────────────────────────────────────────────────────────
def get_biblioteca(user_id: int, status: str = None) -> list:
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM biblioteca WHERE user_id = ? AND status = ? ORDER BY adicionado DESC",
                (user_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM biblioteca WHERE user_id = ? ORDER BY adicionado DESC", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]

def atualizar_biblioteca(user_id: int, livro: dict, status: str) -> bool:
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO biblioteca (user_id, titulo, autor, isbn, capa_url, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, isbn) DO UPDATE SET status=excluded.status, adicionado=datetime('now')
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), status))
        return True
    except Exception:
        return False

def avaliar_livro(user_id: int, livro: dict, estrelas: int, comentario: str = "") -> bool:
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO avaliacoes (user_id, isbn, titulo, autor, estrelas, comentario)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, isbn) DO UPDATE SET estrelas=excluded.estrelas,
                    comentario=excluded.comentario, avaliado_em=datetime('now')
            """, (user_id, livro.get("isbn",""), livro["titulo"], livro.get("autor",""), estrelas, comentario))
            # Atualiza na biblioteca também
            conn.execute("""
                INSERT INTO biblioteca (user_id, titulo, autor, isbn, capa_url, status, avaliacao, comentario)
                VALUES (?, ?, ?, ?, ?, 'lido', ?, ?)
                ON CONFLICT(user_id, isbn) DO UPDATE SET avaliacao=excluded.avaliacao,
                    comentario=excluded.comentario, status='lido'
            """, (user_id, livro["titulo"], livro.get("autor",""), livro.get("isbn",""),
                  livro.get("capa_url",""), estrelas, comentario))
        return True
    except Exception:
        return False

# ─── Histórico de preços ──────────────────────────────────────────────────────
def registrar_preco(isbn: str, loja: str, preco: float, url: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO historico_precos (isbn, loja, preco, url) VALUES (?, ?, ?, ?)",
            (isbn, loja, preco, url)
        )

def get_historico_precos(isbn: str) -> list:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM historico_precos WHERE isbn = ? ORDER BY registrado DESC LIMIT 60",
            (isbn,)
        ).fetchall()]

def get_menor_preco(isbn: str) -> float | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT MIN(preco) as menor FROM historico_precos WHERE isbn = ?", (isbn,)
        ).fetchone()
        return row["menor"] if row else None

# ─── Config guild ─────────────────────────────────────────────────────────────
def get_config(guild_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM config_guild WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else {}

def salvar_config(guild_id: int, chave: str, valor):
    with get_db() as conn:
        conn.execute(f"""
            INSERT INTO config_guild (guild_id, {chave}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {chave}=excluded.{chave}
        """, (guild_id, valor))

# ─── Cache de livros ──────────────────────────────────────────────────────────
def get_cache_livro(isbn: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT dados FROM cache_livros WHERE isbn = ? AND cached_em > datetime('now', '-1 day')",
            (isbn,)
        ).fetchone()
        return json.loads(row["dados"]) if row else None

def salvar_cache_livro(isbn: str, dados: dict):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache_livros (isbn, dados) VALUES (?, ?)",
            (isbn, json.dumps(dados))
        )

# ─── Ranking ──────────────────────────────────────────────────────────────────
def get_ranking_wishlist(limit: int = 10) -> list:
    with get_db() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT titulo, autor, isbn, COUNT(*) as total
            FROM wishlist GROUP BY isbn ORDER BY total DESC LIMIT ?
        """, (limit,)).fetchall()]

def get_ranking_avaliacoes(limit: int = 10) -> list:
    with get_db() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT titulo, autor, isbn, AVG(estrelas) as media, COUNT(*) as votos
            FROM avaliacoes GROUP BY isbn HAVING votos >= 2
            ORDER BY media DESC, votos DESC LIMIT ?
        """, (limit,)).fetchall()]

def get_stats_usuario(user_id: int) -> dict:
    with get_db() as conn:
        lidos = conn.execute(
            "SELECT COUNT(*) as n FROM biblioteca WHERE user_id = ? AND status = 'lido'", (user_id,)
        ).fetchone()["n"]
        media = conn.execute(
            "SELECT AVG(estrelas) as m FROM avaliacoes WHERE user_id = ?", (user_id,)
        ).fetchone()["m"]
        wishlist = conn.execute(
            "SELECT COUNT(*) as n FROM wishlist WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]
        return {"lidos": lidos, "media_avaliacao": round(media or 0, 1), "wishlist": wishlist}
