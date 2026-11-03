-- Upgrade a database created by the original scaffold. Idempotent; safe to re-run.
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  role TEXT NOT NULL DEFAULT 'reviewer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sites ADD COLUMN IF NOT EXISTS district TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS description_source TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE images ADD COLUMN IF NOT EXISTS original_filename TEXT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS licence_url TEXT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS sha256 TEXT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS width INT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS height INT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS mime_type TEXT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE image_tags ADD COLUMN IF NOT EXISTS model_name TEXT;
ALTER TABLE image_tags ADD COLUMN IF NOT EXISTS model_version TEXT;
ALTER TABLE image_tags ADD COLUMN IF NOT EXISTS prompt_version TEXT;
ALTER TABLE image_tags ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE tag_reviews ADD COLUMN IF NOT EXISTS reviewer_id INT REFERENCES users(id);
ALTER TABLE tag_reviews ADD COLUMN IF NOT EXISTS previous_status TEXT;
ALTER TABLE tag_reviews ADD COLUMN IF NOT EXISTS new_status TEXT;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count INT NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE trails ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'trail_stops_trail_order_key'
  ) THEN
    ALTER TABLE trail_stops
      ADD CONSTRAINT trail_stops_trail_order_key
      UNIQUE (trail_id, stop_order) DEFERRABLE INITIALLY DEFERRED;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS images_sha256_key ON images (sha256);
CREATE INDEX IF NOT EXISTS sites_region_idx ON sites (region);
CREATE INDEX IF NOT EXISTS sites_category_idx ON sites (category);
CREATE INDEX IF NOT EXISTS images_site_idx ON images (site_id);
CREATE INDEX IF NOT EXISTS images_status_idx ON images (status);
CREATE INDEX IF NOT EXISTS image_tags_image_idx ON image_tags (image_id);
CREATE INDEX IF NOT EXISTS image_tags_status_idx ON image_tags (status);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
CREATE INDEX IF NOT EXISTS trail_stops_trail_idx ON trail_stops (trail_id, stop_order);
