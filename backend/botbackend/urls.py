from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.shortcuts import redirect
from .views import (
    login_user, 
    feedback, 
    QuestionResponseViewSet, 
    UserFeedbackViewSet,
    create_message,
    chat_response,
)
from django.contrib import admin

router = DefaultRouter()
router.register(r'questions', QuestionResponseViewSet, basename='questions')
router.register(r'feedbacks', UserFeedbackViewSet, basename='feedbacks')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('', include(router.urls)),
        path('login/', login_user, name='login'),
        path('create_message/', create_message, name='create_message'),
        path('feedback/', feedback, name='feedback'),
        path('chat/', chat_response, name='chat_response'),
    ])),
    # 將根路徑重定向到 api/chat/
    path('', lambda request: redirect('api/chat/')),
]