# api/v1/routes/__init__.py

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
from .waitlist import router as waitlist_router
from .downloads import router as downloads_router
from .auth import auth_router
from .auth import google_auth_router
from .delete_account import router as delete_account_router
from .user_profile import router as user_profile_router
from .admin import router as admin_router
from .faq import router as faq_router
from .user_settings import router as user_settings_router
from .memories import router as memories_router

from .task.list_task import router as task_list_router
from .task.create_task import router as create_task_router
from .task.edit_task import router as edit_task_router
from .task.toggle_completion import router as toggle_completion_router
from .task.delete_task import router as delete_task_router

from .child_profile.create_child_profile import router as create_child_profile_router
from .child_profile.get_child_profile import router as get_child_profile_router
from .child_profile.list_child_profiles import router as list_child_profiles_router
from .child_profile.update_child_profile import router as update_child_profile_router
from .child_profile.delete_child_profile import router as delete_child_profile_router
from .child_profile.upload_picture import router as upload_child_picture_router

from .ai_chat import router as ai_chat_router
from .profile_setup import router as profile_setup_router
# ONLY include the milestone router you need
from .milestone import router as milestone_router

from .album import album_router
from .albums import router as albums_router
from .album_memories import router as album_memories_router
from .image import router as image_router
from .resource_media import router as resource_media_router

app = APIRouter()
app.mount("/files", StaticFiles(directory="app/uploads"), name="files")

app.include_router(image_router)
app.include_router(auth_router)
app.include_router(waitlist_router)
app.include_router(google_auth_router)
app.include_router(delete_account_router)

# Task routes 
app.include_router(create_task_router)
app.include_router(task_list_router)
app.include_router(toggle_completion_router)
app.include_router(edit_task_router)
app.include_router(delete_task_router)

# Child Profile routes
app.include_router(create_child_profile_router)
app.include_router(get_child_profile_router)
app.include_router(list_child_profiles_router)
app.include_router(update_child_profile_router)
app.include_router(delete_child_profile_router)
app.include_router(upload_child_picture_router)

# Profile Setup routes
app.include_router(profile_setup_router)

# Album routes
app.include_router(album_router)
app.include_router(albums_router)
app.include_router(album_memories_router)

# AI Chat routes
app.include_router(ai_chat_router)

# Milestone router
app.include_router(milestone_router)

# Resource Media routes (Community Posts)
app.include_router(resource_media_router)

# Other routes
app.include_router(user_profile_router)
app.include_router(admin_router)
app.include_router(faq_router)
app.include_router(user_settings_router)
app.include_router(downloads_router)
app.include_router(memories_router)

# Backwards-compatibility
contact_router = app