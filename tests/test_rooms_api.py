from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.rooms.models import RoomMembership
from apps.users.models import User
from tests.factories import invite_annotator, make_room, make_user


class RoomsApiTests(APITestCase):
    def setUp(self):
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

    def test_annotator_cannot_join_uninvited_room(self):
        room = make_room(customer=self.customer, title="Locked room")

        response = self.client.post(
            reverse("room-join", kwargs={"room_id": room.id}),
            format="json",
            **self.auth(self.annotator),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
