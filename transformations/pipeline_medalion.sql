-- ==============================================================================
-- CAMADA BRONZE: Ingestão Bruta em Lote (Batch) via Unity Catalog Volume
-- Origem: /Volumes/workspace/dados_fraude/banco_inteligente_dados (arquivos CSV PaySim)
-- Destino: workspace.bronze.cidade_inteligente
-- Objetivo: Ingerir os arquivos CSV brutos em modo lote (batch) a partir do
--           Volume do Unity Catalog, mantendo todas as colunas originais como
--           STRING (padrão Raw Bronze) e adicionando metadados de auditoria.
-- Nota: O objeto foi definido como MATERIALIZED VIEW (sem STREAM) por se tratar
--       de uma carga estática do Kaggle, evitando dependências de checkpoint e
--       facilitando reprocessamentos caso o arquivo no Volume seja substituído.
--       O parâmetro inferSchema => false força a leitura como texto (STRING)
--       para evitar falhas na ingestão, delegando a tipagem para a camada Silver.
-- ==============================================================================

CREATE OR REFRESH MATERIALIZED VIEW workspace.bronze.cidade_inteligente_transacoes
COMMENT "Dados brutos de transações financeiras (base PaySim) ingeridos em lote do Volume como STRING."
TBLPROPERTIES (
  "quality" = "bronze"
)
AS
SELECT
  -- 1. Dados Brutos do Dataset (Schema-on-Read):
  -- Seleciona todas as 11 colunas originais do CSV como STRING (step, type, amount,
  -- nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest,
  -- isFraud, isFlaggedFraud) além da coluna _rescued_data, criada automaticamente
  -- pela função read_files para isolar linhas corrompidas ou colunas inesperadas.
  *,

  -- 2. Metadados de Auditoria e Linhagem (Governança em Produção):
  -- Registra o caminho exato do arquivo lido no Volume para rastreabilidade
  _metadata.file_path AS arquivo_origem,

  -- Grava o carimbo de data/hora exato em que a carga em lote foi executada,
  -- permitindo auditoria de processamento e controle de atualização da tabela
  current_timestamp() AS data_ingestao

-- Leitura em lote (batch) dos arquivos CSV contidos no diretório do Volume
FROM read_files(
  '/Volumes/workspace/dados_fraude/banco_inteligente_dados',
  format => 'csv',
  header => true,
  inferSchema => false
);


-- ==============================================================================
-- CAMADA SILVER: Tabela Refinada, Tipada e Padronizada (Fonte Única da Verdade)
-- Origem: workspace.bronze.cidade_inteligente
-- Destino: workspace.silver.transacoes
-- Objetivo: Converter tipos (STRING -> INT/DOUBLE), limpar, traduzir, gerar chave
--           primária, deduplicar e enriquecer temporalmente as transações financeiras
--           (base PaySim), servindo como base estruturada tanto para pipelines de
--           Machine Learning (ML) quanto para modelos analíticos de BI e Agentes de IA.
-- Nota: Mantém a granularidade transacional (1 linha por operação) e preserva
--       os atributos tratados antes das agregações (Gold BI) e da seleção/remoção
--       de features contra target leakage (Gold ML).
-- ==============================================================================

CREATE OR REFRESH MATERIALIZED VIEW workspace.silver.transacoes (
  -- Regras de Qualidade de Dados (DLT Expectations):
  -- Atuam em conjunto com o TRY_CAST da CTE 'dados_tipados'. Se algum registro
  -- vier com texto inválido em colunas numéricas, o TRY_CAST retorna NULL e as
  -- regras abaixo descartam a linha automaticamente sem derrubar a pipeline.
  CONSTRAINT valor_valido EXPECT (valor IS NOT NULL AND valor >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT step_valido  EXPECT (step IS NOT NULL AND step >= 1)   ON VIOLATION DROP ROW,
  CONSTRAINT tipo_valido  EXPECT (tipo_transacao IS NOT NULL AND tipo_transacao != '') ON VIOLATION DROP ROW
)
COMMENT "Transações financeiras limpas, tipadas, traduzidas e deduplicadas"
AS
WITH dados_tipados AS (
  -- 1. Schema Enforcement e Sanitização (Tipagem na Silver):
  -- Remove espaços em branco extras (TRIM) e converte as colunas que vieram como
  -- STRING da Bronze para seus respectivos tipos numéricos usando TRY_CAST.
  SELECT
    TRY_CAST(TRIM(step) AS INT)              AS step,
    TRIM(type)                               AS type,
    TRY_CAST(TRIM(amount) AS DOUBLE)         AS amount,
    TRIM(nameOrig)                           AS nameOrig,
    TRY_CAST(TRIM(oldbalanceOrg) AS DOUBLE)  AS oldbalanceOrg,
    TRY_CAST(TRIM(newbalanceOrig) AS DOUBLE) AS newbalanceOrig,
    TRIM(nameDest)                           AS nameDest,
    TRY_CAST(TRIM(oldbalanceDest) AS DOUBLE) AS oldbalanceDest,
    TRY_CAST(TRIM(newbalanceDest) AS DOUBLE) AS newbalanceDest,
    TRY_CAST(TRIM(isFraud) AS INT)           AS isFraud,
    TRY_CAST(TRIM(isFlaggedFraud) AS INT)    AS isFlaggedFraud
  FROM workspace.bronze.cidade_inteligente_transacoes
),
base_hasheada AS (
  SELECT
    -- 2. Chave Primária Determinística (Surrogate Key):
    -- Gera um hash SHA-256 truncado em 16 caracteres combinando os 9 atributos
    -- imutáveis da transação já tipados. O COALESCE evita que valores nulos anulem
    -- o hash, e as colunas de fraude ficam de fora para manter o ID estável.
    LEFT(
      sha2(
        concat_ws(
          '||',
          COALESCE(CAST(step AS STRING), '_NULL_'),
          COALESCE(UPPER(type), '_NULL_'),
          COALESCE(CAST(amount AS STRING), '_NULL_'),
          COALESCE(nameOrig, '_NULL_'),
          COALESCE(CAST(oldbalanceOrg AS STRING), '_NULL_'),
          COALESCE(CAST(newbalanceOrig AS STRING), '_NULL_'),
          COALESCE(nameDest, '_NULL_'),
          COALESCE(CAST(oldbalanceDest AS STRING), '_NULL_'),
          COALESCE(CAST(newbalanceDest AS STRING), '_NULL_')
        ),
        256
      ),
      16
    ) AS id_transacao,

    -- Limpa espaços, padroniza em minúsculas e traduz o domínio da operação sem acentos
    CASE LOWER(type)
      WHEN 'transfer' THEN 'transferencia'
      WHEN 'cash_in'  THEN 'deposito'
      WHEN 'cash_out' THEN 'saque'
      WHEN 'debit'    THEN 'debito'
      WHEN 'payment'  THEN 'pagamento'
      ELSE LOWER(type)
    END AS tipo_transacao,

    step AS step,

    -- Traduz o nome das colunas para português
    amount         AS valor,
    nameOrig       AS conta_origem,
    oldbalanceOrg  AS saldo_inicial_origem,
    newbalanceOrig AS saldo_final_origem,
    nameDest       AS conta_destino,
    oldbalanceDest AS saldo_inicial_destino,
    newbalanceDest AS saldo_final_destino,
    isFraud        AS eh_fraude,
    isFlaggedFraud AS flag_fraude_sistema

  FROM dados_tipados
)
SELECT
  *,

  -- 3. Enriquecimento Temporal (cada unidade de 'step' equivale a 1 hora):
  -- Extrai a hora do dia em ciclo de 0 a 23
  (step - 1) % 24 AS hora_do_dia,

  -- Calcula o dia corrido da simulação (iniciando no dia 1)
  FLOOR((step - 1) / 24) + 1 AS dia_simulacao,

  -- Calcula o dia da semana em ciclo contínuo de 1 a 7
  (FLOOR((step - 1) / 24) % 7) + 1 AS dia_semana

FROM base_hasheada

-- 4. Deduplicação:
-- Garante que cada 'id_transacao' apareça apenas uma vez na tabela Silver,
-- mantendo a primeira ocorrência cronológica em caso de linhas idênticas na Bronze.
QUALIFY ROW_NUMBER() OVER (PARTITION BY id_transacao ORDER BY step) = 1;


-- ==============================================================================
-- CAMADA GOLD LIGHTGBM: Materialized View para Treinamento e Inferência (ML)
-- Origem: workspace.silver.transacoes
-- Destino: workspace.gold_ml.gbm_transacoes
-- Objetivo: Disponibilizar features numéricas, binárias e históricas otimizadas
--           especificamente para o algoritmo LightGBM (aproveitando valores
--           contínuos sem necessidade de normalização de escala e tratamento nativo
--           de valores ausentes/NULL).
-- Nota: Definida como MATERIALIZED VIEW (e não Streaming Table) por utilizar
--       Window Functions globais sobre todo o histórico transacional.
--       Decisões de modelagem aplicadas:
--       1. Colunas de saldo bruto foram omitidas para evitar target leakage
--          (o simulador PaySim cancela transações fraudulentas).
--       2. Variáveis de dia da semana/fim de semana foram removidas porque o volume
--          do PaySim varia por fases da simulação (dias 2-4 e 17-30 com baixo volume),
--          e não por ciclo semanal real — mantê-las geraria correlações espúrias
--       3. Todas as janelas temporais olham estritamente para o passado (1 PRECEDING),
--          garantindo ausência total de vazamento de dados futuros (data leakage).
-- ==============================================================================

CREATE OR REFRESH MATERIALIZED VIEW workspace.gold_ml.gbm_transacoes
COMMENT 'Camada Gold LightGBM: tabela física de features comportamentais e temporais (sem leakage) para treinamento e inferência do modelo LightGBM.'
AS
SELECT
  -- --------------------------------------------------------------------------
  -- 1. CHAVES DE RASTREIO E CONTROLE TEMPORAL (NÃO ENTRAM NO X_train)
  -- --------------------------------------------------------------------------
  -- id_transacao: rastreia cada predição para auditoria e investigação
  -- step: controle cronológico granular (em horas) para divisão treino/teste
  -- dia_absoluto: índice diário contínuo (base 0) para validação cruzada
  --               temporal (GroupKFold / split por dia sem vazamento entre grupos)
  id_transacao,
  step,
  FLOOR((step - 1) / 24) AS dia_absoluto,

  -- --------------------------------------------------------------------------
  -- 2. ONE-HOT ENCODING MANUAL DO TIPO DE OPERAÇÃO (VARIÁVEIS BINÁRIAS)
  -- --------------------------------------------------------------------------
  -- Converte a categoria textual da operação em 5 flags exclusivas (0 ou 1)
  CASE WHEN tipo_transacao = 'pagamento'     THEN 1 ELSE 0 END AS eh_pagamento,
  CASE WHEN tipo_transacao = 'deposito'      THEN 1 ELSE 0 END AS eh_deposito,
  CASE WHEN tipo_transacao = 'debito'        THEN 1 ELSE 0 END AS eh_debito,
  CASE WHEN tipo_transacao = 'saque'         THEN 1 ELSE 0 END AS eh_saque,
  CASE WHEN tipo_transacao = 'transferencia' THEN 1 ELSE 0 END AS eh_transferencia,

  -- --------------------------------------------------------------------------
  -- 3. ENGENHARIA DE VALOR FINANCEIRO
  -- --------------------------------------------------------------------------
  -- Mantém o valor contínuo exato preservando eventuais NULLs (o LightGBM trata
  -- valores ausentes nativamente direcionando-os para o ramo ótimo da árvore)
  valor,

  -- --------------------------------------------------------------------------
  -- 4. PERFIL E HISTÓRICO COMPORTAMENTAL DA CONTA DE DESTINO
  -- --------------------------------------------------------------------------
  -- Identifica se o recebedor é Comerciante (prefixo 'M', onde não ocorrem fraudes
  -- no PaySim) ou Cliente comum (prefixo 'C')
  CASE
    WHEN UPPER(conta_destino) LIKE 'M%' THEN 1
    ELSE 0
  END AS destino_eh_comercio,

  -- Histórico acumulado de recebimentos anteriores da conta destino (0 = conta nunca vista):
  -- Delimitado até 1 PRECEDING para contabilizar apenas transações estritamente anteriores
  COUNT(*) OVER (
    PARTITION BY conta_destino
    ORDER BY step
    RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
  ) AS qtd_recebimentos_destino_hist,

  -- Velocidade de recebimentos nas últimas 24 horas (janela móvel de 24 steps anteriores):
  -- Captura picos recentes de entrada na conta receptora (mais estacionária que o
  -- acumulado histórico, embora sofra redução natural nas fases de baixo volume)
  COUNT(*) OVER (
    PARTITION BY conta_destino
    ORDER BY step
    RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING
  ) AS qtd_recebimentos_destino_24h,

  -- --------------------------------------------------------------------------
  -- 5. ENRIQUECIMENTO TEMPORAL - HORA EXATA E TURNOS (BLOCOS DE 6 HORAS)
  -- --------------------------------------------------------------------------
  -- hora_do_dia (0 a 23): permite ao LightGBM cortes cirúrgicos em horários específicos
  hora_do_dia,

  -- Flags de turno: capturam o comportamento macro dos períodos do dia
  CASE WHEN hora_do_dia BETWEEN 0  AND 5  THEN 1 ELSE 0 END AS eh_madrugada,
  CASE WHEN hora_do_dia BETWEEN 6  AND 11 THEN 1 ELSE 0 END AS eh_manha,
  CASE WHEN hora_do_dia BETWEEN 12 AND 17 THEN 1 ELSE 0 END AS eh_tarde,
  CASE WHEN hora_do_dia BETWEEN 18 AND 23 THEN 1 ELSE 0 END AS eh_noite,

  -- --------------------------------------------------------------------------
  -- 6. REGRA LEGADA (CONTROLE) E VARIÁVEL ALVO (TARGET)
  -- --------------------------------------------------------------------------
  -- flag_fraude_sistema: sinalizador legado do PaySim (usado apenas para benchmark/auditoria)
  -- eh_fraude: variável alvo binária (0 = legítima, 1 = fraude) tipada como inteiro
  CAST(COALESCE(flag_fraude_sistema, 0) AS INT) AS flag_fraude_sistema,
  CAST(eh_fraude AS INT)                        AS eh_fraude

-- Leitura da camada Silver limpa e deduplicada
FROM workspace.silver.transacoes

-- Garante integridade supervisionada descartando registros sem rótulo definido
-- em vez de imputar 0 artificialmente como "não fraude"
WHERE eh_fraude IS NOT NULL;


-- ==============================================================================
-- CAMADA GOLD KNN: Materialized View para Treinamento e Inferência (K-Nearest Neighbors)
-- Origem: workspace.silver.transacoes
-- Destino: workspace.gold_ml.knn_transacoes
-- Objetivo: Disponibilizar features estritamente escalonadas em [0, 1], sem valores
--           nulos (NaN), de baixa dimensionalidade e enriquecidas com o histórico
--           comportamental da conta de destino, otimizadas para o algoritmo KNN.
-- Nota: Definida como MATERIALIZED VIEW (e não Streaming Table) por utilizar
--       Window Functions globais sobre todo o histórico transacional.
--       Decisões de modelagem e engenharia aplicadas:
--       1. Ordem de filtragem (Pós-Janela): apenas 'saque' e 'transferencia' são
--          mantidos na saída (únicas modalidades com fraude no PaySim), mas o filtro
--          WHERE é aplicado APÓS as Window Functions para que o histórico da conta
--          destino considere todas as operações prévias (incluindo depósitos/pagamentos).
--       2. Prevenção de Target Leakage: colunas de saldo bruto foram omitidas, pois
--          o simulador PaySim cancela transações fraudulentas.
--       3. Prevenção de Data Leakage na normalização: as transformações logarítmicas
--          usam divisores fixos (3.0 e 18.5) em vez de MIN/MAX da tabela, evitando
--          vazamento de estatísticas globais/futuras para o conjunto de treino.
--       4. Seleção rigorosa de dimensionalidade: 'dia_semana' e 'eh_final_de_semana'
--          foram removidos (o volume do PaySim varia por fases da simulação, não
--          por ciclo semanal, gerando ruído na distância); 'destino_eh_comercio' foi
--          omitido por tornar-se constante (0) após o filtro de saque/transferência.
--       5. Integridade sem imputação artificial: linhas com nulos em valor, hora ou
--          rótulo são descartadas (sem COALESCE), pois o KNN não aceita NaN e
--          imputar 0 criaria pontos artificiais no espaço geométrico.
--       6. Nota para etapa Python: antes do fit/predict, padronize/pese as features
--          (limitar em [0, 1] não equaliza a variância entre variáveis binárias e
--          contínuas) e aplique subamostragem (undersampling) na classe majoritária.
-- ==============================================================================

CREATE OR REFRESH MATERIALIZED VIEW workspace.gold_ml.knn_transacoes
COMMENT 'Camada Gold KNN: features escalonadas em [0, 1] de saques e transferências, enriquecidas com comportamento histórico da conta destino (sem leakage).'
AS
WITH base_comportamental AS (
  -- --------------------------------------------------------------------------
  -- CTE 1: ENGENHARIA DE ATRIBUTOS COMPORTAMENTAIS DA CONTA DE DESTINO
  -- --------------------------------------------------------------------------
  -- Calcula métricas históricas e de velocidade sobre TODAS as transações da
  -- camada Silver (antes do filtro de modalidade) olhando estritamente para o
  -- passado (1 PRECEDING / LAG) para evitar vazamento de dados futuros.
  SELECT
    id_transacao,
    step,
    tipo_transacao,
    valor,
    hora_do_dia,
    eh_fraude,

    -- Histórico acumulado de recebimentos anteriores da conta destino:
    -- Retorna 0 na primeira aparição da conta, permitindo identificar contas novas
    COUNT(*) OVER (
      PARTITION BY conta_destino
      ORDER BY step, id_transacao
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS qtd_recebimentos_anterior,

    -- Velocidade de recebimentos nas últimas 24h (excluindo o step atual):
    -- Métrica mais estacionária que a contagem acumulada total (embora sofra
    -- redução natural nas fases de baixo volume do simulador PaySim)
    COUNT(*) OVER (
      PARTITION BY conta_destino
      ORDER BY step
      RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING
    ) AS qtd_recebimentos_24h,

    -- Intervalo de tempo (em steps/horas) desde o último recebimento da conta destino:
    -- Retorna NULL na primeira transação da conta; usado para detectar rajadas
    step - LAG(step) OVER (
      PARTITION BY conta_destino
      ORDER BY step, id_transacao
    ) AS diff_step_destino

  FROM workspace.silver.transacoes
)
SELECT
  -- --------------------------------------------------------------------------
  -- 1. CHAVES DE RASTREIO E CONTROLE TEMPORAL (NÃO ENTRAM NO X DO KNN)
  -- --------------------------------------------------------------------------
  -- id_transacao: rastreia cada predição para auditoria e investigação
  -- step: controle cronológico granular (em horas) para ordenação temporal
  -- dia_absoluto: índice diário contínuo (base 0) para validação cruzada
  --               temporal (GroupKFold / split por dia sem vazamento entre grupos)
  id_transacao,
  step,
  CAST(FLOOR((step - 1) / 24) AS INT) AS dia_absoluto,

  -- --------------------------------------------------------------------------
  -- 2. CODIFICAÇÃO DO TIPO DE OPERAÇÃO EM [0, 1]
  -- --------------------------------------------------------------------------
  -- Como o subconjunto contém apenas 'saque' e 'transferencia', uma única flag
  -- binária basta (1 = transferencia, 0 = saque), evitando colinearidade e peso
  -- duplicado no cálculo de distância Euclidiana
  CASE WHEN tipo_transacao = 'transferencia' THEN 1 ELSE 0 END AS eh_transferencia,

  -- --------------------------------------------------------------------------
  -- 3. COMPORTAMENTO HISTÓRICO E VELOCIDADE DA CONTA DE DESTINO EM [0, 1]
  -- --------------------------------------------------------------------------
  -- Flag binária de conta inédita: sinaliza 1 quando a conta de destino nunca
  -- recebeu valores anteriormente (contas receptoras de fraude costumam ser novas)
  CASE WHEN qtd_recebimentos_anterior = 0 THEN 1 ELSE 0 END AS eh_conta_nova,

  -- Frequência recente de recebimentos nas últimas 24h normalizada em [0, 1]:
  -- Compressão logarítmica com divisor fixo 3.0 (satura em ~19 recebimentos;
  -- parâmetro calibrável conforme a distribuição observada no treino)
  LEAST(LN(1.0 + qtd_recebimentos_24h) / 3.0, 1.0) AS freq_destino_24h_norm,

  -- Flag binária de rajada no destino (velocity check): sinaliza 1 quando a conta
  -- recebe duas ou mais operações no mesmo step ou em steps consecutivos (<= 1h)
  CASE WHEN diff_step_destino IS NOT NULL AND diff_step_destino <= 1 THEN 1 ELSE 0 END AS eh_rajada_destino,

  -- --------------------------------------------------------------------------
  -- 4. ENGENHARIA DE VALOR FINANCEIRO EM ESCALA LOGARÍTMICA [0, 1]
  -- --------------------------------------------------------------------------
  -- Comprime a forte assimetria dos valores monetários via LN(1 + valor) com
  -- divisor fixo 18.5 (cobre montantes até ~108 milhões sem saturar fraudes de
  -- alto valor e sem depender de estatísticas globais da tabela)
  LEAST(LN(1.0 + valor) / 18.5, 1.0) AS valor_log_norm,

  -- --------------------------------------------------------------------------
  -- 5. CODIFICAÇÃO CÍCLICA CONTÍNUA DA HORA DO DIA EM [0, 1]
  -- --------------------------------------------------------------------------
  -- Projeta 'hora_do_dia' (0 a 23) no círculo trigonométrico (seno e cosseno)
  -- deslocado de [-1, 1] para [0, 1], preservando a proximidade geométrica
  -- entre 23h e 0h no espaço de distâncias do KNN
  (SIN(2.0 * PI() * hora_do_dia / 24.0) + 1.0) / 2.0 AS hora_sin,
  (COS(2.0 * PI() * hora_do_dia / 24.0) + 1.0) / 2.0 AS hora_cos,

  -- --------------------------------------------------------------------------
  -- 6. VARIÁVEL ALVO (TARGET)
  -- --------------------------------------------------------------------------
  -- Rótulo binário supervisionado (0 = legítima, 1 = fraude) tipado como inteiro
  CAST(eh_fraude AS INT) AS eh_fraude

FROM base_comportamental

-- Filtro pós-janela: restringe o dataset às modalidades onde ocorrem fraudes
-- no PaySim e elimina qualquer registro com valores ausentes nas features/alvo
WHERE tipo_transacao IN ('saque', 'transferencia')
  AND eh_fraude IS NOT NULL
  AND valor IS NOT NULL
  AND hora_do_dia IS NOT NULL;


-- ==============================================================================
-- CAMADA GOLD BI: Materialized View Analítica para Dashboards de Fraude
-- Origem: workspace.silver.transacoes
-- Destino: workspace.gold_dashboard.bi_fato_transacoes
-- Objetivo: Disponibilizar métricas absolutas pré-agregadas por dimensões de
--           negócio e tempo para consumo de alta performance em ferramentas de BI.
-- Nota: Percentuais (como taxa de fraude) não são calculados aqui para evitar
--       distorções matemáticas em agregações dinâmicas; devem ser criados via
--       medidas (DAX/SQL) diretamente no painel.
-- ==============================================================================

-- Define o objeto como Materialized View no Delta Live Tables (DLT), padrão obrigatório
-- para consultas que realizam agregações (GROUP BY, COUNT, SUM) no Unity Catalog
CREATE OR REFRESH MATERIALIZED VIEW workspace.gold_dashboard.bi_fato_transacoes
COMMENT 'Tabela fato agregada por tipo de transação, perfil de destino, dia e turno para dashboards de BI.'
AS
SELECT 
    -- Dimensão de Operação: Categoria da movimentação (transferencia, saque, pagamento, deposito, debito)
    tipo_transacao,

    -- Dimensão de Perfil de Destino: Regra de negócio do dataset PaySim onde contas
    -- iniciadas com 'M' (Merchants) representam lojistas/comércios e as demais ('C') clientes
    CASE
        WHEN conta_destino LIKE 'M%' THEN 'comercio'
        ELSE 'cliente'
    END AS conta_destino_tipo,

    -- Dimensão Temporal: Dia corrido da simulação (derivado dos steps de 1 hora)
    dia_simulacao,

    -- Coluna Auxiliar de Ordenação: Índice numérico (1 a 4) para permitir que o BI ordene
    -- os turnos cronologicamente, evitando a ordenação alfabética ('noite' antes de 'tarde')
    CASE 
        WHEN hora_do_dia BETWEEN 0  AND 5  THEN 1
        WHEN hora_do_dia BETWEEN 6  AND 11 THEN 2
        WHEN hora_do_dia BETWEEN 12 AND 17 THEN 3
        WHEN hora_do_dia BETWEEN 18 AND 23 THEN 4
    END AS ordem_turno,

    -- Dimensão Temporal (Rótulo): Faixa horária legível para exibição nos gráficos e filtros
    CASE 
        WHEN hora_do_dia BETWEEN 0  AND 5  THEN 'madrugada'
        WHEN hora_do_dia BETWEEN 6  AND 11 THEN 'manha'
        WHEN hora_do_dia BETWEEN 12 AND 17 THEN 'tarde'
        WHEN hora_do_dia BETWEEN 18 AND 23 THEN 'noite'
    END AS turno,

    -- Métrica Financeira de Mitigação: Parcela do montante fraudulento interceptada por
    -- regras preventivas (valor >= 200.000 ou tentativa de movimentação com saldo de origem zerado)
    ROUND(SUM(
        CASE 
            WHEN eh_fraude = 1 AND (valor >= 200000 OR saldo_inicial_origem = 0) THEN valor 
            ELSE 0 
        END
    ), 2) AS valor_retido_bloqueio_preventivo,

    -- Métrica Financeira de Exposição Líquida: Parcela complementar do montante fraudulento
    -- que não acionou o bloqueio preventivo (COALESCE evita perda de registros caso o saldo seja nulo)
    ROUND(SUM(
        CASE 
            WHEN eh_fraude = 1 AND valor < 200000 AND COALESCE(saldo_inicial_origem, -1) <> 0 THEN valor 
            ELSE 0 
        END
    ), 2) AS exposicao_residual_em_analise,

    -- Métrica Base (Denominador): Volume total de operações no recorte.
    -- Mantida absoluta para permitir o cálculo dinâmico da taxa de fraude no dashboard
    COUNT(*) AS total_transacoes,

    -- Métrica Financeira: Soma total do valor movimentado no recorte (2 casas decimais)
    ROUND(SUM(valor), 2) AS volume_financeiro,

    -- Métrica Base (Numerador): Contagem condicional apenas das transações fraudulentas
    SUM(CASE WHEN eh_fraude = 1 THEN 1 ELSE 0 END) AS total_fraudes,

    -- Métrica Financeira de Risco: Soma total dos valores das fraudes confirmadas
    -- (corresponde à soma exata entre valor_retido_bloqueio_preventivo e exposicao_residual_em_analise)
    ROUND(SUM(CASE WHEN eh_fraude = 1 THEN valor ELSE 0 END), 2) AS valor_associado_fraudes
    
-- Leitura da tabela limpa e tipada na camada Silver
FROM workspace.silver.transacoes

-- Granularidade da Gold: Consolida milhões de registros nas combinações únicas das dimensões
GROUP BY 
    tipo_transacao, 
    conta_destino_tipo, 
    dia_simulacao, 
    ordem_turno, 
    turno;


-- ==============================================================================
-- CAMADA GOLD AGENTE DE IA: Materialized View Semântica para Consulta em Linguagem Natural
-- Origem: workspace.silver.transacoes
-- Destino: workspace.gold_agente.ia_dados_transacoes
-- Objetivo: Disponibilizar dados transacionais enriquecidos semanticamente
--           (traduzindo códigos, prefixos e flags numéricas em termos descritivos)
--           para maximizar a precisão de Agentes de IA (Text-to-SQL / Genie / RAG).
-- Nota: Valores categóricos foram padronizados sem acentuação (ex: 'nao', 'manha',
--       'comercio') para evitar falhas de correspondência em filtros gerados por LLMs.
--       Colunas de saldo bruto foram omitidas para manter o contexto enxuto e focado
--       na investigação de comportamento e detecção de fraude.
-- ==============================================================================

CREATE OR REFRESH MATERIALIZED VIEW workspace.gold_agente.ia_dados_transacoes
COMMENT 'Visao semantica de transacoes financeiras enriquecida com rotulos descritivos de fraude, periodo do dia, perfil de destino e final de semana para consumo por Agentes de IA.'
TBLPROPERTIES (
    'quality' = 'gold',
    'consumo' = 'agente_ia'
)
AS
SELECT
    -- --------------------------------------------------------------------------
    -- 1. IDENTIFICAÇÃO E VALORES BASE DA TRANSAÇÃO
    -- --------------------------------------------------------------------------
    id_transacao,       -- Identificador único da transação (granularidade da tabela)
    tipo_transacao,     -- Modalidade da operação (transferencia, saque, pagamento, deposito, debito)
    valor,              -- Montante financeiro movimentado na transação
    conta_origem,       -- Identificador da conta que iniciou a movimentação
    conta_destino,      -- Identificador bruto da conta que recebeu os recursos

    -- --------------------------------------------------------------------------
    -- 2. ENRIQUECIMENTO DE ENTIDADES (PREFIXOS DO DATASET PAYSIM)
    -- --------------------------------------------------------------------------
    -- No dataset PaySim, contas de destino iniciadas com 'M' representam estabelecimentos
    -- comerciais (Merchants) e 'C' representam clientes finais (Customers). A regra abaixo
    -- evita que o Agente de IA precise conhecer convenções internas de prefixo.
    CASE
        WHEN conta_destino LIKE 'M%' THEN 'comercio'
        ELSE 'cliente'
    END AS conta_destino_tipo,

    -- --------------------------------------------------------------------------
    -- 3. TRADUÇÃO SEMÂNTICA DE INDICADORES DE FRAUDE
    -- --------------------------------------------------------------------------
    -- Converte a flag binária de fraude confirmada (1/0) para linguagem natural,
    -- facilitando perguntas diretas como "quais transações foram fraude?".
    CASE
        WHEN eh_fraude = 1 THEN 'sim'
        ELSE 'nao'
    END AS eh_fraude,

    -- Traduz o alerta do sistema legado de regras (isFlaggedFraud no PaySim, que sinaliza
    -- tentativas suspeitas de alto valor) para diferenciar alerta preventivo de fraude real.
    CASE
        WHEN flag_fraude_sistema = 1 THEN 'possivel fraude'
        ELSE 'normal'
    END AS flag_fraude_sistema,

    -- --------------------------------------------------------------------------
    -- 4. DIMENSÃO TEMPORAL E DISCRETIZAÇÃO DE PERÍODOS
    -- --------------------------------------------------------------------------
    hora_do_dia,        -- Hora exata da transação (0 a 23)

    -- Agrupa as horas em faixas semânticas do dia para responder perguntas qualitativas
    -- (ex: "ocorrem mais fraudes de madrugada?") sem exigir filtros numéricos complexos do LLM.
    CASE 
        WHEN hora_do_dia BETWEEN 0  AND 5  THEN 'madrugada'
        WHEN hora_do_dia BETWEEN 6  AND 11 THEN 'manha'
        WHEN hora_do_dia BETWEEN 12 AND 17 THEN 'tarde'
        WHEN hora_do_dia BETWEEN 18 AND 23 THEN 'noite'
    END AS turno,

    dia_simulacao,      -- Dia sequencial dentro da janela simulada (1 a 31)
    dia_semana,         -- Índice numérico do dia da semana definido na camada Silver

    -- Identifica explicitamente se a operação ocorreu no fim de semana (índices 4 e 5
    -- conforme mapeamento do calendário da simulação na Silver).
    CASE
        WHEN dia_semana IN (4, 5) THEN 'sim'
        ELSE 'nao'
    END AS eh_final_de_semana

FROM workspace.silver.transacoes;