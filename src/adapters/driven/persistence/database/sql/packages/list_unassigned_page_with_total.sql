WITH page AS (
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
    WHERE p.status = %s AND p.route_id IS NULL
    ORDER BY p.package_id
    LIMIT %s OFFSET %s
),
totals AS (
    SELECT COUNT(*) AS total
    FROM public.packages
    WHERE status = %s AND route_id IS NULL
)
SELECT
    page.package_id,
    page.start_location,
    page.end_location,
    page.weight,
    page.status,
    page.current_location,
    page.expected_arrival,
    page.customer_id,
    page.route_id,
    page.customer_name,
    page.customer_email,
    page.customer_phone,
    totals.total
FROM totals
LEFT JOIN page
    ON TRUE
ORDER BY page.package_id;
