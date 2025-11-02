from django.contrib import admin
from .models import Course, Lesson, Video, Test, Question, Choice, StudentProgress
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Video)
admin.site.register(Test)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(StudentProgress)

# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import Profile, Course, Lesson, Video, Test, Question, Choice, StudentProgress

# User adminni kengaytirish
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)

# Eski UserAdmin ni o'chirish va yangisini qo'shish
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Profile)
# admin.py

from django.contrib import admin
from .models import Course, Lesson, Video, Test, Question, Choice, StudentProgress, Profile, Schedule

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('group', 'lesson', 'get_day', 'start_time', 'end_time', 'room')
    list_filter = ('group', 'day_of_week')
    search_fields = ('lesson__title', 'group__name')

    def get_day(self, obj):
        return obj.get_day_of_week_display()
    get_day.short_description = 'Kun'