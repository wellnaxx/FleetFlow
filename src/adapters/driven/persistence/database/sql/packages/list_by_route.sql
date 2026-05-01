SELECT
    p.package_id,
    p.start_location,
    p.end_location,
    p.weight,
    p.status,
    p.current_location,
    p.expected_arrival,
    p.customer_id,
    p.route_id,
    c.name AS customer_name,
    c.email AS customer_email,
    c.phone AS customer_phone
FROM public.packages p
JOIN public.customers c
    ON c.customer_id = p.customer_id
WHERE p.route_id = %s
ORDER BY p.package_id;
