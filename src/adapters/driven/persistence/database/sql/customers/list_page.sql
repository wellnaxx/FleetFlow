SELECT customer_id, name, email, phone
FROM public.customers
ORDER BY customer_id
LIMIT %s OFFSET %s;
