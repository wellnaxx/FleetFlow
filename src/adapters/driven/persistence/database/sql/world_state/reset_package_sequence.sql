SELECT setval(
    pg_get_serial_sequence('public.packages', 'package_id'),
    GREATEST(%s, (SELECT COALESCE(MAX(package_id), 0) + 1 FROM public.packages)),
    false
);