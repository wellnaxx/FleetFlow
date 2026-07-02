WITH page AS (
    SELECT
        audit_id,
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
        payload_json,
        created_at
    FROM public.audit_records
    {where_clause}
    ORDER BY occurred_at DESC, audit_id DESC
    LIMIT %s OFFSET %s
),
totals AS (
    SELECT COUNT(*) AS total
    FROM public.audit_records
    {where_clause}
)
SELECT
    page.audit_id,
    page.event_id,
    page.event_type,
    page.occurred_at,
    page.recorded_at,
    page.envelope_id,
    page.correlation_id,
    page.causation_id,
    page.source,
    page.actor_user_id,
    page.actor_username,
    page.resource_type,
    page.resource_id,
    page.action,
    page.payload_json,
    page.created_at,
    totals.total
FROM totals
LEFT JOIN page
    ON TRUE
ORDER BY page.occurred_at DESC, page.audit_id DESC;