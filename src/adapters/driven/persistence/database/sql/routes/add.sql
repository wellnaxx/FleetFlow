INSERT INTO public.routes (departure_time, status)
VALUES (%s, %s)
RETURNING route_id;