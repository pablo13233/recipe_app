from django.db import models
from django.contrib.auth.models import User
from apps.core.models import Company


class CompanyMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('operator', 'Operador / Emisor'),
        ('viewer', 'Solo Lectura'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='company_memberships',
        verbose_name="Usuario"
    )
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='memberships',
        verbose_name="Empresa"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='admin',
        verbose_name="Rol en la Empresa"
    )
    is_default = models.BooleanField(
        default=False, 
        verbose_name="Empresa por Defecto"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membresía / Asignación de Usuario"
        verbose_name_plural = "Membresías de Usuarios por Empresa"
        unique_together = ('user', 'company')
        ordering = ['company', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.get_role_display()})"


class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name="Usuario"
    )
    phone = models.CharField(max_length=50, blank=True, verbose_name="Teléfono")
    job_title = models.CharField(max_length=100, blank=True, verbose_name="Cargo / Puesto")
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"Perfil: {self.user.get_full_name() or self.user.username}"
