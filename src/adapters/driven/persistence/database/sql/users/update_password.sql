UPDATE public.users
SET password_hash = %s, token_version = token_version + 1
WHERE lower(username) = %s;
