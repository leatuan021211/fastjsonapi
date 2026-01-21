# FastAPI JSON:API

A comprehensive JSON:API v1.1 library for FastAPI with SQLAlchemy support, inspired by Django REST Framework JSON:API.

## Features

- ✅ **Full JSON:API v1.1 specification compliance** - Complete implementation of the JSON:API specification
- ✅ **FastAPI integration** - Seamless integration with FastAPI and automatic OpenAPI documentation
- ✅ **SQLAlchemy ORM support** - Full async/await support with SQLAlchemy 2.0+
- ✅ **ViewSet pattern** - DRF-style viewsets with hook-based extensibility (`before_`, `perform_`, `after_`)
- ✅ **Dependency injection** - Support for FastAPI's dependency injection system
- ✅ **Advanced filtering** - Complex filtering with nested relationships, logical operators (`and`, `or`), and multiple comparison operators
- ✅ **Nested filtering** - Filter on related resources (e.g., `filter[comment.id]=2`)
- ✅ **Sparse fieldsets** - Optimize queries with `fields[resource]=field1,field2`
- ✅ **Pagination** - Offset/limit pagination with metadata (`total`, `limit`, `offset`)
- ✅ **Sorting** - Multi-field sorting with relationship path support
- ✅ **Includes** - Eager loading of related resources with nested includes
- ✅ **Relationships** - Full support for to-one and to-many relationships
- ✅ **Related resources** - Endpoint to fetch full related resources (`/articles/1/comments`)
- ✅ **Content negotiation** - Automatic enforcement of `application/vnd.api+json` media type
- ✅ **Error handling** - JSON:API compliant error responses

## Quick Start

```python
from fastapi import Depends, FastAPI
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from fastapi_jsonapi import (
    JSONAPIRouter,
    JSONAPISerializer,
    JSONAPIViewSet,
    SQLAlchemyDataLayer,
    SQLAlchemyQueryHelper,
    StandardPagination,
)

Base = declarative_base()

# Define your SQLAlchemy models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="articles")

User.articles = relationship("Article", back_populates="author")

# Define serializers
class ArticleSerializer(JSONAPISerializer):
    class Meta:
        type_ = "articles"
        model = Article
        fields = ["id", "title", "body", "author_id"]

# Setup database
engine = create_async_engine("sqlite+aiosqlite:///./example.db")
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Dependency for database session
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Create viewset
class ArticleViewSet(JSONAPIViewSet):
    serializer_class = ArticleSerializer
    pagination_class = StandardPagination
    included_serializers = {"author": UserSerializer}

    def __init__(self, session: AsyncSession) -> None:
        query_helper = SQLAlchemyQueryHelper(model=Article)
        self.data_layer = SQLAlchemyDataLayer(
            model=Article,
            session=session,
            query_helper=query_helper,
        )

# Dependency factory for viewset
def get_article_viewset(session: AsyncSession = Depends(get_session)) -> ArticleViewSet:
    return ArticleViewSet(session)

# Setup FastAPI app
app = FastAPI()
router = JSONAPIRouter(prefix="/api/v1")

# Register viewset with dependency injection
router.register_viewset("/articles", get_article_viewset)

app.include_router(router)
```

## Usage Examples

### Filtering

**Simple filtering:**
```bash
GET /api/v1/articles?filter[title]=JSON:API
```

**Complex filtering with operators:**
```bash
GET /api/v1/articles?filter=[{"field":"title","op":"ilike","val":"%FastAPI%"},{"field":"author_id","op":"eq","val":1}]
```

**Nested filtering:**
```bash
GET /api/v1/articles?filter=[{"field":"comment.id","op":"eq","val":2}]
```

### Sparse Fieldsets

Only load specific fields:
```bash
GET /api/v1/articles?fields[articles]=title,body&fields[users]=name
```

### Pagination

```bash
GET /api/v1/articles?page[offset]=0&page[limit]=10
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "links": {
    "self": "...",
    "first": "...",
    "last": "...",
    "prev": "...",
    "next": "..."
  },
  "meta": {
    "total": 100,
    "limit": 10,
    "offset": 0
  }
}
```

### Includes (Related Resources)

```bash
GET /api/v1/articles?include=author,comments,comments.author
```

### Sorting

```bash
GET /api/v1/articles?sort=title,-created_at
```

## Advanced Features

### Custom Hooks

Override viewset hooks for custom logic:

```python
class ArticleViewSet(JSONAPIViewSet):
    async def before_list(self, request: Request, *args, **kwargs):
        # Pre-processing logic
        return None
    
    async def perform_list(self, request: Request, params, *args, **kwargs):
        # Custom list logic
        return await super().perform_list(request, params, *args, **kwargs)
    
    async def after_list(self, request: Request, document, *args, **kwargs):
        # Post-processing logic
        return document
```

### Relationship Endpoints

Access relationship data:
- **Relationship linkage**: `GET /api/v1/articles/1/relationships/author`
- **Related resources**: `GET /api/v1/articles/1/author`

## Documentation

- [API Guide](docs/jsonapi_api.md) - Complete JSON:API v1.1 API reference
- [Implementation Notes](docs/implementation_notes.md) - Development notes and decisions
- [Example Application](examples/jsonapi_example_app.py) - Full working example

## Requirements

- Python 3.9+
- FastAPI >= 0.104.0
- SQLAlchemy >= 2.0.0
- Pydantic >= 2.0.0

## License

MIT License
