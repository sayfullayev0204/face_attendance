from django.urls import path
from . import views
app_name = 'courses'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('accounts/login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('video/<int:video_id>/watched/', views.mark_video_watched, name='mark_video_watched'),
    path('video/<int:video_id>/stream/', views.secure_video, name='secure_video'),
    path('lesson/<int:lesson_id>/test/', views.test_page, name='test_page'),
    path('lesson/<int:lesson_id>/test/submit/', views.submit_test, name='submit_test'),
    path('schedule/', views.schedule_view, name='schedule'),
    path('verify/<uuid:uuid>/', views.verify_certificate, name='verify_certificate'),
    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificate/download/<int:cert_id>/', views.download_certificate, name='download_certificate'),
]
urlpatterns += [
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
]