# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Employee


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'email' in self.fields:
            del self.fields['email']


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'email' in self.fields:
            del self.fields['email']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'cuit_dni', 'email', 'phone', 'is_deleted', 'created_at')
    search_fields = ('first_name', 'last_name', 'cuit_dni', 'email', 'normalized_full_name')
    list_filter = ('is_deleted', 'created_at')
    readonly_fields = ('normalized_full_name', 'created_at')
    
    def get_queryset(self, request):
        return Employee.all_objects.all()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('username', 'email_empleado', 'first_name', 'last_name', 'employee', 'is_staff', 'is_deleted')
    search_fields = ('username', 'first_name', 'last_name', 'employee__email')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_deleted')
    
    # SOBREESCRIBIMOS COMPLETAMENTE fieldsets para evitar que BaseUserAdmin inyecte 'email'
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información personal', {'fields': ('first_name', 'last_name')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
        ('Información Comercial / Soft Delete', {'fields': ('employee', 'is_deleted')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'employee', 'is_deleted'),
        }),
    )

    @admin.display(description='Correo electrónico (Empleado)')
    def email_empleado(self, obj):
        if obj.employee and obj.employee.email:
            return obj.employee.email
        return 'Sin correo / Sin empleado'

    def get_queryset(self, request):
        return User.all_objects.all()