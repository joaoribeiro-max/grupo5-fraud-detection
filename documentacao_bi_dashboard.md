# 🏦 Banco Cidade Inteligente — Dashboard de Monitoramento de Transações e Fraudes

Este repositório contém a documentação e os recursos visuais do dashboard analítico desenvolvido para o **Banco Cidade Inteligente**. O projeto tem como objetivo monitorar o volume transacional da instituição, identificar padrões de comportamento e acompanhar a incidência e o impacto financeiro de transações fraudulentas.

---

## 📊 Visão Geral do Dashboard

O painel foi estruturado para oferecer uma leitura rápida e executiva (top-down), partindo de indicadores macro (Big Numbers) até o detalhamento por categoria de operação e evolução temporal.

### 🎯 Principais KPIs (Big Numbers)
* **Transações:** `6,36 mi` — Volume total de operações processadas no período analisado.
* **Volume Financeiro:** `R$ 1,14 tri` — Montante financeiro total movimentado.
* **Fraudes Detectadas:** `8,21 mil` — Quantidade total de transações identificadas como fraudulentas.
* **Exposição Financeira:** `R$ 12,06 bi` — Soma do valor financeiro envolvido nas operações fraudulentas (risco direto).

---

## 📈 Visualizações e Análises

1. **Filtro Dinâmico por Turno:**
   * Permite segmentar todas as métricas e gráficos do painel de acordo com o período do dia (ex: Manhã, Tarde, Noite, Madrugada ou *All*), facilitando a identificação de janelas de maior risco.

2. **Filtro Dinâmico por Tipos de Contas Destino:**
  * Permite segmentar todas as métricas e gráficos do painel de acordo com o tipo de conta de destino (ex: Cliente, Comércio ou *All*), facilitando a identificação de dados relacionados a essas tipagens de conta.
  
3. **Volume Financeiro x Tipos de Transações (Gráfico de Colunas):**
   * Apresenta a distribuição do montante movimentado por modalidade: *Débito* (`227,2 mi`), *Pagamento* (`28,09 bi`), *Depósito* (`236,37 bi`), *Saque* (`394,41 bi`) e *Transferência* (`485,29 bi`).

4. **Valor financeiro Retido/Protegido (Gráfico de Colunas Agrupadas Horizontais):**
   * Apresenta a distribuição do montante total de exposição financeira por tipos: *Exposição Residual em Análise* (`221,9 mi`), *Valor Retido (Bloqueio Preventivo)* (`11,83 bi`).

5. **Fraudes por Tipos de Transações (Gráfico de Colunas Agrupadas):**
   * Compara lado a lado o volume financeiro de operações **Legítimas** (azul) versus **Fraudulentas** (rosa/vermelho) em cada categoria.
   * **Insight principal:** As fraudes financeiras concentram-se quase exclusivamente nas modalidades de **Saque** (`R$ 5,99 bi`) e **Transferência** (`R$ 6,07 bi`), enquanto operações como Pagamento e Depósito apresentam impacto financeiro de fraude praticamente nulo.

6. **Transações por Dia (Gráfico de Linhas):**
   * Acompanha a série histórica diária (Dias 1 a 31) comparando o comportamento das transações legítimas e fraudulentas, permitindo identificar anomalias, picos de ataque e quedas bruscas no fluxo normal.

---

## 🛠️ Arquitetura e Tratamento de Dados

* **Fonte de Dados (Camada Gold):** O dashboard consome diretamente um dataset refinado da camada **Gold** (arquitetura Medalhão), garantindo que os dados já estejam limpos, agregados e otimizados para performance analítica.
* **Padronização e Tratamento (Coluna Calculada):** 
  * Para garantir uma apresentação executiva clara e em português nos eixos e legendas dos gráficos, foi criada algumas **colunas calculadas** para tratar e traduzir os tipos de transação originais do banco de dados (ex: padronizando termos técnicos/em inglês para *Transferência*, *Saque*, *Depósito*, *Pagamento* e *Débito*).
  * O mesmo tratamento semântico foi aplicado para categorizar o status das operações entre **Legítima** e **Fraudulenta**.

---

## 🚀 Como Utilizar

1. Acesse o Link disponível no Databricks para acesso do dashboard > https://dbc-97bd1f30-bee3.cloud.databricks.com/dashboardsv3/01f1e07c867b14f5b20870bf665632e9/published?o=7474645444335671
2. Caso deseje, abrindo o dashboard pode clicar nos três pontos e fazer download do PDF


---

*Projeto desenvolvido com foco em Business Intelligence, Análise de Risco e Prevenção à Fraude.*
