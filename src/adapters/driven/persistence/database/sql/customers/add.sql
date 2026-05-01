INSERT INTO public.customers (name, email, phone)
VALUES (%s, %s, %s)
RETURNING customer_id;