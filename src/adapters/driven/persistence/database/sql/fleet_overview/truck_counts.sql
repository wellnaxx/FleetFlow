-- Truck assignment totals and the overlapping unknown-location count.
SELECT
    COUNT(*) FILTER (WHERE status = 'Free') AS free,
    COUNT(*) FILTER (WHERE status = 'On the way') AS on_the_way,
    COUNT(*) FILTER (WHERE current_location IS NULL) AS unknown_location
FROM public.trucks;
