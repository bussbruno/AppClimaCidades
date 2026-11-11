"""Regras de dados para os gráficos: agregações mensais, meses parciais e rótulos."""
from __future__ import annotations

import pandas as pd

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _agrupar_mensal(df: pd.DataFrame, coluna: str, funcao: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["cidade", "mes", "valor"])
    d = df.copy()
    d["cidade"] = d["nome"] + "/" + d["uf"]
    d["mes"] = d["data"].dt.to_period("M").astype(str)
    serie = d.groupby(["cidade", "mes"], as_index=False)[coluna]
    agregado = serie.mean() if funcao == "media" else serie.sum(min_count=1)
    return agregado.rename(columns={coluna: "valor"}).round({"valor": 2})


def media_mensal(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Média mensal de `coluna` por cidade. Retorna: cidade, mes (YYYY-MM), valor."""
    return _agrupar_mensal(df, coluna, "media")


def soma_mensal(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Soma mensal de `coluna` por cidade. Retorna: cidade, mes (YYYY-MM), valor."""
    return _agrupar_mensal(df, coluna, "soma")


def meses_parciais(df: pd.DataFrame) -> dict[str, int]:
    """Meses com menos dias de dados do que o mês tem -> {'2026-11': 11, ...}."""
    if df.empty:
        return {}
    periodo = df["data"].dt.to_period("M")
    dias = df.groupby(periodo)["data"].nunique()
    return {str(p): int(n) for p, n in dias.items() if n < p.days_in_month}


def rotulo_mes(mes: str, parciais: dict[str, int] | None = None) -> str:
    """'2026-03' -> 'mar/26' (com '*' no final se o mês for parcial)."""
    texto = f"{MESES[int(mes[5:]) - 1]}/{mes[2:4]}"
    return texto + ("*" if parciais and mes in parciais else "")


def texto_parciais(parciais: dict[str, int]) -> str | None:
    """Nota explicativa dos meses parciais (None se não houver nenhum)."""
    if not parciais:
        return None
    itens = ", ".join(f"{rotulo_mes(m)} ({n} dias de dados)" for m, n in parciais.items())
    return (f"\\* Mês parcial (barra hachurada): {itens}. "
            "O valor considera só os dias já coletados.")


def horaria_para_df(dados: list[dict]) -> pd.DataFrame:
    """Lista da previsão horária (api.temperatura_horaria) -> DataFrame com 'hora' datetime."""
    h = pd.DataFrame(dados)
    h["hora"] = pd.to_datetime(h["hora"])
    return h
