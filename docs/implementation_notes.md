## Implementation Notes

### 2026-01-15

- Added JSON:API v1.1 API guide covering CRUD, filtering, includes, sparse
  fieldsets, sorting, and pagination.
- Added DRF-style JSON:API v1.1 template package with stubs and structure.
- Added schema, middleware, and utility stubs for JSON:API parsing.
- Implemented core builders, serializers, query parsing, router/viewset wiring,
  SQLAlchemy data layer, and pagination helpers.
- Implemented JSON:API filter parsing for field, relationship paths, and
  complex logical filters.
- Added `examples/jsonapi_example_app.py` demonstrating models, relationships,
  and JSON:API viewsets.
- Added `aiosqlite` dependency for the async SQLite example app.
- Added `greenlet` dependency required by SQLAlchemy async engine.
- Added seed data helper and `/seed` endpoint to the example app.
- Applied JSON:API fetching guidance for list/retrieve, filtering, fieldsets,
  include, sorting, and response shape in `docs/jsonapi_api.md`.
- Implemented include loading with joinedload/selectinload by relationship type.
- Added relationship links and included resources in JSON:API responses.
- Added relationship `data` with id/type identifiers in responses.
- Avoided async lazy-loads when building relationship identifiers.
- Added sparse fieldset support for main and included resources.
- Treat empty sparse fieldsets as full resource selection.
- Applied sparse fieldsets to SQLAlchemy load_only for main/included queries.
- Added relationship path support for sorting.
- Included all nested relationship levels in `included` payloads.
- Added comment author relationship to support `comments.author`.
- Added per-path included serializer mapping (e.g. `comments.author`).
- Omit relationship objects when relationship data is empty or null.
- Expanded example seed data with more users, articles, and comments.
- Include API prefix in relationship `links.related` URLs.
- Added pagination links (self/first/last/next) for list endpoints.
- Switched pagination strategy to page[offset]/page[limit].
- Sparse fieldsets now use database table names only (no relation aliases).
- Added `self` and `related` relationship links per JSON:API examples.
- Added photo endpoints to match JSON:API create example.
- Added OpenAPI metadata and endpoint docs in the example app.
- Added example query strings in the example app docstring.
- Added OpenAPI query parameters for include/sort/fields/pagination on list/retrieve.
- Added relationship linkage endpoint `GET /{resource_type}/{id}/relationships/{relationship}` 
  that returns relationship object with `links` (self/related) and `data` (type/id identifiers).
- Added `allowed_actions` attribute to `JSONAPIViewSet` to configure which actions 
  (list, retrieve, create, update, destroy, relationship) are enabled per viewset.
- Router now respects `allowed_actions` when registering routes, allowing read-only or 
  restricted viewsets.
- Tests: `pytest` (fails: no tests collected / coverage no data).
## Implementation Notes

### 2026-01-15 — Parse query params in ViewSet
- Moved request parsing for include/filter/sort/fields into `JSONAPIViewSet` and pass to `JSONAPIDataLayer`.
- Updated data layer list/retrieve to accept parsed params instead of reading request directly.
- Tests: `pytest`
