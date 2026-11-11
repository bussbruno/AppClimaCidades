"""Coleta o clima diário de uma cidade. Uso: python coletor.py --cidade "São Paulo" [--backfill-dias 365]"""
from __future__ import annotations

import argparse
import sys

from clima import api, db, servico


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Coleta o clima diário de uma cidade brasileira (Open-Meteo)")
    p.add_argument("--cidade", default="São Paulo",
                   help='nome da cidade (uma só, como no app). Padrão: "São Paulo"')
    p.add_argument("--backfill-dias", type=int, default=0,
                   help="baixa também o histórico dos últimos N dias (ex.: 1825 = 5 anos)")
    args = p.parse_args(argv)

    nome = args.cidade.strip()
    if not nome or "," in nome:
        p.error("informe uma única cidade, sem vírgulas (ex.: --cidade \"Curitiba\")")

    try:
        achadas = api.buscar_cidades(nome, 1)
        if not achadas:
            print(f"[ERRO] cidade não encontrada: {nome}")
            return 1
        c = achadas[0]
        r = servico.coletar_cidade(
            db.conectar(), c["nome"], c["uf"], c["lat"], c["lon"], args.backfill_dias)
    except Exception as e:
        print(f"[ERRO] {nome}: {e}")
        return 1

    print(f"[OK] {c['nome']}/{c['uf']}: {r['clima']} dias de clima gravados")
    for f in r["falhas"]:
        print(f"[AVISO] {c['nome']}: histórico NÃO baixado em {f}. Rode de novo para tentar.")
    return 1 if r["falhas"] else 0


if __name__ == "__main__":
    sys.exit(main())
