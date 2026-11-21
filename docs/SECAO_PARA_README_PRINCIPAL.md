## Status do LightGBM V2 — 21/11/2026

- Modelo LightGBM V2 congelado: 137 iterações; limiar `0.08341406734582016`.
- Avaliação independente: 89.466 transações; Precision 0.778195; Recall 0.496006; F1 0.605854; ROC-AUC 0.970289; Average Precision 0.659264.
- Scoring persistido: 89.466/89.466 transações; 798 alertas; 0 duplicados; 0 transações sem score; 0 registros fora do teste.
- SHA-256: `29f183255645bbcdef16c96ca802f02d121476548a18e224cad82298e488c076`.
- Relatório técnico: `docs/RELATORIO_FINAL_LIGHTGBM_V2.md`.
- Guia operacional: `docs/GUIA_OPERACIONAL_LIGHTGBM_V2.md`.
- SQL Views nativas do Databricks: `sql/lightgbm_v2_databricks_views.sql`.
- Dashboard nativo Databricks AI/BI: `dashboard/databricks/README.md`.

**Nota:** PaySim é sintético; os alertas não são fraudes confirmadas e a exposição sinalizada não é prejuízo ou valor recuperado.


**Arquitetura de apresentação:** toda a camada de dados, SQL Views e dashboard fica no workspace Databricks.
