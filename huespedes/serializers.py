from rest_framework import serializers
from .models import Huesped, Acompanante


class AcompananteSerializer(serializers.ModelSerializer):
    """Serializer para acompañantes"""
    
    class Meta:
        model = Acompanante
        fields = [
            'id',
            'tipo_documento',
            'numero_documento',
            'nombres_apellidos',
            'fecha_nacimiento',
            'nacionalidad',
            'procedencia',
            'fecha_registro',
        ]
        read_only_fields = ['id', 'fecha_registro']
        extra_kwargs = {
            'tipo_documento': {'required': False},
            'numero_documento': {'required': False, 'allow_blank': True, 'allow_null': True},
            'nombres_apellidos': {'required': False, 'allow_blank': True, 'allow_null': True},
            'fecha_nacimiento': {'required': False, 'allow_null': True},
            'nacionalidad': {'required': False, 'allow_blank': True},
            'procedencia': {'required': False, 'allow_blank': True, 'allow_null': True},
        }


class HuespedSerializer(serializers.ModelSerializer):
    duracion_estadia = serializers.ReadOnlyField()
    total_estadia = serializers.ReadOnlyField()
    total_huespedes = serializers.ReadOnlyField()
    is_day_use = serializers.ReadOnlyField()
    acompanantes = AcompananteSerializer(many=True, required=False)
    
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
            'celular',
            # Información de hospedaje
            'check_in',
            'hora_entrada',
            'check_out',
            'hora_salida',
            'tipo_habitacion',
            'numero_habitacion',
            'tarifa_noche',
            'adultos',
            'ninos',
            'metodo_pago',
            'tipo_desayuno',
            'observacion',
            # Campos de control
            'fecha_registro',
            'fecha_actualizacion',
            # Propiedades calculadas
            'duracion_estadia',
            'total_estadia',
            'total_huespedes',
            'is_day_use',
            # Acompañantes
            'acompanantes',
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
        """Validar que check_out sea igual o posterior a check_in (permite DAY USE)"""
        if 'check_in' in self.initial_data and self.initial_data.get('check_in'):
            from datetime import datetime
            check_in = self.initial_data.get('check_in')
            if isinstance(check_in, str):
                check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
            
            # Permitir DAY USE: check_out puede ser igual a check_in
            if value < check_in:
                raise serializers.ValidationError("La fecha de check-out no puede ser anterior a check-in")
        return value
    
    def validate_numero_ruc(self, value):
        """Validar que el RUC tenga 11 dígitos si se proporciona"""
        if value and len(value) != 11:
            raise serializers.ValidationError("El RUC debe tener 11 dígitos")
        return value
    
    def create(self, validated_data):
        """Crear huésped con acompañantes"""
        acompanantes_data = validated_data.pop('acompanantes', [])
        huesped = Huesped.objects.create(**validated_data)
        
        for acompanante_data in acompanantes_data:
            Acompanante.objects.create(huesped=huesped, **acompanante_data)
        
        return huesped
    
    def update(self, instance, validated_data):
        """Actualizar huésped y sus acompañantes"""
        acompanantes_data = validated_data.pop('acompanantes', None)
        
        # Actualizar campos del huésped
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Si se envían acompañantes, actualizar la lista
        if acompanantes_data is not None:
            # Eliminar acompañantes existentes
            instance.acompanantes.all().delete()
            
            # Crear nuevos acompañantes
            for acompanante_data in acompanantes_data:
                Acompanante.objects.create(huesped=instance, **acompanante_data)
        
        return instance

