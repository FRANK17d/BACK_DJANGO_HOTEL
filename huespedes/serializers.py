from rest_framework import serializers
from .models import Huesped


class HuespedSerializer(serializers.ModelSerializer):
    duracion_estadia = serializers.ReadOnlyField()
    total_estadia = serializers.ReadOnlyField()
    total_huespedes = serializers.ReadOnlyField()
    
    class Meta:
        model = Huesped
        fields = [
            'id',
            # Información de venta
            'canal_venta',
            'tipo_comprobante',
            # Información personal
            'nombres_apellidos',
            'tipo_documento',
            'numero_documento',
            'numero_ruc',
            'nombre_o_razon_social',
            'estado',
            'condicion',
            'direccion_completa',
            'fecha_nacimiento',
            'nacionalidad',
            'procedencia',
            # Información de hospedaje
            'check_in',
            'check_out',
            'tipo_habitacion',
            'numero_habitacion',
            'tarifa_noche',
            'adultos',
            'ninos',
            'metodo_pago',
            'observacion',
            # Campos de control
            'fecha_registro',
            'fecha_actualizacion',
            # Propiedades calculadas
            'duracion_estadia',
            'total_estadia',
            'total_huespedes',
        ]
        read_only_fields = ['id', 'fecha_registro', 'fecha_actualizacion']
        extra_kwargs = {
            'nombres_apellidos': {'required': False, 'allow_blank': True, 'allow_null': True},
            'numero_documento': {'required': False, 'allow_blank': True, 'allow_null': True},
            'fecha_nacimiento': {'required': False, 'allow_null': True},
            'procedencia': {'required': False, 'allow_blank': True, 'allow_null': True},
            'check_in': {'required': False, 'allow_null': True},
            'check_out': {'required': False, 'allow_null': True},
            'tipo_habitacion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'numero_habitacion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'tarifa_noche': {'required': False, 'allow_null': True},
        }
    
    def validate_check_out(self, value):
        """Validar que check_out sea posterior a check_in"""
        if 'check_in' in self.initial_data and self.initial_data.get('check_in'):
            from datetime import datetime
            check_in = self.initial_data.get('check_in')
            if isinstance(check_in, str):
                check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
            
            if value <= check_in:
                raise serializers.ValidationError("La fecha de check-out debe ser posterior a check-in")
        return value
    
    def validate_numero_ruc(self, value):
        """Validar que el RUC tenga 11 dígitos si se proporciona"""
        if value and len(value) != 11:
            raise serializers.ValidationError("El RUC debe tener 11 dígitos")
        return value
