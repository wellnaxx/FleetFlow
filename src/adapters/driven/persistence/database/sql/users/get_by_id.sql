SELECT user_id, username, role, name, email, phone, password_hash, token_version
FROM public.users
WHERE user_id = %s;
