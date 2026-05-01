SELECT package_id, start_location, end_location, weight, status, current_location, expected_arrival, customer_id, route_id
FROM public.packages
WHERE package_id = %s;