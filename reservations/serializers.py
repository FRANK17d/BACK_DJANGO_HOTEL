from rest_framework import serializers
from .models import Reservation, Companion


class ReservationSerializer(serializers.ModelSerializer):
    companions = serializers.SerializerMethodField()
    rooms = serializers.SerializerMethodField()
    class Meta:
        model = Reservation
        fields = (
            'id', 'reservation_id', 'channel', 'guest_name', 'room_label',
            'check_in', 'check_out', 'total_amount', 'status', 'paid',
            'document_type', 'document_number', 'arrival_time', 'departure_time',
            'num_people', 'num_adults', 'num_children', 'num_rooms',
            'address', 'department', 'province', 'district',
            'taxpayer_type', 'business_status', 'business_condition', 'room_type',
            'companions', 'rooms'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'reservationId': data['reservation_id'],
            'channel': data['channel'],
            'guest': data['guest_name'],
            'room': data['room_label'],
            'rooms': self.get_rooms(instance),
            'checkIn': data['check_in'],
            'checkOut': data['check_out'],
            'total': f"S/ {data['total_amount']}",
            'status': data['status'],
            'paid': data['paid'],
            'documentType': data.get('document_type'),
            'documentNumber': data.get('document_number'),
            'arrivalTime': data.get('arrival_time'),
            'departureTime': data.get('departure_time'),
            'numPeople': data.get('num_people'),
            'numAdults': data.get('num_adults'),
            'numChildren': data.get('num_children'),
            'numRooms': data.get('num_rooms'),
            'companions': self.get_companions(instance),
            'address': data.get('address'),
            'department': data.get('department'),
            'province': data.get('province'),
            'district': data.get('district'),
            'roomType': data.get('room_type'),
            'taxpayerType': data.get('taxpayer_type'),
            'businessStatus': data.get('business_status'),
            'businessCondition': data.get('business_condition'),
        }

    def get_companions(self, instance):
        items = []
        for c in instance.companions.all():
            items.append({
                'name': c.name,
                'documentType': c.document_type,
                'documentNumber': c.document_number,
                'address': c.address,
                'department': c.department,
                'province': c.province,
                'district': c.district,
                'taxpayerType': c.taxpayer_type,
                'businessStatus': c.business_status,
                'businessCondition': c.business_condition,
            })
        return items

    def get_rooms(self, instance):
        codes = [ar.room_code for ar in instance.assigned_rooms.all()]
        if not codes and instance.room_label:
            return [instance.room_label]
        return codes
