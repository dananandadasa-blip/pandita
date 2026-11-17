"""Testes: python -m unittest discover -s tests

Só os de Word pedem python-docx; sem ele, são pulados.
"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pandita  # noqa: E402

TEM_DOCX = importlib.util.find_spec("docx") is not None
GLOSS = [{"termo": "Kṛṣṇa", "variantes": ["Krishna"], "categoria": "nome", "fonte": "teste"}]


def calado(fn, *args):
    """Roda sem sujar a saída do teste; devolve (retorno, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn(*args)
    return rc, out.getvalue(), err.getvalue()


class TestSanscrito(unittest.TestCase):
    def test_detecta_nfd(self):
        texto = "O mantra ātman está aqui"  # ā pré-composto
        self.assertTrue(pandita.cmd_sanscrito(texto, []) == [])
        nfd = "ātman"
        achados = pandita.cmd_sanscrito(f"O mantra {nfd} está aqui", [])
        self.assertIn("IAST-NFC", [a["regra"] for a in achados])

    def test_variante_vira_termo(self):
        achados = pandita.cmd_sanscrito("Hare Krishna.", GLOSS)
        self.assertEqual(len(achados), 1)
        self.assertEqual(achados[0]["depois"], "Kṛṣṇa")

    def test_termo_correto_nao_gera_achado(self):
        self.assertEqual(pandita.cmd_sanscrito("Hare Kṛṣṇa.", GLOSS), [])

    def test_variante_nao_casa_dentro_de_outra_palavra(self):
        self.assertEqual(pandita.cmd_sanscrito("Krishnamurti escreveu.", GLOSS), [])

    def test_citacao_direta_fica_como_esta(self):
        self.assertEqual(pandita.cmd_sanscrito("Ele disse: “Krishna é tudo”.", GLOSS), [])

    def test_aspa_sem_fecho_nao_esconde_o_resto(self):
        texto = "“Krishna disse algo\n\nDepois Krishna saiu, e ela falou: “fim”."
        self.assertEqual(len(pandita.cmd_sanscrito(texto, GLOSS)), 2)

    def test_plural_do_glossario_continua_plural(self):
        gloss = pandita.carregar_glossario(RAIZ / "glossario.csv")
        achados = pandita.cmd_sanscrito("Os Pandavas e os Kauravas lutaram.", gloss)
        self.assertEqual([(a["antes"], a["depois"]) for a in achados], [("Pandavas", "Pāṇḍavas")])


class TestApply(unittest.TestCase):
    def _ns(self, tmp, forcar=False):
        return types.SimpleNamespace(
            texto=str(tmp / "texto.txt"),
            achados=str(tmp / "achados.json"),
            out=str(tmp),
            forcar=forcar,
        )

    def _roda(self, texto, achados, forcar=False):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "texto.txt").write_text(texto, encoding="utf-8")
            (tmp / "achados.json").write_text(json.dumps(achados), encoding="utf-8")
            calado(pandita.cmd_apply, self._ns(tmp, forcar))
            conflitos = tmp / "conflitos.json"
            return ((tmp / "revisada.txt").read_text(encoding="utf-8"),
                    json.loads(conflitos.read_text(encoding="utf-8")) if conflitos.exists() else [])

    def _achado(self, antes, depois):
        return {"regra": "X", "antes": antes, "depois": depois,
                "categoria": "ortografia", "severidade": "alta", "motivo": "m"}

    def test_aplica_unico(self):
        revisada, _ = self._roda("um erro aqui", [self._achado("erro", "acerto")])
        self.assertEqual(revisada, "um acerto aqui")

    def test_repeticao_legitima_aplica_todas(self):
        revisada, _ = self._roda("Krishna e Krishna.", [self._achado("Krishna", "Kṛṣṇa")] * 2)
        self.assertEqual(revisada, "Kṛṣṇa e Kṛṣṇa.")

    def test_ambiguo_nao_aplica(self):
        revisada, conflitos = self._roda("erro erro", [self._achado("erro", "acerto")])
        self.assertEqual(revisada, "erro erro")
        self.assertEqual(len(conflitos), 1)

    def test_forcar_aplica_o_primeiro_ambiguo(self):
        revisada, _ = self._roda("erro erro", [self._achado("erro", "acerto")], forcar=True)
        self.assertEqual(revisada, "acerto erro")

    def test_nao_encontrado_vira_conflito(self):
        revisada, conflitos = self._roda("nada aqui", [self._achado("ausente", "x")])
        self.assertEqual(revisada, "nada aqui")
        self.assertEqual(conflitos[0]["motivo_conflito"], "trecho não encontrado")

    def test_achado_repetido_nao_troca_dentro_de_outra_palavra(self):
        # dois especialistas apontam o mesmo Krishna: Krishnamurti não pode pagar por isso
        revisada, conflitos = self._roda("Krishna falou. Krishnamurti escreveu.",
                                         [self._achado("Krishna", "Kṛṣṇa")] * 2)
        self.assertEqual(revisada, "Kṛṣṇa falou. Krishnamurti escreveu.")
        self.assertEqual(conflitos, [])

    def test_nfd_do_check_vira_nfc_sem_duplicar_letra(self):
        nfd = ("O ātman é eterno e não morre quando o corpo morre, diz o verso "
               "que todos conhecem bem, e assim segue a vida do sábio.")
        revisada, conflitos = self._roda(nfd, pandita.cmd_sanscrito(nfd, []))
        self.assertEqual(revisada, unicodedata.normalize("NFC", nfd))
        self.assertEqual(conflitos, [])

    def test_aviso_sem_troca_nao_vira_conflito(self):
        texto = "ahiṁsā e saṃsāra."
        achados = pandita.cmd_sanscrito(texto, [])
        self.assertEqual([a["regra"] for a in achados], ["IAST-ANUSVARA"])
        self.assertEqual(self._roda(texto, achados), (texto, []))


class TestIndiceIA(unittest.TestCase):
    LIMPO = ("A casa ficava no fim da rua. O menino corria atrás do cachorro. "
             "Dona Zulmira regava as plantas todas as manhãs, sem pressa.")
    CARREGADO = ("É importante ressaltar que, no cenário atual, a jornada transformadora "
                 "é fundamental para o ecossistema. Em suma, não é uma questão de ferramenta, "
                 "é uma questão de mentalidade robusta e holística.")

    def test_carregado_pontua_mais(self):
        limpo = pandita.cmd_ia(self.LIMPO)["score_documento"]
        carregado = pandita.cmd_ia(self.CARREGADO)["score_documento"]
        self.assertGreater(carregado, limpo)

    def test_estrutura(self):
        r = pandita.cmd_ia(self.LIMPO)
        self.assertIn("score_documento", r)
        self.assertEqual(len(r["paragrafos"]), 1)

    def test_paragrafo_curto_nao_pontua(self):
        r = pandita.cmd_ia("É importante ressaltar.")
        self.assertEqual(r["paragrafos"][0]["score"], 0)


class TestDestaques(unittest.TestCase):
    def test_marca_trecho_alterado(self):
        mapa = pandita._destaques("Krishna disse.", "Kṛṣṇa disse.")
        self.assertTrue(any(destacar for _, destacar in mapa[0]))

    def test_paragrafo_igual_nao_destaca(self):
        mapa = pandita._destaques("Frase igual.", "Frase igual.")
        self.assertFalse(any(destacar for _, destacar in mapa[0]))

    def test_paragrafo_novo_destaca_tudo(self):
        mapa = pandita._destaques("Um.", "Um.\n\nDois.")
        self.assertEqual(mapa[1], [("Dois.", True)])


class TestFiltrosLanguageTool(unittest.TestCase):
    def test_diacritico_sanscrito(self):
        self.assertTrue(pandita._parece_sanscrito("Kṛṣṇa", [], set()))

    def test_variante_do_glossario(self):
        self.assertTrue(pandita._parece_sanscrito("Krishna", GLOSS, set()))

    def test_palavra_comum(self):
        self.assertFalse(pandita._parece_sanscrito("casa", GLOSS, set()))


class TestCheck(unittest.TestCase):
    def _check(self, tmp, texto, lt):
        (tmp / "texto.txt").write_text(texto, encoding="utf-8")
        ns = types.SimpleNamespace(texto=str(tmp / "texto.txt"), out=str(tmp), glossario=None,
                                   lt=lt, idioma=None, picky=False)
        rc, out, err = calado(pandita.cmd_check, ns)
        return rc, out, err, (tmp / "achados.md").read_text(encoding="utf-8")

    def test_languagetool_fora_do_ar_nao_derruba_e_avisa_no_relatorio(self):
        with tempfile.TemporaryDirectory() as d:
            # porta 9 (discard): nada escuta, a conexão é recusada na hora
            rc, out, err, md = self._check(Path(d), "Um texto simples.", "http://127.0.0.1:9/v2")
            self.assertEqual(rc, 0)
            self.assertIn("LanguageTool: fora do ar", out)
            self.assertIn("[aviso]", err)
            self.assertIn("LanguageTool fora do ar: a gramática objetiva não foi checada", md)

    def test_languagetool_no_ar_filtra_sanscrito_e_guarda_gramatica(self):
        texto = "Kṛṣṇa disse que nós vai."
        resposta = {"matches": [
            {"offset": 0, "length": 5, "message": "erro de grafia", "replacements": [{"value": "Crina"}],
             "rule": {"id": "MORFOLOGIK", "issueType": "misspelling"}},
            {"offset": 16, "length": 7, "message": "concordância", "replacements": [{"value": "nós vamos"}],
             "rule": {"id": "CONCORDANCIA", "issueType": "grammar"}},
        ]}
        falso = mock.MagicMock()
        falso.__enter__.return_value.read.return_value = json.dumps(resposta).encode("utf-8")
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen", return_value=falso):
            rc, out, _, md = self._check(Path(d), texto, "http://localhost:8081/v2")
            achados = json.loads((Path(d) / "achados.json").read_text(encoding="utf-8"))
        self.assertIn("LanguageTool: consultado", out)
        self.assertNotIn("não foi checada", md)
        self.assertEqual([(a["regra"], a["antes"]) for a in achados], [("LT:CONCORDANCIA", "nós vai")])

    def test_languagetool_so_aceita_http(self):
        # file:// leria um arquivo local no lugar do servidor
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen") as abre:
            rc, out, err, md = self._check(Path(d), "Um texto simples.", "file:///tmp/qualquer.txt")
        abre.assert_not_called()
        self.assertEqual(rc, 0)
        self.assertIn("http", err)
        self.assertIn("não foi checada", md)


class TestExtract(unittest.TestCase):
    def test_markdown_vira_texto_puro(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "a.md").write_text("# Título\n\nUm **forte** e um *leve*.\n", encoding="utf-8")
            ns = types.SimpleNamespace(arquivo=str(tmp / "a.md"), out=str(tmp / "saida"))
            self.assertEqual(calado(pandita.cmd_extract, ns)[0], 0)
            self.assertEqual((tmp / "saida" / "texto.txt").read_text(encoding="utf-8"),
                             "Título\n\nUm forte e um leve.\n")

    def test_nao_sobrescreve_a_propria_origem(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "texto.txt").write_text("Um *itálico* aqui.\n", encoding="utf-8")
            ns = types.SimpleNamespace(arquivo=str(tmp / "texto.txt"), out=str(tmp))
            self.assertEqual(calado(pandita.cmd_extract, ns)[0], 2)
            self.assertEqual((tmp / "texto.txt").read_text(encoding="utf-8"), "Um *itálico* aqui.\n")


class TestLinhaDeComando(unittest.TestCase):
    def test_arquivo_inexistente_da_mensagem_e_codigo_2(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(sys, "argv", ["pandita", "check", str(Path(d) / "sumiu.txt"), "--out", d]):
            rc, _, err = calado(pandita.main)
        self.assertEqual(rc, 2)
        self.assertTrue(err.startswith("erro:"))

    def test_tracked_sem_original_e_recusado(self):
        ns = types.SimpleNamespace(texto="r.txt", mudancas=None, original=None,
                                   tracked=True, autor=None, out="t.docx")
        rc, _, err = calado(pandita.cmd_docx, ns)
        self.assertEqual(rc, 2)
        self.assertIn("--original", err)


@unittest.skipUnless(TEM_DOCX, "python-docx não instalado")
class TestMarcasDeRevisao(unittest.TestCase):
    def _tracked(self, original, revisado):
        import docx

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "o.txt").write_text(original, encoding="utf-8")
            (tmp / "r.txt").write_text(revisado, encoding="utf-8")
            ns = types.SimpleNamespace(
                texto=str(tmp / "r.txt"), mudancas=None, original=str(tmp / "o.txt"),
                tracked=True, autor="teste", out=str(tmp / "t.docx"),
            )
            calado(pandita.cmd_docx, ns)
            return docx.Document(str(tmp / "t.docx")).element.body

    def test_gera_ins_e_del(self):
        from docx.oxml.ns import qn

        body = self._tracked("Krishna disse.", "Kṛṣṇa falou.")
        ins, dele = body.findall(".//" + qn("w:ins")), body.findall(".//" + qn("w:del"))
        self.assertTrue(ins)
        self.assertTrue(dele)
        self.assertEqual(ins[0].get(qn("w:author")), "teste")
        self.assertEqual("".join(t.text for t in body.iter(qn("w:delText"))).strip(), "Krishna disse.")

    def test_paragrafo_novo_e_paragrafo_removido(self):
        from docx.oxml.ns import qn

        body = self._tracked("Fica.\n\nSai inteiro.", "Fica.\n\nEntra um.\n\nEntra outro.")
        self.assertEqual(len(body.findall(".//" + qn("w:ins"))), 2)
        self.assertEqual(len(body.findall(".//" + qn("w:del"))), 1)

    def test_quebra_de_linha_do_verso_sobrevive(self):
        from docx.oxml.ns import qn

        body = self._tracked("Krishna disse.\nSegunda linha.", "Kṛṣṇa disse.\nSegunda linha.")
        self.assertTrue(body.findall(".//" + qn("w:br")))


class TestPainel(unittest.TestCase):
    def _painel(self, original, revisado, mudancas):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "o.txt").write_text(original, encoding="utf-8")
            (tmp / "r.txt").write_text(revisado, encoding="utf-8")
            (tmp / "m.json").write_text(json.dumps(mudancas), encoding="utf-8")
            ns = types.SimpleNamespace(
                original=str(tmp / "o.txt"), revisada=str(tmp / "r.txt"),
                mudancas=str(tmp / "m.json"), achados=None, ia=None,
                out=str(tmp / "painel.html"), titulo="Teste",
            )
            _, out, _ = calado(pandita.cmd_painel, ns)
            return (tmp / "painel.html").read_text(encoding="utf-8"), out

    def test_gera_marcas(self):
        html, _ = self._painel("Krishna disse isso.", "Kṛṣṇa disse isso.", [{
            "regra": "IAST", "antes": "Krishna", "depois": "Kṛṣṇa",
            "categoria": "sanscrito", "severidade": "alta", "motivo": "m",
        }])
        self.assertIn('<mark class="chg" data-cat="sanscrito"', html)
        self.assertIn("Kṛṣṇa", html)

    def test_remocao_pura_e_troca_sem_registro_contam_como_alteracao(self):
        html, out = self._painel("Um combo de ideias.\n\nKrishna disse.\n\nFica igual.",
                                 "Um de ideias.\n\nKṛṣṇa falou.\n\nFica igual.", [])
        self.assertIn("(2 trechos", out)
        # cada parágrafo alterado aparece nas duas colunas; o igual, em nenhuma
        self.assertEqual(html.count('class="par alt"'), 4)
        self.assertIn('<del class="del">combo </del>', html)

    def test_escapa_html_do_texto(self):
        html, _ = self._painel("a <script>alert(1)</script>", "b <script>alert(1)</script>", [])
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("&lt;script&gt;alert(1)", html)

    def test_escapa_categoria_e_severidade_vindas_do_json(self):
        # mudancas.json é escrito por agente: categoria e severidade também são dado não confiável
        html, _ = self._painel("Krishna disse.", "Kṛṣṇa disse.", [{
            "regra": "X", "antes": "Krishna", "depois": "Kṛṣṇa",
            "categoria": '"><img src=x onerror=alert(1)>', "severidade": "<b>alta</b>", "motivo": "m",
        }])
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("<b>alta</b>", html)


class TestDiff(unittest.TestCase):
    def test_escapa_html_do_texto(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "a.txt").write_text("um <b>forte</b> & pronto", encoding="utf-8")
            (tmp / "b.txt").write_text("um <b>forte</b> & pronto, fim", encoding="utf-8")
            ns = types.SimpleNamespace(original=str(tmp / "a.txt"), revisada=str(tmp / "b.txt"),
                                       out=str(tmp / "diff.html"))
            calado(pandita.cmd_diff, ns)
            html = (tmp / "diff.html").read_text(encoding="utf-8")
        self.assertNotIn("<b>forte</b>", html)
        self.assertIn("&lt;b&gt;forte&lt;/b&gt;", html)
        self.assertIn("<ins>", html)


class TestRetomada(unittest.TestCase):
    def test_estado_acumula_decisoes_e_troca_pendencias(self):
        with tempfile.TemporaryDirectory() as d:
            calado(pandita.cmd_estado, types.SimpleNamespace(out=d, etapa="mecânica", decisao=["A"], pendencia=["p1"]))
            calado(pandita.cmd_estado, types.SimpleNamespace(out=d, etapa=None, decisao=["B"], pendencia=None))
            md = (Path(d) / "ESTADO.md").read_text(encoding="utf-8")
            self.assertIn("Etapa: mecânica", md)
            self.assertIn("- A", md); self.assertIn("- B", md); self.assertIn("- p1", md)

    def test_init_nao_sobrescreve(self):
        with tempfile.TemporaryDirectory() as d:
            calado(pandita.cmd_init, types.SimpleNamespace(pasta=d))
            (Path(d) / "CLAUDE.md").write_text("meu", encoding="utf-8")
            calado(pandita.cmd_init, types.SimpleNamespace(pasta=d))
            self.assertEqual((Path(d) / "CLAUDE.md").read_text(encoding="utf-8"), "meu")


if __name__ == "__main__":
    unittest.main()
