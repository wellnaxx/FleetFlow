-- Package loads associated with the selected active-route candidate ids.
SELECT
    p.route_id,
    p.package_id,
    p.start_location,
    p.end_location,
    p.weight
FROM public.packages p
WHERE p.route_id = ANY(%s)
ORDER BY p.route_id, p.package_id;
