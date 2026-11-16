# CONTRATO DE INTEGRAÇÃO — MACHINE LEARNING E GOOGLE ADK

**Projeto:** Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes
**Responsável pela ferramenta ML:** FinOps / Machine Learning
**Consumidor:** Engenharia de Inteligência Artificial
**Data:** 16/11/2026
**Status:** Ferramenta desenvolvida e testes funcionais aprovados

## 1. Objetivo

Definir a interface de comunicação entre o módulo de Machine Learning e o agente de Inteligência Artificial desenvolvido com Google ADK.

O objetivo é permitir que o agente solicite a análise individual de transações financeiras e receba resultados estruturados para interpretação e apresentação ao usuário.

## 2. Componentes envolvidos

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Scoring ML | `src/finops_ml/fraud_scoring.py` | Preparação, classificação e estimativa de exposição |
| Ferramenta ADK | `src/tools/ml_scoring_tool.py` | Interface de comunicação entre o agente e o modelo |
| Modelo treinado | `models/lightgbm_fraud_detector.joblib` | Classificação das transações |
| Metadados | `models/lightgbm_fraud_detector_metadata.json` | Parâmetros e configurações do modelo |
| Agente | `src/ai_agent/fraud_analysis_agent/agent.py` | Orquestração das ferramentas |

## 3. Interface disponibilizada

**Função:** `analisar_transacao()`

**Localização:** `src/tools/ml_scoring_tool.py`

### Parâmetros de entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `amount` | float | Sim | Valor original da transação |
| `tipo_transacao` | str | Sim | Tipo da operação financeira |
| `destino_eh_comercio` | bool | Sim | Identifica destinatário comercial |

Tipos de transação aceitos:

- CASH_IN
- CASH_OUT
- DEBIT
- PAYMENT
- TRANSFER

### Exemplo de chamada

```python
resultado = analisar_transacao(
    amount=20000.0,
    tipo_transacao="TRANSFER",
    destino_eh_comercio=True
)
```

## 4. Estrutura da resposta

A ferramenta retorna um dicionário compatível com a serialização JSON.

Exemplo ilustrativo:

```json
{
  "status": "sucesso",
  "modelo": "LightGBM",
  "experimento": "Sem ponderação",
  "analise": {
    "tipo_transacao": "TRANSFER",
    "valor_transacao": 20000.0,
    "fraud_score": 0.013,
    "limiar_aplicado": 0.012455002510276548,
    "alerta_fraude": true,
    "status_analise": "ALERTA",
    "exposicao_financeira_sinalizada": 20000.0
  },
  "ressalvas": [
    "O score não representa uma probabilidade calibrada.",
    "Um alerta indica uma transação que merece investigação.",
    "A exposição sinalizada não representa prejuízo confirmado.",
    "O modelo foi desenvolvido com dados sintéticos PaySim."
  ]
}
```

O exemplo não representa uma previsão real do modelo.

## 5. Configuração do modelo

| Parâmetro | Valor |
|---|---|
| Algoritmo | LightGBM |
| Experimento | Sem ponderação |
| Melhor iteração | 12 |
| Features | 4 |
| Limiar | 0,012455002510276548 |
| Capping superior | 502605.225 |

Features utilizadas:

1. `amount`
2. `type`
3. `destino_eh_comercio`
4. `faixa_valor`

O módulo carrega o modelo e os metadados salvos, sem necessidade de realizar novo treinamento.

## 6. Regras de interpretação

- `ALERTA`: o score retornado pelo modelo é maior ou igual ao limiar definido.
- `SEM_ALERTA`: o score está abaixo do limiar.
- O score não representa uma probabilidade calibrada de fraude.
- Um alerta não confirma a ocorrência de fraude.
- A exposição financeira sinalizada utiliza o valor original da transação.
- A exposição não representa prejuízo real, valor recuperado ou perda evitada.

## 7. Validações realizadas

### 7.1 Compilação

Os arquivos `fraud_scoring.py` e `ml_scoring_tool.py` passaram pela validação de sintaxe Python.

### 7.2 Testes funcionais

Foram realizadas verificações de preparação das features, classificação, geração de alertas e resumo financeiro.

### 7.3 Avaliação no conjunto completo de teste

| Indicador | Resultado |
|---|---:|
| Transações analisadas | 89.466 |
| Alertas | 816 |
| Verdadeiros positivos | 280 |
| Falsos positivos | 536 |
| Verdadeiros negativos | 87.678 |
| Falsos negativos | 972 |

A matriz de confusão produzida pelo módulo coincidiu com os resultados documentados no experimento original.

### 7.4 Teste individual da ferramenta

Foram validados dois cenários:

- Transação classificada como `SEM_ALERTA`.
- Transação classificada como `ALERTA`.

Ambos retornaram respostas estruturadas com sucesso.

## 8. Responsabilidades de integração

**FinOps / Machine Learning:**

- Disponibilizar o modelo e os metadados.
- Manter o módulo de scoring.
- Documentar mudanças na interface.
- Comunicar atualizações de features e parâmetros.

**Engenharia de Inteligência Artificial:**

- Importar a função `analisar_transacao`.
- Registrar a função como ferramenta do Google ADK.
- Interpretar a resposta estruturada.
- Apresentar resultados e ressalvas ao usuário.
- Tratar respostas de erro sem inventar resultados.

## 9. Exemplo de registro no agente ADK

A integração deverá importar a função pelo caminho correspondente à estrutura do repositório:

```python
from src.tools.ml_scoring_tool import analisar_transacao
```

A função poderá ser adicionada à lista de ferramentas do agente Google ADK:

```python
tools=[
    seach_in_sql,
    analisar_transacao,
]
```

O exemplo deverá ser adaptado ao arquivo `agent.py` existente, preservando as ferramentas já configuradas.

## 10. Limitações conhecidas e próximos cuidados

O LightGBM apresentou concentração de scores no conjunto de teste, com o maior score coincidindo com o limiar selecionado na validação.

Essa característica exige investigação adicional antes de qualquer utilização operacional.

Outros cuidados:

- Versionar modelo e metadados em conjunto.
- Manter as quatro features compatíveis com o treinamento.
- Não expor informações sensíveis nas respostas do agente.
- Não interpretar alertas como confirmações de fraude.
- Considerar os dados PaySim como sintéticos.
- Validar segurança, desempenho e estabilidade antes de implantação.

## 11. Status da entrega

**Concluído pela frente FinOps / ML:**

- Desenvolvimento do módulo de scoring.
- Persistência do modelo e metadados.
- Carregamento do modelo salvo.
- Validação da classificação.
- Testes de alertas positivos e negativos.
- Ferramenta independente para consumo pelo agente.
- Contrato técnico de integração.

**Pendente de integração conjunta:**

- Registro da ferramenta no agente Google ADK.
- Testes de comunicação ponta a ponta.
- Validação das respostas do agente.
- Demonstração integrada da solução.

---

**Grupo 5 — Projeto Integrador**
Cidade Inteligente: Auditoria e Prevenção de Fraudes
