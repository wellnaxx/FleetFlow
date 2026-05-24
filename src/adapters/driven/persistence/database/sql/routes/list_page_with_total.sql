WITH route_page AS (
    SELECT route_id
    FROM public.routes
    ORDER BY route_id
    LIMIT %s OFFSET %s
),
route_rows AS (
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
),
totals AS (
    SELECT COUNT(*) AS total
    FROM public.routes
)
SELECT
    route_rows.route_id,
    route_rows.departure_time,
    route_rows.status,
    route_rows.truck_vehicle_id,
    route_rows.stop_order,
    route_rows.location_code,
    totals.total
FROM totals
-- Cross-join ensures total is returned even when route_rows is empty
LEFT JOIN route_rows
    ON TRUE
ORDER BY route_rows.route_id, route_rows.stop_order;
