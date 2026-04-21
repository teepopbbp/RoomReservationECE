from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LoginForm
from .models import CustomUser


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = auth.authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            auth.login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    auth.logout(request)
    return redirect('accounts:login')


@login_required
def user_list_view(request):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')

    users = CustomUser.objects.all().order_by('role', 'full_name')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def change_role_view(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('accounts:user_list')

    target = get_object_or_404(CustomUser, pk=user_id)
    new_role = request.POST.get('role')
    if new_role in (CustomUser.ROLE_LECTURER, CustomUser.ROLE_ADMIN):
        target.role = new_role
        target.save()
        messages.success(request, f'เปลี่ยนบทบาทของ {target.display_name()} เรียบร้อยแล้ว')
    else:
        messages.error(request, 'บทบาทไม่ถูกต้อง')

    return redirect('accounts:user_list')
