# Índice de marcas de IA

Heurística, não detector. O número serve para triagem: onde olhar primeiro, não para acusar ninguém.

## Como o número sai

1. O texto é dividido em parágrafos.
2. Cada parágrafo é varrido por padrões conhecidos de escrita de IA, com peso.
3. A soma ponderada é normalizada pelo tamanho do parágrafo, com saturação suave (um padrão isolado não vira 100).
4. O documento combina a média ponderada por palavras com a **burstiness** (variação de tamanho de frase). Frase sempre do mesmo tamanho é suspeita.
5. Sai 0–100. Acima de 60, vermelho; 35–60, âmbar; abaixo, verde.

## Padrões contados

| Padrão | Peso |
|---|---|
| contraste "não é X, é Y" | 3 |
| "não apenas… mas também" | 2 |
| "é importante ressaltar/notar/destacar" | 2 |
| "vale destacar/lembrar" | 2 |
| "em suma / em última análise" | 2 |
| "por fim", "além disso" | 1 |
| abertura de cenário ("no cenário atual") | 3 |
| léxico: jornada, transformador, robusto, holístico, sinergia, ecossistema | 2 |
| "de forma abrangente/significativa/profunda" | 2 |
| "a verdade é que / o fato é que" | 2 |
| "convido você", "respire fundo" | 3 |
| rótulo em negrito no início do parágrafo | 2 |
| travessão em excesso (mais de 2 no parágrafo) | 0,5 cada |

## O que o índice não faz

- Não prova autoria. Texto humano cansado pontua alto; texto de IA bem editado pontua baixo.
- Não substitui leitura. É mapa de calor, não laudo.
- Não foi calibrado em corpus editorial ainda. A calibração precisa de ~10 textos seus e ~10 textos sabidamente de IA, para ajustar pesos e cortes.

## Como usar na revisão

- Parágrafo acima de 60: leitura humana obrigatória.
- Acima de 35: conferir abertura e fechamento, onde a marca costuma se concentrar.
- Nunca reescrever só para baixar o índice. O alvo é o texto soar como a autora, não como a métrica.
