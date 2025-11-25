from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, FileResponse
from .models import Certificate, Lesson, Video, StudentProgress, Test, Choice
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

# views.py ichida submit_test ni almashtiring
# courses/views.py → submit_test ni to'liq almashtiring

from django.contrib import messages
from .utils import generate_certificate_pdf  # <-- bu joyida ekanligiga ishonch hosil qiling

@login_required
def submit_test(request, lesson_id):
    if request.method != 'POST':
        return redirect('courses:lesson_detail', lesson_id=lesson_id)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    test = getattr(lesson, 'test', None)
    if not test:
        return HttpResponseForbidden('Bu dars uchun test mavjud emas.')

    # Progressni olish yoki yaratish
    prog, _ = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)

    # Barcha videolar ko‘rilganmi?
    all_video_ids = set(lesson.videos.values_list('id', flat=True))
    watched_ids = set(prog.watched_videos.values_list('id', flat=True))
    if not all_video_ids.issubset(watched_ids):
        return HttpResponseForbidden('Avval barcha videolarni ko‘ring!')

    # Test javoblarini hisoblash
    total_questions = test.questions.count()
    correct = 0

    for question in test.questions.all():
        selected_id = request.POST.get(str(question.id))
        if selected_id:
            try:
                choice = Choice.objects.get(id=selected_id, question=question)
                if choice.is_correct:
                    correct += 1
            except Choice.DoesNotExist:
                pass

    score = (correct / total_questions) * 100 if total_questions > 0 else 0
    passed = score >= 60  # 60% va undan yuqori o‘tdi

    # Progressni yangilash
    prog.test_passed = passed
    prog.test_score = round(score, 1)
    prog.attended = passed
    prog.save()

    # =================== SERTIFIKAT BERISH LOGIKASI ===================
    if passed and lesson.course:
        course = lesson.course
        all_lessons_in_course = course.lessons.all()

        # Kursdagi barcha lessonlar uchun progressni tekshirish
        completed_lessons = 0
        total_score_sum = 0
        scored_lessons = 0

        for l in all_lessons_in_course:
            p = StudentProgress.objects.filter(student=request.user, lesson=l).first()
            if p and p.test_passed:
                completed_lessons += 1
                if p.test_score:
                    total_score_sum += p.test_score
                    scored_lessons += 1

        # Agar kursdagi barcha lessonlar testdan o‘tilgan bo‘lsa
        if completed_lessons == all_lessons_in_course.count():
            avg_score = round(total_score_sum / scored_lessons, 1) if scored_lessons > 0 else score

            # Sertifikatni yaratish (agar hali yo‘q bo‘lsa)
            cert, created = Certificate.objects.get_or_create(
                student=request.user,
                course=course,
                defaults={'test_score': avg_score}
            )

            if created:
                try:
                    from .utils import generate_certificate_pdf
                    generate_certificate_pdf(cert)
                    messages.success(request, f"Tabriklaymiz! '{course.title}' kursini muvaffaqiyatli yakunladingiz! Sertifikatingiz tayyor bo‘ldi!")
                except Exception as e:
                    messages.error(request, f"Sertifikat PDF yaratishda xato: {e}")
            else:
                messages.info(request, "Bu kurs bo‘yicha sertifikatingiz allaqachon mavjud.")

        else:
            # Debug uchun foydali xabar
            messages.info(request, f"Kursni tugatish uchun yana {all_lessons_in_course.count() - completed_lessons} ta dars testidan o‘tishingiz kerak.")

    # Oddiy muvaffaqiyat xabari
    messages.success(request, f"Test muvaffaqiyatli topshirildi! Ball: {score:.1f}% — {'O‘tdingiz!' if passed else 'O‘tmadingiz'}")
    return redirect('courses:lesson_detail', lesson_id=lesson.id)


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
# views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime, timedelta
from .models import Schedule, WEEK_DAYS

@login_required
def schedule_view(request):
    profile = request.user.profile
    if not profile.group:
        return render(request, 'schedule.html', {
            'error': 'Siz hech qanday guruhga biriktirilmagansiz.'
        })

    # Hafta sanasini olish
    week_param = request.GET.get('week')
    try:
        current_monday = datetime.strptime(week_param, '%Y-%m-%d').date()
        if current_monday.weekday() != 0:  # Dushanba bo'lishi kerak
            raise ValueError
    except:
        today = datetime.today().date()
        current_monday = today - timedelta(days=today.weekday())

    prev_monday = current_monday - timedelta(days=7)
    next_monday = current_monday + timedelta(days=7)

    # Hafta kunlari
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    week_dates = {day_order[i]: current_monday + timedelta(days=i) for i in range(7)}

    # Barcha darslarni olish (faqat guruh bo‘yicha)
    schedules = Schedule.objects.filter(group=profile.group).select_related('lesson')

    # Har bir kun uchun faqat mos darslarni yig'ish
    schedule_by_day = defaultdict(list)
    for item in schedules:
        day_key = item.day_of_week
        if day_key in week_dates:
            schedule_by_day[day_key].append(item)

    # Tartiblangan jadval
    ordered_schedule = []
    for day in day_order:
        items = sorted(schedule_by_day[day], key=lambda x: x.start_time)
        date_obj = week_dates[day]
        ordered_schedule.append({
            'day_name': dict(WEEK_DAYS)[day],
            'date': date_obj.strftime('%d.%m'),
            'items': items
        })

    context = {
        'schedule': ordered_schedule,
        'group': profile.group,
        'current_week': current_monday.strftime('%Y-%m-%d'),
        'prev_week': prev_monday.strftime('%Y-%m-%d'),
        'next_week': next_monday.strftime('%Y-%m-%d'),
        'week_range': f"{current_monday.strftime('%d.%m')} — {(current_monday + timedelta(days=6)).strftime('%d.%m.%Y')}",
        'today': datetime.today().date().strftime('%Y-%m-%d'),  # bugungi kunni belgilash uchun
    }
    return render(request, 'schedule.html', context)

# views.py yoki service funksiyada

from django.db import transaction

def issue_certificate_if_eligible(student, course):
    from .models import StudentProgress, Certificate

    # Barcha lessonlarni tekshirish
    lessons = course.lessons.all()
    all_passed = True
    total_score = 0
    test_count = 0

    for lesson in lessons:
        progress = StudentProgress.objects.filter(student=student, lesson=lesson).first()
        if not progress or not progress.test_passed:
            all_passed = False
            break
        if progress.test_score:
            total_score += progress.test_score
            test_count += 1

    if all_passed and test_count > 0:
        avg_score = total_score / test_count

        # Sertifikat allaqachon berilganmi?
        if not Certificate.objects.filter(student=student, course=course).exists():
            Certificate.objects.create(
                student=student,
                course=course,
                test_score=round(avg_score, 1)
            )

# views.py

@login_required
def my_certificates(request):
    certificates = Certificate.objects.filter(student=request.user).select_related('course')
    return render(request, 'certificates/my_certificates.html', {
        'certificates': certificates
    })

@login_required
def download_certificate(request, cert_id):
    cert = get_object_or_404(Certificate, id=cert_id, student=request.user)
    if not cert.pdf_file:
        return HttpResponse("Sertifikat hali tayyor emas.", status=400)
    
    response = FileResponse(cert.pdf_file.open(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Sertifikat_{cert.course.title}.pdf"'
    return response

# courses/views.py (oxiriga qo‘shing)

def verify_certificate(request, uuid):
    try:
        cert = Certificate.objects.select_related('student', 'course').get(certificate_id=uuid)
        return render(request, 'certificates/verify.html', {
            'valid': True,
            'cert': cert,
            'student_name': cert.student.profile.full_name or cert.student.get_full_name() or cert.student.username,
        })
    except Certificate.DoesNotExist:
        return render(request, 'certificates/verify.html', {'valid': False})