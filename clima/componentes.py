"""Blocos de HTML do app (cartão do dia e legenda de classificação). Sem Streamlit."""
from __future__ import annotations

# (emoji, nome, faixa, cor de fundo, temperatura mínima da faixa)
FAIXAS = [
    ("🥶", "frio", "abaixo de 12°", "#A5D8FF", -99),
    ("🧥", "fresco", "12° a 18°", "#B2F2BB", 12),
    ("🙂", "agradável", "18° a 24°", "#FFEC99", 18),
    ("☀️", "quente", "24° a 30°", "#FFC078", 24),
    ("🔥", "muito quente", "30° ou mais", "#FF8787", 30),
]


def indice_faixa(temp: float) -> int:
    """Posição em FAIXAS da temperatura média informada."""
    return max(i for i, f in enumerate(FAIXAS) if temp >= f[4])


def legenda_faixas(temp: float) -> str:
    """Faixa de 5 blocos coloridos, com a classificação atual destacada."""
    atual = indice_faixa(temp)
    chips = []
    for i, (emoji, nome, faixa, cor, _) in enumerate(FAIXAS):
        destaque = (
            "box-shadow:0 0 0 3px #343A40;transform:scale(1.06);font-weight:700;"
            if i == atual else "opacity:0.55;"
        )
        chips.append(
            f'<div style="flex:1;min-width:110px;background:{cor};color:#212529;border-radius:10px;'
            f'padding:10px 6px;text-align:center;{destaque}">'
            f'<div style="font-size:22px">{emoji}</div><div>{nome}</div>'
            f'<div style="font-size:12px">{faixa}</div></div>'
        )
    return ('<div style="font-size:13px;margin-bottom:6px;opacity:0.7">Classificação da '
            'temperatura média (a faixa atual está destacada)</div>'
            '<div style="display:flex;gap:8px;flex-wrap:wrap">' + "".join(chips) + "</div>")


def icone_tempo(codigo: int, dia: bool) -> str:
    """Emoji para o código de tempo da Open-Meteo (WMO)."""
    if codigo == 0:
        return "☀️" if dia else "🌙"
    if codigo in (1, 2):
        return "🌤️" if dia else "☁️"
    if codigo in (45, 48):
        return "🌫️"
    if codigo in (51, 53, 55, 56, 57, 80, 81, 82):
        return "🌦️"
    if codigo in (61, 63, 65, 66, 67):
        return "🌧️"
    if codigo in (71, 73, 75, 77, 85, 86):
        return "❄️"
    if codigo >= 95:
        return "⛈️"
    return "☁️"


def cartao_clima(r, icone: str) -> str:
    """Cartão do dia: título, ícone, temperatura, cidade, data e botões Mín/Máx.
    `r` é uma linha do clima diário (temp_media, temp_min, temp_max, nome, data)."""
    chip = ("display:inline-block;background:#fff;border:1px solid #CED4DA;border-radius:999px;"
            "padding:6px 18px;font-size:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-right:10px")
    return (
        '<div style="padding:22px 0">'
        '<div style="display:flex;align-items:center;gap:12px;font-size:38px;font-weight:700">'
        '<span>🌤️</span><span>Clima na Cidade</span></div>'
        '<div style="display:flex;align-items:center;gap:22px;margin:10px 0 14px">'
        f'<div style="font-size:96px;line-height:1">{icone}</div>'
        '<div>'
        f'<div style="font-size:56px;font-weight:700;line-height:1.1">{r["temp_media"]:.1f} °C</div>'
        f'<div style="font-size:24px;font-weight:700">{r["nome"]}</div>'
        f'<div style="font-size:20px;opacity:0.8">{r["data"]:%d/%m/%Y}</div>'
        '</div></div>'
        '<div style="white-space:nowrap">'
        f'<span style="{chip}"><b style="color:#1C7ED6">▼</b> Mín {r["temp_min"]:.1f}°</span>'
        f'<span style="{chip}"><b style="color:#F76707">▲</b> Máx {r["temp_max"]:.1f}°</span>'
        '</div></div>'
    )
