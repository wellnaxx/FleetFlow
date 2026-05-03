INSERT INTO public.trucks (
    vehicle_id,
    name,
    capacity,
    max_range,
    status,
    current_location,
    busy_from,
    busy_until,
    in_transit_to
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
