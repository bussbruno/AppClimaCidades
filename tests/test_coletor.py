import pytest

import coletor
from clima import api, db, servico

SP = {"nome": "São Paulo", "uf": "São Paulo", "lat": -23.5, "lon": -46.6}


@pytest.fixture
def sem_rede(monkeypatch, tmp_path):
    chamadas = []
    monkeypatch.setattr(db, "DB_PADRAO", tmp_path / "t.db")
    monkeypatch.setattr(db, "conectar", lambda *a, **k: db.sqlite3.connect(":memory:"))
    monkeypatch.setattr(api, "buscar_cidades", lambda nome, n=5: [SP] if nome == "São Paulo" else [])
    monkeypatch.setattr(servico, "coletar_cidade",
                        lambda con, nome, uf, lat, lon, dias=0: chamadas.append((nome, dias))
                        or {"cidade_id": 1, "clima": 8, "falhas": []})
    return chamadas


def test_coleta_uma_cidade_com_padrao_sao_paulo(sem_rede, capsys):
    assert coletor.main([]) == 0
    assert sem_rede == [("São Paulo", 0)]
    assert "[OK] São Paulo/São Paulo" in capsys.readouterr().out


def test_repassa_backfill(sem_rede):
    assert coletor.main(["--backfill-dias", "1825"]) == 0
    assert sem_rede == [("São Paulo", 1825)]


def test_rejeita_mais_de_uma_cidade(sem_rede, capsys):
    with pytest.raises(SystemExit) as e:  # argparse encerra com código 2
        coletor.main(["--cidade", "São Paulo,Curitiba"])
    assert e.value.code == 2
    assert "uma única cidade" in capsys.readouterr().err
    assert sem_rede == []  # nada foi coletado


def test_cidade_inexistente_retorna_erro(sem_rede, capsys):
    assert coletor.main(["--cidade", "Xyzland"]) == 1
    assert "cidade não encontrada" in capsys.readouterr().out
