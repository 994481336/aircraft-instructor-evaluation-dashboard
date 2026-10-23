"""Compatibility exports; dashboard code imports instructor_statistics directly.

Keep one statistics implementation. Streamlit may retain the old ``analysis``
module during a live update, so new UI functions must not import through it.
"""

from instructor_statistics import (
    company_summary,
    person_score_frame,
    risk_summary,
    score_distribution,
    score_text,
    subject_loss,
    subject_score_frame,
    subject_summary,
    summary_metrics,
    top_deductions,
    type_briefing,
    type_briefing_segments,
    unit_summary,
    with_person_identity,
    xlsx_bytes,
)

__all__ = [
    "company_summary", "person_score_frame", "risk_summary", "score_distribution",
    "score_text", "subject_loss", "subject_score_frame", "subject_summary",
    "summary_metrics", "top_deductions", "type_briefing", "type_briefing_segments",
    "unit_summary", "with_person_identity", "xlsx_bytes",
]
