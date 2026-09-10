# Quanto Ganham

Observatório cívico independente das remunerações dos titulares de cargos políticos em Portugal.

## Sobre o projeto

O **Quanto Ganham** é uma ferramenta de transparência que agrega e apresenta, de forma acessível, os vencimentos dos políticos portugueses — desde o Presidente da República aos 308 presidentes de câmara municipal — com base exclusivamente em fontes públicas e legislação em vigor.

## Funcionalidades

- **Remunerações do Estado central** — Presidente da República, Primeiro-Ministro, ministros, deputados à Assembleia da República e eurodeputados
- **Os 308 concelhos de Portugal** — Vencimentos detalhados de todos os presidentes de câmara, com escalão de eleitores, despesas de representação e total anual
- **Simulador interativo** — Permite testar como variações no vencimento-base do Presidente da República afetam automaticamente todos os vencimentos autárquicos
- **Pesquisa e filtros** — Por distrito, escalão ou nome do titular
- **Protocolo de atualização** — Documentação clara sobre como o dataset é atualizado após cada ato eleitoral
- **Metodologia transparente** — Todas as fontes e fórmulas de cálculo são citadas

## Enquadramento legal

Os vencimentos apresentados derivam de:
- **Lei n.º 29/87** — Estatuto dos Eleitos Locais (fixa os escalões autárquicos como percentagem do vencimento do PR)
- **Orçamento do Estado** (anual) — Atualizações das remunerações
- **Regime jurídico das autarquias locais** — Composição dos órgãos municipais

## Dados

O dataset cobre o mandato autárquico **2025–2029** e inclui:
- 308 câmaras municipais
- 3.259 freguesias
- 230 deputados à Assembleia da República
- 21 eurodeputados

Os nomes dos titulares correspondem aos eleitos nas eleições locais de 12 de outubro de 2025.

## Stack técnica

- HTML5 semântico
- CSS3 puro (Grid, Flexbox, animações)
- JavaScript vanilla (sem dependências)
- Google Fonts (Archivo, Public Sans, IBM Plex Mono)
- Dados em JSON estático (`dados.json`)

## Como usar

```bash
# Clonar o repositório
git clone https://github.com/teu-username/quanto-ganham.git

# Abrir num servidor local (necessário para fetch do dados.json)
cd quanto-ganham
python -m http.server 8000
# Aceder a http://localhost:8000
