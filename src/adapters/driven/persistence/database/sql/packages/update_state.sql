UPDATE public.packages
SET
    status = %s,
    current_location = %s,
    expected_arrival = %s,
    route_id = %s
WHERE package_id = %s;
