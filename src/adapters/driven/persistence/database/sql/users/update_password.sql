UPDATE public.users
SET password_hash = %s
WHERE lower(username) = %s;
