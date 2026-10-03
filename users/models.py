# users/models.py
import unicodedata
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


def normalize_text(text):
    """
    Funcion normalizadora (Rasho nomalizador): Elimina tildes, pasa a minusculas, 
    remueve espacios extra y caracteres especiales.
    """
    if not text:
        return ""
    cleaned = " ".join(text.split()).lower()
    normalized = unicodedata.normalize('NFD', cleaned)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn')


class ActiveManager(UserManager):
    """
    Funcion para que ignore los campos que tengan "is_deleted" como false
    evitando asi mostrar estos campos.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Employee(models.Model):
    """
    Ficha de información laboral del empleado.
    """
    first_name = models.CharField('Nombre', max_length=100)
    last_name = models.CharField('Apellido', max_length=100)
    
    # Campo normalizado para búsquedas rápidas
    normalized_full_name = models.CharField(max_length=255, editable=False, db_index=True)
    
    cuit_dni = models.CharField('CUIT / DNI', max_length=20, unique=True, db_index=True)
    
    # El correo vive aquí de manera independiente (un empleado puede no tener usuario pero sí correo)
    email = models.EmailField(
        'Correo electrónico', 
        unique=True, 
        null=True, 
        blank=True, 
        db_index=True,
        error_messages={'unique': 'Ya existe un empleado registrado con este correo.'}
    )
    
    phone = models.CharField('Teléfono', max_length=20, blank=True, null=True)
    
    # Soft Delete
    is_deleted = models.BooleanField('Esta Borrado', default=False, db_index=True)
    created_at = models.DateTimeField('Fecha de registro', auto_now_add=True)

    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['cuit_dni', 'is_deleted'], name='emp_cuit_deleted_idx'),
            models.Index(fields=['email', 'is_deleted'], name='emp_email_deleted_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = " ".join(self.first_name.split()).title()
        if self.last_name:
            self.last_name = " ".join(self.last_name.split()).title()
        if self.cuit_dni:
            self.cuit_dni = self.cuit_dni.strip().upper()
        if self.email:
            self.email = self.email.strip().lower()
            
        full_name_raw = f"{self.first_name} {self.last_name}"
        self.normalized_full_name = normalize_text(full_name_raw)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.cuit_dni})"


class User(AbstractUser):
    """
    Modelo de Usuario Personalizado para credenciales y acceso al sistema.
    """
    # Eliminamos el campo email de aquí para evitar redundancias.
    email = None
    
    username = models.CharField(
        'Nombre de usuario',
        max_length=150,
        unique=True,
        db_index=True,
        help_text='Requerido. 150 caracteres o menos. Letras, números y @/./+/-/_'
    )
    
    employee = models.OneToOneField(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account',
        verbose_name='Perfil de Empleado'
    )

    is_deleted = models.BooleanField('Esta Borrado', default=False, db_index=True)

    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        indexes = [
            models.Index(fields=['username', 'is_deleted'], name='user_username_deleted_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.strip()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username}"