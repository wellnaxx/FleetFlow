INSERT INTO public.packages (
    package_id,
    start_location,
    end_location,
    weight,
    status,
    current_location,
    expected_arrival,
    customer_id,
    route_id
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);