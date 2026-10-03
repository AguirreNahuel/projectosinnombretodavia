# users/views.py
import io
import base64
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import User, Employee, normalize_text
from django.core.paginator import Paginator
from .forms import EmployeeForm

# ==========================================
# VISTAS DE AUTENTICACIÓN Y 2FA (HTMX)
# ==========================================

def login_view(request):
    """
    Maneja el flujo de autenticación de dos pasos con HTMX:
    - Paso 1: Valida usuario/email (del empleado) y contraseña.
    - Evalúa 2FA (Solo obligatorio para Staff/Superuser).
    """
    if request.method == 'GET':
        return render(request, 'users/login/login.html')

    # 1. EVALUACIÓN DE PASO 1: Credenciales
    if 'verify_credentials' in request.POST:
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        # Buscar por username del usuario O por el email que pertenece al Employee vinculado
        user_obj = User.objects.filter(
            Q(username__iexact=identifier) | Q(employee__email__iexact=identifier)
        ).first()

        if user_obj:
            # Usamos siempre el username real del objeto encontrado para autenticar
            user = authenticate(request, username=user_obj.username, password=password)
        else:
            user = None

        if not user:
            return render(request, 'users/partials/login_step1.html', {
                'error': 'Credenciales inválidas o la cuenta se encuentra desactivada.'
            })

        # Regla de Negocio: Si NO es staff ni superuser, salta el 2FA e inicia sesión directamente
        if not (user.is_staff or user.is_superuser):
            auth_login(request, user)
            response = HttpResponse()
            response['HX-Redirect'] = '/dashboard/'
            return response

        # Guardar ID de usuario temporalmente en la sesión de preconexión 2FA
        request.session['pre_2fa_user_id'] = user.id

        # Evaluar estado de 2FA para el usuario Administrador / Staff
        device = TOTPDevice.objects.filter(user=user, name='default').first()

        # CASO A: Ya configuró 2FA previamente
        if device and device.confirmed:
            return render(request, 'users/login/partials/login_step2_otp.html')

        # CASO B: Primera vez / No tiene 2FA configurado
        if not device:
            device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)

        otp_uri = device.config_url
        
        img = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return render(request, 'users/login/partials/login_step2_qr.html', {
            'qr_code': qr_base64,
            'secret_key': device.key
        })

    # 2. EVALUACIÓN DE PASO 2: Validación OTP
    if 'verify_otp' in request.POST:
        user_id = request.session.get('pre_2fa_user_id')
        if not user_id:
            return render(request, 'users/login/partials/login_step1.html', {
                'error': 'Sesión de autenticación expirada. Vuelva a ingresar sus credenciales.'
            })

        user = User.objects.get(id=user_id)
        otp_code = request.POST.get('otp_code', '').strip()

        device = TOTPDevice.objects.filter(user=user, name='default').first()
        
        if device and device.verify_token(otp_code):
            if not device.confirmed:
                device.confirmed = True
                device.save()

            auth_login(request, user)
            
            if 'pre_2fa_user_id' in request.session:
                del request.session['pre_2fa_user_id']

            response = HttpResponse()
            response['HX-Redirect'] = '/dashboard/'
            return response

        context = {'error': 'El código ingresado es incorrecto o ha expirado.'}
        if device and not device.confirmed:
            otp_uri = device.config_url
            img = qrcode.make(otp_uri)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            context['qr_code'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return render(request, 'users/login/partials/login_step2_qr.html', context)

        return render(request, 'users/login/partials/login_step2_otp.html', context)

    return render(request, 'users/login/login.html')


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')


# ==========================================
# VISTAS DE GESTIÓN Y CRUD EMPLEADOS
# ==========================================

@login_required
def dashboard_view(request):
    total_employees = Employee.objects.count()
    total_products = 0

    context = {
        'total_employees': total_employees,
        'total_products': total_products,
    }

    # SI ES UNA PETICIÓN HTMX -> Devuelve ÚNICAMENTE el fragmento de tarjetas (sin sidebar)
    if request.headers.get('HX-Request'):
        return render(request, 'users/dashboard/partials/dashboard_home.html', context)

    # SI ES RECARGA (F5) O URL DIRECTA -> Devuelve el dashboard completo con su sidebar
    return render(request, 'users/dashboard/dashboard.html', context)

@login_required
def employee_list(request):
    search_query = request.GET.get('q', '').strip()
    # Asegúrate de excluir los eliminados si manejas borrado lógico (is_deleted)
    queryset = Employee.objects.filter(is_deleted=False) if hasattr(Employee, 'is_deleted') else Employee.objects.all()

    if search_query:
        normalized_q = normalize_text(search_query)
        queryset = queryset.filter(
            Q(normalized_full_name__icontains=normalized_q) |
            Q(cuit_dni__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Configurar la paginación (por ejemplo, 10 empleados por página)
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'employees': page_obj, # Ahora pasamos el objeto de página
        'page_obj': page_obj,
        'search_query': search_query, # Útil para mantener el buscador si cambias de página
    }

    # Si es una petición HTMX (ya sea escribiendo en el buscador o cambiando de página)
    if request.headers.get('HX-Request'):
        # Si la petición viene específicamente del input de búsqueda o de la paginación dentro de la tabla
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'users/employees/partials/employee_table.html', context)
        return render(request, 'users/employees/employee_list.html', context)

    return render(request, 'users/employees/employee_list_page.html', context)


@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/empleados/'
            return response
    else:
        form = EmployeeForm()

    context = {'form': form, 'action_url': '/empleados/nuevo/', 'title': 'Nuevo Empleado'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'users/employees/partials/employee_form.html', context)
    return render(request, 'users/employees/employee_form_page.html', context)


@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/empleados/'
            return response
    else:
        form = EmployeeForm(instance=employee)

    context = {'form': form, 'action_url': f'/empleados/{pk}/editar/', 'title': 'Editar Empleado'}
    
    if request.headers.get('HX-Request'):
        return render(request, 'users/employees/partials/employee_form.html', context)
    return render(request, 'users/employees/employee_form_page.html', context)


@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.is_deleted = True # o employee.delete()
        employee.save()
        
        if request.headers.get('HX-Request'):
            # Replicar la consulta y paginación actual
            queryset = Employee.objects.filter(is_deleted=False) if hasattr(Employee, 'is_deleted') else Employee.objects.all()
            paginator = Paginator(queryset, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'users/employees/partials/employee_table.html', {'employees': page_obj, 'page_obj': page_obj})
            
        response = HttpResponse()
        response['HX-Redirect'] = '/empleados/'
        return response

    return render(request, 'users/employees/partials/employee_form_modal.html')