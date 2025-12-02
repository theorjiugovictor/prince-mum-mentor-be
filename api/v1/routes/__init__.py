"""
This module aggregates all the v1 API routes into a single router.
"""

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from .admin import router as admin_router
from .ai_chat import router as ai_chat_router
from .album import router as album_router
from .auth import auth_router, google_auth_router
from .child_profile import router as child_profile_router
from .community import router as community_router
from .downloads import router as downloads_router
from .faq import router as faq_router
from .image import router as image_router
from .journal import router as journal_router
from .memories import router as memories_router
from .milestone import router as milestone_router
from .user_profile import router as profile_router, old_profile_router1, old_profile_router2
from .resource import router as resource_router
from .search import router as search_router
from .task import router as task_router
from .user_settings import router as user_settings_router
from .waitlist import router as waitlist_router

# The main router for the v1 API
app = APIRouter()

# Mount static files
app.mount("/files", StaticFiles(directory="app/uploads"), name="files")

# --- Authentication and User Management ---
app.include_router(auth_router)
app.include_router(google_auth_router)
app.include_router(profile_router)
app.include_router(old_profile_router1)
app.include_router(old_profile_router2)
app.include_router(user_settings_router)

# --- Child Profile ---
app.include_router(child_profile_router)


# --- Core Features ---
app.include_router(ai_chat_router)
app.include_router(album_router)
app.include_router(image_router)
app.include_router(journal_router)
app.include_router(memories_router)
app.include_router(milestone_router)
app.include_router(task_router)

# --- Community and Resources ---
app.include_router(community_router)
app.include_router(resource_router)
app.include_router(search_router)

# --- Miscellaneous ---
app.include_router(waitlist_router)
app.include_router(downloads_router)
app.include_router(faq_router)
app.include_router(admin_router)
