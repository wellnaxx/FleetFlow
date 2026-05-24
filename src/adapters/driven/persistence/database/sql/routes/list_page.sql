WITH route_page AS (
    SELECT route_id
    FROM public.routes
    ORDER BY route_id
    LIMIT %s OFFSET %s
)
SELECT
    r.route_id,
    r.departure_time,
    r.status,
    r.truck_vehicle_id,
    rs.stop_order,
    rs.location_code
FROM route_page rp
JOIN public.routes r
    ON r.route_id = rp.route_id
JOIN public.route_stops rs
    ON rs.route_id = r.route_id
ORDER BY r.route_id, rs.stop_order;
