UPDATE public.users
SET role = %s
WHERE lower(username) = %s;
