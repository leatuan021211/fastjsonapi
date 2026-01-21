"""Example FastAPI app using the JSON:API template with relationships.

Run with:
    uvicorn examples.jsonapi_example_app:app --reload
"""
from __future__ import annotations

import os
import sys
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from fastapi_jsonapi.pagination import StandardPagination
from fastapi_jsonapi.routers import JSONAPIRouter
from fastapi_jsonapi.serializers import JSONAPISerializer
from fastapi_jsonapi.sqlalchemy import SQLAlchemyDataLayer, SQLAlchemyQueryHelper
from fastapi_jsonapi.viewsets import JSONAPIViewSet

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = "sqlite+aiosqlite:///./jsonapi_example.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    bio = Column(String, nullable=False)
    articles = relationship("Article", back_populates="author")
    comments = relationship("Comment", back_populates="author")
    photos = relationship("Photo", back_populates="photographer")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="articles")
    comments = relationship("Comment", back_populates="article")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    body = Column(String, nullable=False)
    author_name = Column(String, nullable=False)
    author_email = Column(String, nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    article = relationship("Article", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    src = Column(String, nullable=False)
    photographer_id = Column(Integer, ForeignKey("users.id"))
    photographer = relationship("User", back_populates="photos")


class UserSerializer(JSONAPISerializer):
    class Meta:
        type_ = "users"
        model = User
        fields = ["id", "name", "email", "bio"]


class ArticleSerializer(JSONAPISerializer):
    class Meta:
        type_ = "articles"
        model = Article
        fields = ["id", "title", "body", "author_id"]


class CommentSerializer(JSONAPISerializer):
    class Meta:
        type_ = "comments"
        model = Comment
        fields = ["id", "body"]


class PhotoSerializer(JSONAPISerializer):
    class Meta:
        type_ = "photos"
        model = Photo
        fields = ["id", "title", "src", "photographer_id"]


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


async def seed_example_data(session: AsyncSession) -> None:
    """Insert example users, articles, comments, and photos if empty."""
    result = await session.execute(select(User.id).limit(1))
    if result.first() is not None:
        return

    author_jane = User(
        name="Jane Doe",
        email="jane.doe@example.com",
        bio="Tech writer and API enthusiast.",
    )
    author_john = User(
        name="John Smith",
        email="john.smith@example.com",
        bio="Backend developer and data modeler.",
    )
    author_sara = User(
        name="Sara Lee",
        email="sara.lee@example.com",
        bio="Product engineer and API reviewer.",
    )
    author_mike = User(
        name="Mike Chen",
        email="mike.chen@example.com",
        bio="Data engineer focused on performance.",
    )
    session.add_all([author_jane, author_john, author_sara, author_mike])
    await session.flush()

    article_one = Article(
        title="JSON:API with FastAPI",
        body="An example article using JSON:API patterns.",
        author_id=author_jane.id,
    )
    article_two = Article(
        title="Filtering relationships",
        body="Demonstrating relationship field filters.",
        author_id=author_john.id,
    )
    article_three = Article(
        title="Sparse fieldsets in practice",
        body="Exploring fields[resource] for efficient payloads.",
        author_id=author_sara.id,
    )
    article_four = Article(
        title="Nested includes explained",
        body="How include=comments.author expands related resources.",
        author_id=author_mike.id,
    )
    session.add_all([article_one, article_two, article_three, article_four])
    await session.flush()

    comments = [
        Comment(
            body="Great article!",
            author_name="Alice",
            author_email="alice@example.com",
            article_id=article_one.id,
            author_id=author_jane.id,
        ),
        Comment(
            body="Helpful examples.",
            author_name="Bob",
            author_email="bob@example.com",
            article_id=article_one.id,
            author_id=author_john.id,
        ),
        Comment(
            body="Thanks for sharing.",
            author_name="Carol",
            author_email="carol@example.com",
            article_id=article_two.id,
            author_id=author_jane.id,
        ),
        Comment(
            body="Clear explanation!",
            author_name="Dan",
            author_email="dan@example.com",
            article_id=article_three.id,
            author_id=author_sara.id,
        ),
        Comment(
            body="Would love more examples.",
            author_name="Erin",
            author_email="erin@example.com",
            article_id=article_three.id,
            author_id=author_mike.id,
        ),
        Comment(
            body="This helped a lot.",
            author_name="Fiona",
            author_email="fiona@example.com",
            article_id=article_four.id,
            author_id=author_sara.id,
        ),
    ]
    session.add_all(comments)

    photos = [
        Photo(
            title="Ember Hamster",
            src="http://example.com/images/productivity.png",
            photographer_id=author_jane.id,
        ),
        Photo(
            title="API Blueprint",
            src="http://example.com/images/blueprint.png",
            photographer_id=author_sara.id,
        ),
        Photo(
            title="Schema Sketch",
            src="http://example.com/images/schema.png",
            photographer_id=author_mike.id,
        ),
    ]
    session.add_all(photos)
    await session.commit()


class ArticleViewSet(JSONAPIViewSet):
    serializer_class = ArticleSerializer
    pagination_class = StandardPagination
    included_serializers = {
        "author": UserSerializer,
        "comments": CommentSerializer,
        "comments.author": UserSerializer,
    }

    def __init__(self, session: AsyncSession) -> None:
        query_helper = SQLAlchemyQueryHelper(model=Article)
        self.data_layer = SQLAlchemyDataLayer(
            model=Article,
            session=session,
            query_helper=query_helper,
        )

    async def list(self, request: Request, *args: object, **kwargs: object) -> dict:
        return await super().list(request, *args, **kwargs)


class PhotoViewSet(JSONAPIViewSet):
    serializer_class = PhotoSerializer
    pagination_class = StandardPagination
    included_serializers = {
        "photographer": UserSerializer,
    }
    # Example: Restrict to read-only operations
    # allowed_actions = ["list", "retrieve", "relationship"]

    def __init__(self, session: AsyncSession) -> None:
        query_helper = SQLAlchemyQueryHelper(model=Photo)
        self.data_layer = SQLAlchemyDataLayer(
            model=Photo,
            session=session,
            query_helper=query_helper,
        )


app = FastAPI(
    title="FastAPI JSON:API Example",
    description="Example API showcasing JSON:API v1.1 behavior.",
    version="0.1.0",
)
router = JSONAPIRouter(prefix="/api/v1")


# Dependency factories for viewsets
def get_article_viewset(session: AsyncSession = Depends(get_session)) -> ArticleViewSet:
    """Dependency factory for ArticleViewSet."""
    return ArticleViewSet(session)


def get_photo_viewset(session: AsyncSession = Depends(get_session)) -> PhotoViewSet:
    """Dependency factory for PhotoViewSet."""
    return PhotoViewSet(session)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await seed_example_data(session)


# Register viewsets using register_viewset with dependency injection
router.register_viewset("/articles", get_article_viewset)
router.register_viewset("/photos", get_photo_viewset)


@router.post("/seed")
async def seed_data() -> dict:
    async with async_session() as session:
        await seed_example_data(session)
    return {"meta": {"seeded": True}}


app.include_router(router)
