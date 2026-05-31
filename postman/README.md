# FleetFlow Postman Collection

Import both files into Postman:

- `FleetFlow API.postman_collection.json`
- `FleetFlow local.postman_environment.json`

Before running the collection, set `adminPassword` in the environment to the password for the existing initial manager account. That account must exist in the active user repository selected by `PERSISTENCE_BACKEND`; users from `users.json` are not visible when the API is running in PostgreSQL mode.

The collection expects the API to be running at:

```text
http://127.0.0.1:8000/api
```

Override `baseUrl` in the environment if the API is running elsewhere.

The first request logs in as the manager using OAuth2-style `application/x-www-form-urlencoded` form data and initializes per-run variables. Run the collection in order so tokens and created resource IDs are captured before dependent requests execute.

The API requires separate randomly generated JWT secrets before login or refresh can issue tokens:

```text
JWT_ACCESS_SECRET=<openssl rand -hex 32>
JWT_REFRESH_SECRET=<different openssl rand -hex 32>
```

Password changes, manager password resets, and logout revoke existing tokens through token-version changes. The collection includes token-revocation checks for those flows.

The collection covers:

- Authentication happy paths and token failures.
- User registration, duplicate username, permission denial, password change/reset, and token revocation.
- Customer and truck listing.
- Package create/list/get/delete, validation errors, missing resources, and suitable-route lookup.
- Route create/list/get/delete, assignment workflows, suitable-truck lookup, pagination validation, and missing-resource paths.
- State save/load import-export paths, invalid paths, missing snapshots, and employee permission denial.

Database `500` paths are documented in API code but are not directly triggered here because they require controlled persistence-adapter failure injection rather than normal public API input.
