import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.labeling.models import Annotation, Task, TaskAssignment
from apps.rooms.models import RoomMembership, RoomPin
from apps.users.models import User
from tests.factories import invite_annotator, make_room, make_user


class RoomsApiTests(APITestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.customer = make_user(username="customer", role=User.Role.CUSTOMER)
        self.annotator = make_user(username="annotator", role=User.Role.ANNOTATOR)
        self.other_annotator = make_user(username="annotator2", role=User.Role.ANNOTATOR)

    def auth(self, user):
        return {"HTTP_X_USER_ID": str(user.id)}

    def test_customer_can_create_room(self):
        response = self.client.post(
            reverse("room-list-create"),
            {"title": "New room", "description": "MVP room"},
            format="json",
            **self.auth(self.customer),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New room")
        self.assertEqual(response.data["created_by_id"], self.customer.id)

    def test_customer_can_create_room_with_cross_validation_settings(self):
        response = self.client.post(
            reverse("room-list-create"),
            {
                "title": "Cross room",
                "cross_validation_enabled": True,
                "cross_validation_annotators_count": 3,
                "cross_validation_similarity_threshold": 85,
            },
            format="json",
            **self.auth(self.customer),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["cross_validation_enabled"])
        self.assertEqual(response.data["cross_validation_annotators_count"], 3)
        self.assertEqual(response.data["cross_validation_similarity_threshold"], 85)

    def test_customer_can_invite_annotator(self):
        room = make_room(customer=self.customer, title="Room 1")

        response = self.client.post(
            reverse("room-invite", kwargs={"room_id": room.id}),
            {"annotator_id": self.annotator.id},
            format="json",
            **self.auth(self.customer),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        membership = RoomMembership.objects.get(room=room, user=self.annotator)
        self.assertEqual(membership.status, RoomMembership.Status.INVITED)

    def test_annotator_sees_only_invited_rooms(self):
        visible_room = make_room(customer=self.customer, title="Visible room")
        hidden_room = make_room(customer=self.customer, title="Hidden room")
        invite_annotator(room=visible_room, annotator=self.annotator, invited_by=self.customer)
        invite_annotator(room=hidden_room, annotator=self.other_annotator, invited_by=self.customer)

        response = self.client.get(reverse("my-rooms"), **self.auth(self.annotator))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], visible_room.id)

    def test_user_can_pin_room_and_pinned_rooms_appear_first(self):
        first_room = make_room(customer=self.customer, title="First room")
        second_room = make_room(customer=self.customer, title="Second room")
        invite_annotator(room=first_room, annotator=self.annotator, invited_by=self.customer)
        invite_annotator(room=second_room, annotator=self.annotator, invited_by=self.customer)

        pin_response = self.client.post(
            reverse("room-pin", kwargs={"room_id": first_room.id}),
            {"is_pinned": True},
            format="json",
            **self.auth(self.annotator),
        )
        list_response = self.client.get(reverse("my-rooms"), **self.auth(self.annotator))

        self.assertEqual(pin_response.status_code, status.HTTP_200_OK)
        self.assertTrue(RoomPin.objects.filter(room=first_room, user=self.annotator).exists())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in list_response.data], [first_room.id, second_room.id])
        self.assertTrue(list_response.data[0]["is_pinned"])
        self.assertFalse(list_response.data[1]["is_pinned"])

    def test_room_pinning_is_per_user(self):
        room = make_room(customer=self.customer, title="Shared room")
        invite_annotator(room=room, annotator=self.annotator, invited_by=self.customer)
        invite_annotator(room=room, annotator=self.other_annotator, invited_by=self.customer)

        self.client.post(
            reverse("room-pin", kwargs={"room_id": room.id}),
            {"is_pinned": True},
            format="json",
            **self.auth(self.annotator),
        )

        annotator_response = self.client.get(reverse("my-rooms"), **self.auth(self.annotator))
        other_response = self.client.get(reverse("my-rooms"), **self.auth(self.other_annotator))

        self.assertEqual(annotator_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_200_OK)
        self.assertTrue(annotator_response.data[0]["is_pinned"])
        self.assertFalse(other_response.data[0]["is_pinned"])

    def test_annotator_cannot_join_uninvited_room(self):
        room = make_room(customer=self.customer, title="Locked room")

        response = self.client.post(
            reverse("room-join", kwargs={"room_id": room.id}),
            format="json",
            **self.auth(self.annotator),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(RoomMembership.objects.filter(room=room, user=self.annotator).exists())

    def test_invited_annotator_can_join_room(self):
        room = make_room(customer=self.customer, title="Invited room")
        invite_annotator(room=room, annotator=self.annotator, invited_by=self.customer)

        response = self.client.post(
            reverse("room-join", kwargs={"room_id": room.id}),
            format="json",
            **self.auth(self.annotator),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = RoomMembership.objects.get(room=room, user=self.annotator)
        self.assertEqual(membership.status, RoomMembership.Status.JOINED)

    def test_user_can_enter_room_by_id_and_password(self):
        room = make_room(customer=self.customer, title="Password room")
        room.set_access_password("demo123")
        room.save(update_fields=["access_password_hash", "updated_at"])

        response = self.client.post(
            reverse("room-access"),
            {"room_id": room.id, "password": "demo123"},
            format="json",
            **self.auth(self.annotator),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["redirect_url"], f"/rooms/{room.id}/")
        membership = RoomMembership.objects.get(room=room, user=self.annotator)
        self.assertEqual(membership.status, RoomMembership.Status.JOINED)

    def test_customer_can_create_image_room_with_labels_and_uploads(self):
        response = self.client.post(
            reverse("room-list-create"),
            {
                "title": "Image room",
                "dataset_mode": "image",
                "dataset_label": "Cars",
                "labels": json.dumps(
                    [
                        {"name": "car", "color": "#FF6B6B"},
                        {"name": "truck", "color": "#4ECDC4"},
                    ]
                ),
                "media_manifest": json.dumps(
                    [
                        {"name": "car-1.jpg", "width": 1920, "height": 1080},
                        {"name": "car-2.jpg", "width": 1280, "height": 720},
                    ]
                ),
                "dataset_files": [
                    SimpleUploadedFile("car-1.jpg", b"fake-image-1", content_type="image/jpeg"),
                    SimpleUploadedFile("car-2.jpg", b"fake-image-2", content_type="image/jpeg"),
                ],
            },
            format="multipart",
            **self.auth(self.customer),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = self.customer.created_rooms.get(id=response.data["id"])
        self.assertEqual(room.dataset_type, "image")
        self.assertEqual(room.labels.count(), 2)
        self.assertEqual(room.tasks.count(), 2)
        first_task = room.tasks.order_by("id").first()
        self.assertEqual(first_task.source_type, Task.SourceType.IMAGE)
        self.assertTrue(first_task.source_file.name)
        self.assertEqual(first_task.input_payload["width"], 1920)

    def test_customer_can_create_video_room_and_split_it_into_frame_tasks(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg is not available in the current environment")

        video_path = Path(self.media_dir.name) / "sample.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=32x32:d=0.2:r=5",
                str(video_path),
            ],
            check=True,
            capture_output=True,
        )

        with video_path.open("rb") as video_handle:
            response = self.client.post(
                reverse("room-list-create"),
                {
                    "title": "Video room",
                    "dataset_mode": "video",
                    "dataset_label": "Frames",
                    "labels": json.dumps([{"name": "car", "color": "#FF6B6B"}]),
                    "media_manifest": json.dumps(
                        [
                            {
                                "name": "sample.mp4",
                                "width": 32,
                                "height": 32,
                                "duration": 0.2,
                                "frame_rate": 5,
                            }
                        ]
                    ),
                    "dataset_files": [
                        SimpleUploadedFile("sample.mp4", video_handle.read(), content_type="video/mp4"),
                    ],
                },
                format="multipart",
                **self.auth(self.customer),
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = self.customer.created_rooms.get(id=response.data["id"])
        self.assertEqual(room.dataset_type, "video")
        self.assertGreater(room.tasks.count(), 0)
        first_task = room.tasks.order_by("id").first()
        self.assertEqual(first_task.source_type, Task.SourceType.IMAGE)
        self.assertEqual(first_task.input_payload["origin_source_type"], Task.SourceType.VIDEO)
        self.assertTrue(first_task.source_file.name.endswith(".jpg"))

    def test_customer_can_export_native_room_dataset(self):
        room = make_room(customer=self.customer, title="Export room", dataset_type="image")
        label = room.labels.create(name="car", color="#FF6B6B", sort_order=0)
        task = Task.objects.create(
            room=room,
            source_type=Task.SourceType.IMAGE,
            source_name="car-1.jpg",
            input_payload={"width": 640, "height": 480, "source_name": "car-1.jpg"},
        )
        assignment = TaskAssignment.objects.create(
            task=task,
            annotator=self.annotator,
            round_number=1,
            status=TaskAssignment.Status.SUBMITTED,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
        )
        Annotation.objects.create(
            task=task,
            assignment=assignment,
            annotator=self.annotator,
            result_payload={
                "annotations": [
                    {
                        "type": "bbox",
                        "label_id": label.id,
                        "points": [10, 12, 110, 112],
                        "frame": 0,
                        "attributes": [],
                        "occluded": False,
                    }
                ]
            },
            submitted_at=timezone.now(),
        )
        task.consensus_payload = {
            "annotations": [
                {
                    "type": "bbox",
                    "label_id": label.id,
                    "points": [10, 12, 110, 112],
                    "frame": 0,
                    "attributes": [],
                    "occluded": False,
                }
            ]
        }
        task.validation_score = 100.0
        task.status = Task.Status.SUBMITTED
        task.save(update_fields=["consensus_payload", "validation_score", "status", "updated_at"])

        response = self.client.get(
            f'{reverse("room-export", kwargs={"room_id": room.id})}?export_format=native_json',
            **self.auth(self.customer),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment;", response["Content-Disposition"])
        payload = json.loads(response.content)
        self.assertEqual(payload["room"]["id"], room.id)
        self.assertEqual(payload["labels"][0]["name"], "car")
        self.assertEqual(payload["tasks"][0]["annotation"]["annotations"][0]["label_id"], label.id)

    def test_export_ignores_non_validated_annotations(self):
        room = make_room(customer=self.customer, title="Export filtered room", dataset_type="image")
        label = room.labels.create(name="car", color="#FF6B6B", sort_order=0)

        valid_task = Task.objects.create(
            room=room,
            status=Task.Status.SUBMITTED,
            source_type=Task.SourceType.IMAGE,
            source_name="valid.jpg",
            input_payload={"width": 640, "height": 480, "source_name": "valid.jpg"},
            consensus_payload={
                "annotations": [
                    {
                        "type": "bbox",
                        "label_id": label.id,
                        "points": [10, 10, 100, 100],
                        "frame": 0,
                        "attributes": [],
                        "occluded": False,
                    }
                ]
            },
            validation_score=100.0,
        )
        pending_task = Task.objects.create(
            room=room,
            status=Task.Status.PENDING,
            source_type=Task.SourceType.IMAGE,
            source_name="pending.jpg",
            input_payload={"width": 640, "height": 480, "source_name": "pending.jpg"},
        )

        submitted_assignment = TaskAssignment.objects.create(
            task=pending_task,
            annotator=self.annotator,
            round_number=1,
            status=TaskAssignment.Status.SUBMITTED,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
        )
        Annotation.objects.create(
            task=pending_task,
            assignment=submitted_assignment,
            annotator=self.annotator,
            result_payload={
                "annotations": [
                    {
                        "type": "bbox",
                        "label_id": label.id,
                        "points": [20, 20, 120, 120],
                        "frame": 0,
                        "attributes": [],
                        "occluded": False,
                    }
                ]
            },
            submitted_at=timezone.now(),
        )

        native_response = self.client.get(
            f'{reverse("room-export", kwargs={"room_id": room.id})}?export_format=native_json',
            **self.auth(self.customer),
        )
        coco_response = self.client.get(
            f'{reverse("room-export", kwargs={"room_id": room.id})}?export_format=coco_json',
            **self.auth(self.customer),
        )

        self.assertEqual(native_response.status_code, status.HTTP_200_OK)
        self.assertEqual(coco_response.status_code, status.HTTP_200_OK)

        native_payload = json.loads(native_response.content)
        coco_payload = json.loads(coco_response.content)

        self.assertEqual([item["task_id"] for item in native_payload["tasks"]], [valid_task.id])
        self.assertEqual([item["id"] for item in coco_payload["images"]], [valid_task.id])
        self.assertEqual([item["image_id"] for item in coco_payload["annotations"]], [valid_task.id])

    def test_owner_can_review_and_reject_submitted_task(self):
        room = make_room(customer=self.customer, title="Review room", dataset_type="image")
        label = room.labels.create(name="car", color="#FF6B6B", sort_order=0)
        task = Task.objects.create(
            room=room,
            status=Task.Status.SUBMITTED,
            source_type=Task.SourceType.IMAGE,
            source_name="review.jpg",
            input_payload={"width": 640, "height": 480, "source_name": "review.jpg"},
            consensus_payload={
                "annotations": [
                    {
                        "type": "bbox",
                        "label_id": label.id,
                        "points": [10, 10, 100, 100],
                        "frame": 0,
                        "attributes": [],
                        "occluded": False,
                    }
                ]
            },
            validation_score=92.0,
        )
        assignment = TaskAssignment.objects.create(
            task=task,
            annotator=self.annotator,
            round_number=1,
            status=TaskAssignment.Status.SUBMITTED,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
        )
        Annotation.objects.create(
            task=task,
            assignment=assignment,
            annotator=self.annotator,
            result_payload=task.consensus_payload,
            submitted_at=timezone.now(),
        )

        list_response = self.client.get(
            reverse("room-review-tasks", kwargs={"room_id": room.id}),
            **self.auth(self.customer),
        )
        detail_response = self.client.get(
            reverse("task-review-detail", kwargs={"task_id": task.id}),
            **self.auth(self.customer),
        )
        reject_response = self.client.post(
            reverse("task-reject", kwargs={"task_id": task.id}),
            format="json",
            **self.auth(self.customer),
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]["id"], task.id)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["task"]["id"], task.id)
        self.assertEqual(len(detail_response.data["annotations"]), 1)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertEqual(task.current_round, 2)
        self.assertIsNone(task.consensus_payload)
