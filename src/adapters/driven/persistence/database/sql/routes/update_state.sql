UPDATE public.routes
SET
    departure_time = %s,
    status = %s,
    truck_vehicle_id = %s
WHERE route_id = %s;
