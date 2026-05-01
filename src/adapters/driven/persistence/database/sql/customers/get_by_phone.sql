SELECT customer_id, name, email, phone
FROM public.customers
WHERE phone = %s;