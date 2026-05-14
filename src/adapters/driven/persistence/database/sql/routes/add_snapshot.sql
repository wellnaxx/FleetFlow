INSERT INTO public.routes (
    route_id,
    departure_time,
    status,
    truck_vehicle_id
)
VALUES (%s, %s, %s, %s);
