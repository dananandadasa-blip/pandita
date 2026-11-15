---
name: Mapas de skills
description: Páginas-explicação das skills do workspace, desenhadas como uma folha de caderno pautada com margem verde.
colors:
  verde: "#2f5d3a"
  verde-claro: "#dce8d8"
  ocre: "#87581f"
  risco-tinta: "#8a3b2a"
  risco: "#f1ddd2"
  tinta: "#1f2a22"
  suave: "#4e5a4f"
  papel: "#f3ecdd"
  folha: "#fbf7ee"
  pauta: "#d9e2d3"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "clamp(2.4rem, 5.2vw, 4.6rem)"
    fontWeight: 600
    lineHeight: 1.04
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  lesson-hero:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "clamp(1.25rem, 2.5vw, 2.25rem)"
    fontWeight: 400
    lineHeight: 1.6
  lesson:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: "2rem"
  title:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  note:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.35
  lead:
    fontFamily: "Montserrat, system-ui, Segoe UI, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Montserrat, system-ui, Segoe UI, Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Montserrat, system-ui, Segoe UI, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.5
  code:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.3
rounded:
  none: "0"
  focus: "2px"
  circle: "50%"
spacing:
  margem: "13rem"
  margem-tablet: "4.5rem"
  margem-mobile: "2.25rem"
  arquivo: "13rem"
  recuo-texto: "clamp(2.5rem, 5vw, 4.5rem)"
  respiro-direito: "clamp(1.5rem, 4vw, 4rem)"
  estacao: "clamp(2.5rem, 5vw, 4rem)"
  secao: "clamp(3rem, 6vw, 5rem)"
  folha-max: "84rem"
components:
  station-node:
    backgroundColor: "{colors.verde}"
    textColor: "{colors.folha}"
    typography: "{typography.title}"
    rounded: "{rounded.circle}"
    size: "2.75rem"
  station-node-idle:
    backgroundColor: "{colors.folha}"
    textColor: "{colors.verde}"
    rounded: "{rounded.circle}"
    size: "2.75rem"
  file-chip:
    backgroundColor: "{colors.verde-claro}"
    textColor: "{colors.tinta}"
    typography: "{typography.code}"
    rounded: "{rounded.none}"
    padding: ".35rem .65rem"
  lesson-line:
    textColor: "{colors.tinta}"
    typography: "{typography.lesson}"
    width: "40rem"
  insertion:
    backgroundColor: "{colors.verde-claro}"
    textColor: "{colors.tinta}"
  deletion:
    backgroundColor: "{colors.risco}"
    textColor: "{colors.risco-tinta}"
  margin-note:
    textColor: "{colors.verde}"
    typography: "{typography.note}"
  toc-link:
    textColor: "{colors.suave}"
    typography: "{typography.label}"
  toc-link-hover:
    textColor: "{colors.verde}"
  skip-link:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.folha}"
    padding: ".5rem .8rem"
---

# Design System: Mapas de skills

## Overview

**Creative North Star: "O Caderno de Lição"**

Cada mapa é uma folha de caderno escolar. O texto que a skill trata é a lição, escrita em serifa sobre pauta fina. Quem encontra um problema escreve na margem; só um editor escreve no texto. A margem esquerda tem uma linha verde, no lugar onde o professor usaria vermelho, e essa linha é o eixo do mapa: ela desce com a leitura e acende cada estação quando chega nela.

A página é calma e legível, de densidade média: uma coluna de margem, uma coluna de texto e, no desktop, uma coluna estreita à direita que diz qual arquivo cada passo deixa. Não há cartões, sombras nem gradientes. A profundidade vem só de dois tons de papel (o fundo e a folha) e da pauta. A cor é quase toda verde; o ocre aparece só no visto e o vermelho só no que sai do texto.

O tom é de aula para criança: frases curtas, uma ideia por linha, exemplo real em vez de diagrama abstrato.

**Key Characteristics:**
- Folha clara sobre papel mais quente, sem sombra.
- Linha de margem verde como trilho, com nós numerados em círculo.
- Texto de lição em serifa com pauta de 1px; explicação em sans.
- Marcas dos professores distintas pela forma (sublinhado duplo, pontilhado, círculo), não pela cor.
- Cada estação nomeia o arquivo que deixa, num rótulo de código chapado.

## Colors

Paleta de caderno: papel quente, tinta verde-escura, uma única cor de estrutura (verde botânico) e dois acentos semânticos raros.

### Primary
- **Verde Botânico** (verde): a cor da margem e da estrutura. Trilho da margem, nós das estações, marcas e notas dos professores, links, foco, marcador das listas, números de destaque, seleção de texto.

### Secondary
- **Ocre de Visto** (ocre): só o sinal de visto do revisor. Escurecido para manter 4.5:1 sobre a folha.

### Tertiary
- **Risco Vermelho** (risco-tinta sobre risco): só para trechos apagados, com traço de corte #c48b78. Repete a convenção do painel.html do produto, onde remoção é vermelha.

### Neutral
- **Papel** (papel): fundo da janela, em volta da folha.
- **Folha** (folha): a superfície da página; também o texto sobre o verde.
- **Tinta** (tinta): todo o texto principal e os títulos.
- **Tinta Suave** (suave): rótulos, sumário, legendas, rodapé.
- **Pauta** (pauta): só as linhas de 1px sob o texto da lição. Não vira fio divisor de seção.
- **Verde-claro** (verde-claro): fundo do que entra no texto e do rótulo de arquivo.

### Named Rules
**The Margin Green Rule.** O verde é a única cor de estrutura. Tudo que é margem, caminho, marca ou ação é verde; nada estrutural ganha outra cor.

**The Rare Accent Rule.** O ocre existe só para o visto e o vermelho só para o que sai do texto. Nenhum dos dois decora.

## Typography

**Display Font:** Source Serif 4 (com Georgia, Times New Roman)
**Body Font:** Montserrat (com system-ui, Segoe UI, Arial)
**Label/Mono Font:** ui-monospace, Cascadia Mono, Consolas, só para nomes de arquivo e comandos

**Character:** A serifa é a voz da lição e dos títulos, a letra do caderno. A sans é a voz de quem explica, ao lado.

### Hierarchy
- **Display** (600, clamp 2.4–4.6rem, 1.04): o h1 da página, no máximo 18ch, balanceado.
- **Headline** (600, clamp 1.6–2.25rem, 1.15): título de cada estação e de cada seção final.
- **Lesson hero** (400, clamp 1.25–2.25rem, 1.6): a frase de amostra na abertura, sobre pauta.
- **Lesson** (400, 1.25rem, entrelinha 2rem): as linhas da lição dentro das estações; a pauta tem o mesmo passo de 2rem. Cai para 1.0625rem em colunas duplas e no celular.
- **Title** (600, 1.25rem): números da medição, papéis em "Quem faz o quê", número dentro do nó.
- **Note** (itálico 400, 1rem, 1.35): notas na margem, em verde.
- **Lead** (400, 1.25rem, 1.6): o parágrafo de abertura, até 42rem.
- **Body** (400, 1.0625rem, 1.7; 1rem no celular): explicação, até 36rem.
- **Label** (500–600, 0.8125rem): sumário, rótulos curtos da lição ("antes", "depois"), legendas. Caixa normal, sem caixa alta.

### Named Rules
**The Two Voices Rule.** Serifa é o texto tratado e os títulos; sans é a explicação. Um trecho do texto do usuário nunca aparece em sans.

**The Mark Shape Rule.** Cada professor marca com uma forma própria: sublinhado duplo (sânscrito), sublinhado pontilhado de 2px (fluidez), círculo de 1.5px (pontuação). A forma identifica; a cor é sempre o verde.

## Layout

Grade de três colunas dentro da folha: margem (margem), texto (1fr) e arquivo (arquivo). A folha tem largura máxima de folha-max, centralizada, com respiro de clamp(0, 3vw, 2.5rem) em volta. A linha da margem fica na divisa entre a primeira e a segunda coluna: um fio de 2px a 22% de opacidade na folha toda, e o trilho de 4px que desce sobre ele no caminho.

O texto começa recuado da margem (recuo-texto) e respira à direita (respiro-direito). Estações têm bloco vertical de estacao. Linhas de leitura: corpo 36rem, lição 40rem, lead 42rem.

Na abertura, a margem leva o sumário numerado e a folha leva o h1, o lead, a frase de amostra e o princípio em uma linha. As notas dos professores ocupam a coluna da margem, alinhadas à direita, ao lado da linha que comentam.

**Responsivo.** Até 68rem: a margem cai para margem-tablet, a coluna de arquivo some e o rótulo de arquivo desce para baixo do texto; o sumário vai para baixo do h1 em duas colunas; as notas passam para baixo da lição, alinhadas à esquerda. Até 34rem: margem-mobile, folha sem respiro externo, sumário em uma coluna, colunas duplas empilhadas, nós menores (2.1rem).

### Named Rules
**The Margin Holds Comment Rule.** Comentário mora na margem; a coluna do texto só recebe a lição e a troca já aplicada.

## Elevation & Depth

Plano por princípio. Não há sombra nem gradiente. A profundidade é tonal: a folha (folha) sobre o papel (papel) e a pauta de 1px sob a lição. As seções finais se separam só por espaço (o padding-block da seção anterior; a seguinte zera o topo), sem fio. O único volume é o trilho verde, mais grosso que o fio da margem.

### Named Rules
**The Ruled Sheet Rule.** Pauta é só para a lição. Se algo precisa se separar, use espaço, recuo ou tom de papel. Nunca sombra, nunca cartão, nunca fio divisor.

## Shapes

Cantos retos em tudo: folha, rótulos de arquivo, realces de inserção e de corte. Os únicos círculos são o nó da estação (50%) e a marca de pontuação. O anel de foco tem 2px de raio. Linhas são finas: 1px na pauta, 2px na linha da margem, 4px no trilho, 2px na borda do nó.

## Components

### Nó da estação
Círculo verde de 2.75rem com o número em serifa 600 na cor folha, borda de 2px verde, centrado sobre a linha da margem. Com JS e movimento permitido, começa vazio (folha, número verde) e se enche de verde quando o trilho chega nele (transição de 0.5s, cubic-bezier(.16,1,.3,1)).

### Trilho da margem
Barra verde de 4px na divisa da margem, crescendo de cima para baixo com a rolagem (scaleY) até 55% da altura da tela. Sem JS ou com movimento reduzido, nasce inteira.

### Linha da lição
Texto em serifa 400 sobre pauta de 1px no passo da entrelinha. Pode ter rótulo em sans 600 0.8125rem (tinta suave) logo acima. Ao acender a estação, sobe 1.25rem e vai de 25% a 100% de opacidade em 0.9s; a segunda linha atrasa 0.15s.

### Inserção e corte
Inserção: fundo verde-claro, sem sublinhado. Corte: texto risco-tinta riscado com traço #c48b78 sobre fundo risco. Corte só aparece na comparação antes/depois.

### Nota de margem
Serifa itálica verde, alinhada à direita na margem, com o nome do professor em romano 600 marcado pela forma dele. Nota resolvida mostra a troca em realce verde-claro. Na estação do editor, as notas entram deslizando 2rem da margem para dentro (1.1s).

### Rótulo de arquivo
Código em monoespaçada 500, 1.0625rem, sobre verde-claro, cantos retos, acima dele um rótulo curto ("deixa") em sans suave. No desktop vive na coluna da direita; abaixo de 68rem desce para baixo do texto.

### Sumário (navegação)
Lista numerada na margem: número em serifa 600 verde, link em sans 500 0.8125rem tinta suave sem sublinhado; no hover vira verde sublinhado. Título do sumário em sans 600 verde.

### Links e foco
Links verdes com sublinhado de 1px afastado 0.2em, 2px no hover. Foco: contorno verde de 2px com 3px de afastamento. Link de pular para o conteúdo em tinta sobre folha, visível só com foco.

### Visto
Lista sem marcador; cada item leva um visto em SVG inline de 1.2rem, traço de 2.4 com pontas redondas, na cor ocre.

## Do's and Don'ts

### Do:
- **Do** manter a folha (folha) sobre o papel (papel) e separar seções só com espaço (secao).
- **Do** pôr toda nota e todo apontamento na coluna da margem, em serifa itálica verde.
- **Do** distinguir quem marcou pela forma da marca (duplo, pontilhado, círculo), sempre em verde.
- **Do** dizer em cada estação qual arquivo ela deixa, no rótulo de código sobre verde-claro.
- **Do** deixar todo o conteúdo visível sem JS e com movimento reduzido; a animação só acende o que já está lá.

### Don't:
- **Don't** usar sombra, gradiente ou cartão com borda e raio; a folha é plana.
- **Don't** usar ocre fora do visto nem vermelho fora do corte.
- **Don't** dar uma cor a cada professor; a cor da marca é sempre o verde.
- **Don't** escrever o texto do usuário em sans nem a explicação em serifa.
- **Don't** arredondar cantos de rótulos e realces; círculo só no nó e na marca de pontuação.
