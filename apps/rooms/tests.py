import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.labeling.models import Task
from apps.rooms.models import Room, RoomMembership
from apps.users.models import User


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RoomListCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="owner", password="secret123")
        self.client.force_authenticate(self.user)

    def tearDown(self):
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for path in sorted(media_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            media_root.rmdir()

    def test_multipart_request_with_dataset_files_creates_image_room(self):
        response = self.client.post(
            "/api/v1/rooms/",
            data={
                "title": "Vision room",
                "dataset_mode": Room.DatasetType.IMAGE,
                "labels": json.dumps([{"name": "Car", "color": "#FF0000"}]),
                "media_manifest": json.dumps([{"name": "sample.png", "width": 100, "height": 50}]),
                "dataset_files": [self._uploaded_file("sample.png")],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = Room.objects.get(title="Vision room")
        self.assertEqual(room.dataset_type, Room.DatasetType.IMAGE)
        self.assertEqual(room.labels.count(), 1)
        self.assertEqual(room.tasks.count(), 1)
        task = Task.objects.get(room=room)
        self.assertEqual(task.source_name, "sample.png")
        self.assertEqual(task.input_payload["width"], 100)
        self.assertEqual(task.input_payload["height"], 50)

    def test_multipart_request_with_single_annotator_id_creates_membership(self):
        annotator = User.objects.create_user(username="annotator", password="secret123")

        response = self.client.post(
            "/api/v1/rooms/",
            data={
                "title": "Demo room",
                "dataset_mode": Room.DatasetType.DEMO,
                "annotator_ids": [str(annotator.id)],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = Room.objects.get(title="Demo room")
        membership = RoomMembership.objects.get(room=room, user=annotator)
        self.assertEqual(membership.status, RoomMembership.Status.INVITED)

    def test_owner_can_delete_room(self):
        room = Room.objects.create(title="Delete me", created_by=self.user)

        response = self.client.delete(f"/api/v1/rooms/{room.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(id=room.id).exists())

    @staticmethod
    def _uploaded_file(name: str):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/png")
