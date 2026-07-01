# Dataset Provenance — LabOps Agent

## Source
B2B clinical laboratory derivation data from Labmedicina
(Swiss Medical Group / Diagnóstico Maipú), Argentina.
Collected during 4 years of B2B Key Account Management operations.

## Dataset characteristics
- Records: 414,289 rows
- Period: January 2025 – May 2026 (17 months)
- Coverage: 14+ provinces (Buenos Aires, San Juan, Chaco,
  Corrientes, Capital Federal, Mendoza, Córdoba, and more)
- Fields: client_code, client_name, province,
  determination_code, determination_name, sector,
  medical_sector, quantity, unit_cost, total_cost,
  unit_price, total_price, year
- Unique clients: 507 B2B laboratory clients
- Top sector: Endocrinología (174,024 records)

## Privacy compliance
- No patient data (PHI) of any kind
- No patient names, IDs, diagnoses, or personal information
- Data represents institutional B2B operational volumes only
- Compliant with Ley 25.326 (Argentina Personal Data Protection)
- Unit of analysis: monthly derivation volume per test type
  per laboratory client (institutional, not individual)

## Key findings used for model calibration
- TSH is the highest-volume test type
- TSH demand peaks in Argentine autumn (March-May),
  not winter — contrary to Northern Hemisphere assumptions
- Peak/trough ratio: 2.50x (March 52,184 vs December 20,897 units)
- Hemograma shows moderate variation (CV=0.359),
  higher January-May, lower June-December
- Glucosa, Ionograma, Urea, Creatinina: stable year-round

## Usage in this project
Raw data used to:
1. Identify correct seasonal patterns per test type
2. Calibrate Prophet model peak_mult and peak_months parameters
3. Validate that TSH autumn peak is real, not assumed

Raw data is NOT included in this repository (proprietary B2B).
Derived calibration parameters: backend/prediction.py _SEASONAL_PATTERNS.

## Data authorization
Used with authorization in the context of B2B KAM operations
and internal business intelligence development at Labmedicina.
