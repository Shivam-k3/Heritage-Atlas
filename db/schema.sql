CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sites (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT,
  category TEXT,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION,
  description TEXT,                      -- original field note, never overwritten by AI
  description_embedding vector(384),     -- Sentence-Transformers (MiniLM)
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE images (
  id SERIAL PRIMARY KEY,
  site_id INT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  author TEXT, licence TEXT, source_url TEXT,   -- attribution is per image
  clip_embedding vector(512),                   -- CLIP ViT-B/32 image space
  status TEXT NOT NULL DEFAULT 'uploaded',      -- uploaded|processed|failed
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tags (
  id SERIAL PRIMARY KEY,
  label TEXT UNIQUE NOT NULL,
  tag_type TEXT NOT NULL                        -- site_type|feature
);

CREATE TABLE image_tags (
  id SERIAL PRIMARY KEY,
  image_id INT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  tag_id INT NOT NULL REFERENCES tags(id),
  score REAL,                                   -- raw cosine similarity, NOT a probability
  status TEXT NOT NULL DEFAULT 'auto',          -- auto|verified|rejected|added_by_human
  UNIQUE (image_id, tag_id)
);

CREATE TABLE tag_reviews (                      -- audit history, append-only
  id SERIAL PRIMARY KEY,
  image_tag_id INT NOT NULL REFERENCES image_tags(id) ON DELETE CASCADE,
  reviewer TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE jobs (
  id SERIAL PRIMARY KEY,
  image_id INT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL DEFAULT 'process_image',
  status TEXT NOT NULL DEFAULT 'pending',       -- pending|running|done|failed
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE trails (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL, description TEXT,
  created_by TEXT, is_public BOOLEAN DEFAULT false
);

CREATE TABLE trail_stops (
  id SERIAL PRIMARY KEY,
  trail_id INT NOT NULL REFERENCES trails(id) ON DELETE CASCADE,
  site_id INT NOT NULL REFERENCES sites(id),
  stop_order INT NOT NULL,
  visit_date DATE, note TEXT
);

CREATE INDEX images_clip_hnsw ON images USING hnsw (clip_embedding vector_cosine_ops);
CREATE INDEX sites_desc_hnsw ON sites USING hnsw (description_embedding vector_cosine_ops);
