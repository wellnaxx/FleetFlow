SELECT
    audit_id,
    event_id,
    event_version,
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
    payload_json,
    created_at
FROM public.audit_records
{where_clause}
ORDER BY occurred_at DESC, audit_id DESC
LIMIT %s OFFSET %s;