INSERT INTO public.packages (
    start_location,
    end_location,
    weight,
    customer_id
)
VALUES (%s, %s, %s, %s)
RETURNING package_id;