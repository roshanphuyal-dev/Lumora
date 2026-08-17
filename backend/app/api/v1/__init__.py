from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chat,
    courses,
    documents,
    flashcards,
    learning,
    notebooks,
    notes,
    personalization,
    quiz_attempts,
    quizzes,
    studio,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(documents.router)
api_router.include_router(notebooks.router)
api_router.include_router(chat.router)
api_router.include_router(notes.router)
api_router.include_router(flashcards.router)
api_router.include_router(studio.router)
api_router.include_router(quizzes.router)
api_router.include_router(quiz_attempts.router)
api_router.include_router(learning.router)
api_router.include_router(learning.user_router)
api_router.include_router(personalization.preferences_router)
api_router.include_router(personalization.recommendations_router)
