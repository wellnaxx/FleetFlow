SELECT
    t.vehicle_id,
    t.name,
    t.capacity,
    t.max_range,
    t.status,
    t.current_location,
    t.busy_from,
    t.busy_until,
    t.in_transit_to
FROM public.routes r
JOIN public.trucks t
    ON t.vehicle_id = r.truck_vehicle_id
WHERE r.route_id = %s;