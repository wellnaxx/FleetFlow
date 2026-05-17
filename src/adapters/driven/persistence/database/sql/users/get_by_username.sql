SELECT user_id, username, role, name, email, phone, password_hash, token_version from public.users
WHERE lower(username) = %s;
