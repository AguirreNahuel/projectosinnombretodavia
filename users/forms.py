# users/forms.py
from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'cuit_dni', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. Juan'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. Pérez'}),
            'cuit_dni': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. 20384958674'}),
            'email': forms.EmailInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'correo@ejemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej. +5491123456789'}),
        }