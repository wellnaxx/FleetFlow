SELECT COUNT(*) AS total
FROM public.packages
WHERE status = %s AND route_id IS NULL;
