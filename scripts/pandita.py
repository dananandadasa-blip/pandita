#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pandita — utilitários determinísticos de revisão.

Subcomandos:
  extract  arquivo                  -> texto.txt + meta.json
  check    texto.txt                -> achados.json + achados.md + indice-ia.json
  apply    texto.txt achados.json   -> revisada.txt + mudancas.json
  painel   texto.txt revisada.txt mudancas.json -> painel.html
  docx     revisada.txt mudancas.json -> revisado.docx (destaque amarelo)
  diff     original.txt revisada.txt -> diff.html
  ia       texto.txt                -> indice de marcas de IA
  estado   --out pasta --etapa X    -> ESTADO.md (ponto de parada)
  doctor                            -> confere Python, python-docx, LanguageTool
  init     [pasta]                  -> CLAUDE.md para retomar em outro computador

Sem dependências além de python-docx (só no extract/docx).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

VERSION = "1.0.0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SEV = {"alta": 3, "media": 2, "baixa": 1}


def raiz() -> Path:
    """Pasta da skill, para achar glossário e referências sem depender do cwd."""
    return Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- utilidades

def ler(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def escrever(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


def paragrafos(texto: str) -> list[str]:
    blocos = re.split(r"\n\s*\n", texto)
    return [b.strip() for b in blocos if b.strip()]


def palavras(texto: str) -> list[str]:
    return re.findall(r"[^\s]+", texto)


def frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?…])\s+", texto)
    return [p.strip() for p in partes if p.strip()]


def norma(s: str) -> str:
    """minúsculas e sem acento, para comparação tolerante."""
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------- extract

def cmd_extract(args) -> int:
    src = Path(args.arquivo)
    out = Path(args.out)
    if not src.exists():
        print(f"arquivo não encontrado: {src}", file=sys.stderr)
        return 2
    if (out / "texto.txt").resolve() == src.resolve():
        print("a origem já é o texto.txt desta pasta; use outro --out para não sobrescrever o original.",
              file=sys.stderr)
        return 2

    meta: dict = {"fonte": str(src), "formato": src.suffix.lower().lstrip(".")}
    texto = ""

    if src.suffix.lower() == ".docx":
        try:
            import docx  # type: ignore
        except ImportError:
            print("python-docx não está instalado. Rode: pip install python-docx "
                  "(ou use .md/.txt)", file=sys.stderr)
            return 2

        doc = docx.Document(str(src))
        blocos, italicos = [], []
        for p in doc.paragraphs:
            t = p.text.strip()
            if not t:
                continue
            blocos.append(t)
            for r in p.runs:
                if r.italic and r.text.strip():
                    italicos.append(r.text.strip())
        texto = "\n\n".join(blocos)
        meta["italicos"] = sorted(set(italicos))
        meta["titulo"] = doc.core_properties.title or ""
    elif src.suffix.lower() in (".md", ".markdown", ".txt"):
        texto = ler(src)
        # tira marcação markdown óbvia mantendo o conteúdo
        texto = re.sub(r"^#{1,6}\s+", "", texto, flags=re.MULTILINE)
        texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
        texto = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", texto)
    else:
        print(f"formato não suportado: {src.suffix} (use .docx, .md ou .txt)", file=sys.stderr)
        return 2

    paras = paragrafos(texto)
    meta.update({
        "paragrafos": len(paras),
        "palavras": len(palavras(texto)),
        "caracteres": len(texto),
    })
    escrever(out / "texto.txt", "\n\n".join(paras) + "\n")
    escrever(out / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"extraído: {len(paras)} parágrafos, {meta['palavras']} palavras -> {out/'texto.txt'}")
    return 0


# ---------------------------------------------------------------- glossário

def carregar_glossario(caminho: Path | None) -> list[dict]:
    if not caminho or not caminho.exists():
        return []
    import csv

    linhas = []
    with caminho.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not row.get("termo_iast"):
                continue
            variantes = [v.strip() for v in (row.get("variantes_erradas") or "").split("|") if v.strip()]
            linhas.append({
                "termo": row["termo_iast"].strip(),
                "variantes": variantes,
                "categoria": (row.get("categoria") or "").strip(),
                "fonte": (row.get("fonte") or "").strip(),
            })
    return linhas


# ---------------------------------------------------------------- sânscrito

def carregar_config() -> dict:
    p = raiz() / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def faixas_de_citacao(texto: str) -> list[tuple[int, int]]:
    """Trechos entre aspas: citação direta não se corrige."""
    faixas = []
    # a aspa não atravessa parágrafo: uma aspa sem fecho não pode esconder o resto do documento
    for rx in (r"“(?:[^”\n]|\n(?!\s*\n))*”", r'"[^"\n]*"'):
        for m in re.finditer(rx, texto):
            faixas.append((m.start(), m.end()))
    return faixas


def dentro(pos: int, faixas: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in faixas)


ISO_SO_IAST = [
    ("ṁ", "ṃ", "anusvāra em ISO 15919; em IAST usa-se ṃ"),
    ("r̥", "ṛ", "vogal r em ISO 15919; em IAST usa-se ṛ"),
    ("l̥", "ḷ", "vogal l em ISO 15919; em IAST usa-se ḷ"),
]


def cmd_sanscrito(texto: str, glossario: list[dict], config: dict | None = None) -> list[dict]:
    config = config if config is not None else carregar_config()
    sistema = (config.get("transliteracao") or "bbt-pt").lower()
    achados: list[dict] = []
    paras = paragrafos(texto)
    citacoes = faixas_de_citacao(texto) if config.get("ignorar_citacao_direta", True) else []

    def add(regra, sev, linha, antes, depois, motivo, fonte=""):
        achados.append({
            "regra": regra, "categoria": "sanscrito", "severidade": sev,
            "linha": linha, "antes": antes, "depois": depois,
            "motivo": motivo, "fonte": fonte,
        })

    # anusvāra misturado no mesmo documento é o único caso que sempre denuncia erro
    if "ṁ" in texto and "ṃ" in texto:
        # depois=None: é aviso para decisão humana, não troca que o apply consiga fazer
        add("IAST-ANUSVARA", "media", 1, "ṁ / ṃ", None,
            "O documento mistura dois anusvāras. Escolha um padrão e mantenha.", "PADRAO §7")

    for i, par in enumerate(paras, 1):
        # NFC: um achado por palavra; cortar o parágrafo em 80 caracteres duplicava letras no apply
        for tok in re.findall(r"\S+", par):
            nfc = unicodedata.normalize("NFC", tok)
            if nfc != tok:
                add("IAST-NFC", "alta", i, tok, nfc,
                    "Acento separado da letra (NFD). Normalize para NFC antes de exportar.", "PADRAO §7")
        # ISO 15919 só quando a casa pede IAST estrito
        if sistema == "iast":
            for ruim, bom, explic in ISO_SO_IAST:
                if ruim in par:
                    add("IAST-ISO", "alta", i, ruim, bom, explic, "PADRAO §7")
        # SLP1 disfarçado: termo do glossário escrito em SLP1
        for g in glossario:
            slp = None
            try:
                slp = slp1_de_iast(g["termo"])
            except Exception:
                pass
            if slp and slp != g["termo"] and re.search(rf"\b{re.escape(slp)}\b", par):
                add("IAST-SLP1", "alta", i, slp, g["termo"],
                    "Termo em SLP1 (f = ṛ, w = ṭ etc.). Converter para IAST.", "PADRAO §7")

    # variantes erradas do glossário, ignorando citação direta
    for g in glossario:
        sev = "media" if g["categoria"] in ("nome", "título") else "alta"
        for v in g["variantes"]:
            if v == g["termo"]:
                continue
            for m in re.finditer(rf"(?<![\w]){re.escape(v)}(?![\w])", texto):
                if dentro(m.start(), citacoes):
                    continue
                linha = texto[:m.start()].count("\n\n") + 1
                nota = " Se for nome próprio na casa, manter." if g["categoria"] == "nome" else ""
                add("IAST-GLOSSARIO", sev, linha, v, g["termo"],
                    f"Variante fora do padrão para {g['termo']}.{nota}",
                    g["fonte"] or "glossário da casa")

    return achados


def slp1_de_iast(termo: str) -> str:
    """Conversão mínima IAST -> SLP1 para detectar vazamento (não é conversor completo)."""
    mapa = {
        "ā": "A", "ī": "I", "ū": "U", "ṛ": "f", "ṝ": "F", "ḷ": "x", "ḹ": "X",
        "ṃ": "M", "ḥ": "H", "ṅ": "N", "ñ": "Y", "ṭ": "w", "ḍ": "q", "ṇ": "R",
        "ś": "S", "ṣ": "z", "ē": "e", "ō": "o",
    }
    out = []
    for c in termo:
        out.append(mapa.get(c, c))
    return "".join(out)


# ---------------------------------------------------------------- índice de IA

PADROES_IA = [
    (r"\bnão (?:é|se trata de) [^.,;]{1,60}, (?:é|mas|e sim)\b", 3, "contraste 'não é X, é Y'"),
    (r"\bnão apenas\b[^.]{1,80}\bmas também\b", 2, "'não apenas... mas também'"),
    (r"\bé importante (?:ressaltar|notar|destacar|lembrar)\b", 2, "muleta 'é importante...'"),
    (r"\bvale (?:ressaltar|destacar|lembrar|notar)\b", 2, "muleta 'vale destacar'"),
    (r"\bem (?:suma|última análise|síntese)\b", 2, "fechamento 'em suma'"),
    (r"\bpor fim\b", 1, "conector 'por fim'"),
    (r"\balém disso\b", 1, "conector 'além disso'"),
    (r"\bno (?:cenário|mundo|contexto) (?:atual|de hoje|contemporâneo)\b", 3, "abertura de cenário"),
    (r"\b(?:mergulh|jornada|transformador|revolucion|robust|holístic|sinergia|ecossistema)\w*", 2, "léxico de IA"),
    (r"\bde (?:forma|maneira) (?:abrangente|significativa|profunda|consistente)\b", 2, "advérbio inflado"),
    (r"\ba verdade é que\b|\bo fato é que\b", 2, "abertura 'a verdade é que'"),
    (r"\bconvido (?:você|o leitor)\b|\brespire fundo\b", 3, "convite de palco"),
    (r"\*\*[^*\n]{2,40}:\*\*", 2, "rótulo em negrito no início"),
]

def cmd_ia(texto: str, sensibilidade: float = 1.0) -> dict:
    import math

    paras = paragrafos(texto)
    total_pal = max(1, len(palavras(texto)))
    linhas = []
    soma_pond = 0.0
    for i, par in enumerate(paras, 1):
        n_pal = max(1, len(palavras(par)))
        if n_pal < 8:  # título, linha solta: não pontua
            linhas.append({"paragrafo": i, "palavras": n_pal, "score": 0,
                           "padroes": [], "inicio": par[:70]})
            continue
        acertos = []
        peso = 0.0
        for rx, w, label in PADROES_IA:
            n = len(re.findall(rx, par, flags=re.IGNORECASE))
            if n:
                peso += w * min(n, 3)
                acertos.append({"padrao": label, "ocorrencias": n, "peso": w * min(n, 3)})
        trave = par.count("—")
        if trave > 2:
            peso += (trave - 2) * 0.5
            acertos.append({"padrao": "travessão em excesso", "ocorrencias": trave, "peso": (trave - 2) * 0.5})
        # saturação suave: um padrão isolado não vira 100
        razao = peso * 8 / max(n_pal, 20)
        score = min(100, round(100 * (1 - math.exp(-razao)) * sensibilidade))
        soma_pond += score * n_pal
        linhas.append({"paragrafo": i, "palavras": n_pal, "score": score,
                       "padroes": acertos, "inicio": par[:70]})

    # burstiness: frases de tamanho parecido soam de máquina
    tamanhos = [len(palavras(f)) for f in frases(texto)]
    if len(tamanhos) >= 3:
        media = sum(tamanhos) / len(tamanhos)
        var = sum((t - media) ** 2 for t in tamanhos) / len(tamanhos)
        desvio = var ** 0.5
    else:
        desvio = 10.0
    burst = max(0.0, min(100.0, (12 - desvio) * 8))

    medio = soma_pond / total_pal
    doc = round(0.7 * medio + 0.3 * burst)
    return {
        "metodo": "índice heurístico de marcas de IA (v0) — não é probabilidade nem detector",
        "score_documento": min(100, doc),
        "burstiness": round(desvio, 1),
        "paragrafos": linhas,
        "palavras": total_pal,
    }


# ---------------------------------------------------------------- LanguageTool

def _palavra_em(texto: str, pos: int) -> str:
    ini = pos
    while ini > 0 and (texto[ini - 1].isalnum() or texto[ini - 1] in "-'’"):
        ini -= 1
    fim = pos
    while fim < len(texto) and (texto[fim].isalnum() or texto[fim] in "-'’"):
        fim += 1
    return texto[ini:fim]


def _carregar_ignoradas() -> set[str]:
    p = raiz() / "ignorar.txt"
    if not p.exists():
        return set()
    return {norma(l.strip()) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


SANSKRITO_RX = re.compile(r"[ṛṣṃḥśīūṁṭḍṇḷāēōṝḹĀĪŪṚṢṂḤŚḌṬṆḶ]")


def _parece_sanscrito(palavra: str, glossario: list[dict], ignoradas: set[str]) -> bool:
    """Evita que o corretor de português trate termo sânscrito como erro."""
    alvo = norma(palavra)
    if not alvo:
        return False
    if SANSKRITO_RX.search(palavra):
        return True
    if alvo in ignoradas:
        return True
    for g in glossario:
        termo = norma(g["termo"])
        if alvo == termo or (len(alvo) >= 4 and (termo.startswith(alvo) or alvo.startswith(termo))):
            return True
        for v in g["variantes"]:
            if alvo == norma(v):
                return True
    return False


def lt_check(texto: str, endpoint: str, idioma: str = "pt-BR",
             glossario: list[dict] | None = None, picky: bool = False) -> list[dict]:
    # file:// e outros esquemas fariam o urllib ler um arquivo local no lugar do servidor
    if urllib.parse.urlparse(endpoint).scheme not in ("http", "https"):
        raise ValueError("languagetool_url precisa começar com http:// ou https://")
    dados = urllib.parse.urlencode({
        "text": texto, "language": idioma,
        "enabledOnly": "false", "level": "picky" if picky else "default",
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/check", data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    glossario = glossario or []
    ignoradas = _carregar_ignoradas()
    achados = []
    for m in data.get("matches", []):
        off, ln = m["offset"], m["length"]
        antes = texto[off:off + ln]
        palavra = _palavra_em(texto, off)
        tipo = m["rule"].get("issueType", "")
        rep = (m.get("replacements") or [{}])[0].get("value")

        # regras de estilo do LT são genéricas e puxam português europeu; ficam fora
        if tipo in ("style", "uncategorized", "locale-violation"):
            continue

        if tipo == "misspelling":
            if _parece_sanscrito(palavra, glossario, ignoradas):
                continue
            bloco = texto[:off].rsplit("\n\n", 1)[-1] + texto[off:].split("\n\n", 1)[0]
            if len(palavra) <= 4 and SANSKRITO_RX.search(bloco):
                continue  # palavra curta em bloco de transliteração (cha, ca, eva…)
            if rep:
                razao = SequenceMatcher(None, norma(palavra), norma(rep)).ratio()
                if razao < 0.55:
                    continue  # sugestão distante: provável nome próprio
            sev = "alta"
        elif tipo == "grammar":
            sev = "alta"
        else:
            sev = "media"

        achados.append({
            "regra": "LT:" + m["rule"]["id"],
            "categoria": "languagetool",
            "severidade": sev,
            "linha": texto[:off].count("\n\n") + 1,
            "antes": antes,
            "depois": rep,
            "motivo": m["message"],
            "fonte": "LanguageTool",
        })
    return achados


# ---------------------------------------------------------------- check

def cmd_check(args) -> int:
    src = Path(args.texto)
    out = Path(args.out)
    texto = ler(src)
    if args.glossario:
        glossario = carregar_glossario(Path(args.glossario))
    else:
        glossario = carregar_glossario(raiz() / "glossario.csv")

    config = carregar_config()
    achados = cmd_sanscrito(texto, glossario, config)
    endpoint = args.lt or config.get("languagetool_url")
    idioma = args.idioma or config.get("idioma") or "pt-BR"
    lt = "não configurado"
    if endpoint:
        try:
            achados += lt_check(texto, endpoint, idioma, glossario, args.picky)
            lt = "consultado"
        except Exception as e:  # servidor fora do ar não derruba a revisão
            lt = "fora do ar"
            print(f"[aviso] LanguageTool indisponível em {endpoint}: {e}", file=sys.stderr)

    ia = cmd_ia(texto)

    escrever(out / "achados.json", json.dumps(achados, ensure_ascii=False, indent=2))
    escrever(out / "indice-ia.json", json.dumps(ia, ensure_ascii=False, indent=2))
    escrever(out / "achados.md", relatorio_achados(achados, ia, lt))

    altos = sum(1 for a in achados if a["severidade"] == "alta")
    print(f"achados: {len(achados)} ({altos} de severidade alta) | índice de IA: {ia['score_documento']}/100"
          f" | LanguageTool: {lt}")
    return 0


def relatorio_achados(achados: list[dict], ia: dict, lt: str = "consultado") -> str:
    linhas = ["# Achados mecânicos", ""]
    if lt != "consultado":  # o relatório diz o que não foi checado
        linhas += [f"**LanguageTool {lt}: a gramática objetiva não foi checada.**", ""]
    if not achados:
        linhas.append("Nenhum achado automático.")
    for a in sorted(achados, key=lambda x: (-SEV.get(x["severidade"], 0), x["linha"])):
        rep = f" → **{a['depois']}**" if a.get("depois") else ""
        linhas.append(f"- [ ] `{a['severidade']}` **{a['regra']}** (linha {a['linha']}): "
                      f"“{a['antes']}”{rep} — {a['motivo']}")
    linhas += ["", "## Índice de marcas de IA", "",
               f"**{ia['score_documento']}/100** (burstiness {ia['burstiness']}) — heurístico, não veredito.", ""]
    for p in ia["paragrafos"]:
        if p["score"] >= 40:
            linhas.append(f"- parágrafo {p['paragrafo']} ({p['score']}): {p['inicio']}…")
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- apply

def _rx_trecho(antes: str) -> re.Pattern:
    """Casa o trecho inteiro: 'Krishna' não casa dentro de 'Krishnamurti'."""
    ini = r"(?<!\w)" if re.match(r"\w", antes) else ""
    fim = r"(?!\w)" if re.search(r"\w$", antes) else ""
    return re.compile(ini + re.escape(antes) + fim)


def cmd_apply(args) -> int:
    origem = Path(args.texto)
    out = Path(args.out)
    texto = ler(origem)
    achados = json.loads(ler(Path(args.achados)))

    # quantas vezes cada trecho pode ser trocado: permite repetição legítima
    from collections import Counter
    pendentes = Counter(
        a["antes"] for a in achados
        if a.get("antes") and a.get("depois") is not None and a["antes"] != a["depois"]
    )

    # só o que tem substituição; ordem estável para o relatório
    mudancas, conflitos = [], []
    feitas = set()
    for a in achados:
        antes, depois = a.get("antes"), a.get("depois")
        if not antes or depois is None or antes == depois:
            continue
        rx = _rx_trecho(antes)
        achou = rx.search(texto)
        if not achou:
            # dois especialistas apontaram a mesma troca: a segunda já está feita, não é conflito
            if (antes, depois) not in feitas:
                conflitos.append({**a, "motivo_conflito": "trecho não encontrado"})
            continue
        if len(rx.findall(texto)) > pendentes[antes] and not args.forcar:
            conflitos.append({**a, "motivo_conflito": "trecho ambíguo (aparece mais vezes do que o previsto)"})
            continue
        texto = texto[:achou.start()] + depois + texto[achou.end():]
        feitas.add((antes, depois))
        pendentes[antes] -= 1
        mudancas.append({"antes": antes, "depois": depois,
                         "regra": a.get("regra"), "categoria": a.get("categoria"),
                         "severidade": a.get("severidade"), "motivo": a.get("motivo")})

    escrever(out / "revisada.txt", texto)
    escrever(out / "mudancas.json", json.dumps(mudancas, ensure_ascii=False, indent=2))
    if conflitos:
        escrever(out / "conflitos.json", json.dumps(conflitos, ensure_ascii=False, indent=2))
    print(f"aplicadas: {len(mudancas)} mudanças | conflitos: {len(conflitos)}")
    return 0


# ---------------------------------------------------------------- docx

def _destaques(original: str, revisado: str) -> dict[int, list[tuple[str, bool]]]:
    """Mapeia cada parágrafo revisado em pedaços (texto, destacar?)."""
    o_paras, r_paras = paragrafos(original), paragrafos(revisado)
    sm = SequenceMatcher(None, o_paras, r_paras)
    mapa: dict[int, list[tuple[str, bool]]] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j2 - j1):
                mapa[j1 + k] = [(r_paras[j1 + k], False)]
        elif tag == "insert":
            for k in range(j1, j2):
                mapa[k] = [(r_paras[k], True)]
        else:
            for k in range(j2 - j1):
                o = o_paras[i1 + k] if i1 + k < i2 else ""
                r = r_paras[j1 + k]
                if not o:
                    mapa[j1 + k] = [(r, True)]
                    continue
                segs: list[tuple[str, bool]] = []
                s2 = SequenceMatcher(None, _tokens(o), _tokens(r))
                for op, a1, a2, b1, b2 in s2.get_opcodes():
                    txt = "".join(_tokens(r)[b1:b2])
                    if not txt:
                        continue
                    destaca = op in ("insert", "replace")
                    if segs and segs[-1][1] == destaca:
                        segs[-1] = (segs[-1][0] + txt, destaca)
                    else:
                        segs.append((txt, destaca))
                mapa[j1 + k] = segs
    return mapa


def _seg_tracked(o: str, r: str) -> list[tuple[str, str]]:
    """Pedaços na ordem do revisado, com marcação de igual/inserido/removido."""
    segs: list[tuple[str, str]] = []
    sm = SequenceMatcher(None, _tokens(o), _tokens(r))
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        velho = "".join(_tokens(o)[a1:a2])
        novo = "".join(_tokens(r)[b1:b2])
        if op == "equal":
            segs.append(("equal", novo))
        elif op == "insert":
            segs.append(("ins", novo))
        elif op == "delete":
            segs.append(("del", velho))
        else:
            if velho:
                segs.append(("del", velho))
            if novo:
                segs.append(("ins", novo))
    return segs


def _docx_tracked(doc, original: str, revisado: str, autor: str) -> int:
    """Escreve o documento com marcas de revisão do Word (w:ins / w:del)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from datetime import datetime, timezone

    data = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    contador = [0]

    def run_el(texto: str, removido: bool = False):
        r = OxmlElement("w:r")
        # verso tem quebra de linha dentro do parágrafo: vira w:br, senão o Word junta as linhas
        for k, parte in enumerate(texto.split("\n")):
            if k:
                r.append(OxmlElement("w:br"))
            t = OxmlElement("w:delText" if removido else "w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = parte
            r.append(t)
        return r

    def marca(tag: str, filhos: list):
        el = OxmlElement(tag)
        contador[0] += 1
        el.set(qn("w:id"), str(contador[0]))
        el.set(qn("w:author"), autor)
        el.set(qn("w:date"), data)
        for f in filhos:
            el.append(f)
        return el

    o_paras, r_paras = paragrafos(original), paragrafos(revisado)
    sm = SequenceMatcher(None, o_paras, r_paras)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j2 - j1):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p._p.append(run_el(r_paras[j1 + k]))
        elif tag == "insert":
            for k in range(j1, j2):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p._p.append(marca("w:ins", [run_el(r_paras[k])]))
        elif tag == "delete":
            for k in range(i1, i2):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p._p.append(marca("w:del", [run_el(o_paras[k], removido=True)]))
        else:
            total = max(i2 - i1, j2 - j1)
            for k in range(total):
                o = o_paras[i1 + k] if i1 + k < i2 else ""
                r = r_paras[j1 + k] if j1 + k < j2 else ""
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                if not o:
                    p._p.append(marca("w:ins", [run_el(r)]))
                    continue
                if not r:
                    p._p.append(marca("w:del", [run_el(o, removido=True)]))
                    continue
                for tipo, texto in _seg_tracked(o, r):
                    if tipo == "equal":
                        p._p.append(run_el(texto))
                    elif tipo == "ins":
                        p._p.append(marca("w:ins", [run_el(texto)]))
                    else:
                        p._p.append(marca("w:del", [run_el(texto, removido=True)]))
    return contador[0]


def cmd_docx(args) -> int:
    if getattr(args, "tracked", False) and not getattr(args, "original", None):
        print("--tracked precisa de --original <texto.txt>: sem o original não há o que marcar como removido.",
              file=sys.stderr)
        return 2
    try:
        import docx  # type: ignore
    except ImportError:
        print("python-docx não está instalado. Rode: pip install python-docx", file=sys.stderr)
        return 2
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX

    texto = ler(Path(args.texto))
    mudancas = json.loads(ler(Path(args.mudancas))) if args.mudancas else []

    original = ler(Path(args.original)) if getattr(args, "original", None) else None

    mapa = _destaques(original, texto) if original else None

    doc = docx.Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(3)
    sec.right_margin = Cm(2.5)

    estilo = doc.styles["Normal"]
    estilo.font.name = "Source Serif Pro"
    estilo.font.size = Pt(11.5)
    estilo.paragraph_format.space_after = Pt(6)
    estilo.paragraph_format.line_spacing = 1.4

    if original and getattr(args, "tracked", False):
        _docx_tracked(doc, original, texto, getattr(args, "autor", None) or "pandita")
        destino = Path(args.out)
        destino.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(destino))
        print(f"docx com marcas de revisão: {destino}")
        return 0

    # cada mudança destaca no máximo uma ocorrência no documento
    restantes: dict[str, int] = {}
    for m in mudancas:
        d = (m.get("depois") or "").strip()
        if d:
            restantes[d] = restantes.get(d, 0) + 1

    for i, par in enumerate(paragrafos(texto)):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if mapa is not None:
            for txt, destacar in mapa.get(i, [(par, False)]):
                run = p.add_run(txt)
                if destacar:
                    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            continue

        usar = [m for m in mudancas
                if m.get("depois") and m["depois"] in par and restantes.get(m["depois"].strip(), 0) > 0]

        if not usar:
            p.add_run(par)
            continue

        # divide o parágrafo nos trechos alterados (1ª ocorrência de cada)
        resto, cursor = par, 0
        marcas = []
        for m in usar:
            pos = resto.find(m["depois"])
            if pos < 0:
                continue
            marcas.append((cursor + pos, cursor + pos + len(m["depois"]), m))
            cursor += pos + len(m["depois"])
            resto = resto[pos + len(m["depois"]):]

        corte = 0
        for ini, fim, m in sorted(marcas):
            if ini > corte:
                p.add_run(par[corte:ini])
            run = p.add_run(par[ini:fim])
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            restantes[m["depois"].strip()] -= 1
            corte = fim
        if corte < len(par):
            p.add_run(par[corte:])

    destino = Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    print(f"docx: {destino} ({len(mudancas)} mudanças destacadas)")
    return 0


# ---------------------------------------------------------------- diff

def cmd_diff(args) -> int:
    a = paragrafos(ler(Path(args.original)))
    b = paragrafos(ler(Path(args.revisada)))

    # o texto pode ter < e &: sem escape, o navegador leria como HTML
    a, b = [esc(p) for p in a], [esc(p) for p in b]

    def inline(x: str, y: str) -> str:
        sm = SequenceMatcher(None, x.split(), y.split())
        saida = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            velho = " ".join(x.split()[i1:i2])
            novo = " ".join(y.split()[j1:j2])
            if op == "equal":
                saida.append(velho)
            elif op == "delete":
                saida.append(f"<del>{velho}</del>")
            elif op == "insert":
                saida.append(f"<ins>{novo}</ins>")
            else:
                saida.append(f"<del>{velho}</del> <ins>{novo}</ins>")
        return " ".join(saida)

    sm = SequenceMatcher(None, a, b)
    corpo = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for p in a[i1:i2]:
                corpo.append(f"<p>{p}</p>")
        elif op == "delete":
            for p in a[i1:i2]:
                corpo.append(f'<p class="del">{p}</p>')
        elif op == "insert":
            for p in b[j1:j2]:
                corpo.append(f'<p class="ins">{p}</p>')
        else:
            for k in range(max(i2 - i1, j2 - j1)):
                x = a[i1 + k] if i1 + k < i2 else ""
                y = b[j1 + k] if j1 + k < j2 else ""
                corpo.append(f"<p>{inline(x, y) if x and y else y or x}</p>")

    html = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>diff — {esc(Path(args.original).name)}</title>
<style>
 body{{font-family:Georgia,serif;max-width:46rem;margin:4rem auto;padding:0 1.5rem;line-height:1.65;color:#222}}
 p{{margin:0 0 1rem}} ins{{background:#d9f2d9;text-decoration:none}} del{{background:#f7d9d9;text-decoration:line-through}}
 p.ins{{background:#f0faf0}} p.del{{background:#fdf0f0}}
</style>
<h1>Original × revisado</h1>
{chr(10).join(corpo)}
</html>"""
    destino = Path(args.out)
    escrever(destino, html)
    print(f"diff: {destino}")
    return 0


# ---------------------------------------------------------------- painel

CAT_COR = {
    "pontuacao": "#b45309", "gramatica": "#1d4ed8", "ortografia": "#b91c1c",
    "fluidez": "#7c3aed", "genero": "#0f766e", "sanscrito": "#9d174d",
    "ia": "#525252", "languagetool": "#0369a1",
}


def _tokens(t: str) -> list[str]:
    return re.findall(r"\S+\s*", t)


def _marcar(original: str, revisado: str, mudancas: list[dict]) -> tuple[str, str, set]:
    """Devolve (html_original, html_revisado, categorias) de um par de parágrafos."""
    to, tr = _tokens(original), _tokens(revisado)
    sm = SequenceMatcher(None, to, tr)
    cats: set[str] = set()

    # intervalos inseridos no revisado, com posição em caracteres
    inseridos: list[tuple[int, int, str]] = []
    pos = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        trecho = "".join(tr[j1:j2])
        if tag in ("insert", "replace") and trecho:
            inseridos.append((pos, pos + len(trecho), trecho))
        if tag in ("equal", "insert", "replace"):
            pos += len(trecho)

    # casa cada intervalo com uma mudança declarada
    def cat_de(trecho: str) -> tuple[str | None, str | None]:
        alvo = trecho.strip()
        for m in mudancas:
            d = (m.get("depois") or "").strip()
            if d and (alvo == d or alvo in d or d in alvo):
                return m.get("categoria") or "fluidez", m.get("regra")
        return None, None

    # revisado
    partes_r, cursor, pos = [], 0, 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        trecho = "".join(tr[j1:j2])
        if tag == "equal":
            partes_r.append(esc(trecho))
            pos += len(trecho)
        elif tag in ("insert", "replace"):
            cat, regra = cat_de(trecho)
            if cat:
                cats.add(cat)
                marca = f'<mark class="chg" data-cat="{esc(cat)}" data-regra="{esc(regra or "")}">{esc(trecho)}</mark>'
            else:
                cats.add("fluidez")
                marca = f'<mark class="chg" data-cat="fluidez">{esc(trecho)}</mark>'
            partes_r.append(marca)
            pos += len(trecho)

    # original
    partes_o = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        velho = "".join(to[i1:i2])
        if tag == "equal":
            partes_o.append(esc(velho))
        elif tag in ("delete", "replace"):
            if velho:
                partes_o.append(f'<del class="del">{esc(velho)}</del>')
    return "".join(partes_o), "".join(partes_r), cats


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def cmd_painel(args) -> int:
    original = ler(Path(args.original))
    revisado = ler(Path(args.revisada))
    mudancas = json.loads(ler(Path(args.mudancas))) if Path(args.mudancas).exists() else []
    achados = json.loads(ler(Path(args.achados))) if args.achados and Path(args.achados).exists() else []
    ia = json.loads(ler(Path(args.ia))) if args.ia and Path(args.ia).exists() else None

    o_paras, r_paras = paragrafos(original), paragrafos(revisado)
    sm = SequenceMatcher(None, o_paras, r_paras)
    linhas = []
    n_alt = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                linhas.append({"o": esc(o_paras[i1 + k]), "r": esc(r_paras[j1 + k]),
                               "alt": False, "cats": set()})
        elif tag == "delete":
            for p in o_paras[i1:i2]:
                linhas.append({"o": f'<del class="del">{esc(p)}</del>', "r": "",
                               "alt": True, "cats": set()})
                n_alt += 1
        elif tag == "insert":
            for p in r_paras[j1:j2]:
                linhas.append({"o": "", "r": f'<mark class="chg" data-cat="fluidez">{esc(p)}</mark>',
                               "alt": True, "cats": {"fluidez"}})
                n_alt += 1
        else:
            total = max(i2 - i1, j2 - j1)
            for k in range(total):
                o = o_paras[i1 + k] if i1 + k < i2 else ""
                r = r_paras[j1 + k] if j1 + k < j2 else ""
                if o and r:
                    ho, hr, cats = _marcar(o, r, mudancas)
                    # mudou = o texto difere, com ou sem registro: remoção pura e troca
                    # não declarada são justamente o que a pessoa precisa ver
                    mudou = o != r
                    n_alt += mudou
                    linhas.append({"o": ho, "r": hr, "alt": mudou, "cats": cats})
                elif o:
                    linhas.append({"o": f'<del class="del">{esc(o)}</del>', "r": "", "alt": True, "cats": set()})
                    n_alt += 1
                else:
                    linhas.append({"o": "", "r": f'<mark class="chg" data-cat="fluidez">{esc(r)}</mark>',
                                   "alt": True, "cats": {"fluidez"}})
                    n_alt += 1

    corpo_o = "\n".join(
        f'<p class="par{" alt" if l["alt"] else ""}" data-cats="{esc(",".join(sorted(l["cats"])))}">{l["o"]}</p>'
        for l in linhas)
    corpo_r = "\n".join(
        f'<p class="par{" alt" if l["alt"] else ""}" data-cats="{esc(",".join(sorted(l["cats"])))}">{l["r"]}</p>'
        for l in linhas)

    # cards
    cards = []
    for m in mudancas:
        cor = CAT_COR.get(m.get("categoria") or "fluidez", "#525252")
        cat = esc(m.get("categoria") or "fluidez")
        sev = esc(m.get("severidade") or "media")
        cards.append(f"""
        <article class="card" data-cat="{cat}" data-regra="{esc(m.get('regra') or '')}">
          <div class="tag" style="--cor:{cor}"><span>{cat}</span><b>{sev}</b></div>
          <p class="de"><span class="rot">antes</span>{esc(m.get('antes') or '')}</p>
          <p class="para"><span class="rot">depois</span>{esc(m.get('depois') or '')}</p>
          <p class="por">{esc(m.get('motivo') or '')}</p>
          <p class="fonte">{esc(m.get('fonte') or '')}</p>
        </article>""")

    # pendências: achados que não viraram mudança
    aplicados = {(m.get("antes") or "").strip() for m in mudancas}
    pend = [a for a in achados if (a.get("antes") or "").strip() not in aplicados]
    pend_html = "".join(
        f'<li><b>{esc(a.get("regra") or "")}</b> · {esc(a.get("antes") or "")} — {esc(a.get("motivo") or "")}</li>'
        for a in pend[:40])

    ia_html = ""
    if ia:
        # indice-ia.json também é arquivo editável: número vira número antes de ir para o style
        for p in ia.get("paragrafos", []):
            p["paragrafo"], p["score"] = int(p.get("paragrafo", 0)), int(p.get("score", 0))
        barras = "".join(
            f'<div class="barra"><span>{p["paragrafo"]}</span>'
            f'<i style="width:{p["score"]}%;background:{"#b91c1c" if p["score"]>=60 else "#b45309" if p["score"]>=35 else "#4d7c0f"}"></i>'
            f'<b>{p["score"]}</b></div>'
            for p in ia.get("paragrafos", []))
        ia_html = f"""
        <section class="bloco">
          <h3>Marcas de IA <span class="nota">índice, não veredito</span></h3>
          <div class="score">{int(ia.get('score_documento', 0))}<small>/100</small></div>
          <p class="nota">burstiness {float(ia.get('burstiness', 0))} · parágrafos com marca aparecem em vermelho</p>
          <div class="barras">{barras}</div>
        </section>"""

    html = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>pandita — %(titulo)s</title>
<style>
:root{--tinta:#1c1917;--papel:#faf7f1;--linha:#e3dccd;--acento:#7c5e3c;--suave:#6b6357}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
 font-family:"Source Serif Pro",Georgia,serif;line-height:1.62}
header{padding:2.2rem 2rem 1.2rem;border-bottom:1px solid var(--linha)}
.marca{font:600 .72rem/1 Montserrat,system-ui,sans-serif;letter-spacing:.18em;
 text-transform:uppercase;color:var(--acento)}
h1{font-size:1.9rem;margin:.4rem 0 .3rem;font-weight:600}
.meta{font:400 .8rem/1.4 Montserrat,system-ui,sans-serif;color:var(--suave)}
.ferramentas{position:sticky;top:0;z-index:5;display:flex;gap:.5rem;flex-wrap:wrap;
 align-items:center;padding:.7rem 2rem;background:rgba(250,247,241,.94);
 backdrop-filter:blur(6px);border-bottom:1px solid var(--linha)}
.chip{font:500 .72rem/1 Montserrat,system-ui,sans-serif;border:1px solid var(--linha);
 background:#fff;border-radius:999px;padding:.42rem .7rem;cursor:pointer;color:var(--suave)}
.chip.on{background:var(--tinta);color:#fff;border-color:var(--tinta)}
.wrap{display:grid;grid-template-columns:1fr 1fr 340px;gap:0;align-items:start}
.col{padding:1.4rem 1.6rem 4rem;border-right:1px solid var(--linha);min-width:0}
.col h2{font:600 .7rem/1 Montserrat,system-ui,sans-serif;letter-spacing:.14em;
 text-transform:uppercase;color:var(--suave);margin:0 0 1rem;position:sticky;top:3.2rem;
 background:var(--papel);padding:.5rem 0;z-index:2}
.par{margin:0 0 1.05rem;white-space:pre-wrap}
.par.oculto{display:none}
mark.chg{background:#fff1a8;color:inherit;padding:.05em .1em;border-radius:2px;
 cursor:pointer;transition:background .2s}
mark.chg[data-cat=pontuacao]{background:#fde3c8}mark.chg[data-cat=gramatica]{background:#dbe6ff}
mark.chg[data-cat=ortografia]{background:#ffd9d9}mark.chg[data-cat=fluidez]{background:#e9defb}
mark.chg[data-cat=sanscrito]{background:#fbd9e7}mark.chg[data-cat=genero]{background:#d3f0ea}
mark.chg.flash{outline:2px solid #b45309;outline-offset:2px}
del.del{background:#f7dcdc;color:#7f1d1d;text-decoration:line-through}
aside{padding:1.2rem 1.2rem 5rem;background:#f3ede2;height:100vh;
 position:sticky;top:0;overflow-y:auto}
aside h3{font:600 .72rem/1.3 Montserrat,system-ui,sans-serif;letter-spacing:.1em;
 text-transform:uppercase;margin:.2rem 0 .8rem;color:var(--suave)}
.bloco{background:#fff;border:1px solid var(--linha);border-radius:10px;
 padding:1rem;margin-bottom:1rem}
.score{font-size:2.4rem;font-weight:600;line-height:1}
.score small{font-size:.9rem;color:var(--suave)}
.nota{font:400 .72rem/1.45 Montserrat,system-ui,sans-serif;color:var(--suave);margin:.2rem 0 .8rem}
.barras{display:grid;gap:.25rem}
.barra{display:grid;grid-template-columns:1.4rem 1fr 1.8rem;gap:.4rem;align-items:center;
 font:400 .66rem/1 Montserrat,system-ui,sans-serif;color:var(--suave)}
.barra i{display:block;height:5px;border-radius:3px;background:#4d7c0f;min-width:2px}
.barra b{text-align:right;font-weight:600}
.card{background:#fff;border:1px solid var(--linha);border-radius:10px;padding:.8rem .9rem;margin-bottom:.6rem}
.card.oculto{display:none}
.tag{display:flex;justify-content:space-between;align-items:center;
 font:600 .62rem/1 Montserrat,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.tag span{color:var(--cor);border-left:3px solid var(--cor);padding-left:.45rem}
.tag b{color:var(--suave);font-weight:500}
.rot{display:block;font:600 .58rem/1 Montserrat,system-ui,sans-serif;letter-spacing:.12em;
 text-transform:uppercase;color:var(--suave);margin-bottom:.15rem}
.card .de{color:#7f1d1d;text-decoration:line-through;text-decoration-color:#d9a3a3;
 margin:.5rem 0 .4rem;font-size:.9rem}
.card .para{color:#14532d;margin:0 0 .45rem;font-size:.9rem}
.card .por{margin:0;font-size:.82rem;color:#3f3a33}
.card .fonte{margin:.35rem 0 0;font:.6rem/1 Montserrat,system-ui,sans-serif;color:#9a9184}
.pend{font:400 .76rem/1.5 Montserrat,system-ui,sans-serif;color:#3f3a33;margin:0;padding-left:1rem}
footer{position:fixed;bottom:0;left:0;right:0;display:flex;gap:1rem;align-items:center;
 justify-content:space-between;padding:.7rem 2rem;background:var(--tinta);color:#f5f0e6;
 font:400 .75rem/1 Montserrat,system-ui,sans-serif;z-index:9}
footer button{font:600 .72rem/1 Montserrat,system-ui,sans-serif;letter-spacing:.06em;
 text-transform:uppercase;background:#f5f0e6;color:var(--tinta);border:0;border-radius:999px;
 padding:.5rem .9rem;cursor:pointer}
@media(max-width:1100px){.wrap{grid-template-columns:1fr}aside{min-height:0}
 .col{border-right:0;border-bottom:1px solid var(--linha)}}
</style></head><body>
<header>
  <div class="marca">pandita · revisão</div>
  <h1>%(titulo)s</h1>
  <div class="meta">%(palavras)s palavras · %(n_alt)s trechos alterados · %(n_mud)s mudanças registradas</div>
</header>
<div class="ferramentas">
  <button class="chip on" data-filtro="tudo">Tudo</button>
  <button class="chip" data-filtro="pontuacao">Pontuação</button>
  <button class="chip" data-filtro="gramatica">Gramática</button>
  <button class="chip" data-filtro="ortografia">Ortografia</button>
  <button class="chip" data-filtro="fluidez">Fluidez</button>
  <button class="chip" data-filtro="genero">Gênero</button>
  <button class="chip" data-filtro="sanscrito">Sânscrito</button>
  <button class="chip" data-filtro="so-alt">Só alterações</button>
</div>
<div class="wrap">
  <section class="col"><h2>Original</h2><div id="col-o">%(corpo_o)s</div></section>
  <section class="col"><h2>Revisado</h2><div id="col-r">%(corpo_r)s</div></section>
  <aside>
    %(ia)s
    <section class="bloco">
      <h3>Mudanças <span class="nota">clique para localizar</span></h3>
      <div id="cards">%(cards)s</div>
    </section>
    <section class="bloco">
      <h3>Pendências <span class="nota">apontadas, não aplicadas</span></h3>
      <ul class="pend" id="pend">%(pend)s</ul>
    </section>
  </aside>
</div>
<footer>
  <span>Para aprovar, responda no chat: <b>aprovado</b></span>
  <button id="copiar">Copiar texto revisado</button>
</footer>
<script>
const chips=[...document.querySelectorAll('.chip')];
const cards=[...document.querySelectorAll('.card')];
const pars=[...document.querySelectorAll('.par')];
const marks=[...document.querySelectorAll('mark.chg')];
let filtro='tudo';
function aplica(){
  const soAlt=chips.find(c=>c.dataset.filtro==='so-alt')?.classList.contains('on');
  chips.forEach(c=>{if(c.dataset.filtro!=='so-alt')c.classList.toggle('on',c.dataset.filtro===filtro)});
  cards.forEach(c=>c.classList.toggle('oculto',filtro!=='tudo'&&c.dataset.cat!==filtro));
  marks.forEach(m=>m.style.outline='none');
  pars.forEach(p=>{
    const cats=(p.dataset.cats||'').split(',').filter(Boolean);
    const bate=filtro==='tudo'||cats.includes(filtro);
    p.classList.toggle('oculto', (soAlt&&!p.classList.contains('alt')) || !bate);
  });
  if(filtro!=='tudo') marks.filter(m=>m.dataset.cat===filtro).forEach(m=>m.style.outline='2px solid '+getComputedStyle(m).outlineColor);
}
chips.forEach(c=>c.onclick=()=>{if(c.dataset.filtro==='so-alt'){c.classList.toggle('on')}
 else{filtro=c.dataset.filtro} aplica();});
function flash(el){el.classList.add('flash');el.scrollIntoView({behavior:'smooth',block:'center'});
 setTimeout(()=>el.classList.remove('flash'),1600);}
cards.forEach((c,i)=>c.onclick=()=>{const regra=c.dataset.regra;
 const alvo=marks.find(m=>m.dataset.regra===regra)||marks[i]; if(alvo)flash(alvo);});
marks.forEach(m=>m.onclick=()=>{const r=m.dataset.regra;
 const card=cards.find(c=>c.dataset.regra===r); if(card){card.scrollIntoView({behavior:'smooth',block:'center'});
 card.style.outline='2px solid #b45309'; setTimeout(()=>card.style.outline='none',1600);}});
document.getElementById('copiar').onclick=async()=>{
 const t=[...document.querySelectorAll('#col-r .par')].map(p=>p.innerText.trim()).filter(Boolean).join('\\n\\n');
 try{await navigator.clipboard.writeText(t);document.getElementById('copiar').textContent='copiado';}
 catch(e){document.getElementById('copiar').textContent='selecione e copie';}};
</script></body></html>""" % {
        "titulo": esc(args.titulo or Path(args.revisada).stem),
        "palavras": len(palavras(revisado)),
        "n_alt": n_alt,
        "n_mud": len(mudancas),
        "corpo_o": corpo_o,
        "corpo_r": corpo_r,
        "ia": ia_html,
        "cards": "".join(cards) or '<p class="nota">Nenhuma mudança registrada.</p>',
        "pend": pend_html or '<li>Nenhuma pendência.</li>',
    }

    destino = Path(args.out)
    escrever(destino, html)
    print(f"painel: {destino} ({n_alt} trechos, {len(mudancas)} mudanças)")
    return 0


# ---------------------------------------------------------------- CLI

# ------------------------------------------------- retomar em outro computador

MODELO_CLAUDE = """# Revisões com a skill pandita

Esta pasta é compartilhada entre computadores. Ao abrir uma conversa aqui:

1. Se existir `revisoes/*/ESTADO.md`, leia e resuma em 3 linhas onde a revisão parou.
   Se houver mais de um documento, pergunte qual. Não refaça etapa que já está pronta.
2. Rode `python <pasta-da-skill>/scripts/pandita.py doctor`. Diga o que falta nesta máquina.
3. Se o Drive criou cópias de conflito de um arquivo, mostre as duas e pergunte qual vale.
4. A cada etapa concluída, grave o ponto de parada com o subcomando `estado`.
"""


def cmd_init(args) -> int:
    destino = Path(args.pasta) / "CLAUDE.md"
    if destino.exists():
        print(f"mantido: {destino}")
        return 0
    escrever(destino, MODELO_CLAUDE)
    print(f"criado: {destino}")
    return 0


def _lista(md: str, titulo: str) -> list[str]:
    m = re.search(rf"^## {titulo}\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    return [l[2:].strip() for l in (m.group(1).splitlines() if m else []) if l.startswith("- ")]


def cmd_estado(args) -> int:
    import socket
    from datetime import datetime
    pasta = Path(args.out)
    arq = pasta / "ESTADO.md"
    antigo = arq.read_text(encoding="utf-8") if arq.exists() else ""
    decisoes = _lista(antigo, "Decisões") + (args.decisao or [])
    pendencias = args.pendencia if args.pendencia else _lista(antigo, "Pendências")
    m = re.search(r"^- Etapa: (.*)$", antigo, re.M)
    etapa = args.etapa or (m.group(1) if m else "começando")
    arquivos = sorted(f.name for f in pasta.iterdir() if f.is_file() and f.name != "ESTADO.md") if pasta.exists() else []

    def bloco(itens: list[str]) -> str:
        return "\n".join(f"- {i}" for i in itens) or "- (nada)"

    md = (f"# Estado da revisão: {pasta.name}\n\n- Etapa: {etapa}\n"
          f"- Atualizado: {datetime.now():%Y-%m-%d %H:%M} em {socket.gethostname()}\n\n"
          f"## Decisões\n{bloco(decisoes)}\n\n## Pendências\n{bloco(pendencias)}\n\n"
          f"## Arquivos\n{bloco(arquivos)}\n")
    escrever(arq, md)
    print(f"estado gravado: {arq} (etapa: {etapa})")
    return 0


def cmd_doctor(args) -> int:
    ok = True
    def linha(bom: bool, msg: str, dica: str = "") -> None:
        nonlocal ok
        ok = ok and bom
        print(("ok     " if bom else "FALTA  ") + msg + ("" if bom or not dica else f"  -> {dica}"))
    linha(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}", "precisa de 3.9 ou mais")
    try:
        import docx  # noqa: F401
        linha(True, "python-docx")
    except ImportError:
        linha(False, "python-docx", "pip install python-docx (sem ele não lê nem gera .docx)")
    linha((raiz() / "glossario.csv").exists(), "glossario.csv")
    url = carregar_config().get("languagetool_url")
    if not url:
        print("aviso  languagetool_url não definido: a checagem gramatical objetiva fica de fora")
    else:
        try:
            urllib.request.urlopen(url.rstrip("/") + "/languages", timeout=3).read(1)
            linha(True, f"LanguageTool em {url}")
        except Exception:
            linha(False, f"LanguageTool em {url}", "suba com scripts/lt.ps1 -Acao start (ou lt.sh start)")
    print("tudo pronto." if ok else "resolva o que faltou antes de revisar.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="pandita", description="revisão editorial PT-BR + sânscrito")
    ap.add_argument("--version", action="version", version=f"pandita {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("extract"); p1.add_argument("arquivo"); p1.add_argument("--out", default=".")
    p2 = sub.add_parser("check"); p2.add_argument("texto"); p2.add_argument("--out", default=".")
    p2.add_argument("--glossario"); p2.add_argument("--lt")
    p2.add_argument("--idioma", help="padrão: o do config.json, ou pt-BR")
    p2.add_argument("--picky", action="store_true")
    p3 = sub.add_parser("apply"); p3.add_argument("texto"); p3.add_argument("achados")
    p3.add_argument("--out", default="."); p3.add_argument("--forcar", action="store_true")
    p4 = sub.add_parser("docx"); p4.add_argument("texto"); p4.add_argument("mudancas", nargs="?")
    p4.add_argument("--out", required=True); p4.add_argument("--original")
    p4.add_argument("--tracked", action="store_true"); p4.add_argument("--autor")
    p5 = sub.add_parser("diff"); p5.add_argument("original"); p5.add_argument("revisada")
    p5.add_argument("--out", default="diff.html")
    p6 = sub.add_parser("ia"); p6.add_argument("texto"); p6.add_argument("--out", default=".")
    p7 = sub.add_parser("painel")
    p7.add_argument("original"); p7.add_argument("revisada"); p7.add_argument("mudancas")
    p7.add_argument("--achados"); p7.add_argument("--ia"); p7.add_argument("--out", default="painel.html")
    p7.add_argument("--titulo")

    p8 = sub.add_parser("estado", help="grava o ponto de parada em ESTADO.md")
    p8.add_argument("--out", default="."); p8.add_argument("--etapa")
    p8.add_argument("--decisao", action="append"); p8.add_argument("--pendencia", action="append")
    p9 = sub.add_parser("doctor", help="confere o que falta neste computador")
    p10 = sub.add_parser("init", help="cria o CLAUDE.md na pasta de trabalho")
    p10.add_argument("pasta", nargs="?", default=".")

    args = ap.parse_args()
    try:
        return _despachar(args)
    except UnicodeDecodeError:
        print("erro: o arquivo não está em UTF-8. Salve como UTF-8 e rode de novo.", file=sys.stderr)
    except (OSError, json.JSONDecodeError) as e:
        print(f"erro: {e}", file=sys.stderr)
    return 2


def _despachar(args) -> int:
    if args.cmd == "extract":
        return cmd_extract(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "apply":
        return cmd_apply(args)
    if args.cmd == "docx":
        return cmd_docx(args)
    if args.cmd == "diff":
        return cmd_diff(args)
    if args.cmd == "ia":
        ia = cmd_ia(ler(Path(args.texto)))
        escrever(Path(args.out) / "indice-ia.json", json.dumps(ia, ensure_ascii=False, indent=2))
        print(f"índice de IA: {ia['score_documento']}/100")
        return 0
    if args.cmd == "painel":
        return cmd_painel(args)
    if args.cmd == "estado":
        return cmd_estado(args)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "init":
        return cmd_init(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
