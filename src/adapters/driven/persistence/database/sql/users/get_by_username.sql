SELECT user_id, username, role, name, email, phone, password_hash from public.users
WHERE lower(username) = %s;