from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import accountant_admin_required
from users.forms import AppUserCreateForm, AppUserPasswordForm, AppUserUpdateForm
from users.models import User


@accountant_admin_required
def app_user_list(request):
    users = User.objects.order_by("username")
    return render(request, "users/user_list.html", {"users": users})


@accountant_admin_required
def app_user_create(request):
    if request.method == "POST":
        form = AppUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Пользователь {user.username} создан.")
            return redirect("app_user_list")
    else:
        form = AppUserCreateForm(initial={"is_active": True})

    return render(request, "users/user_form.html", {"form": form, "title": "Новый пользователь"})


@accountant_admin_required
def app_user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = AppUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Пользователь {user.username} обновлен.")
            return redirect("app_user_list")
    else:
        form = AppUserUpdateForm(instance=user)

    return render(request, "users/user_form.html", {"form": form, "title": user.username, "edited_user": user})


@accountant_admin_required
def app_user_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = AppUserPasswordForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.save(update_fields=["password"])
            messages.success(request, f"Пароль пользователя {user.username} изменен.")
            return redirect("app_user_list")
    else:
        form = AppUserPasswordForm(user=user)

    return render(
        request,
        "users/user_password_form.html",
        {"form": form, "edited_user": user},
    )


@accountant_admin_required
def app_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "Нельзя удалить свою учетную запись.")
        return redirect("app_user_list")

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"Пользователь {username} удален.")
        return redirect("app_user_list")

    return render(request, "users/user_confirm_delete.html", {"edited_user": user})
