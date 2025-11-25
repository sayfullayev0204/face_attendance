from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    file = models.FileField(upload_to='lessons/', null=True, blank=True)
    def __str__(self):
        return self.title

class Video(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='videos/')
    order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['order']
    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

class Test(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='test', null=True, blank=True)
    title = models.CharField(max_length=200)
    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    def __str__(self):
        return self.text[:50]

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=400)
    is_correct = models.BooleanField(default=False)
    def __str__(self):
        return self.text[:50]

class StudentProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    watched_videos = models.ManyToManyField(Video, blank=True)
    test_passed = models.BooleanField(default=False)
    test_score = models.FloatField(null=True, blank=True)  # YANGI
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'lesson')

# models.py (oldingi modellardan keyin qo'shing)

from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, verbose_name="To'liq ism")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    bio = models.TextField(blank=True, verbose_name="O'zim haqimda")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Rasm")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan sana")
    group = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Guruh")
    registered_at = models.DateTimeField(default=timezone.now, verbose_name="Ro'yxatdan o'tgan vaqti")

    def __str__(self):
        return f"{self.user.username} - Profil"

    class Meta:
        verbose_name = "Foydalanuvchi profili"
        verbose_name_plural = "Foydalanuvchi profillari"


# Avtomatik profil yaratish
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    
# models.py (oxirida qo'shing)

WEEK_DAYS = [
    ('monday', 'Dushanba'),
    ('tuesday', 'Seshanba'),
    ('wednesday', 'Chorshanba'),
    ('thursday', 'Payshanba'),
    ('friday', 'Juma'),
    ('saturday', 'Shanba'),
    ('sunday', 'Yakshanba'),
]

class Schedule(models.Model):
    group = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='schedule')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='scheduled_in')
    day_of_week = models.CharField(max_length=10, choices=WEEK_DAYS, verbose_name="Hafta kuni")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(verbose_name="Tugash vaqti")
    room = models.CharField(max_length=50, blank=True, verbose_name="Xona")

    class Meta:
        unique_together = ('group', 'lesson', 'day_of_week', 'start_time')
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.group.title} - {self.lesson.title} ({self.get_day_of_week_display()})"

# models.py (oxiriga qo'shing)

from django.utils import timezone
import uuid

class Certificate(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    test_score = models.FloatField()  # testdan olgan bali (masalan, 85.5)
    issued_at = models.DateTimeField(default=timezone.now)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pdf_file = models.FileField(upload_to='certificates/', null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} - {self.course.title}"

    def get_verification_url(self):
        # Sertifikatni tekshirish uchun maxsus URL
        from django.urls import reverse
        return f"https://phoenix-rapid-factually.ngrok-free.app{reverse('verify_certificate', kwargs={'uuid': self.certificate_id})}"