ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 1;

DO $$
BEGIN
    ALTER TABLE public.users
    ADD CONSTRAINT chk_users_token_version_positive
    CHECK (token_version >= 1);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;