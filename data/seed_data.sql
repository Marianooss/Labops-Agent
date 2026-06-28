-- LabOps Agent — Seed Data for Supabase
-- DEMO badge visible on all synthetic data.
-- Calibrated with patterns from 414,289 B2B derivation records (Argentina).

-- ⚠️ DEMO DATA — Synthetic, calibrated with real AR patterns. Not real lab data.
-- Table: inventory
INSERT INTO inventory (reagent_name, current_stock, unit, criticality, reorder_lead_time_days, updated_at, is_demo) VALUES
('TSH', 680, 'tests', 'high', 7, now(), true),
('Hemograma', 2100, 'tests', 'critical', 5, now(), true),
('Ionograma', 1850, 'tests', 'medium', 5, now(), true),
('Glucosa', 920, 'tests', 'medium', 7, now(), true),
('Urea', 760, 'tests', 'low', 10, now(), true),
('Creatinina', 640, 'tests', 'medium', 7, now(), true);

-- ⚠️ DEMO DATA — Synthetic, calibrated with real AR patterns. Not real lab data.
-- Table: demand_history (synthetic, calibrated patterns)
-- TSH winter spike in Argentina (Jun-Aug)
INSERT INTO demand_history (reagent_name, date, quantity, test_type, is_demo) VALUES
-- 2024 historical data (Prophet seasonality calibration)
('TSH', '2024-01-15', 124, 'TSH', true),
('TSH', '2024-02-15', 119, 'TSH', true),
('TSH', '2024-03-15', 121, 'TSH', true),
('TSH', '2024-04-15', 117, 'TSH', true),
('TSH', '2024-05-15', 123, 'TSH', true),
('TSH', '2024-06-15', 196, 'TSH', true),  -- winter spike
('TSH', '2024-07-15', 203, 'TSH', true),
('TSH', '2024-08-15', 189, 'TSH', true),
('TSH', '2024-09-15', 118, 'TSH', true),
('TSH', '2024-10-15', 122, 'TSH', true),
('TSH', '2024-11-15', 116, 'TSH', true),
('TSH', '2024-12-15', 120, 'TSH', true),
('Hemograma', '2024-01-15', 208, 'Hemograma', true),
('Hemograma', '2024-03-15', 211, 'Hemograma', true),
('Hemograma', '2024-06-15', 215, 'Hemograma', true),
('Hemograma', '2024-09-15', 206, 'Hemograma', true),
('Hemograma', '2024-12-15', 207, 'Hemograma', true),
('Ionograma', '2024-01-15', 187, 'Ionograma', true),
('Ionograma', '2024-03-15', 190, 'Ionograma', true),
('Ionograma', '2024-06-15', 193, 'Ionograma', true),
('Ionograma', '2024-09-15', 185, 'Ionograma', true),
('Ionograma', '2024-12-15', 186, 'Ionograma', true),
-- 2025 historical data (Prophet seasonality calibration)
('TSH', '2025-01-15', 126, 'TSH', true),
('TSH', '2025-02-15', 118, 'TSH', true),
('TSH', '2025-03-15', 124, 'TSH', true),
('TSH', '2025-04-15', 115, 'TSH', true),
('TSH', '2025-05-15', 120, 'TSH', true),
('TSH', '2025-06-15', 198, 'TSH', true),  -- winter spike
('TSH', '2025-07-15', 207, 'TSH', true),
('TSH', '2025-08-15', 192, 'TSH', true),
('TSH', '2025-09-15', 121, 'TSH', true),
('TSH', '2025-10-15', 117, 'TSH', true),
('TSH', '2025-11-15', 123, 'TSH', true),
('TSH', '2025-12-15', 119, 'TSH', true),
('Hemograma', '2025-01-15', 209, 'Hemograma', true),
('Hemograma', '2025-03-15', 212, 'Hemograma', true),
('Hemograma', '2025-06-15', 216, 'Hemograma', true),
('Hemograma', '2025-09-15', 207, 'Hemograma', true),
('Hemograma', '2025-12-15', 208, 'Hemograma', true),
('Ionograma', '2025-01-15', 188, 'Ionograma', true),
('Ionograma', '2025-03-15', 191, 'Ionograma', true),
('Ionograma', '2025-06-15', 194, 'Ionograma', true),
('Ionograma', '2025-09-15', 186, 'Ionograma', true),
('Ionograma', '2025-12-15', 187, 'Ionograma', true),
-- 2026 current data
('TSH', '2026-01-15', 125, 'TSH', true),
('TSH', '2026-02-15', 118, 'TSH', true),
('TSH', '2026-03-15', 122, 'TSH', true),
('TSH', '2026-04-15', 119, 'TSH', true),
('TSH', '2026-05-15', 121, 'TSH', true),
('TSH', '2026-06-15', 198, 'TSH', true),  -- winter spike
('TSH', '2026-06-20', 205, 'TSH', true),
('Hemograma', '2026-06-20', 210, 'Hemograma', true),
('Ionograma', '2026-06-20', 185, 'Ionograma', true);

-- ⚠️ DEMO DATA — Synthetic, calibrated with real AR patterns. Not real lab data.
-- Table: orders
INSERT INTO orders (reagent_name, quantity, supplier, status, created_at, is_demo) VALUES
('TSH', 500, 'LabSupplier AR', 'delivered', '2026-05-01T10:00:00Z', true),
('Hemograma', 1000, 'LabSupplier AR', 'delivered', '2026-05-15T10:00:00Z', true),
('Ionograma', 900, 'LabSupplier AR', 'pending', '2026-06-20T14:30:00Z', true);

-- ⚠️ DEMO DATA — Synthetic, calibrated with real AR patterns. Not real lab data.
-- Table: alerts_log
INSERT INTO alerts_log (reagent_name, predicted_stockout_date, severity, explanation, created_at, is_demo) VALUES
('TSH', '2026-06-29', 'critical', 'TSH demand spikes in winter (Jun-Aug). Current stock will not cover projected usage.', '2026-06-25T09:00:00Z', true);
