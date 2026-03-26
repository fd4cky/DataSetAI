import io
import json
import zipfile
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.labeling.models import Task
from apps.rooms.models import Room, RoomLabel, RoomMembership
from apps.users.models import User
from common.exceptions import AccessDeniedError, ConflictError, NotFoundError


DEMO_DATASET_SAMPLES = [
    "Пользователь оставил положительный отзыв о качестве сервиса.",
    "Нужно определить тематику короткого сообщения из поддержки.",
    "Определи тональность комментария под товаром.",
    "Классифицируй новостной заголовок по теме публикации.",
    "Отметь, содержит ли текст токсичную лексику.",
    "Определи язык сообщения в пользовательском фидбэке.",
    "Разметь интент обращения клиента в поддержку.",
    "Определи, относится ли сообщение к жалобе или благодарности.",
]

DEFAULT_LABEL_COLORS = [
    "#FF6B6B",
    "#4ECDC4",
    "#FFD166",
    "#118AB2",
    "#EF476F",
    "#06D6A0",
    "#F78C6B",
    "#9B5DE5",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
JSON_EXTENSIONS = {".json"}


@dataclass
class ExportArtifact:
    content: bytes
    filename: str
    content_type: str


def get_supported_export_formats(*, room: Room) -> list[dict[str, str]]:
    formats = [
        {"value": "native_json", "label": "Native JSON"},
    ]
    if room.dataset_type == Room.DatasetType.IMAGE:
        formats.extend(
            [
                {"value": "coco_json", "label": "COCO JSON"},
                {"value": "yolo_zip", "label": "YOLO ZIP"},
            ]
        )
    return formats


def create_room(
    *,
    creator: User,
    title: str,
    description: str = "",
    password: str = "",
    deadline=None,
    annotator_ids: list[int] | None = None,
    dataset_mode: str = "demo",
    test_task_count: int = 12,
    dataset_label: str = "",
    dataset_files: list | None = None,
    labels: list[dict] | None = None,
    media_manifest: list[dict] | None = None,
) -> Room:
    normalized_label = dataset_label or "Тестовый датасет"
    unique_annotator_ids = list(dict.fromkeys(annotator_ids or []))
    dataset_files = list(dataset_files or [])
    label_definitions = list(labels or [])
    media_manifest = list(media_manifest or [])

    with transaction.atomic():
        room = Room(
            title=title,
            description=description,
            created_by=creator,
            deadline=deadline,
            dataset_label=normalized_label,
            dataset_type=dataset_mode,
        )
        room.set_access_password(password)
        room.save()

        if dataset_mode == "demo":
            _create_demo_tasks(room=room, task_count=test_task_count, dataset_label=normalized_label)
        elif dataset_mode == Room.DatasetType.JSON:
            _create_json_tasks(room=room, dataset_label=normalized_label, dataset_files=dataset_files)
        elif dataset_mode == Room.DatasetType.IMAGE:
            _create_media_tasks(
                room=room,
                dataset_label=normalized_label,
                dataset_files=dataset_files,
                media_manifest=media_manifest,
                source_type=Task.SourceType.IMAGE,
            )
        elif dataset_mode == Room.DatasetType.VIDEO:
            _create_media_tasks(
                room=room,
                dataset_label=normalized_label,
                dataset_files=dataset_files,
                media_manifest=media_manifest,
                source_type=Task.SourceType.VIDEO,
            )

        if label_definitions:
            _create_room_labels(room=room, label_definitions=label_definitions)

        for annotator_id in unique_annotator_ids:
            invite_user_to_room(room=room, inviter=creator, invited_user_id=annotator_id)

        return room


def invite_user_to_room(*, room: Room, inviter: User, invited_user_id: int) -> RoomMembership:
    if room.created_by_id != inviter.id:
        raise AccessDeniedError("Only the room owner can invite participants.")

    try:
        invited_user = User.objects.get(id=invited_user_id)
    except User.DoesNotExist as exc:
        raise NotFoundError("Invited user not found.") from exc

    if invited_user.id == room.created_by_id:
        raise ConflictError("Room owner already has access to this room.")

    membership, created = RoomMembership.objects.get_or_create(
        room=room,
        user=invited_user,
        defaults={
            "invited_by": inviter,
            "status": RoomMembership.Status.INVITED,
        },
    )

    if not created and membership.status == RoomMembership.Status.INVITED:
        membership.invited_by = inviter
        membership.save(update_fields=["invited_by", "updated_at"])

    return membership


def validate_room_password(*, room: Room, password: str = "") -> None:
    if not room.check_access_password(password):
        raise AccessDeniedError("Incorrect room password.")


def join_room(*, room: Room, annotator: User, password: str | None = None) -> RoomMembership:
    if password is not None:
        validate_room_password(room=room, password=password)

    membership, _ = RoomMembership.objects.get_or_create(
        room=room,
        user=annotator,
        defaults={
            "invited_by": room.created_by,
            "status": RoomMembership.Status.JOINED,
            "joined_at": timezone.now(),
        },
    )

    if membership.status != RoomMembership.Status.JOINED or membership.joined_at is None:
        membership.status = RoomMembership.Status.JOINED
        membership.joined_at = timezone.now()
        membership.save(update_fields=["status", "joined_at", "updated_at"])

    return membership


def _create_demo_tasks(*, room: Room, task_count: int, dataset_label: str) -> None:
    sample_iterator = cycle(DEMO_DATASET_SAMPLES)
    tasks = []
    for index in range(task_count):
        tasks.append(
            Task(
                room=room,
                source_type=Task.SourceType.TEXT,
                input_payload={
                    "dataset": dataset_label,
                    "item_number": index + 1,
                    "text": next(sample_iterator),
                },
            )
        )

    Task.objects.bulk_create(tasks)


def _create_room_labels(*, room: Room, label_definitions: list[dict]) -> None:
    labels = []
    for index, item in enumerate(label_definitions):
        labels.append(
            RoomLabel(
                room=room,
                name=item["name"].strip(),
                color=(item.get("color") or DEFAULT_LABEL_COLORS[index % len(DEFAULT_LABEL_COLORS)]).upper(),
                sort_order=index,
            )
        )
    RoomLabel.objects.bulk_create(labels)


def _normalize_json_task_payload(item, dataset_label: str, item_number: int) -> dict:
    if isinstance(item, dict):
        payload = dict(item)
    else:
        payload = {"value": item}
    payload.setdefault("dataset", dataset_label)
    payload.setdefault("item_number", item_number)
    return payload


def _load_json_dataset_items(dataset_file) -> list:
    try:
        payload = json.loads(dataset_file.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConflictError("JSON dataset must be a valid UTF-8 JSON file.") from exc

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("tasks", "items", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]

    raise ConflictError("JSON dataset must contain an array or an object.")


def _create_json_tasks(*, room: Room, dataset_label: str, dataset_files: list) -> None:
    if len(dataset_files) != 1:
        raise ConflictError("JSON dataset upload expects exactly one .json file.")

    items = _load_json_dataset_items(dataset_files[0])
    if not items:
        raise ConflictError("JSON dataset file is empty.")

    tasks = []
    for index, item in enumerate(items):
        tasks.append(
            Task(
                room=room,
                source_type=Task.SourceType.TEXT,
                input_payload=_normalize_json_task_payload(item, dataset_label, index + 1),
            )
        )
    Task.objects.bulk_create(tasks)


def _create_media_tasks(
    *,
    room: Room,
    dataset_label: str,
    dataset_files: list,
    media_manifest: list[dict],
    source_type: str,
) -> None:
    manifest_by_name = {item["name"]: item for item in media_manifest if item.get("name")}

    for index, dataset_file in enumerate(dataset_files):
        file_name = Path(dataset_file.name).name
        metadata = manifest_by_name.get(file_name, {})
        input_payload = {
            "dataset": dataset_label,
            "item_number": index + 1,
            "source_name": file_name,
        }
        if metadata.get("width"):
            input_payload["width"] = metadata["width"]
        if metadata.get("height"):
            input_payload["height"] = metadata["height"]
        if source_type == Task.SourceType.VIDEO:
            input_payload["duration"] = metadata.get("duration") or 0
            input_payload["frame_rate"] = metadata.get("frame_rate") or 25

        Task.objects.create(
            room=room,
            source_type=source_type,
            source_name=file_name,
            source_file=dataset_file,
            input_payload=input_payload,
        )


def validate_dataset_upload(*, dataset_mode: str, dataset_files: list) -> None:
    if dataset_mode == Room.DatasetType.DEMO:
        return

    if not dataset_files:
        raise ConflictError("Upload at least one dataset file.")

    suffixes = {Path(file.name).suffix.lower() for file in dataset_files}

    if dataset_mode == Room.DatasetType.JSON:
        if suffixes - JSON_EXTENSIONS:
            raise ConflictError("JSON mode accepts only .json files.")
        return

    allowed_extensions = IMAGE_EXTENSIONS if dataset_mode == Room.DatasetType.IMAGE else VIDEO_EXTENSIONS
    if suffixes - allowed_extensions:
        raise ConflictError("Uploaded files do not match the selected dataset type.")


def _build_native_export(*, room: Room, tasks, labels, base_url: str | None) -> ExportArtifact:
    content = {
        "room": {
            "id": room.id,
            "title": room.title,
            "dataset_label": room.dataset_label,
            "dataset_type": room.dataset_type,
            "deadline": room.deadline.isoformat() if room.deadline else None,
        },
        "labels": [
            {
                "id": label.id,
                "name": label.name,
                "color": label.color,
            }
            for label in labels
        ],
        "tasks": [],
    }

    for task in tasks:
        source_url = task.source_file.url if task.source_file else None
        if source_url and base_url:
            source_url = f"{base_url}{source_url}"
        content["tasks"].append(
            {
                "task_id": task.id,
                "source_type": task.source_type,
                "source_name": task.source_name,
                "source_url": source_url,
                "input_payload": task.input_payload,
                "annotation": task.annotation.result_payload if hasattr(task, "annotation") else None,
            }
        )

    return ExportArtifact(
        content=json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"),
        filename=f"room_{room.id}_native.json",
        content_type="application/json; charset=utf-8",
    )


def _build_coco_export(*, room: Room, tasks, labels) -> ExportArtifact:
    if room.dataset_type != Room.DatasetType.IMAGE:
        raise ConflictError("COCO export is available only for image datasets.")

    annotations = []
    images = []
    annotation_id = 1

    for task in tasks:
        width = int(task.input_payload.get("width") or 0)
        height = int(task.input_payload.get("height") or 0)
        images.append(
            {
                "id": task.id,
                "file_name": task.source_name,
                "width": width,
                "height": height,
            }
        )

        if not hasattr(task, "annotation"):
            continue

        for item in task.annotation.result_payload.get("annotations", []):
            x_min, y_min, x_max, y_max = item["points"]
            width_value = max(x_max - x_min, 0)
            height_value = max(y_max - y_min, 0)
            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": task.id,
                    "category_id": item["label_id"],
                    "bbox": [x_min, y_min, width_value, height_value],
                    "area": width_value * height_value,
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

    content = {
        "info": {
            "description": room.title,
        },
        "images": images,
        "annotations": annotations,
        "categories": [
            {
                "id": label.id,
                "name": label.name,
                "supercategory": room.dataset_label or "dataset",
            }
            for label in labels
        ],
    }

    return ExportArtifact(
        content=json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"),
        filename=f"room_{room.id}_coco.json",
        content_type="application/json; charset=utf-8",
    )


def _build_yolo_export(*, room: Room, tasks, labels) -> ExportArtifact:
    if room.dataset_type != Room.DatasetType.IMAGE:
        raise ConflictError("YOLO export is available only for image datasets.")

    label_order = {label.id: index for index, label in enumerate(labels)}
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "data.yaml",
            "\n".join(
                [
                    f"path: room_{room.id}",
                    "train: images",
                    "val: images",
                    f"nc: {len(labels)}",
                    f"names: [{', '.join(json.dumps(label.name, ensure_ascii=False) for label in labels)}]",
                ]
            ),
        )

        for task in tasks:
            width = float(task.input_payload.get("width") or 0)
            height = float(task.input_payload.get("height") or 0)
            stem = Path(task.source_name or f"task_{task.id}").stem
            lines = []

            if hasattr(task, "annotation") and width > 0 and height > 0:
                for item in task.annotation.result_payload.get("annotations", []):
                    x_min, y_min, x_max, y_max = item["points"]
                    box_width = max(x_max - x_min, 0)
                    box_height = max(y_max - y_min, 0)
                    x_center = x_min + box_width / 2
                    y_center = y_min + box_height / 2
                    lines.append(
                        " ".join(
                            [
                                str(label_order[item["label_id"]]),
                                f"{x_center / width:.6f}",
                                f"{y_center / height:.6f}",
                                f"{box_width / width:.6f}",
                                f"{box_height / height:.6f}",
                            ]
                        )
                    )

            archive.writestr(f"labels/{stem}.txt", "\n".join(lines))

    return ExportArtifact(
        content=buffer.getvalue(),
        filename=f"room_{room.id}_yolo.zip",
        content_type="application/zip",
    )


def export_room_annotations(*, room: Room, export_format: str, base_url: str | None = None) -> ExportArtifact:
    tasks = list(room.tasks.select_related("annotation").all())
    labels = list(room.labels.all())

    if export_format == "native_json":
        return _build_native_export(room=room, tasks=tasks, labels=labels, base_url=base_url)
    if export_format == "coco_json":
        return _build_coco_export(room=room, tasks=tasks, labels=labels)
    if export_format == "yolo_zip":
        return _build_yolo_export(room=room, tasks=tasks, labels=labels)

    raise NotFoundError("Unsupported export format.")
