# 🏦 Banco Cidade Inteligente — Dashboard de Monitoramento de Transações e Fraudes

Este repositório contém a documentação e os recursos visuais dos dashboards analíticos desenvolvidos para o **Banco Cidade Inteligente**. O projeto tem como objetivo monitorar o volume transacional da instituição, identificar padrões de comportamento, acompanhar a incidência e o impacto financeiro de transações fraudulentas e analisar o desempenho de modelos de Machine Learning aplicados à detecção de fraudes.

---

## 📊 Visão Geral dos Dashboards

O projeto está dividido em dois painéis complementares:

- **Dashboard Principal:** Monitoramento de transações, volume financeiro, exposição financeira e distribuição de fraudes.
- **Dashboard de Automação:** Monitoramento dos resultados da detecção automatizada de fraudes por meio de modelos de Machine Learning, com foco na análise de desempenho e comparação entre algoritmos.

---

# 1. 📊 Dashboard Principal — Monitoramento de Transações e Fraudes

O painel foi estruturado para oferecer uma leitura rápida e executiva (top-down), partindo de indicadores macro (Big Numbers) até o detalhamento por categoria de operação e evolução temporal.

### 🎯 Principais KPIs (Big Numbers)

- **Transações:** `6,36 mi` — Volume total de operações processadas no período analisado.
- **Volume Financeiro:** `R$ 1,14 tri` — Montante financeiro total movimentado.
- **Fraudes Detectadas:** `8,21 mil` — Quantidade total de transações identificadas como fraudulentas.
- **Exposição Financeira:** `R$ 12,06 bi` — Soma do valor financeiro envolvido nas operações fraudulentas (risco direto).

---

## 📈 Visualizações e Análises

1. **Filtro Dinâmico por Turno:**
   - Permite segmentar todas as métricas e gráficos do painel de acordo com o período do dia (ex: Manhã, Tarde, Noite, Madrugada ou *All*), facilitando a identificação de janelas de maior risco.

2. **Filtro Dinâmico por Tipos de Contas Destino:**
   - Permite segmentar todas as métricas e gráficos do painel de acordo com o tipo de conta de destino (ex: Cliente, Comércio ou *All*), facilitando a identificação de dados relacionados a essas tipagens de conta.

3. **Volume Financeiro x Tipos de Transações (Gráfico de Colunas):**
   - Apresenta a distribuição do montante movimentado por modalidade: *Débito* (`227,2 mi`), *Pagamento* (`28,09 bi`), *Depósito* (`236,37 bi`), *Saque* (`394,41 bi`) e *Transferência* (`485,29 bi`).

4. **Valor financeiro Retido/Protegido (Gráfico de Colunas Agrupadas Horizontais):**
   - Apresenta a distribuição do montante total de exposição financeira por tipos: *Exposição Residual em Análise* (`221,9 mi`), *Valor Retido (Bloqueio Preventivo)* (`11,83 bi`).

5. **Fraudes por Tipos de Transações (Gráfico de Colunas Agrupadas):**
   - Compara lado a lado o volume financeiro de operações **Legítimas** (azul) versus **Fraudulentas** (rosa/vermelho) em cada categoria.
   - **Insight principal:** As fraudes financeiras concentram-se quase exclusivamente nas modalidades de **Saque** (`R$ 5,99 bi`) e **Transferência** (`R$ 6,07 bi`), enquanto operações como Pagamento e Depósito apresentam impacto financeiro de fraude praticamente nulo.

6. **Transações por Dia (Gráfico de Linhas):**
   - Acompanha a série histórica diária (Dias 1 a 31) comparando o comportamento das transações legítimas e fraudulentas, permitindo identificar anomalias, picos de ataque e quedas bruscas no fluxo normal.

---

# 2. 🤖 Dashboard de Automação — Monitoramento de Machine Learning

O segundo painel foi desenvolvido para acompanhar os resultados da detecção automatizada de fraudes, permitindo visualizar indicadores de desempenho dos modelos de Machine Learning utilizados na análise das transações.

### 🎯 Indicadores de Desempenho — LightGBM

O dashboard apresenta três métricas principais para avaliar a capacidade do modelo LightGBM na identificação de fraudes:

- **Precisão (Precision):** `77,82%` — Representa a proporção de classificações positivas realizadas pelo modelo que realmente correspondem a fraudes.
- **Recall:** `49,60%` — Representa a proporção de fraudes reais que foram corretamente identificadas pelo modelo.
- **F1-Score:** `60,59%` — Métrica que combina Precision e Recall por meio da média harmônica, permitindo avaliar o equilíbrio entre essas duas medidas.

Esses indicadores permitem analisar não apenas a capacidade do modelo de identificar fraudes, mas também a confiabilidade de suas classificações.

### 📊 Indicadores Operacionais — LightGBM

O painel também apresenta indicadores relacionados ao volume de dados processados e às ocorrências identificadas:

- **Total de Transações Analisadas:** `89,47 mil` — Quantidade de transações submetidas à análise do modelo.
- **Fraudes:** `1,25 mil` — Quantidade de fraudes reais submetidas à análise do modelo.

### 🔍 Análise de Detecção de Fraudes

O gráfico de colunas apresenta a distribuição dos resultados da detecção de fraudes, segmentados em duas categorias:

- **Falsos Negativos:** `631`.
- **Verdadeiros Positivos:** `621`.

Essas categorias permitem observar os diferentes resultados da classificação realizada pelo modelo:

- **Verdadeiros Positivos (True Positives):** Transações fraudulentas identificadas corretamente pelo modelo.
- **Falsos Negativos (False Negatives):** Transações fraudulentas classificadas incorretamente como legítimas.

A visualização auxilia na compreensão dos acertos e erros do processo de classificação, permitindo avaliar o comportamento do modelo diante das operações fraudulentas.


### 🧠 Precisão do Agente de Machine Learning

O painel também contempla uma área específica para acompanhar a precisão do agente de ML, permitindo centralizar informações relacionadas ao desempenho da automação.

Essa visualização foi incorporada à estrutura do dashboard para possibilitar o acompanhamento de indicadores do agente e complementar a análise dos modelos utilizados na detecção de fraudes.

---

## 🛠️ Arquitetura e Tratamento de Dados

- **Fonte de Dados (Camada Gold):** O dashboard principal consome diretamente um dataset refinado da camada **Gold** (arquitetura Medalhão), garantindo que os dados já estejam limpos, agregados e otimizados para performance analítica.

- **Padronização e Tratamento (Coluna Calculada):**
  - Para garantir uma apresentação executiva clara e em português nos eixos e legendas dos gráficos, foram criadas algumas **colunas calculadas** para tratar e traduzir os tipos de transação originais do banco de dados (ex: padronizando termos técnicos/em inglês para *Transferência*, *Saque*, *Depósito*, *Pagamento* e *Débito*).
  - O mesmo tratamento semântico foi aplicado para categorizar o status das operações entre **Legítima** e **Fraudulenta**.

- **Análise Automatizada com Machine Learning:**
  - O Dashboard de Automação apresenta os resultados de modelos de Machine Learning aplicados à identificação de transações fraudulentas.
  - Os algoritmos contemplados na estrutura de análise são **LightGBM**.
  - As métricas de Precision, Recall e F1-Score são utilizadas para acompanhar o desempenho do processo de classificação.
  - Os resultados são apresentados por meio de indicadores operacionais e gráficos de distribuição de classificações, permitindo avaliar a identificação correta de fraudes e os erros de classificação.

---

## 🚀 Como Utilizar

1. **Dashboard Principal:** Acesse o link disponível no Databricks para visualizar o painel de monitoramento de transações e fraudes:

   [Acessar Dashboard Principal](https://dbc-97bd1f30-bee3.cloud.databricks.com/dashboardsv3/01f1e07c867b14f5b20870bf665632e9/published?o=7474645444335671)

2. **Dashboard de Automação:** Dentro do ambiente Databricks, selecione a aba **Dashboard Automação**, localizada ao lado da aba **Dashboard principal**, para acessar os indicadores de Machine Learning.

3. **Download em PDF:** Caso deseje, abra o dashboard, clique nos três pontos e selecione a opção de download em PDF.

---

## 📌 Considerações Finais

Os dois dashboards trabalham de forma complementar para oferecer uma visão analítica e operacional do combate às fraudes no Banco Cidade Inteligente.

Enquanto o **Dashboard Principal** permite acompanhar o comportamento transacional, o impacto financeiro das fraudes e os valores retidos ou protegidos, o **Dashboard de Automação** possibilita observar os resultados dos modelos de Machine Learning utilizados na identificação de operações suspeitas.

A integração dessas duas perspectivas contribui para uma análise mais abrangente, conectando o monitoramento financeiro à eficiência dos mecanismos automatizados de detecção de fraudes.
