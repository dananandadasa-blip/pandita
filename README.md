# pandita

Revisão editorial para **português brasileiro** e **sânscrito**, empacotada como skill para agentes de IA.

O nome vem de *paṇḍita*, o mestre erudito. A ideia é essa: um revisor que não só corrige, mas explica a regra e mostra o antes e o depois.

```
/pandita revisa este documento.docx
```

## O que ela faz

- **Quatro especialistas** trabalham em paralelo: norma e gramática, pontuação e travessão, fluidez e gênero, sânscrito e tipografia.
- **Um editor aplica** todas as correções de uma vez, para o texto não virar colcha de retalhos.
- **Segunda revisão** confere se cada mudança se justifica e se nada quebrou.
- **Painel comparativo** em HTML: original e revisado lado a lado, mudanças coloridas por categoria, clicáveis.
- **Sânscrito**: IAST, diacríticos, glossário da casa e regras de tipografia BBT (itálico, maiúscula, citação de verso).
- **Índice de marcas de IA** por parágrafo — heurístico e rotulado como tal, não um detector.
- **Word** com as mudanças destacadas, gerado só depois da aprovação.
- **Marcas de revisão** opcionais (`--tracked`): o Word abre com inserções e remoções registradas.

O caminho de um texto, do envio ao Word, numa página só: [`mapa/pandita-mapa.html`](mapa/pandita-mapa.html).

## Instalação

Requisitos: **Python 3.9+**. Para ler e gerar `.docx`, também `python-docx`:

```bash
pip install python-docx
```

### Claude Code

```bash
git clone https://github.com/dananandadasa-blip/pandita.git ~/.claude/skills/pandita
```

Ou, no projeto: `git clone … .claude/skills/pandita`.

### DeepSeek Harness (DSH)

```bash
git clone https://github.com/dananandadasa-blip/pandita.git .dsh/skills/pandita
```

### Outros agentes

Qualquer agente que leia o padrão de skills (`SKILL.md` com `name` e `description`) funciona. Copie a pasta para o diretório de skills do agente.

### Instalador simples

```bash
./install.sh                 # instala em ~/.claude/skills/pandita
./install.sh ~/meu/agente    # ou onde você quiser
```

No Windows: `powershell -ExecutionPolicy Bypass -File .\install.ps1 -Destino "$HOME\.claude\skills\pandita"`. O `-ExecutionPolicy Bypass` vale só para esse comando; sem ele, o Windows costuma recusar scripts baixados. O mesmo vale para `pandita.ps1` e `scripts\lt.ps1`.

Rodar de novo atualiza a skill. O que é da casa (`PADRAO.md`, `glossario.csv`, `config.json`, `ignorar.txt`) fica como você deixou.

Se não houver `python` no PATH (Windows), use o atalho: `.\pandita.ps1 check texto.txt`.

## Como usar

| Você diz | O que acontece |
|---|---|
| `/pandita` + arquivo | revisão completa, com painel |
| `/pandita rápido` | checagem mecânica + um especialista |
| `/pandita só sânscrito` | IAST, glossário e tipografia BBT |
| `/pandita compara` | duas versões suas, aponta o que mudou |
| `/pandita aprovo` | gera o `.docx` com destaques |
| `/pandita retomar` | continua uma revisão iniciada em outro computador |

Sem o comando, também funciona: "revisa este texto", "dá uma passada nesse capítulo".

### Linha de comando

```bash
python3 scripts/pandita.py extract documento.docx --out revisoes/doc
python3 scripts/pandita.py check revisoes/doc/texto.txt --out revisoes/doc
python3 scripts/pandita.py apply revisoes/doc/texto.txt achados.json --out revisoes/doc
python3 scripts/pandita.py painel texto.txt revisada.txt mudancas.json --out painel.html
python3 scripts/pandita.py docx revisada.txt mudancas.json --out revisado.docx
python3 scripts/pandita.py docx revisada.txt mudancas.json --original texto.txt --tracked --out revisado.docx
python3 scripts/pandita.py ia texto.txt
python3 scripts/pandita.py estado --out revisoes/doc --etapa "aplicada"
python3 scripts/pandita.py doctor
python3 scripts/pandita.py init .
python3 scripts/pandita.py diff original.txt revisada.txt --out diff.html
```

`check` usa o `glossario.csv` da própria skill por padrão. Com um LanguageTool local, acrescente `--lt http://localhost:8081/v2`.

## Trabalhar em dois computadores

Use a mesma pasta do Drive nos dois, mesmo que o caminho seja diferente. Em cada computador, instale a skill e o LanguageTool uma vez. A skill grava o `ESTADO.md` a cada etapa; ao abrir o Claude Code na pasta, o `CLAUDE.md` (criado por `python scripts/pandita.py init`) manda ler esse estado e rodar `doctor`. Espere o Drive terminar de sincronizar antes de trocar, e não edite o mesmo arquivo nos dois ao mesmo tempo.

## LanguageTool local (opcional, recomendado)

Sem ele, a camada gramatical objetiva fica de fora — e o relatório diz isso.

1. Baixe `LanguageTool-stable.zip` (~240 MB) em <https://languagetool.org/download/>.
2. Extraia em `%LOCALAPPDATA%\pandita\languagetool` (Windows) ou `~/.pandita/languagetool` (macOS/Linux).
3. Suba o servidor: `powershell -ExecutionPolicy Bypass -File .\scripts\lt.ps1 -Acao start` ou `./scripts/lt.sh start`.
4. O `config.json` já aponta para `http://localhost:8081/v2`; o `check` usa sozinho.

Precisa de Java 17+. O `stop` e o `status` são o mesmo script.

## Estrutura

```
SKILL.md              o comando e o fluxo
PADRAO.md             o manual da casa (editável)
glossario.csv         termos sânscritos e variantes erradas
ignorar.txt           nomes que o corretor de português não conhece
config.json           idioma, transliteração e URL do LanguageTool
referencias/
  pt-br/norma.md      gramática, pontuação, acentuação
  pt-br/generos.md    gênero e registro
  sanscrito/tipografia-bbt.md
  indice-ia.md        como o índice é calculado
scripts/pandita.py    extrair, checar, aplicar, painel, diff, docx
scripts/lt.ps1        sobe/derruba o LanguageTool (Windows)
scripts/lt.sh         sobe/derruba o LanguageTool (macOS/Linux)
install.sh            instalador (macOS/Linux)
install.ps1           instalador (Windows)
examples/             amostra e achados de exemplo
mapa/                 o mapa do fluxo (HTML, SVG e DESIGN.md); não é instalado
tests/                testes; os de Word pedem python-docx e são pulados sem ele
```

## Adaptar para outro idioma

O idioma mora em `referencias/<idioma>/`. Crie `norma.md` e `generos.md` para a língua, ajuste o glossário e troque o `idioma` no `config.json`. O fluxo continua o mesmo. Ainda ficam em português: os padrões do índice de IA, os rótulos do painel e as mensagens do script.

## Limites, sem enfeite

- PDF não entra, escaneado ou não. DOCX, MD e TXT entram.
- O índice de IA é heurístico e precisa de calibração com corpus real. Ele não prova autoria.
- Sem um LanguageTool local, a checagem gramatical objetiva fica de fora — e o relatório diz isso.
- O `.docx` sai como texto corrido, com destaque ou com marcas de revisão. Itálico, títulos, tabelas e notas de rodapé do original não voltam.
- Nada sai da sua máquina enquanto o `languagetool_url` do `config.json` apontar para `localhost`. Se você trocar por um servidor de fora, o texto vai para lá.

## Créditos

- Regras de tipografia BBT resumidas do *BBT Style Guide* (2016), documento público. Este projeto não tem vínculo com a BBT.
- [LanguageTool](https://languagetool.org) é opcional e roda local.
- Estrutura de skill no padrão aberto do [Agent Skills](https://github.com/anthropics/skills).

## Licença

MIT. Use, adapte, publique. Se melhorar, mande de volta.

---

### English

*Pandita* is an editorial revision skill for **Brazilian Portuguese** and **Sanskrit**. It runs four specialist passes, consolidates them into one edit, verifies the result, and produces a side-by-side HTML panel plus a highlighted Word file. Install by cloning into your agent's skills directory (`~/.claude/skills/pandita`, `.dsh/skills/pandita`, or any `SKILL.md`-aware agent). Python 3.9+; `python-docx` for `.docx`. MIT.
