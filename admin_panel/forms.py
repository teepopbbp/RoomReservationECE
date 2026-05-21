from django import forms
from rooms.models import Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['code', 'name', 'room_type', 'capacity', 'is_active']
        widgets = {
            'code':      forms.TextInput(attrs={'class': 'form-control'}),
            'name':      forms.TextInput(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'capacity':  forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
