from django import forms
from django.contrib.auth.models import User
from .models import CompanyMembership, EmployeeProfile
from apps.core.models import Company


class EmployeeUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña segura'}),
        label="Contraseña"
    )
    role = forms.ChoiceField(
        choices=CompanyMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Rol en la Empresa"
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Empresa Asignada"
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. +504 9999-9999'}),
        label="Teléfono"
    )
    job_title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Administrador, Asistente, Contador'}),
        label="Puesto / Cargo"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'nombre_usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            company = self.cleaned_data.get('company')
            role = self.cleaned_data.get('role')
            CompanyMembership.objects.create(
                user=user,
                company=company,
                role=role,
                is_default=True
            )
            EmployeeProfile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', ''),
                job_title=self.cleaned_data.get('job_title', '')
            )
        return user


class CompanyMembershipEditForm(forms.ModelForm):
    class Meta:
        model = CompanyMembership
        fields = ['company', 'role', 'is_default']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
