-- Heritage Atlas schema. Source of truth for a fresh database.
-- Every statement is idempotent so scripts/init_db.py can also upgrade an existing dev database.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  role TEXT NOT NULL DEFAULT 'reviewer' CHECK (role IN ('admin', 'reviewer', 'researcher', 'visitor')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sites (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT,                                   -- state, e.g. Gujarat
  district TEXT,
  category TEXT,                                 -- stepwell | fort | temple | palace | haveli
  lat DOUBLE PRECISION CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
  lon DOUBLE PRECISION CHECK (lon IS NULL OR lon BETWEEN -180 AND 180),
  description TEXT,                              -- original field note, never overwritten by AI
  description_source TEXT,
  description_embedding vector(384),             -- MiniLM; never compared with CLIP
  status TEXT NOT NULL DEFAULT 'canonical'
    CHECK (status IN ('canonical', 'draft', 'rejected', 'merged')),
  source TEXT,                                   -- dataset | upload | exif_cluster
  merged_into_site_id INT REFERENCES sites(id),  -- set when a draft cluster is merged
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS images (
  id SERIAL PRIMARY KEY,
  site_id INT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  original_filename TEXT,
  author TEXT,
  licence TEXT,
  licence_url TEXT,
  source_url TEXT,
  sha256 TEXT UNIQUE,
  width INT,
  height INT,
  mime_type TEXT,
  file_size BIGINT,
  captured_at TIMESTAMPTZ,                       -- EXIF DateTimeOriginal when present
  exif JSONB,                                    -- preserved camera/GPS metadata, never invented
  clip_embedding vector(512),                    -- CLIP ViT-B/32 image space
  status TEXT NOT NULL DEFAULT 'uploaded'
    CHECK (status IN ('uploaded', 'processing', 'processed', 'failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tags (
  id SERIAL PRIMARY KEY,
  label TEXT UNIQUE NOT NULL,
  tag_type TEXT NOT NULL CHECK (tag_type IN ('site_type', 'feature'))
);

CREATE TABLE IF NOT EXISTS image_tags (
  id SERIAL PRIMARY KEY,
  image_id INT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  tag_id INT NOT NULL REFERENCES tags(id),
  score REAL CHECK (score IS NULL OR score BETWEEN -1 AND 1),  -- raw cosine, NOT a probability
  status TEXT NOT NULL DEFAULT 'auto'
    CHECK (status IN ('auto', 'verified', 'rejected', 'added_by_human')),
  model_name TEXT,
  model_version TEXT,
  prompt_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (image_id, tag_id)
);

CREATE TABLE IF NOT EXISTS tag_reviews (         -- append-only audit history
  id SERIAL PRIMARY KEY,
  image_tag_id INT NOT NULL REFERENCES image_tags(id) ON DELETE CASCADE,
  reviewer TEXT NOT NULL,
  reviewer_id INT REFERENCES users(id),
  action TEXT NOT NULL CHECK (action IN ('confirm', 'reject', 'add')),
  previous_status TEXT,
  new_status TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
  id SERIAL PRIMARY KEY,
  image_id INT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL DEFAULT 'process_image',
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'done', 'failed')),
  error TEXT,
  retry_count INT NOT NULL DEFAULT 0,
  claimed_at TIMESTAMPTZ,                        -- lease start; stale rows are recovered
  worker_id TEXT,
  available_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- retry backoff gate
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest_batches (       -- folder ingestion progress and report
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

CREATE TABLE IF NOT EXISTS trails (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  created_by TEXT,
  is_public BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trail_stops (
  id SERIAL PRIMARY KEY,
  trail_id INT NOT NULL REFERENCES trails(id) ON DELETE CASCADE,
  site_id INT NOT NULL REFERENCES sites(id),
  stop_order INT NOT NULL CHECK (stop_order > 0),
  visit_date DATE,
  note TEXT,                                     -- original field note, never overwritten
  CONSTRAINT trail_stops_trail_order_key
    UNIQUE (trail_id, stop_order) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS sites_region_idx ON sites (region);
CREATE INDEX IF NOT EXISTS sites_category_idx ON sites (category);
CREATE INDEX IF NOT EXISTS images_site_idx ON images (site_id);
CREATE INDEX IF NOT EXISTS images_status_idx ON images (status);
CREATE INDEX IF NOT EXISTS image_tags_image_idx ON image_tags (image_id);
CREATE INDEX IF NOT EXISTS image_tags_status_idx ON image_tags (status);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
CREATE INDEX IF NOT EXISTS trail_stops_trail_idx ON trail_stops (trail_id, stop_order);
-- jobs_claim_idx and sites_status_idx live in migrations/002_phase1.sql: a legacy database
-- must gain the new columns before an index can reference them.

CREATE INDEX IF NOT EXISTS images_clip_hnsw ON images USING hnsw (clip_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS sites_desc_hnsw ON sites USING hnsw (description_embedding vector_cosine_ops);
