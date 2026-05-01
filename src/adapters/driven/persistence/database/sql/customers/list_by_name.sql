SELECT customer_id, name, email, phone
FROM public.customers
WHERE lower(name) = %s
ORDER BY customer_id;