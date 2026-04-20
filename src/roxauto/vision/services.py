from __future__ import annotations

from typing import Iterable

from roxauto.core.models import VisionMatch
from roxauto.vision.models import AnchorSpec, MatchStatus, TemplateMatchResult


def build_match_result(
    *,
    source_image: str,
    candidates: Iterable[VisionMatch],
    expected_anchor: AnchorSpec | None = None,
    threshold: float | None = None,
    message: str = "",
) -> TemplateMatchResult:
    candidate_list = list(candidates)
    selected_threshold = threshold
    if selected_threshold is None and expected_anchor is not None:
        selected_threshold = expected_anchor.confidence_threshold
    if selected_threshold is None:
        selected_threshold = 0.85

    if expected_anchor is not None:
        matching_candidates = [
            candidate
            for candidate in candidate_list
            if candidate.anchor_id == expected_anchor.anchor_id and candidate.confidence >= selected_threshold
        ]
        best_candidate = max(matching_candidates, key=lambda candidate: candidate.confidence, default=None)
    else:
        best_candidate = max(candidate_list, key=lambda candidate: candidate.confidence, default=None)
        if best_candidate is not None and best_candidate.confidence < selected_threshold:
            best_candidate = None

    is_match = best_candidate is not None

    return TemplateMatchResult(
        source_image=source_image,
        candidates=candidate_list,
        expected_anchor_id=expected_anchor.anchor_id if expected_anchor else "",
        threshold=selected_threshold,
        status=MatchStatus.MATCHED if is_match else MatchStatus.MISSED,
        message=message or ("matched" if is_match else "no anchor met threshold"),
    )
