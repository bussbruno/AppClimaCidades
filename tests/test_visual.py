import pandas as pd

from clima import analise, componentes, graficos


def _clima(datas, temp=20.0):
    return pd.DataFrame({
        "nome": "X", "uf": "SP", "data": pd.to_datetime(datas),
        "temp_min": temp - 5, "temp_max": temp + 5, "temp_media": temp, "precipitacao": 1.0,
    })


def test_meses_parciais_e_rotulos():
    # janeiro completo (31 dias) e fevereiro com só 3 dias
    datas = list(pd.date_range("2026-01-01", "2026-01-31")) + list(pd.date_range("2026-02-01", "2026-02-03"))
    parciais = analise.meses_parciais(_clima(datas))
    assert parciais == {"2026-02": 3}
    assert analise.rotulo_mes("2026-01", parciais) == "jan/26"
    assert analise.rotulo_mes("2026-02", parciais) == "fev/26*"
    assert "fev/26 (3 dias de dados)" in analise.texto_parciais(parciais)
    assert analise.texto_parciais({}) is None
    assert analise.meses_parciais(pd.DataFrame()) == {}


def test_grafico_mensal_hachura_apenas_o_mes_parcial():
    datas = list(pd.date_range("2026-01-01", "2026-01-31")) + [pd.Timestamp("2026-02-01")]
    df = _clima(datas)
    fig = graficos.temperatura_mensal(df, "temp_max", "Máxima (°C)", graficos.COR_MAX,
                                      analise.meses_parciais(df))
    assert list(fig.data[0].x) == ["jan/26", "fev/26*"]
    assert list(fig.data[0].marker.pattern.shape) == ["", "/"]
    assert graficos.chuva_mensal(df, analise.meses_parciais(df)).data[0].y[0] == 31.0


def test_classificacao_da_temperatura():
    assert componentes.indice_faixa(5) == 0      # frio
    assert componentes.indice_faixa(12) == 1     # fresco (limite inferior incluso)
    assert componentes.indice_faixa(20.2) == 2   # agradável
    assert componentes.indice_faixa(35) == 4     # muito quente
    html = componentes.legenda_faixas(20.2)
    assert html.count("box-shadow") == 1 and "agradável" in html


def test_icone_do_tempo():
    assert componentes.icone_tempo(0, True) == "☀️"
    assert componentes.icone_tempo(0, False) == "🌙"
    assert componentes.icone_tempo(63, True) == "🌧️"
    assert componentes.icone_tempo(95, True) == "⛈️"


def test_graficos_do_dia_com_previsao_horaria():
    dados = [{"hora": f"2026-01-01T{h:02d}:00", "temp": 15.0 + h / 2, "chuva": 0.3 if h == 13 else 0.0,
              "codigo": 0, "dia": True} for h in range(24)]
    h = analise.horaria_para_df(dados)
    fig_t = graficos.temperatura_hoje(h, agora=pd.Timestamp("2026-01-01 13:00"))
    assert len(fig_t.data) == 3                       # linha + rótulos + hora atual
    assert list(fig_t.data[1].text)[:2] == ["15°C", "16°C"]  # rótulos de 2 em 2 horas (0h, 2h...)
    assert len(graficos.temperatura_hoje(h, agora=pd.Timestamp("2030-01-01")).data) == 2
    fig_c = graficos.chuva_hoje(h)
    assert list(fig_c.data[1].text).count("0 mm") == 23 and "0.3 mm" in fig_c.data[1].text
