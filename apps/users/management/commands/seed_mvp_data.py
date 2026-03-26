from django.core.management.base import BaseCommand

from apps.labeling.models import Task
from apps.rooms.models import Room, RoomMembership
from apps.users.models import User


class Command(BaseCommand):
    help = "Create local MVP seed data for manual API testing."

    def handle(self, *args, **options):
        customer, _ = User.objects.get_or_create(
            username="customer_demo",
            defaults={
                "email": "customer@example.com",
                "role": User.Role.CUSTOMER,
            },
        )

        annotator_1, _ = User.objects.get_or_create(
            username="annotator_alice",
            defaults={
                "email": "alice@example.com",
                "role": User.Role.ANNOTATOR,
            },
        )
        annotator_2, _ = User.objects.get_or_create(
            username="annotator_bob",
            defaults={
                "email": "bob@example.com",
                "role": User.Role.ANNOTATOR,
            },
        )

        room, _ = Room.objects.get_or_create(
            title="Demo dataset room",
            created_by=customer,
            defaults={"description": "Room with sample tasks for local MVP checks."},
        )

        RoomMembership.objects.get_or_create(
            room=room,
            user=annotator_1,
            defaults={
                "invited_by": customer,
                "status": RoomMembership.Status.INVITED,
            },
        )
        RoomMembership.objects.get_or_create(
            room=room,
            user=annotator_2,
            defaults={
                "invited_by": customer,
                "status": RoomMembership.Status.INVITED,
            },
        )

        existing_tasks = Task.objects.filter(room=room).count()
        if existing_tasks == 0:
            Task.objects.bulk_create(
                [
                    Task(room=room, input_payload={"text": "Label sentiment for sample #1"}),
                    Task(room=room, input_payload={"text": "Label sentiment for sample #2"}),
                    Task(room=room, input_payload={"text": "Label sentiment for sample #3"}),
                ]
            )

        self.stdout.write(self.style.SUCCESS("Seed data is ready."))
        self.stdout.write(f"Customer id: {customer.id} ({customer.username})")
        self.stdout.write(f"Annotator Alice id: {annotator_1.id} ({annotator_1.username})")
        self.stdout.write(f"Annotator Bob id: {annotator_2.id} ({annotator_2.username})")
        self.stdout.write(f"Room id: {room.id} ({room.title})")
