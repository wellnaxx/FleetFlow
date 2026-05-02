SELECT 
    r.route_id,
    r.departure_time,
    r.status,
    r.truck_vehicle_id,
    rs.stop_order,
    rs.location_code
FROM public.routes r
JOIN public.route_stops rs
    ON rs.route_id = r.route_id
ORDER BY r.route_id, rs.stop_order;
