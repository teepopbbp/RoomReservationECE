from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        label='ชื่อผู้ใช้ (TU Username)',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
    )
    password = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
