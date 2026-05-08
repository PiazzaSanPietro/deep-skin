"""
Cleanup script for expired and long-revoked refresh tokens.

Deletion criteria:
  1. expires_at < now()                             — 만료된 토큰
  2. revoked_at IS NOT NULL AND revoked_at < now() - 30 days  — 폐기 후 30일 이상 지난 토큰

Usage:
    cd backend
    python scripts/cleanup_refresh_tokens.py [--dry-run]

Options:
    --dry-run   실제 삭제 없이 삭제 대상 건수만 출력한다.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# backend/ 를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import and_, or_

from app.db.database import SessionLocal
from app.models.refresh_token import RefreshToken


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def cleanup(dry_run: bool = False) -> None:
    now = _utcnow()
    revoked_cutoff = now - timedelta(days=30)

    condition = or_(
        RefreshToken.expires_at < now,
        and_(
            RefreshToken.revoked_at.is_not(None),
            RefreshToken.revoked_at < revoked_cutoff,
        ),
    )

    db = SessionLocal()
    try:
        targets = db.query(RefreshToken).filter(condition)
        count = targets.count()

        if dry_run:
            print(f"[dry-run] 삭제 대상: {count}건")
            return

        targets.delete(synchronize_session=False)
        db.commit()
        print(f"[cleanup] 삭제 완료: {count}건 (기준 시각: {now.isoformat()})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="refresh_tokens 정리 스크립트")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 삭제 없이 삭제 대상 건수만 출력한다.",
    )
    args = parser.parse_args()
    cleanup(dry_run=args.dry_run)
