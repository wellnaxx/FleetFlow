SELECT
    vehicle_id,
    name,
    capacity,
    max_range,
    status,
    current_location,
    busy_from,
    busy_until,
    in_transit_to
FROM public.trucks
ORDER BY vehicle_id;
