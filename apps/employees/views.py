from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import CompanyMembership, EmployeeProfile
from .forms import EmployeeUserCreateForm, CompanyMembershipEditForm
from apps.core.models import Company


@login_required
def employee_list_view(request):
    """Lista de usuarios / colaboradores de la empresa activa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    memberships = CompanyMembership.objects.filter(company=company).select_related('user', 'user__profile')
    
    return render(request, 'employees/employee_list.html', {
        'company': company,
        'memberships': memberships,
    })


@login_required
def employee_create_view(request):
    """Crea un nuevo usuario y lo vincula a la empresa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    if request.method == 'POST':
        form = EmployeeUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario '{user.username}' creado y asignado a {company.name}.")
            return redirect('employee_list')
    else:
        form = EmployeeUserCreateForm(initial={'company': company})
        form.fields['company'].initial = company

    return render(request, 'employees/employee_form.html', {
        'form': form,
        'company': company,
        'title': f'Agregar Usuario a {company.name}'
    })


@login_required
def membership_edit_view(request, pk):
    """Edita el rol de un usuario en la empresa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    membership = get_object_or_404(CompanyMembership, pk=pk, company=company)

    if request.method == 'POST':
        form = CompanyMembershipEditForm(request.POST, instance=membership)
        if form.is_valid():
            form.save()
            messages.success(request, f"Permisos actualizados para '{membership.user.username}'.")
            return redirect('employee_list')
    else:
        form = CompanyMembershipEditForm(instance=membership)

    return render(request, 'employees/employee_form.html', {
        'form': form,
        'company': company,
        'membership': membership,
        'title': f'Editar Permisos de {membership.user.username}'
    })


@login_required
def membership_delete_view(request, pk):
    """Elimina la asignación de un usuario a la empresa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    membership = get_object_or_404(CompanyMembership, pk=pk, company=company)

    if request.method == 'POST':
        user_name = membership.user.username
        membership.delete()
        messages.success(request, f"El usuario '{user_name}' ya no pertenece a {company.name}.")
        return redirect('employee_list')

    return render(request, 'employees/employee_confirm_delete.html', {
        'membership': membership,
        'company': company
    })
