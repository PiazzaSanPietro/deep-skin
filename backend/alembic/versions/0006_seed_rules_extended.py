"""seed ingredient_rules and recommendation_rules extended

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-09
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── ingredient_rules 추가 ─────────────────────────────────
# (ingredient_name, display_name, caution_for_sensitive, description)
_NEW_INGREDIENTS = [
    # 보습/장벽
    ("squalane",          "스쿠알란",        False, "피부 장벽 보호와 보습에 도움을 줄 수 있는 성분입니다."),
    ("cholesterol",       "콜레스테롤",       False, "피부 장벽 강화에 도움을 줄 수 있는 지질 성분입니다."),
    ("fatty_acid",        "지방산",          False, "피부 장벽을 구성하는 성분으로 보습과 장벽 강화에 도움을 줄 수 있습니다."),
    ("beta_glucan",       "베타글루칸",       False, "피부 진정과 수분 공급에 도움을 줄 수 있는 성분입니다."),
    ("urea",              "우레아",          True,  "각질 제거와 보습에 도움을 줄 수 있으나 민감 피부는 고농도 사용에 주의해야 합니다."),
    # 진정/민감
    ("centella_asiatica", "병풀추출물",       False, "피부 진정과 재생 관리에 도움을 줄 수 있는 성분입니다."),
    ("green_tea",         "녹차추출물",       False, "항산화와 피부 진정에 도움을 줄 수 있는 성분입니다."),
    ("houttuynia",        "어성초추출물",     False, "피부 진정과 항균 관리에 도움을 줄 수 있는 성분입니다."),
    ("calamine",          "칼라민",          False, "피부 진정과 트러블 완화에 도움을 줄 수 있는 성분입니다."),
    ("bisabolol",         "비사보롤",         False, "피부 진정과 보습에 도움을 줄 수 있는 성분입니다."),
    # 색소침착/톤
    ("tranexamic_acid",   "트라넥사민산",     False, "색소침착 관리에 도움을 줄 수 있는 성분입니다."),
    ("arbutin",           "알부틴",           False, "피부 톤 관리와 색소침착 완화에 도움을 줄 수 있는 성분입니다."),
    ("licorice_root",     "감초추출물",       False, "피부 톤 케어와 진정에 도움을 줄 수 있는 성분입니다."),
    # 모공/피지/여드름
    ("tea_tree",          "티트리",          True,  "항균과 여드름 관리에 도움을 줄 수 있으나 민감 피부는 자극에 주의해야 합니다."),
    ("aha",               "AHA",             True,  "각질 제거와 피부 결 개선에 도움을 줄 수 있으나 자극이 있을 수 있어 사용 빈도 조절이 필요합니다."),
    ("pha",               "PHA",             False, "저자극 각질 케어에 도움을 줄 수 있는 성분으로 AHA에 비해 자극이 적습니다."),
    ("azelaic_acid",      "아젤라익애씨드",  True,  "여드름 및 색소침착 관리에 도움을 줄 수 있으나 민감 피부는 자극에 주의해야 합니다."),
    ("sulfur",            "설퍼",            True,  "피지 조절과 여드름 관리에 도움을 줄 수 있으나 민감 피부는 자극에 주의해야 합니다."),
    # 주름/탄력
    ("bakuchiol",         "바쿠치올",        False, "레티놀과 유사한 주름 관리 효과를 가지며 자극이 적어 민감 피부에도 사용할 수 있습니다."),
    ("vitamin_e",         "비타민E",         False, "항산화와 피부 보호에 도움을 줄 수 있는 성분입니다."),
    ("coenzyme_q10",      "코엔자임Q10",     False, "항산화와 탄력 관리에 도움을 줄 수 있는 성분입니다."),
    # 자외선 차단
    ("zinc_oxide",        "징크옥사이드",     False, "물리적 자외선 차단 성분으로 민감 피부에도 사용 가능합니다."),
    ("titanium_dioxide",  "티타늄디옥사이드", False, "물리적 자외선 차단 성분으로 민감 피부에도 사용 가능합니다."),
]

# ── recommendation_rules 추가 ─────────────────────────────
# 기존 성분 shorthand
_HA  = {"key": "hyaluronic_acid",   "name": "히알루론산"}
_CE  = {"key": "ceramide",          "name": "세라마이드"}
_GL  = {"key": "glycerin",          "name": "글리세린"}
_PA  = {"key": "panthenol",         "name": "판테놀"}
_NI  = {"key": "niacinamide",       "name": "나이아신아마이드"}
_VC  = {"key": "vitamin_c",         "name": "비타민C"}
_BH  = {"key": "bha",               "name": "BHA"}
_ZP  = {"key": "zinc_pca",          "name": "징크 PCA"}
_RE  = {"key": "retinol",           "name": "레티놀"}
_PE  = {"key": "peptide",           "name": "펩타이드"}
_AD  = {"key": "adenosine",         "name": "아데노신"}
_MA  = {"key": "madecassoside",     "name": "마데카소사이드"}
_AL  = {"key": "allantoin",         "name": "알란토인"}

# 신규 성분 shorthand
_CA  = {"key": "centella_asiatica", "name": "병풀추출물"}
_GT  = {"key": "green_tea",         "name": "녹차추출물"}
_BG  = {"key": "beta_glucan",       "name": "베타글루칸"}
_TA  = {"key": "tranexamic_acid",   "name": "트라넥사민산"}
_AB  = {"key": "arbutin",           "name": "알부틴"}
_LR  = {"key": "licorice_root",     "name": "감초추출물"}
_AH  = {"key": "aha",               "name": "AHA"}
_AA  = {"key": "azelaic_acid",      "name": "아젤라익애씨드"}
_BA  = {"key": "bakuchiol",         "name": "바쿠치올"}
_PHA = {"key": "pha",               "name": "PHA"}
_BI  = {"key": "bisabolol",         "name": "비사보롤"}
_CA2 = {"key": "calamine",          "name": "칼라민"}

# (display_part_name, issue_type, issue_display_name, severity,
#  reason_template, recommend_categories, recommend_ingredients, care_tips)
_NEW_RULES = [
    # ── 전체 얼굴 - 여드름 (normal / mild / severe 추가, moderate는 기존에 있음) ──
    ("전체 얼굴", "acne", "여드름", "normal",
     "피부에 여드름성 병변이 없는 양호한 상태입니다. 현재 상태를 유지하기 위한 기본 관리가 적합합니다.",
     ["저자극 클렌저", "수분 토너", "가벼운 보습 크림"],
     [_HA, _GL, _PA],
     ["피지와 노폐물이 쌓이지 않도록 꼼꼼한 세안을 유지하는 것이 좋습니다.",
      "새로운 기능성 제품을 사용할 경우 한 가지씩 도입하는 것이 좋습니다."]),

    ("전체 얼굴", "acne", "여드름", "mild",
     "가벼운 여드름성 경향이 있어 예방적인 피지 조절 및 진정 관리가 필요합니다.",
     ["트러블 케어 토너", "진정 세럼", "저자극 보습 크림"],
     [_NI, _MA, _CA, _PA],
     ["자극적인 피부 관리는 피하고 진정 중심으로 관리하는 것이 좋습니다.",
      "손으로 얼굴을 만지는 습관을 줄이는 것이 좋습니다.",
      "피지 조절 제품과 진정 제품을 함께 사용하는 것이 좋습니다."]),

    ("전체 얼굴", "acne", "여드름", "severe",
     "여드름성 병변이 넓거나 깊은 경향이 있어 집중적인 피지 조절 및 진정 관리가 필요합니다.",
     ["트러블 케어 세럼", "진정 앰플", "피지 조절 토너", "저자극 클렌저"],
     [_BH, _NI, _AA, _MA, _PA],
     ["여드름 부위를 강하게 누르거나 뜯지 않는 것이 좋습니다.",
      "BHA, AHA, 아젤라익애씨드 성분은 낮은 빈도부터 사용하는 것이 좋습니다.",
      "민감 피부라면 저자극 진정 제품을 우선 사용하는 것이 좋습니다.",
      "이중 세안 시 자극이 적은 클렌저를 선택하는 것이 좋습니다."]),

    # ── 전체 얼굴 - 민감 피부 (mild / severe 추가, moderate는 기존에 있음) ──
    ("전체 얼굴", "sensitive", "민감 피부", "mild",
     "피부 민감도가 약간 높은 상태로 자극을 최소화하는 관리가 필요합니다.",
     ["저자극 진정 토너", "장벽 케어 크림", "저자극 보습 세럼"],
     [_PA, _MA, _AL, _BG],
     ["향료와 알코올이 없는 제품을 선택하는 것이 좋습니다.",
      "보습과 진정 중심으로 관리하는 것이 좋습니다.",
      "새로운 제품 사용 전 소량 패치 테스트를 권장합니다."]),

    ("전체 얼굴", "sensitive", "민감 피부", "severe",
     "피부 민감도가 높게 분석되어 장벽 케어와 집중 진정 관리가 필요합니다.",
     ["집중 진정 크림", "장벽 케어 크림", "저자극 보습 앰플"],
     [_CE, _MA, _PA, _AL, _BI],
     ["새로운 제품은 반드시 소량 패치 테스트 후 사용하는 것이 좋습니다.",
      "BHA, 레티놀, 비타민C 등 기능성 성분은 당분간 피하는 것이 좋습니다.",
      "향료, 알코올, 고농도 방부제가 없는 최소 성분 제품을 선택하는 것이 좋습니다.",
      "피부 장벽 관리에 집중하고 보습을 꾸준히 유지하는 것이 좋습니다."]),

    # ── 미간 - 주름 (normal / mild / moderate / severe 신규) ──
    ("미간", "wrinkle", "주름", "normal",
     "미간 주름 상태가 양호하게 분석되었습니다. 현재 상태를 유지하기 위한 보습 관리가 적합합니다.",
     ["수분 크림", "보습 세럼", "자외선 차단제"],
     [_HA, _CE, _GL],
     ["미간 부위는 표정 근육 움직임이 많아 보습 관리를 꾸준히 유지하는 것이 좋습니다.",
      "자외선 차단제를 꾸준히 사용해 피부 노화를 예방하는 것이 좋습니다."]),

    ("미간", "wrinkle", "주름", "mild",
     "미간에 약한 주름 경향이 보여 예방적인 탄력 관리가 필요합니다.",
     ["탄력 세럼", "보습 크림", "주름 예방 세럼"],
     [_PE, _HA, _AD],
     ["보습과 탄력 관리를 함께 하면 주름 예방에 도움이 됩니다.",
      "미간을 자주 찌푸리는 표정 습관을 줄이는 것이 좋습니다."]),

    ("미간", "wrinkle", "주름", "moderate",
     "미간 주름이 보통 이상으로 분석되어 탄력 및 주름 관리가 필요합니다.",
     ["탄력 크림", "주름 개선 세럼", "보습 크림"],
     [_PE, _AD, _HA],
     ["주름 개선 성분과 보습제를 함께 사용하는 것이 좋습니다.",
      "자외선 차단제를 꾸준히 사용하는 것이 좋습니다.",
      "건조함이 심하면 주름이 더 도드라져 보일 수 있으므로 보습제를 꾸준히 사용하는 것이 좋습니다."]),

    ("미간", "wrinkle", "주름", "severe",
     "미간 주름 깊이가 높게 분석되어 집중적인 주름 개선 관리가 필요합니다.",
     ["고기능 탄력 크림", "주름 개선 세럼", "레티놀 또는 바쿠치올 크림"],
     [_BA, _PE, _AD],
     ["레티놀에 자극이 있다면 바쿠치올 성분의 제품을 대안으로 사용하는 것이 좋습니다.",
      "주름 개선 성분은 낮은 빈도부터 사용하는 것이 좋습니다.",
      "낮에는 자외선 차단제를 꾸준히 사용하는 것이 좋습니다."]),

    # ── 이마 - 색소침착 (normal / mild / moderate / severe 신규) ──
    ("이마", "pigmentation", "색소침착", "normal",
     "이마 색소침착 상태가 양호하게 분석되었습니다. 자외선 차단으로 현재 상태를 유지하는 것이 좋습니다.",
     ["수분 크림", "자외선 차단제", "저자극 진정 크림"],
     [_PA, _CE, _HA],
     ["색소침착 예방을 위해 자외선 차단제를 꾸준히 사용하는 것이 좋습니다.",
      "이마에 앞머리가 자주 닿는 경우 모발 제품으로 인한 자극을 줄이는 것이 좋습니다."]),

    ("이마", "pigmentation", "색소침착", "mild",
     "이마에 약한 색소침착 경향이 보여 예방적인 톤 관리가 필요합니다.",
     ["톤 케어 세럼", "자외선 차단제", "진정 크림"],
     [_NI, _LR, _PA],
     ["자외선 차단과 톤 케어를 함께 하는 것이 좋습니다.",
      "고농도 미백 제품보다는 저자극 톤 케어 제품부터 시작하는 것이 좋습니다."]),

    ("이마", "pigmentation", "색소침착", "moderate",
     "이마에 색소침착이 관찰되어 피부 톤 관리가 필요합니다.",
     ["잡티 케어 세럼", "미백 기능성 앰플", "자외선 차단제"],
     [_NI, _VC, _AB],
     ["색소침착 관리는 미백 성분과 자외선 차단을 함께 관리하는 것이 중요합니다.",
      "비타민C 제품은 아침에 사용할 경우 자외선 차단제를 함께 사용하는 것이 좋습니다.",
      "민감 피부는 비타민C를 낮은 농도부터 사용하는 것이 좋습니다."]),

    ("이마", "pigmentation", "색소침착", "severe",
     "이마의 색소침착 정도가 높게 분석되어 집중적인 잡티 및 톤 관리가 필요합니다.",
     ["고기능 잡티 케어 세럼", "미백 기능성 앰플", "톤 개선 크림", "자외선 차단제"],
     [_NI, _TA, _AB, _LR],
     ["색소침착이 심한 경우 자외선 차단제를 꾸준히 사용하는 것이 가장 중요합니다.",
      "트라넥사민산, 알부틴, 감초추출물 등 자극이 적은 미백 성분을 활용하는 것이 좋습니다.",
      "고농도 미백 제품은 피부 자극 여부를 확인하며 사용하는 것이 좋습니다."]),
]


def upgrade() -> None:
    bind = op.get_bind()

    # ingredient_rules — INSERT IGNORE로 중복 방지
    bind.execute(
        sa.text(
            "INSERT IGNORE INTO ingredient_rules "
            "(ingredient_name, display_name, caution_for_sensitive, description) "
            "VALUES (:ingredient_name, :display_name, :caution_for_sensitive, :description)"
        ),
        [
            {
                "ingredient_name": name,
                "display_name": display,
                "caution_for_sensitive": caution,
                "description": desc,
            }
            for name, display, caution, desc in _NEW_INGREDIENTS
        ],
    )

    # recommendation_rules — INSERT IGNORE로 중복 방지
    # unique 제약: (display_part_name, issue_type, severity)
    bind.execute(
        sa.text(
            "INSERT IGNORE INTO recommendation_rules "
            "(display_part_name, issue_type, issue_display_name, severity, "
            "reason_template, recommend_categories, recommend_ingredients, care_tips) "
            "VALUES (:display_part_name, :issue_type, :issue_display_name, :severity, "
            ":reason_template, :recommend_categories, :recommend_ingredients, :care_tips)"
        ),
        [
            {
                "display_part_name": part,
                "issue_type": issue,
                "issue_display_name": issue_display,
                "severity": sev,
                "reason_template": reason,
                "recommend_categories": json.dumps(cats, ensure_ascii=False),
                "recommend_ingredients": json.dumps(ings, ensure_ascii=False),
                "care_tips": json.dumps(tips, ensure_ascii=False),
            }
            for part, issue, issue_display, sev, reason, cats, ings, tips in _NEW_RULES
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()

    new_ingredient_names = [row[0] for row in _NEW_INGREDIENTS]
    placeholders = ", ".join(f":name_{i}" for i in range(len(new_ingredient_names)))
    bind.execute(
        sa.text(f"DELETE FROM ingredient_rules WHERE ingredient_name IN ({placeholders})"),
        {f"name_{i}": name for i, name in enumerate(new_ingredient_names)},
    )

    # 이번 migration에서 추가한 (display_part_name, issue_type, severity) 조합만 삭제
    for part, issue, _, sev, *_ in _NEW_RULES:
        bind.execute(
            sa.text(
                "DELETE FROM recommendation_rules "
                "WHERE display_part_name = :part AND issue_type = :issue AND severity = :sev"
            ),
            {"part": part, "issue": issue, "sev": sev},
        )
