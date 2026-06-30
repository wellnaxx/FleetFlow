CREATE TABLE IF NOT EXISTS public.audit_records (
    audit_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id        UUID NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
    occurred_at     TIMESTAMP NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    envelope_id     UUID NOT NULL,
    correlation_id  UUID NOT NULL,
    causation_id    UUID,
    source          VARCHAR(50) NOT NULL,
    actor_user_id   INT REFERENCES public.users(user_id),
    actor_username  VARCHAR(50),
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     VARCHAR(100),
    action          VARCHAR(50) NOT NULL,
    payload_json    JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_records_event_id_unique
    ON public.audit_records (event_id);

CREATE INDEX IF NOT EXISTS idx_audit_records_resource
    ON public.audit_records (resource_type, resource_id, occurred_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_actor
    ON public.audit_records (actor_user_id, occurred_at DESC, audit_id DESC)
    WHERE actor_user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_records_event_type
    ON public.audit_records (event_type, occurred_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_action
    ON public.audit_records (action, occurred_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_source
    ON public.audit_records (source, occurred_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_occurred_at
    ON public.audit_records (occurred_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_created_at
    ON public.audit_records (created_at DESC, audit_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_records_correlation
    ON public.audit_records (correlation_id, occurred_at DESC, audit_id DESC);
