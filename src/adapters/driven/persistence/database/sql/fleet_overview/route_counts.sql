-- Route totals plus coarse candidates whose final ETA is calculated in Python.
SELECT
    COUNT(*) FILTER (WHERE r.status = 'PLANNED') AS planned,
    COUNT(*) FILTER (WHERE r.status = 'SCHEDULED') AS scheduled,
    COUNT(*) FILTER (WHERE r.status = 'IN_PROGRESS') AS in_progress,
    COUNT(*) FILTER (WHERE r.status = 'COMPLETED') AS completed,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'route_id', r.route_id,
                'departure_time', r.departure_time,
                'stops', rs.stops_data
            )
            ORDER BY r.route_id
        ) FILTER (
            WHERE r.status IN ('SCHEDULED', 'IN_PROGRESS')
                AND r.departure_time IS NOT NULL
                AND r.departure_time <= %s
        ),
        '[]'::jsonb
    ) AS past_due_candidates
FROM public.routes r
LEFT JOIN (
    SELECT
        route_id,
        jsonb_agg(
            jsonb_build_object(
                'stop_order', stop_order,
                'location_code', location_code
            ) ORDER BY stop_order
        ) AS stops_data
    FROM public.route_stops
    GROUP BY route_id
) rs ON rs.route_id = r.route_id;
