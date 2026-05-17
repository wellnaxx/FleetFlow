UPDATE public.users
SET token_version = token_version + 1
WHERE user_id = %s
RETURNING
    user_id,
    username,
    role,
    name,
    email,
    phone,
    password_hash,
    token_version;