SELECT setval(
    pg_get_serial_sequence('public.customers', 'customer_id'),
    GREATEST(%s, (SELECT COALESCE(MAX(customer_id), 0) + 1 FROM public.customers)),
    false
);