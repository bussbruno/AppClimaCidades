"""Gráficos Plotly. Funções puras: recebem DataFrames e devolvem figuras (sem Streamlit)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import analise

COR_MIN = "#1C7ED6"        # mínima: azul
COR_MAX = "#E8590C"        # máxima: laranja
COR_CHUVA = "#1971C2"      # chuva: azul
COR_TEMP_HOJE = "#C92A2A"  # linha de temperatura hora a hora: vermelho
COR_GRADE = "#E9ECEF"


def _estilo(fig: go.Figure, titulo_y: str | None) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=380, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        yaxis_title=titulo_y, xaxis_title=None, hovermode="x unified",
    )
    fig.update_yaxes(gridcolor=COR_GRADE)
    return fig


def _hachurar_parciais(fig: go.Figure, meses: list[str], parciais: dict[str, int],
                       cor: str) -> go.Figure:
    """Hachura as barras dos meses parciais (`meses` na mesma ordem das barras)."""
    fig.update_traces(marker=dict(pattern=dict(
        shape=["/" if m in parciais else "" for m in meses],
        fgcolor=cor, bgcolor="white", size=6)))
    return fig


def _barras_mensais(dados: pd.DataFrame, parciais: dict[str, int], cor: str,
                    texto: str, hover: str) -> go.Figure:
    dados = dados.assign(mes_txt=dados["mes"].map(lambda m: analise.rotulo_mes(m, parciais)))
    fig = px.bar(
        dados, x="mes_txt", y="valor", color="cidade", barmode="group", text="valor",
        color_discrete_map={c: cor for c in dados["cidade"].unique()},
        category_orders={"mes_txt": list(dict.fromkeys(dados["mes_txt"]))})
    fig.update_traces(texttemplate=texto, textposition="outside", hovertemplate=hover)
    fig.update_yaxes(rangemode="tozero", showticklabels=False)  # valores já aparecem nas barras
    return _hachurar_parciais(fig, dados["mes"].tolist(), parciais, cor)


def temperatura_mensal(df_clima: pd.DataFrame, coluna: str, titulo_y: str, cor: str,
                       parciais: dict[str, int]) -> go.Figure:
    """Barras da média mensal de `coluna` (temp_min ou temp_max)."""
    dados = analise.media_mensal(df_clima, coluna)
    fig = _barras_mensais(dados, parciais, cor, "%{text:.1f}°", "%{y:.1f} °C")
    fig.update_layout(showlegend=False)
    return _estilo(fig, titulo_y)


def chuva_mensal(df_clima: pd.DataFrame, parciais: dict[str, int]) -> go.Figure:
    """Barras da chuva total (mm) por mês."""
    dados = analise.soma_mensal(df_clima, "precipitacao")
    fig = _barras_mensais(dados, parciais, COR_CHUVA, "%{text:.0f} mm", "%{y:.0f} mm")
    return _estilo(fig, "Chuva total (mm)")


def _layout_horario(fig: go.Figure, altura: int, yaxis: dict, **extra) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=altura, margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False, hovermode="x unified",
        xaxis=dict(tickformat="%H:%M", dtick=2 * 3600 * 1000, showgrid=False),
        yaxis=dict(gridcolor=COR_GRADE, **yaxis), **extra)
    return fig


def temperatura_hoje(h: pd.DataFrame, agora: pd.Timestamp | None = None) -> go.Figure:
    """Linha de temperatura hora a hora, com rótulos de 2 em 2 horas e a hora atual marcada."""
    agora = agora if agora is not None else pd.Timestamp.now().floor("h")
    pares = h[h["hora"].dt.hour % 2 == 0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=h["hora"], y=h["temp"], mode="lines",
        line=dict(color=COR_TEMP_HOJE, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(201,42,42,0.10)", name="Temperatura",
        hovertemplate="%{x|%H:%M} — %{y:.1f} °C<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=pares["hora"], y=pares["temp"] - 3.5, mode="text", showlegend=False, hoverinfo="skip",
        text=[f"{t:.0f}°C" for t in pares["temp"]],
        textfont=dict(color=COR_TEMP_HOJE, size=13, family="Arial Black")))
    atual = h[h["hora"] == agora]
    if not atual.empty:
        fig.add_trace(go.Scatter(
            x=atual["hora"], y=atual["temp"], mode="markers", showlegend=False,
            marker=dict(size=13, color="white", line=dict(color=COR_TEMP_HOJE, width=3)),
            hovertemplate="Agora — %{y:.1f} °C<extra></extra>"))
    return _layout_horario(fig, 340, dict(range=[0, h["temp"].max() + 4]))


def chuva_hoje(h: pd.DataFrame) -> go.Figure:
    """Linha de chuva (mm) hora a hora, com o valor em todas as horas (cinza quando é 0)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=h["hora"], y=h["chuva"], mode="lines",
        line=dict(color=COR_CHUVA, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(25,113,194,0.12)",
        hovertemplate="%{x|%H:%M} — %{y:.1f} mm<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=h["hora"], y=h["chuva"], mode="text", showlegend=False, hoverinfo="skip",
        text=[f"{v:.1f} mm" if v > 0 else "0 mm" for v in h["chuva"]],
        textposition="top center",
        textfont=dict(size=11, color=[COR_CHUVA if v > 0 else "#ADB5BD" for v in h["chuva"]])))
    topo = max(h["chuva"].max(), 1.0) * 1.6
    return _layout_horario(fig, 260, dict(range=[0, topo], showticklabels=False),
                           yaxis_title="Chuva (mm)")
