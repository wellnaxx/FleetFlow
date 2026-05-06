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
FROM public.trucks t
JOIN public.routes r
    ON r.truck_vehicle_id = t.vehicle_id
WHERE r.route_id IS NOT NULL
ORDER BY t.vehicle_id;