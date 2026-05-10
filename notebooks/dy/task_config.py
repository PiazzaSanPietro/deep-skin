"""Shared task definitions for forehead and glabella skin analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationTask:
    name: str
    column: str
    part_name: str
    display_part_name: str
    metric_name: str
    metric_display_name: str
    issue_type: str
    num_classes: int


CLASSIFICATION_TASKS: tuple[ClassificationTask, ...] = (
    ClassificationTask(
        name="forehead_pigmentation",
        column="label_forehead_pigmentation",
        part_name="forehead",
        display_part_name="이마",
        metric_name="pigmentation",
        metric_display_name="색소침착",
        issue_type="pigmentation",
        num_classes=6,
    ),
    ClassificationTask(
        name="forehead_wrinkle",
        column="label_forehead_wrinkle",
        part_name="forehead",
        display_part_name="이마",
        metric_name="wrinkle",
        metric_display_name="주름",
        issue_type="wrinkle",
        num_classes=7,
    ),
    ClassificationTask(
        name="glabella_wrinkle",
        column="label_glabella_wrinkle",
        part_name="glabella",
        display_part_name="미간",
        metric_name="wrinkle",
        metric_display_name="주름",
        issue_type="wrinkle",
        num_classes=7,
    ),
)

CLASSIFICATION_TASK_NAMES = tuple(task.name for task in CLASSIFICATION_TASKS)
CLASSIFICATION_TASK_BY_NAME = {task.name: task for task in CLASSIFICATION_TASKS}

# A compact set of forehead equipment targets. The raw JSON contains many
# elasticity parameters; these are enough to give the model numeric evidence
# without making the regression head dominate training.
REGRESSION_TARGETS: tuple[str, ...] = (
    "forehead_moisture",
    "forehead_elasticity_R2",
    "forehead_elasticity_R5",
    "forehead_elasticity_R7",
    "forehead_elasticity_Q0",
    "forehead_elasticity_Q1",
    "forehead_elasticity_Q2",
)

REGRESSION_DISPLAY_NAMES: dict[str, str] = {
    "forehead_moisture": "이마 수분",
    "forehead_elasticity_R2": "이마 탄력 R2",
    "forehead_elasticity_R5": "이마 탄력 R5",
    "forehead_elasticity_R7": "이마 탄력 R7",
    "forehead_elasticity_Q0": "이마 탄력 Q0",
    "forehead_elasticity_Q1": "이마 탄력 Q1",
    "forehead_elasticity_Q2": "이마 탄력 Q2",
}

ALL_EQUIPMENT_COLUMNS: tuple[str, ...] = (
    "forehead_moisture",
    "forehead_elasticity_R0",
    "forehead_elasticity_R1",
    "forehead_elasticity_R2",
    "forehead_elasticity_R3",
    "forehead_elasticity_R4",
    "forehead_elasticity_R5",
    "forehead_elasticity_R6",
    "forehead_elasticity_R7",
    "forehead_elasticity_R8",
    "forehead_elasticity_R9",
    "forehead_elasticity_Q0",
    "forehead_elasticity_Q1",
    "forehead_elasticity_Q2",
    "forehead_elasticity_Q3",
)


def grade_to_severity(grade: int) -> str:
    if grade <= 0:
        return "normal"
    if grade == 1:
        return "mild"
    if grade == 2:
        return "moderate"
    return "severe"
