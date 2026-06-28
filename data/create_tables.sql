-- LabOps Agent — Database Schema
-- Run this in Supabase SQL Editor before seed_data.sql

CREATE TABLE IF NOT EXISTS inventory (
  id SERIAL PRIMARY KEY,
  reagent_name TEXT NOT NULL UNIQUE,
  current_stock NUMERIC NOT NULL,
  unit TEXT NOT NULL DEFAULT 'tests',
  criticality TEXT NOT NULL DEFAULT 'medium',
  reorder_lead_time_days INTEGER NOT NULL DEFAULT 7,
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_demo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS demand_history (
  id SERIAL PRIMARY KEY,
  reagent_name TEXT NOT NULL,
  date DATE NOT NULL,
  quantity NUMERIC NOT NULL,
  test_type TEXT,
  is_demo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  reagent_name TEXT NOT NULL,
  quantity NUMERIC NOT NULL,
  supplier TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT now(),
  is_demo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS alerts_log (
  id SERIAL PRIMARY KEY,
  reagent_name TEXT NOT NULL,
  predicted_stockout_date DATE,
  severity TEXT NOT NULL DEFAULT 'warning',
  explanation TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  is_demo BOOLEAN DEFAULT true
);
