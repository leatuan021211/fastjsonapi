## JSON:API v1.1 API Guide

This guide summarizes the core JSON:API v1.1 request/response patterns for
common CRUD and query behaviors. JSON:API responses use the media type
`application/vnd.api+json`, and payloads use the standard top-level document
structure with `data`, `errors`, `meta`, and `links`.

### Common Headers

Requests and responses that carry JSON:API documents must use:

```
Content-Type: application/vnd.api+json
Accept: application/vnd.api+json
```

### List (Collection)

**Request**

```
GET /articles
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": [
    {
      "type": "articles",
      "id": "1",
      "attributes": {
        "title": "Rails is Omakase"
      }
    }
  ],
  "links": {
    "self": "/articles"
  }
}
```

### Retrieve (Single Resource)

**Request**

```
GET /articles/1
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "id": "1",
    "attributes": {
      "title": "Rails is Omakase"
    }
  }
}
```

### Create

**Request**

```
POST /articles
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "attributes": {
      "title": "Rails is Omakase"
    }
  }
}
```

**Response**

```
HTTP/1.1 201 Created
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "id": "1",
    "attributes": {
      "title": "Rails is Omakase"
    }
  }
}
```

### Update

**Request**

```
PATCH /articles/1
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "id": "1",
    "attributes": {
      "title": "Updated Title"
    }
  }
}
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "id": "1",
    "attributes": {
      "title": "Updated Title"
    }
  }
}
```

### Delete

**Request**

```
DELETE /articles/1
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 204 No Content
```

### Filter (Implementation-Specific)

JSON:API allows filtering but leaves the semantics to the implementation.
Use the `filter` query parameter family.

**Simple Filter Format**

```
GET /articles?filter[author]=doe&filter[published]=true
Accept: application/vnd.api+json
```

**Complex Filter Format (JSON Array)**

You can pass complex filters as a JSON array in the `filter` query parameter:

```
GET /articles?filter=[{"field":"name","op":"ilike","val":"%john%"},{"or":[{"and":[{"field":"age","op":"gt","val":60},{"field":"age","op":"lt","val":70}]}]}]
Accept: application/vnd.api+json
```

**Filter Operators**

- `eq` - equals (default)
- `ne`, `neq`, `!=` - not equals
- `gt` - greater than
- `gte`, `ge` - greater than or equal
- `lt` - less than
- `lte`, `le` - less than or equal
- `ilike`, `like` - case-insensitive LIKE (SQL)
- `in` - value in list
- `not_in`, `nin` - value not in list
- `is_null`, `null` - is NULL
- `is_not_null`, `not_null` - is not NULL
- `between` - value between two values (val must be [min, max])

**Logical Operators**

- `and` - all conditions must be true
- `or` - at least one condition must be true

**Filter Structure**

```json
[
  {
    "field": "name",
    "op": "ilike",
    "val": "%john%"
  },
  {
    "or": [
      {
        "and": [
          {"field": "age", "op": "gt", "val": 60},
          {"field": "age", "op": "lt", "val": 70}
        ]
      }
    ]
  }
]
```

**Response**: same as list response, filtered server-side.

### Include (Related Resources)

Use `include` to side-load related resources.

**Request**

```
GET /articles?include=author,comments
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": [
    {
      "type": "articles",
      "id": "1",
      "relationships": {
        "author": {
          "data": { "type": "people", "id": "9" }
        }
      }
    }
  ],
  "included": [
    {
      "type": "people",
      "id": "9",
      "attributes": { "name": "Jane Doe" }
    }
  ]
}
```

### Sparse Fieldsets

Use `fields[type]` to limit returned attributes per resource type.

**Request**

```
GET /articles?fields[articles]=title,created
Accept: application/vnd.api+json
```

**Response**: returns only the requested fields in `attributes`.

### Sorting

Use `sort` with comma-separated fields. Prefix with `-` for descending order.

**Request**

```
GET /articles?sort=created,-title
Accept: application/vnd.api+json
```

**Response**: list response sorted server-side.

### Pagination (Implementation-Specific)

JSON:API provides the `page` parameter family but does not mandate a strategy.
Common strategies include `page[number]`/`page[size]` or `page[offset]`/`page[limit]`.

**Request**

```
GET /articles?page[number]=2&page[size]=10
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": [],
  "links": {
    "self": "/articles?page[number]=2&page[size]=10",
    "first": "/articles?page[number]=1&page[size]=10",
    "prev": "/articles?page[number]=1&page[size]=10",
    "next": "/articles?page[number]=3&page[size]=10",
    "last": "/articles?page[number]=10&page[size]=10"
  }
}
```

## Fetching (List/Retrieve, Filtering, Fieldsets, Include, Sort, Response)

This section applies the JSON:API v1.1 fetching guidance to list/retrieve
endpoints and related query parameters.

### Fetching a Collection (List)

Responses return a top-level `data` array and may include `links` and `meta`.

**Request**

```
GET /articles
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": [
    {
      "type": "articles",
      "id": "1",
      "attributes": {
        "title": "Rails is Omakase"
      },
      "relationships": {
        "author": {
          "data": { "type": "people", "id": "9" }
        }
      }
    }
  ],
  "links": {
    "self": "/articles"
  }
}
```

### Fetching a Resource (Retrieve)

Responses return a single resource object in `data`.

**Request**

```
GET /articles/1
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "articles",
    "id": "1",
    "attributes": {
      "title": "Rails is Omakase"
    }
  }
}
```

### Filtering (Implementation-Specific)

JSON:API allows `filter` but leaves semantics to the implementation. The
`filter` family supports both fields and relationship paths.

**Request**

```
GET /articles?filter[author.name]=Doe&filter[published]=true
Accept: application/vnd.api+json
```

### Sparse Fieldsets

Limit returned fields per resource type.

**Request**

```
GET /articles?fields[articles]=title,created
Accept: application/vnd.api+json
```

### Include

Include related resources via relationship paths. Included resources appear
in the `included` array.

**Request**

```
GET /articles?include=author,comments
Accept: application/vnd.api+json
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/vnd.api+json

{
  "data": [
    {
      "type": "articles",
      "id": "1",
      "relationships": {
        "author": {
          "data": { "type": "people", "id": "9" }
        }
      }
    }
  ],
  "included": [
    {
      "type": "people",
      "id": "9",
      "attributes": {
        "name": "Jane Doe"
      }
    }
  ]
}
```

### Sorting

Sort by comma-separated fields, use `-` for descending order. Relationship
paths may be supported by the implementation.

**Request**

```
GET /articles?sort=created,-title
Accept: application/vnd.api+json
```

### Response Shape

Successful fetches return `data` plus optional `included`, `links`, and `meta`.
Errors return a top-level `errors` array.
