import pandas as pd

from clima import analise, api, db


def test_parse_clima():
    resp = {"daily": {
        "time": ["2026-01-01"], "temperature_2m_max": [30], "temperature_2m_min": [20],
        "temperature_2m_mean": [25], "precipitation_sum": [1.5], "wind_speed_10m_max": [12],
    }}
    assert api.parse_clima(resp)[0]["temp_media"] == 25


def test_temperatura_horaria_vai_de_00h_ate_00h_do_dia_seguinte(monkeypatch):
    horas = [f"2026-01-0{1 + i // 24}T{i % 24:02d}:00" for i in range(48)]
    resp = {"hourly": {
        "time": horas, "temperature_2m": [20.0] * 48, "precipitation": [None] + [0.5] * 47,
        "weather_code": [0] * 48, "is_day": [1] * 48,
    }}
    monkeypatch.setattr(api, "_get", lambda *a, **k: resp)
    r = api.temperatura_horaria(0, 0)
    assert len(r) == 25
    assert r[0]["hora"] == "2026-01-01T00:00" and r[-1]["hora"] == "2026-01-02T00:00"
    assert r[0]["chuva"] == 0.0  # None vira 0


def test_upsert_idempotente():
    con = db.conectar(":memory:")
    cid = db.salvar_cidade(con, "São Paulo", "SP", -23.5, -46.6)
    linha = {"data": "2026-01-01", "temp_max": 30, "temp_min": 20, "temp_media": 25,
             "precipitacao": 0, "vento_max": 5}
    db.salvar_clima(con, cid, [linha])
    db.salvar_clima(con, cid, [{**linha, "temp_media": 26}])
    df = db.clima(con, [cid])
    assert len(df) == 1 and df.iloc[0]["temp_media"] == 26


def test_media_mensal():
    df = pd.DataFrame({
        "nome": ["A"] * 3, "uf": ["SP"] * 3,
        "data": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01"]),
        "temp_media": [20.0, 30.0, 10.0],
    })
    r = analise.media_mensal(df, "temp_media")
    assert r.set_index("mes")["valor"].to_dict() == {"2026-01": 25.0, "2026-02": 10.0}
