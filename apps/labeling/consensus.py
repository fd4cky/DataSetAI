import json
from collections import Counter
from itertools import combinations


def evaluate_annotation_consensus(*, annotations, similarity_threshold: int) -> dict:
    if not annotations:
        return {
            "score": 0.0,
            "accepted": False,
            "consensus_payload": None,
        }

    payloads = [annotation.result_payload for annotation in annotations]
    score = _compute_similarity_score(payloads)
    consensus_payload = _select_consensus_payload(payloads) if score >= similarity_threshold else None

    return {
        "score": score,
        "accepted": score >= similarity_threshold,
        "consensus_payload": consensus_payload,
    }


def _compute_similarity_score(payloads: list) -> float:
    if len(payloads) <= 1:
        return 100.0

    if _is_media_payload(payloads[0]):
        pair_scores = [_media_payload_similarity(left, right) for left, right in combinations(payloads, 2)]
        if not pair_scores:
            return 100.0
        return round((sum(pair_scores) / len(pair_scores)) * 100, 2)

    serialized_payloads = [_serialize_payload(payload) for payload in payloads]
    most_common_count = Counter(serialized_payloads).most_common(1)[0][1]
    return round((most_common_count / len(serialized_payloads)) * 100, 2)


def _select_consensus_payload(payloads: list):
    if not payloads:
        return None

    if _is_media_payload(payloads[0]):
        return max(
            payloads,
            key=lambda candidate: sum(
                _media_payload_similarity(candidate, other)
                for other in payloads
                if other is not candidate
            ),
        )

    serialized_payloads = [_serialize_payload(payload) for payload in payloads]
    most_common_serialized = Counter(serialized_payloads).most_common(1)[0][0]
    return json.loads(most_common_serialized)


def _is_media_payload(payload) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("annotations"), list)


def _serialize_payload(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _media_payload_similarity(left_payload: dict, right_payload: dict) -> float:
    left_annotations = left_payload.get("annotations", [])
    right_annotations = right_payload.get("annotations", [])

    if not left_annotations and not right_annotations:
        return 1.0
    if not left_annotations or not right_annotations:
        return 0.0

    used_indices: set[int] = set()
    matched_iou_sum = 0.0

    for left_item in left_annotations:
        best_index = None
        best_score = 0.0
        for index, right_item in enumerate(right_annotations):
            if index in used_indices:
                continue
            if left_item.get("label_id") != right_item.get("label_id"):
                continue
            if int(left_item.get("frame", 0)) != int(right_item.get("frame", 0)):
                continue

            score = _bbox_iou(left_item.get("points", []), right_item.get("points", []))
            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None:
            used_indices.add(best_index)
            matched_iou_sum += best_score

    denominator = len(left_annotations) + len(right_annotations)
    if denominator == 0:
        return 1.0
    return (2 * matched_iou_sum) / denominator


def _bbox_iou(left_points, right_points) -> float:
    if len(left_points) != 4 or len(right_points) != 4:
        return 0.0

    left_x1, left_y1, left_x2, left_y2 = left_points
    right_x1, right_y1, right_x2, right_y2 = right_points

    intersection_x1 = max(left_x1, right_x1)
    intersection_y1 = max(left_y1, right_y1)
    intersection_x2 = min(left_x2, right_x2)
    intersection_y2 = min(left_y2, right_y2)

    intersection_width = max(intersection_x2 - intersection_x1, 0)
    intersection_height = max(intersection_y2 - intersection_y1, 0)
    intersection_area = intersection_width * intersection_height

    left_area = max(left_x2 - left_x1, 0) * max(left_y2 - left_y1, 0)
    right_area = max(right_x2 - right_x1, 0) * max(right_y2 - right_y1, 0)
    union_area = left_area + right_area - intersection_area
    if union_area <= 0:
        return 0.0

    return intersection_area / union_area
