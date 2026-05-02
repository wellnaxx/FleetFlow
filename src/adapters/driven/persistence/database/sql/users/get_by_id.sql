SELECT user_id, username, role, name, email, phone, password_hash
FROM public.users
WHERE user_id = %s;
