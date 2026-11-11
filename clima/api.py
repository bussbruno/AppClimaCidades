"""Clientes da API Open-Meteo (busca de cidades, clima diário e previsão horária)."""
from __future__ import annotations

import time
from datetime import date

import requests

try:  # usa o repositório de certificados do SO (proxies corporativos com inspeção SSL)
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TZ = "America/Sao_Paulo"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "wind_speed_10m_max",
]


def _get(url: str, params: dict, tentativas: int = 3, timeout: int = 90) -> dict:
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            ultimo_erro = e
            time.sleep(2**i)
    raise RuntimeError(f"Falha ao consultar {url}: {ultimo_erro}")


def buscar_cidades(nome: str, max_resultados: int = 5) -> list[dict]:
    """Busca cidades brasileiras pelo nome. Retorna lista de dicts nome/uf/lat/lon."""
    dados = _get(
        GEOCODING_URL,
        {"name": nome, "count": max_resultados, "language": "pt", "country_code": "BR"},
    )
    return [
        {
            "nome": r["name"],
            "uf": r.get("admin1", ""),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }
        for r in dados.get("results", []) or []
    ]


def clima_diario(
    lat: float,
    lon: float,
    past_days: int = 7,
    inicio: date | None = None,
    fim: date | None = None,
) -> list[dict]:
    """Clima diário. Com inicio/fim usa a API de arquivo (histórico); senão, past_days."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY_VARS),
        "timezone": TZ,
    }
    if inicio and fim:
        params.update(start_date=inicio.isoformat(), end_date=fim.isoformat())
        url = ARCHIVE_URL
    else:
        params.update(past_days=past_days, forecast_days=1)
        url = FORECAST_URL
    return parse_clima(_get(url, params))


def parse_clima(resp: dict) -> list[dict]:
    d = resp.get("daily", {})
    linhas = []
    for i, dia in enumerate(d.get("time", [])):
        linhas.append(
            {
                "data": dia,
                "temp_max": d["temperature_2m_max"][i],
                "temp_min": d["temperature_2m_min"][i],
                "temp_media": d["temperature_2m_mean"][i],
                "precipitacao": d["precipitation_sum"][i],
                "vento_max": d["wind_speed_10m_max"][i],
            }
        )
    return linhas


def temperatura_horaria(lat: float, lon: float) -> list[dict]:
    """Temperatura hora a hora de hoje (24 pontos), com código de tempo e is_day."""
    resp = _get(
        FORECAST_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation,weather_code,is_day",
            "forecast_days": 2,  # precisamos da 00:00 de amanhã para fechar o gráfico
            "timezone": TZ,
        },
    )
    h = resp.get("hourly", {})
    return [
        {
            "hora": ts,
            "temp": h["temperature_2m"][i],
            "chuva": h["precipitation"][i] or 0.0,
            "codigo": h["weather_code"][i],
            "dia": bool(h["is_day"][i]),
        }
        for i, ts in enumerate(h.get("time", []))
    ][:25]  # 00:00 de hoje até 00:00 de amanhã (inclusive)
