INSERT INTO public.users (
    username,
    role,
    name,
    email,
    phone,
    password_hash
)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING user_id;
