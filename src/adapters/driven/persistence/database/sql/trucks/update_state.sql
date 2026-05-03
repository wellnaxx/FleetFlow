UPDATE public.trucks
SET
    status = %s,
    current_location = %s,
    busy_from = %s,
    busy_until = %s,
    in_transit_to = %s
WHERE vehicle_id = %s;
