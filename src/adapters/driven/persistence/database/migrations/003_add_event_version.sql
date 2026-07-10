ALTER TABLE public.audit_records
    ADD COLUMN event_version INT NOT NULL DEFAULT 1
    CHECK (event_version > 0);