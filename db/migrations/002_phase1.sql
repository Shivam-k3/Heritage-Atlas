-- Phase 1: draft sites, EXIF ingestion, job leases and retry backoff.
-- Idempotent; safe to re-run on a database created by 001_backend_expansion.sql.
ALTER TABLE sites ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'canonical';
ALTER TABLE sites ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS merged_into_site_id INT REFERENCES sites(id);

ALTER TABLE images ADD COLUMN IF NOT EXISTS captured_at TIMESTAMPTZ;
ALTER TABLE images ADD COLUMN IF NOT EXISTS exif JSONB;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS worker_id TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS available_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS ingest_batches (
  id SERIAL PRIMARY KEY,
  source_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'failed')),
  total_files INT NOT NULL DEFAULT 0,
  accepted INT NOT NULL DEFAULT 0,
  duplicates INT NOT NULL DEFAULT 0,
  rejected INT NOT NULL DEFAULT 0,
  gps_images INT NOT NULL DEFAULT 0,
  clusters INT NOT NULL DEFAULT 0,
  report JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sites_status_check') THEN
    ALTER TABLE sites ADD CONSTRAINT sites_status_check
      CHECK (status IN ('canonical', 'draft', 'rejected', 'merged'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs (status, available_at, id);
CREATE INDEX IF NOT EXISTS sites_status_idx ON sites (status);
