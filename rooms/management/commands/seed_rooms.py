from django.core.management.base import BaseCommand

from rooms.models import Room

ROOMS = [
    {'code': '406-3',   'name': 'ห้องประชุม 1', 'room_type': Room.TYPE_MEETING,   'capacity': 60},
    {'code': '406-5',   'name': 'ห้องประชุม 2', 'room_type': Room.TYPE_MEETING,   'capacity': 15},
    {'code': '408-1',   'name': 'ห้องประชุม 3', 'room_type': Room.TYPE_MEETING,   'capacity': 10},
    {'code': '408-2/1', 'name': 'ห้องบรรยาย 1', 'room_type': Room.TYPE_CLASSROOM, 'capacity': 20},
    {'code': '408-2/2', 'name': 'ห้องบรรยาย 2', 'room_type': Room.TYPE_CLASSROOM, 'capacity': 20},
]


class Command(BaseCommand):
    help = 'Seed initial room data'

    def handle(self, *args, **options):
        created = 0
        for data in ROOMS:
            _, was_created = Room.objects.get_or_create(code=data['code'], defaults=data)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} room(s).'))
