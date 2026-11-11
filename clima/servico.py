"""Orquestra API + banco (usado pelo coletor e pelo app)."""
from __future__ import annotations

from datetime import date, timedelta

from . import api, db


def coletar_cidade(con, nome: str, uf: str, lat: float, lon: float, backfill_dias: int = 0) -> dict:
    """Coleta e grava o clima diário. Com backfill_dias>0 baixa o histórico do arquivo."""
    cid = db.salvar_cidade(con, nome, uf, lat, lon)
    hoje = date.today()
    recentes = 7
    n_clima = 0
    falhas: list[str] = []  # blocos do histórico que não puderam ser baixados
    if backfill_dias > 0:
        # a API de arquivo tem ~2 dias de atraso; o restante vem do forecast
        fim_arq = hoje - timedelta(days=3)
        ini = hoje - timedelta(days=backfill_dias)
        for b_ini, b_fim in blocos_anuais(ini, fim_arq):
            try:
                n_clima += db.salvar_clima(
                    con, cid, api.clima_diario(lat, lon, inicio=b_ini, fim=b_fim))
            except RuntimeError:  # um bloco falhando não perde os demais
                falhas.append(f"{b_ini} a {b_fim}")
        if falhas:  # reforça os dias recentes com o forecast
            recentes = 92
    n_clima += db.salvar_clima(con, cid, api.clima_diario(lat, lon, past_days=recentes))
    return {"cidade_id": cid, "clima": n_clima, "falhas": falhas}


def blocos_anuais(ini: date, fim: date) -> list[tuple[date, date]]:
    """Divide [ini, fim] em blocos de até 365 dias (pedidos grandes dão timeout/503)."""
    blocos = []
    atual = ini
    while atual <= fim:
        b_fim = min(atual + timedelta(days=364), fim)
        blocos.append((atual, b_fim))
        atual = b_fim + timedelta(days=1)
    return blocos


def inicio_padrao(hoje: date | None = None) -> date:
    """Dia 1 do mesmo mês, 12 meses atrás: 12 meses fechados + o mês atual."""
    hoje = hoje or date.today()
    return date(hoje.year - 1, hoje.month, 1)


def garantir_cidade(con, nome: str, uf: str, lat: float, lon: float) -> int:
    """Garante histórico desde o início do período padrão (faz backfill se faltar)."""
    cid = db.salvar_cidade(con, nome, uf, lat, lon)
    ini = inicio_padrao()
    primeiro = con.execute(
        "SELECT MIN(data) FROM clima_diario WHERE cidade_id=?", (cid,)
    ).fetchone()[0]
    if primeiro is None or primeiro > ini.isoformat():
        coletar_cidade(con, nome, uf, lat, lon, backfill_dias=(date.today() - ini).days)
    return cid
