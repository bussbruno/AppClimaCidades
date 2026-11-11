from datetime import date

from clima import api, db, servico


def test_blocos_anuais_cobrem_periodo_sem_sobreposicao():
    ini, fim = date(2021, 11, 12), date(2026, 11, 8)
    blocos = servico.blocos_anuais(ini, fim)
    assert blocos[0][0] == ini and blocos[-1][1] == fim
    assert all((b - a).days <= 364 for a, b in blocos)
    for (_, f1), (i2, _) in zip(blocos, blocos[1:]):
        assert (i2 - f1).days == 1


def test_inicio_padrao_e_dia_1_do_mesmo_mes_um_ano_atras():
    assert servico.inicio_padrao(date(2026, 11, 11)) == date(2025, 11, 1)
    assert servico.inicio_padrao(date(2026, 12, 1)) == date(2025, 12, 1)
    assert servico.inicio_padrao(date(2024, 2, 29)) == date(2023, 2, 1)


def test_bloco_com_falha_nao_perde_os_demais(monkeypatch):
    chamadas = []

    def falso(lat, lon, past_days=7, inicio=None, fim=None):
        if inicio is None:
            return []
        chamadas.append(inicio)
        if len(chamadas) == 2:
            raise RuntimeError("503")
        return [{"data": inicio.isoformat(), "temp_max": 1, "temp_min": 0, "temp_media": 0.5,
                 "precipitacao": 0, "vento_max": 1}]

    monkeypatch.setattr(api, "clima_diario", falso)
    con = db.conectar(":memory:")
    r = servico.coletar_cidade(con, "X", "SP", 0, 0, backfill_dias=1825)
    assert len(r["falhas"]) == 1
    assert r["clima"] == len(chamadas) - 1
