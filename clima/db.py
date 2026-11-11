"""Persistência em SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_PADRAO = Path(__file__).resolve().parent.parent / "data" / "clima.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    uf TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    UNIQUE(nome, uf)
);
CREATE TABLE IF NOT EXISTS clima_diario (
    cidade_id INTEGER NOT NULL REFERENCES cidades(id),
    data TEXT NOT NULL,
    temp_max REAL, temp_min REAL, temp_media REAL,
    precipitacao REAL, vento_max REAL,
    PRIMARY KEY (cidade_id, data)
);
"""

COLS_CLIMA = ["temp_max", "temp_min", "temp_media", "precipitacao", "vento_max"]


def conectar(caminho: str | Path = DB_PADRAO) -> sqlite3.Connection:
    if str(caminho) != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.executescript(SCHEMA)
    return con


def salvar_cidade(con: sqlite3.Connection, nome: str, uf: str, lat: float, lon: float) -> int:
    con.execute(
        "INSERT INTO cidades(nome, uf, lat, lon) VALUES (?,?,?,?) "
        "ON CONFLICT(nome, uf) DO UPDATE SET lat=excluded.lat, lon=excluded.lon",
        (nome, uf, lat, lon),
    )
    con.commit()
    return con.execute(
        "SELECT id FROM cidades WHERE nome=? AND uf=?", (nome, uf)
    ).fetchone()[0]


def salvar_clima(con: sqlite3.Connection, cidade_id: int, linhas: list[dict]) -> int:
    """Grava (ou atualiza) o clima diário. Idempotente por cidade + data."""
    campos = ["cidade_id", "data", *COLS_CLIMA]
    updates = ",".join(f"{c}=excluded.{c}" for c in COLS_CLIMA)
    sql = (
        f"INSERT INTO clima_diario({','.join(campos)}) VALUES ({','.join('?' * len(campos))}) "
        f"ON CONFLICT(cidade_id, data) DO UPDATE SET {updates}"
    )
    con.executemany(
        sql, [(cidade_id, l["data"], *[l.get(c) for c in COLS_CLIMA]) for l in linhas]
    )
    con.commit()
    return len(linhas)


def clima(con: sqlite3.Connection, cidade_ids: list[int],
          inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Clima diário das cidades no período (datas 'YYYY-MM-DD', inclusive)."""
    if not cidade_ids:
        return pd.DataFrame()
    q = (
        "SELECT t.*, c.nome, c.uf FROM clima_diario t JOIN cidades c ON c.id=t.cidade_id "
        f"WHERE t.cidade_id IN ({','.join('?' * len(cidade_ids))})"
    )
    params: list = list(cidade_ids)
    if inicio:
        q += " AND t.data >= ?"
        params.append(inicio)
    if fim:
        q += " AND t.data <= ?"
        params.append(fim)
    q += " ORDER BY t.data"
    df = pd.read_sql_query(q, con, params=params)
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df
