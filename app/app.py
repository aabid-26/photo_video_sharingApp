from fastapi import FastAPI, HTTPException, File, UploadFile,Depends,Form
from app.schemas import PostCreate, PostResponse
from app.db import Post, create_db_and_tables,get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
#what this would do is it will run the lifespan function as the app is started
# and will create the database and tables

@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(...),
        session: AsyncSession = Depends(get_async_session)
):

    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file,temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        if upload_result.response_metadata.http_status_code == 200:

            #post is an object that you want to create
            post = Post(
                caption=caption,
                url="upload_result.url",
                file_type="video" if file.content_type.startswith("video/") else "image",
                file_name=upload_result.name
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/feed")
async def get_feed(
        session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    posts_data =[]
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat()
            }
        )
    return {"posts" :posts_data}

# text_posts={
#     1:{"title":"New post","content":"Cool test post"},
#     2: {"title": "Mountain Hike", "content": "Reached the summit just in time for sunrise. 🏔️"},
#   3: {"title": "New Puppy!", "content": "Meet Barnaby, the newest member of the family. He loves socks."},
#   4: {"title": "Coding Late", "content": "Finally fixed that bug in the FastAPI middleware. Victory!"},
#   5: {"title": "Morning Coffee", "content": "Nothing beats a fresh brew to start the day. ☕️"},
#   6: {"title": "Throwback Thursday", "content": "Missing this beach in Bali. Take me back to summer. 🏖️"},
#   7: {"title": "Quick Recipe", "content": "The secret to perfect pasta is using the pasta water in the sauce!"},
#   8: {"title": "Golden Hour", "content": "The lighting in the backyard right now is absolutely magical."},
#   9: {"title": "Street Art", "content": "Found some incredible murals in the art district today."},
#   10: {"title": "Weekend Vibes", "content": "Settling in with a good book and some lo-fi beats. 📖"}
# }
#
# @app.get("/posts")
# def get_all_posts(limit:int):
#     if limit:
#         return list (text_posts.values())[:limit]
#     return text_posts
#
# @app.get("/posts/{post_id}")
# def get_post(id:int)-> PostResponse:
#     if id not in text_posts:
#         raise HTTPException(status_code=404, detail="Post not found")
#     return text_posts.get(id)
#
# @app.post("/posts")
# def create_post(post: PostCreate) -> PostResponse:
#     new_post= {"title": post.title, "content": post.content}
#     text_posts [max(text_posts.keys())+ 1] = new_post
#     return new_post

