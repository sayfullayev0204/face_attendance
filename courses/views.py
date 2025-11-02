from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from .models import Lesson, Video, StudentProgress, Test, Choice
from .forms import LoginForm
import os, datetime

def user_login(request):
    if request.user.is_authenticated:
        return redirect('courses:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('courses:dashboard')
    else:
        form = LoginForm()
    return render(request, 'courses/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('courses:login')

@login_required
def dashboard(request):
    today = timezone.localdate()
    lessons = Lesson.objects.filter(date=today).order_by('start_time')
    progress_map = {}
    for lesson in lessons:
        prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)
        progress_map[lesson.id] = prog
    return render(request, 'courses/dashboard.html', {'lessons': lessons, 'progress_map': progress_map})

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    videos = list(lesson.videos.all())
    prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)
    watched_ids = list(prog.watched_videos.values_list('id', flat=True))

    unlocked = []
    for i, v in enumerate(videos):
        if i == 0 or videos[i-1].id in watched_ids:
            unlocked.append(v.id)

    all_video_ids = [v.id for v in videos]
    can_take_test = set(all_video_ids).issubset(set(watched_ids))

    return render(request, 'courses/lesson_detail.html', {
        'lesson': lesson,
        'videos': videos,
        'unlocked': unlocked,
        'watched_ids': watched_ids,
        'can_take_test': can_take_test,
        'progress': prog,
    })

@login_required
def mark_video_watched(request, video_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'detail': 'POST required'}, status=400)

    video = get_object_or_404(Video, id=video_id)
    prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=video.lesson)
    prog.watched_videos.add(video)
    prog.save()

    # attended ni yangilash
    all_ids = set(video.lesson.videos.values_list('id', flat=True))
    watched = set(prog.watched_videos.values_list('id', flat=True))
    if all_ids.issubset(watched) and prog.test_passed:
        prog.attended = True
        prog.save()

    return JsonResponse({'status': 'ok'})  # MUHIM: JSON qaytarish

@login_required
def secure_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    # ensure user is allowed to view (must have lesson progress or be enrolled in lesson)
    # simple check: user must be authenticated (decorator ensures) and video exists
    path = video.video_file.path
    if os.path.exists(path):
        # stream inline, discourage download
        response = FileResponse(open(path, 'rb'), content_type='video/mp4')
        response['Content-Disposition'] = 'inline; filename="{}"'.format(os.path.basename(path))
        return response
    return HttpResponseForbidden('File not found')

@login_required
def test_page(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    test = getattr(lesson, 'test', None)
    if not test:
        return HttpResponseForbidden('Bu dars uchun test mavjud emas.')
    prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)
    # require all videos watched
    all_video_ids = set(lesson.videos.values_list('id', flat=True))
    watched = set(prog.watched_videos.values_list('id', flat=True))
    if not all_video_ids.issubset(watched):
        return HttpResponseForbidden('Barcha videolarni to‘liq ko‘ring, so‘ng test topshiring.')
    return render(request, 'courses/test_page.html', {'test': test, 'lesson': lesson})

@login_required
def submit_test(request, lesson_id):
    if request.method != 'POST':
        return redirect('courses:lesson_detail', lesson_id=lesson_id)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    test = getattr(lesson, 'test', None)
    if not test:
        return HttpResponseForbidden('Bu dars uchun test mavjud emas.')

    prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)

    # Oldin barcha videolar ko'rilganligini tekshirish
    all_video_ids = set(lesson.videos.values_list('id', flat=True))
    watched = set(prog.watched_videos.values_list('id', flat=True))
    if not all_video_ids.issubset(watched):
        return HttpResponseForbidden('Barcha videolarni to‘liq ko‘ring.')

    total = test.questions.count()
    correct = 0
    for q in test.questions.all():
        choice_id = request.POST.get(str(q.id))
        if choice_id:
            try:
                ch = Choice.objects.get(id=int(choice_id), question=q)
                if ch.is_correct:
                    correct += 1
            except (Choice.DoesNotExist, ValueError):
                pass

    score = (correct / total) * 100 if total > 0 else 0
    passed = score >= 60

    # Saqlash
    prog.test_passed = passed
    prog.test_score = score
    if passed and all_video_ids.issubset(watched):
        prog.attended = True
    prog.save()

    # Muvaffaqiyatli redirect + flash message emas, lekin score bor
    return redirect('courses:lesson_detail', lesson_id=lesson.id)


# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import UserRegisterForm, ProfileUpdateForm
from .models import Profile,Schedule,WEEK_DAYS

@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profilingiz muvaffaqiyatli yangilandi!')
            return redirect('courses:profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # MUHIM: Sessiyani yangilash – logout bo‘lmaydi!
            update_session_auth_hash(request, user)
            messages.success(request, 'Parolingiz muvaffaqiyatli o‘zgartirildi!')
            return redirect('courses:profile')
        else:
            messages.error(request, 'Iltimos, xatoliklarni tuzating.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


# views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from collections import defaultdict

@login_required
def schedule_view(request):
    profile = request.user.profile
    if not profile.group:
        return render(request, 'schedule.html', {
            'error': 'Siz hech qanday guruhga biriktirilmagansiz.'
        })

    # Hafta kunlari tartibi
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # Foydalanuvchi guruhidagi barcha darslar
    schedule = Schedule.objects.filter(group=profile.group).select_related('lesson', 'lesson__course')

    # Kun bo‘yicha guruhlash
    schedule_by_day = defaultdict(list)
    for item in schedule:
        schedule_by_day[item.day_of_week].append(item)

    # Tartiblangan jadval
    ordered_schedule = []
    for day in day_order:
        ordered_schedule.append({
            'day_name': dict(WEEK_DAYS)[day],
            'items': sorted(schedule_by_day[day], key=lambda x: x.start_time)
        })

    context = {
        'schedule': ordered_schedule,
        'group': profile.group,
    }
    return render(request, 'schedule.html', context)
