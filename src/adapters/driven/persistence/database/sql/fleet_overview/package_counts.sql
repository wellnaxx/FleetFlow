-- Package lifecycle totals and overlapping operational counts at one business time.
SELECT
    COUNT(*) FILTER (WHERE status = 'To Do') AS todo,
    COUNT(*) FILTER (WHERE status = 'In Progress') AS in_progress,
    COUNT(*) FILTER (WHERE status = 'Done') AS done,
    COUNT(*) FILTER (WHERE route_id IS NULL) AS unassigned,
    COUNT(*) FILTER (
        WHERE status <> 'Done'
            AND expected_arrival IS NOT NULL
            AND expected_arrival < %s
    ) AS past_due
FROM public.packages;
