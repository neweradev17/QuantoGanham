#!/usr/bin/env python3
"""
Verifica os presidentes de câmara em dados.json contra a Wikidata e propõe alterações.

Não depende de bibliotecas externas (só a biblioteca standard do Python 3.9+).

Uso:
  python scripts/verificar_titulares.py                    # só mostra o relatório
  python scripts/verificar_titulares.py --aplicar          # grava as alterações em dados.json
  python scripts/verificar_titulares.py --relatorio r.md   # guarda também o relatório em ficheiro
  python scripts/verificar_titulares.py --entrada res.json # usa resultados SPARQL guardados (testes)

IMPORTANTE: a Wikidata é editada pela comunidade. Este script serve para DETETAR
possíveis mudanças de titular, não para as confirmar. Cada alteração proposta deve
ser confirmada numa fonte oficial (ata, edital, DGAL/Portal Autárquico, site da câmara)
antes de se fazer merge.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "dados.json"

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "QuantoGanham-verificacao/1.0 (https://github.com/neweradev17/QuantoGanham)"
QID_MUNICIPIO = "Q2039348"      # município de Portugal (confirmar se a verificação falhar)
MANDATO_INICIO = "2025-10-01"   # só interessam titulares com início a partir desta data
POSSE_ATE = "2025-12-01"        # início até esta data = titular da instalação (sem «desde»)

QUERY = f"""
SELECT ?m ?mLabel ?h ?hLabel ?start WHERE {{
  ?m wdt:P31 wd:{QID_MUNICIPIO} .
  ?m p:P6 ?st .
  ?st ps:P6 ?h .
  OPTIONAL {{ ?st pq:P580 ?start . }}
  FILTER NOT EXISTS {{ ?st pq:P582 ?end . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}
"""

STOP = {"de", "da", "do", "dos", "das", "e"}


# ---------------------------------------------------------------- normalização
def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def chave_concelho(label):
    return re.sub(r"^(municipio|concelho|camara municipal) de ", "", norm(label))


def tokens(nome):
    return [t for t in norm(nome).split() if t not in STOP]


def mesmo_nome(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    if ta[0] == tb[0] and ta[-1] == tb[-1]:          # ignora nomes do meio
        return True
    if set(ta) <= set(tb) or set(tb) <= set(ta):      # um contém o outro
        return True
    return SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio() >= 0.88


def qid(uri):
    return uri.rsplit("/", 1)[-1]


# ---------------------------------------------------------------- Wikidata
def consultar():
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": QUERY, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    ultimo = None
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:  # rede, timeout, 5xx
            ultimo = e
            time.sleep(5 * (tentativa + 1))
    raise SystemExit(f"Falha ao consultar a Wikidata: {ultimo}")


def agrupar(rows):
    """chave_concelho -> {qid_municipio: [titulares sem data de fim]}"""
    por = {}
    for r in rows:
        nome = r.get("hLabel", {}).get("value", "")
        if re.fullmatch(r"Q\d+", nome):               # item sem etiqueta
            continue
        mq = qid(r["m"]["value"])
        k = chave_concelho(r["mLabel"]["value"])
        por.setdefault(k, {}).setdefault(mq, []).append({
            "nome": nome,
            "qid": qid(r["h"]["value"]),
            "inicio": r.get("start", {}).get("value", "")[:10],
        })
    return por


# ---------------------------------------------------------------- comparação
def comparar(dados, por):
    mun = dados["mun"]
    cont = {}
    for m in mun:
        k = chave_concelho(m[1])
        cont[k] = cont.get(k, 0) + 1

    res = {"ok": 0, "sem_dados": 0, "ambiguos": [], "diferencas": []}
    for i, m in enumerate(mun):
        dist, nome, escalao, pres = m[0], m[1], m[2], m[3]
        k = chave_concelho(nome)
        wd = por.get(k)
        if not wd:
            res["sem_dados"] += 1
            continue
        if cont[k] > 1 or len(wd) > 1:
            res["ambiguos"].append(f"{nome} ({dist})")
            continue
        mq, holders = next(iter(wd.items()))
        atuais = [h for h in holders if h["inicio"] and h["inicio"] >= MANDATO_INICIO]
        if not atuais:                                  # Wikidata desatualizada: ignora
            res["sem_dados"] += 1
            continue
        ultimo = max(h["inicio"] for h in atuais)
        topo = [h for h in atuais if h["inicio"] == ultimo]
        if len({h["qid"] for h in topo}) > 1:
            res["ambiguos"].append(f"{nome} ({dist})")
            continue
        h = topo[0]
        if pres and mesmo_nome(pres, h["nome"]):
            res["ok"] += 1
            continue
        res["diferencas"].append({
            "i": i, "distrito": dist, "concelho": nome, "atual": pres or "—",
            "novo": h["nome"], "inicio": h["inicio"], "mq": mq, "hq": h["qid"],
            "substituicao": h["inicio"] > POSSE_ATE,
        })
    return res


# ---------------------------------------------------------------- relatório
def relatorio(res, total):
    d = res["diferencas"]
    L = [f"## Verificação de titulares — {date.today().isoformat()}", "",
         "Fonte de deteção: Wikidata (editada pela comunidade — **não é fonte oficial**).", "",
         f"- Confirmados (nome coincide): **{res['ok']}** de {total}",
         f"- Diferenças a verificar: **{len(d)}**",
         f"- Sem dados atuais na Wikidata (ignorados): {res['sem_dados']}",
         f"- Ambíguos (nomes de concelho repetidos; verificar à mão): {len(res['ambiguos'])}", ""]
    if d:
        L += ["### Alterações propostas", "",
              "| Concelho | Distrito | Atual | Proposto | Início (Wikidata) | Tipo | Links |",
              "|---|---|---|---|---|---|---|"]
        for x in d:
            tipo = "substituição" if x["substituicao"] else "correção/preenchimento"
            L.append(
                f"| {x['concelho']} | {x['distrito']} | {x['atual']} | {x['novo']} | "
                f"{x['inicio'] or '—'} | {tipo} | "
                f"[concelho](https://www.wikidata.org/wiki/{x['mq']}) · "
                f"[pessoa](https://www.wikidata.org/wiki/{x['hq']}) |"
            )
        L += ["", "### Antes de fazer merge", "",
              "1. Confirmar **cada linha** numa fonte oficial (ata/edital, DGAL/Portal Autárquico, site da câmara).",
              "2. Retirar do `dados.json` (neste PR) qualquer linha que não se confirme.",
              "3. Distinguir suspensões/substituições temporárias de mudanças definitivas."]
    if res["ambiguos"]:
        L += ["", "### Ambíguos", "", ", ".join(res["ambiguos"])]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- escrita
def aplicar(dados, diferencas):
    """Reescreve só as linhas alteradas, para o diff do PR ser mínimo."""
    linhas = DADOS.read_text(encoding="utf-8").split("\n")
    ini = next(i for i, l in enumerate(linhas) if l.strip().startswith('"mun"')) + 1
    idx = []
    for i in range(ini, len(linhas)):
        s = linhas[i].strip()
        if s.startswith("]"):
            break
        if s.startswith("["):
            idx.append(i)
    if len(idx) != len(dados["mun"]):
        raise SystemExit("dados.json: formato inesperado (uma entrada por linha em «mun»).")
    for x in diferencas:
        m = dados["mun"][x["i"]]
        entrada = [m[0], m[1], m[2], x["novo"]]
        if x["substituicao"]:
            entrada.append({"desde": x["inicio"], "fonte": "wikidata"})
        l = idx[x["i"]]
        virg = "," if linhas[l].rstrip().endswith(",") else ""
        linhas[l] = "    " + json.dumps(entrada, ensure_ascii=False, separators=(",", ":")) + virg
    DADOS.write_text("\n".join(linhas), encoding="utf-8")
    json.loads(DADOS.read_text(encoding="utf-8"))      # valida


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true", help="grava as alterações em dados.json")
    ap.add_argument("--relatorio", help="caminho para guardar o relatório (Markdown)")
    ap.add_argument("--entrada", help="JSON com resultados SPARQL (para testes)")
    ap.add_argument("--min", type=int, default=100, help="mínimo de concelhos esperados na Wikidata")
    a = ap.parse_args()

    dados = json.loads(DADOS.read_text(encoding="utf-8"))
    if a.entrada:
        rows = json.loads(Path(a.entrada).read_text(encoding="utf-8"))
    else:
        rows = consultar()
    por = agrupar(rows)
    if len(por) < a.min:
        raise SystemExit(
            f"Só {len(por)} concelhos devolvidos pela Wikidata (esperados ≥ {a.min}). "
            f"Verifique a consulta SPARQL e o identificador {QID_MUNICIPIO}."
        )

    res = comparar(dados, por)
    texto = relatorio(res, len(dados["mun"]))
    print(texto)
    if a.relatorio:
        Path(a.relatorio).write_text(texto, encoding="utf-8")
    if a.aplicar and res["diferencas"]:
        aplicar(dados, res["diferencas"])
        print(f"{len(res['diferencas'])} alteração(ões) gravada(s) em dados.json", file=sys.stderr)


if __name__ == "__main__":
    main()
