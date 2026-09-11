from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password

from users.models import User


class AppUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "role", "is_active")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")
        if password2:
            user = User(
                username=self.cleaned_data.get("username", ""),
                first_name=self.cleaned_data.get("first_name", ""),
                last_name=self.cleaned_data.get("last_name", ""),
            )
            validate_password(password2, user)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class AppUserUpdateForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Пароль",
        help_text="Пароль хранится в хэшированном виде. Для смены используйте отдельную форму.",
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "role", "is_active", "password")

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        elif not user.is_superuser:
            user.is_staff = False
        if commit:
            user.save()
        return user


class AppUserPasswordForm(forms.Form):
    password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")
        if password2:
            validate_password(password2, self.user)
        return password2
