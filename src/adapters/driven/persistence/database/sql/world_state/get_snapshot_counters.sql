SELECT
    (SELECT COALESCE(MAX(customer_id), 0) + 1 FROM public.customers) AS next_customer_id,
    (SELECT COALESCE(MAX(package_id), 0) + 1 FROM public.packages) AS next_package_id,
    (SELECT COALESCE(MAX(route_id), 0) + 1 FROM public.routes) AS next_route_id;
