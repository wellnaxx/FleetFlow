SELECT setval(
    pg_get_serial_sequence('public.routes', 'route_id'),
    GREATEST(%s, (SELECT COALESCE(MAX(route_id), 0) + 1 FROM public.routes)),
    false
);