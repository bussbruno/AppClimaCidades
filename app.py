"""App Streamlit: clima de uma cidade brasileira (Open-Meteo).

Este arquivo só monta a tela. Os dados ficam em clima/db.py e clima/servico.py,
as regras em clima/analise.py, os gráficos em clima/graficos.py e o HTML em clima/componentes.py.
"""
from datetime import date

import pandas as pd
import streamlit as st

from clima import analise, api, componentes, db, graficos, servico

st.set_page_config(page_title="Clima na Cidade", layout="wide")

DEFAULT = {"nome": "São Paulo", "uf": "São Paulo", "lat": -23.5475, "lon": -46.63611}

if "selecionadas" not in st.session_state:
    st.session_state.selecionadas = [DEFAULT]


@st.cache_data(ttl=3600, show_spinner=False)
def _buscar(nome):
    return api.buscar_cidades(nome)


@st.cache_data(ttl=900, show_spinner=False)
def _horaria(lat, lon):
    return analise.horaria_para_df(api.temperatura_horaria(lat, lon))


@st.cache_data(ttl=900, show_spinner=False)
def _icone_agora(lat, lon):
    """Ícone do tempo na hora atual (só faz sentido quando o cartão mostra hoje)."""
    try:
        h = api.temperatura_horaria(lat, lon)
        agora = pd.Timestamp.now().floor("h").strftime("%Y-%m-%dT%H:00")
        linha = next(x for x in h if x["hora"] == agora)
        return componentes.icone_tempo(linha["codigo"], linha["dia"])
    except (RuntimeError, StopIteration):
        return "⛅"


def _rotulo(c):
    return f"{c['nome']} - {c['uf']}"


def _nota_parciais(parciais):
    texto = analise.texto_parciais(parciais)
    if texto:
        st.caption(texto)


# ---------- Barra lateral ----------
hoje = date.today()
ini, fim = servico.inicio_padrao(hoje), hoje  # período fixo: 12 meses fechados + mês atual

with st.sidebar:
    st.header("Cidade")
    st.session_state.selecionadas = st.session_state.selecionadas[:1]
    st.write(f"📍 **{_rotulo(st.session_state.selecionadas[0])}**")

    termo = st.text_input("Trocar de cidade")
    if termo:
        try:
            achadas = _buscar(termo)
        except RuntimeError as e:
            achadas = []
            st.error(f"Busca indisponível: {e}")
        if not achadas:
            st.warning("Nenhuma cidade encontrada.")
        else:
            escolha = st.selectbox("Resultados", achadas, format_func=_rotulo)
            if st.button("Usar esta cidade"):
                st.session_state.selecionadas = [escolha]
                st.rerun()

    st.header("Período")
    ultimo_fechado = (pd.Timestamp(hoje.replace(day=1)) - pd.Timedelta(days=1)).date()
    st.markdown(f"**{ini:%d/%m/%Y} a {fim:%d/%m/%Y}**")
    st.info(
        f"Período fixo, não pode ser alterado: os **12 meses fechados** "
        f"({analise.MESES[ini.month - 1]}/{ini:%y} a "
        f"{analise.MESES[ultimo_fechado.month - 1]}/{ultimo_fechado:%y}) "
        f"mais o **mês atual até hoje** ({analise.MESES[hoje.month - 1]}/{hoje:%y}, parcial). "
        "Atualiza sozinho a cada virada de mês."
    )
    st.caption("Os dados são atualizados automaticamente ao abrir o app.")
    atualizar = st.button("🔄 Atualizar novamente")

# ---------- Dados ----------
con = db.conectar()
ids = []
for c in st.session_state.selecionadas:
    chave = f"coletado:{c['nome']}:{c['uf']}"
    primeira_vez = chave not in st.session_state  # app recém-aberto (ou cidade nova)
    st.session_state[chave] = True  # evita repetir a coleta a cada clique na tela
    try:
        if atualizar or primeira_vez:
            with st.spinner(f"Atualizando dados de {c['nome']}..."):
                servico.garantir_cidade(con, c["nome"], c["uf"], c["lat"], c["lon"])  # histórico
                ids.append(servico.coletar_cidade(con, c["nome"], c["uf"], c["lat"], c["lon"])["cidade_id"])
        else:
            ids.append(db.salvar_cidade(con, c["nome"], c["uf"], c["lat"], c["lon"]))
    except RuntimeError as e:
        st.warning(f"Sem conexão com a API para {c['nome']} ({e}); usando dados já gravados.")
        ids.append(db.salvar_cidade(con, c["nome"], c["uf"], c["lat"], c["lon"]))

df_clima = db.clima(con, ids, str(ini), str(fim))
if df_clima.empty:
    st.info("Ainda não há dados no período. Clique em “Atualizar novamente”.")
    st.stop()

parciais = analise.meses_parciais(df_clima)

# ---------- Cartão do dia e classificação ----------
ultimo = df_clima[df_clima["cidade_id"] == ids[0]].tail(1)
if not ultimo.empty:
    r = ultimo.iloc[0]
    c0 = st.session_state.selecionadas[0]
    icone = _icone_agora(c0["lat"], c0["lon"]) if r["data"].date() == hoje else "🌤️"
    esq, dir_ = st.columns([1.5, 2], gap="large")
    with esq:
        st.markdown(componentes.cartao_clima(r, icone), unsafe_allow_html=True)
    with dir_:
        st.markdown(componentes.legenda_faixas(r["temp_media"]), unsafe_allow_html=True)

# ---------- Gráficos mensais ----------
m1, m2 = st.columns(2)
with m1:
    st.markdown(f'### <span style="color:{graficos.COR_MIN}">▼</span> Temperatura mínima média por mês',
                unsafe_allow_html=True)
    st.plotly_chart(graficos.temperatura_mensal(df_clima, "temp_min", "Mínima média (°C)",
                                                graficos.COR_MIN, parciais),
                    use_container_width=True)
with m2:
    st.markdown('### <span style="color:#F76707">▲</span> Temperatura máxima média por mês',
                unsafe_allow_html=True)
    st.plotly_chart(graficos.temperatura_mensal(df_clima, "temp_max", "Máxima média (°C)",
                                                graficos.COR_MAX, parciais),
                    use_container_width=True)
_nota_parciais(parciais)

st.subheader("Chuva total por mês")
st.plotly_chart(graficos.chuva_mensal(df_clima, parciais), use_container_width=True)
_nota_parciais(parciais)

# ---------- Hoje, hora a hora ----------
st.subheader(f"Temperatura hora a hora — hoje - {hoje:%d/%m/%Y}")
for c in st.session_state.selecionadas:
    st.markdown(f"**{c['nome']}**")
    try:
        horaria = _horaria(c["lat"], c["lon"])
        st.plotly_chart(graficos.temperatura_hoje(horaria), use_container_width=True)
        st.subheader(f"Chuva hora a hora — hoje - {hoje:%d/%m/%Y}")
        st.plotly_chart(graficos.chuva_hoje(horaria), use_container_width=True)
    except RuntimeError as e:
        st.warning(f"Previsão horária indisponível para {c['nome']}: {e}")

# ---------- Dados e créditos ----------
with st.expander("Dados e download"):
    st.dataframe(df_clima.drop(columns=["cidade_id"]), use_container_width=True)
    st.download_button("Baixar CSV (clima)", df_clima.to_csv(index=False).encode("utf-8"),
                       "clima.csv", "text/csv")

st.divider()
st.caption(
    "Dados meteorológicos fornecidos pela API [Open-Meteo.com](https://open-meteo.com), "
    "licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). "
    "A API gratuita é para **uso não comercial**."
)
