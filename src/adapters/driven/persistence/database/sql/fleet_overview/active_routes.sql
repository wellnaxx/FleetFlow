-- Active-route candidate metadata and ordered stops for schedule reconstruction.
WITH candidate_routes AS (
    SELECT
        r.route_id,
        r.departure_time,
        r.status,
        r.truck_vehicle_id
    FROM public.routes r
    WHERE r.status IN ('SCHEDULED', 'IN_PROGRESS')
      AND r.departure_time IS NOT NULL
      AND r.departure_time <= %s
      AND r.route_id > %s
      AND EXISTS (
          SELECT 1
          FROM public.route_stops candidate_stop
          WHERE candidate_stop.route_id = r.route_id
      )
    ORDER BY r.route_id
    LIMIT %s
)
SELECT
    r.route_id,
    r.departure_time,
    r.status,
    r.truck_vehicle_id,
    t.capacity AS truck_capacity,
    rs.stop_order,
    rs.location_code
FROM candidate_routes r
JOIN public.route_stops rs
    ON rs.route_id = r.route_id
LEFT JOIN public.trucks t
    ON t.vehicle_id = r.truck_vehicle_id
ORDER BY r.route_id, rs.stop_order;
