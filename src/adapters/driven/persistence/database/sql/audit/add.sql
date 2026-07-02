INSERT INTO public.audit_records (
    event_id,
    event_type,
    occurred_at,
    recorded_at,
    envelope_id,
    correlation_id,
    causation_id,
    source,
    actor_user_id,
    actor_username,
    resource_type,
    resource_id,
    action,
    payload_json
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;