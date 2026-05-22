WITH page AS (
    SELECT customer_id, name, email, phone
    FROM public.customers
    ORDER BY customer_id
    LIMIT %s OFFSET %s
),
totals AS (
    SELECT COUNT(*) AS total
    FROM public.customers
)
SELECT
    page.customer_id,
    page.name,
    page.email,
    page.phone,
    totals.total
FROM totals
LEFT JOIN page
    ON TRUE
ORDER BY page.customer_id;
