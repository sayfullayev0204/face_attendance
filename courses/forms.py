from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Profile, Course, Lesson, Video, Test, Question, Choice, StudentProgress
class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Login')
    password = forms.CharField(widget=forms.PasswordInput, label='Parol')

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Parol')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Parolni tasdiqlash')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password != password_confirm:
            raise forms.ValidationError("Parollar mos kelmadi.")
        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']