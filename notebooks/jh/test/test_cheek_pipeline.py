"""3단계~6단계 테스트: Dataset / DataLoader / ResNet-50 forward / 미니 학습.

cheek_test_validation_guide.md §6~§9 기준.

선행 조건:
    test_cheek_crop.py 실행 후 다음 파일이 있어야 합니다.
    - data/processed/cheek_train_metadata_test.csv
    - data/processed/cheek_val_metadata_test.csv

실행 방법:
    python notebooks/jh/test/test_cheek_pipeline.py [--target pore|pigmentation]
"""

import argparse
import logging
import sys
from pathlib import Path

# 이 파일 위치: notebooks/jh/test/  →  parents[3] = 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # notebooks/jh/

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "test"

# 테스트 설정 (가이드 §9.1)
CFG = {
    "image_size": 224,
    "batch_size": 8,
    "num_workers": 0,       # Windows 환경 오류 방지
    "epochs": 1,
    "learning_rate": 1e-4,
    "num_classes": 6,
}


# ── 3단계: Dataset 테스트 ──────────────────────────────────────────────────────

def test_dataset(target: str) -> tuple:
    """Dataset 단일 샘플 로딩을 검증한다."""
    from dataset import CheekDataset, get_transforms

    logger.info("=" * 60)
    logger.info("[3단계] Dataset 테스트 (target=%s)", target)

    train_csv = PROCESSED_DIR / "cheek_train_metadata_test.csv"
    val_csv = PROCESSED_DIR / "cheek_val_metadata_test.csv"

    for split, csv_path in [("train", train_csv), ("val", val_csv)]:
        if not csv_path.exists():
            logger.error("CSV 없음: %s — test_cheek_crop.py 먼저 실행하세요", csv_path)
            sys.exit(1)

    train_tf = get_transforms(CFG["image_size"], "train")
    val_tf = get_transforms(CFG["image_size"], "val")

    train_ds = CheekDataset(train_csv, target=target, transform=train_tf)
    val_ds = CheekDataset(val_csv, target=target, transform=val_tf)

    logger.info("  train 샘플 수: %d", len(train_ds))
    logger.info("  val   샘플 수: %d", len(val_ds))

    img, label = train_ds[0]
    assert img.shape == (3, CFG["image_size"], CFG["image_size"]), (
        f"image tensor shape 오류: {img.shape}"
    )
    assert label.dtype == __import__("torch").long, f"label dtype 오류: {label.dtype}"
    assert 0 <= label.item() <= 5, f"label 범위 오류: {label.item()}"

    logger.info("  image shape: %s  ✓", list(img.shape))
    logger.info("  label dtype: %s, value: %d  ✓", label.dtype, label.item())
    logger.info("[3단계] PASS")

    return train_ds, val_ds


# ── 4단계: DataLoader 테스트 ──────────────────────────────────────────────────

def test_dataloader(train_ds, val_ds) -> tuple:
    """DataLoader batch shape을 검증한다."""
    import torch
    from torch.utils.data import DataLoader

    logger.info("=" * 60)
    logger.info("[4단계] DataLoader 테스트 (batch_size=%d)", CFG["batch_size"])

    train_loader = DataLoader(
        train_ds,
        batch_size=CFG["batch_size"],
        shuffle=True,
        num_workers=CFG["num_workers"],
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=CFG["batch_size"],
        shuffle=False,
        num_workers=CFG["num_workers"],
    )

    images, labels = next(iter(train_loader))
    expected_img = (CFG["batch_size"], 3, CFG["image_size"], CFG["image_size"])

    assert images.shape == torch.Size(expected_img), (
        f"images shape 오류: {images.shape} (기대: {expected_img})"
    )
    assert labels.shape == torch.Size([CFG["batch_size"]]), (
        f"labels shape 오류: {labels.shape}"
    )

    logger.info("  images.shape: %s  ✓", list(images.shape))
    logger.info("  labels.shape: %s  ✓", list(labels.shape))
    logger.info("[4단계] PASS")

    return train_loader, val_loader


# ── 5단계: ResNet-50 Forward 테스트 ──────────────────────────────────────────

def test_forward(train_loader, device) -> None:
    """ResNet-50 forward pass와 loss backward를 검증한다."""
    import torch
    import torch.nn as nn
    from model import get_model

    logger.info("=" * 60)
    logger.info("[5단계] ResNet-50 Forward 테스트")

    model = get_model(num_classes=CFG["num_classes"], pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()

    images, labels = next(iter(train_loader))
    images = images.to(device)
    labels = labels.to(device)

    model.eval()
    with torch.no_grad():
        outputs = model(images)

    expected_out = (CFG["batch_size"], CFG["num_classes"])
    assert outputs.shape == torch.Size(expected_out), (
        f"output shape 오류: {outputs.shape} (기대: {expected_out})"
    )
    logger.info("  output shape: %s  ✓", list(outputs.shape))

    model.train()
    outputs = model(images)
    loss = criterion(outputs, labels)
    loss.backward()

    logger.info("  loss: %.4f  ✓", loss.item())
    logger.info("  loss.backward() 정상 완료  ✓")
    logger.info("[5단계] PASS")


# ── 6단계: 미니 학습 테스트 ──────────────────────────────────────────────────

def test_mini_train(train_loader, val_loader, device) -> None:
    """1 epoch 미니 학습 + validation 지표를 검증한다."""
    import torch
    import torch.nn as nn
    from sklearn.metrics import f1_score
    from model import get_model

    logger.info("=" * 60)
    logger.info("[6단계] 미니 학습 테스트 (1 epoch, lr=%.0e)", CFG["learning_rate"])

    model = get_model(num_classes=CFG["num_classes"], pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=CFG["learning_rate"])

    # ── train ──────────────────────────────────────────────────────────────────
    model.train()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    for batch_idx, (images, labels) in enumerate(train_loader):
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        preds = outputs.argmax(dim=1)
        total_correct += (preds == labels).sum().item()
        total_samples += images.size(0)

        if batch_idx % 5 == 0:
            logger.info(
                "  [train] batch %d/%d  loss=%.4f",
                batch_idx + 1,
                len(train_loader),
                loss.item(),
            )

    train_loss = total_loss / total_samples
    train_acc = total_correct / total_samples
    logger.info("  [train] epoch loss=%.4f  acc=%.4f", train_loss, train_acc)

    # ── validation ─────────────────────────────────────────────────────────────
    model.eval()
    val_loss = 0.0
    val_correct = 0
    val_samples = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            val_loss += loss.item() * images.size(0)
            preds = outputs.argmax(dim=1)
            val_correct += (preds == labels).sum().item()
            val_samples += images.size(0)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    val_loss /= val_samples
    val_acc = val_correct / val_samples
    macro_f1 = f1_score(all_labels, all_preds, average="macro", zero_division=0)

    logger.info("  [val]   epoch loss=%.4f  acc=%.4f  macro_F1=%.4f", val_loss, val_acc, macro_f1)

    ckpt_dir = PROJECT_ROOT / "checkpoints" / "trained"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "cheek_test_checkpoint.pth"
    torch.save({"model_state_dict": model.state_dict(), "val_acc": val_acc}, ckpt_path)
    logger.info("  체크포인트 저장: %s  ✓", ckpt_path)

    assert val_loss > 0
    assert 0.0 <= val_acc <= 1.0
    assert 0.0 <= macro_f1 <= 1.0

    logger.info("[6단계] PASS")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        choices=["pore", "pigmentation"],
        default="pore",
        help="분류 대상 (기본: pore)",
    )
    args = parser.parse_args()

    try:
        import torch
    except ImportError:
        logger.error(
            "PyTorch가 설치되어 있지 않습니다.\n"
            "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130"
        )
        sys.exit(1)

    try:
        from sklearn.metrics import f1_score  # noqa: F401
    except ImportError:
        logger.error(
            "scikit-learn이 설치되어 있지 않습니다.\n"
            "  pip install scikit-learn"
        )
        sys.exit(1)

    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    logger.info("사용 디바이스: %s", device)
    logger.info("분류 대상: %s", args.target)

    train_ds, val_ds = test_dataset(args.target)
    train_loader, val_loader = test_dataloader(train_ds, val_ds)
    test_forward(train_loader, device)
    test_mini_train(train_loader, val_loader, device)

    logger.info("=" * 60)
    logger.info("✓ 3~6단계 전체 통과 — 전체 데이터 학습을 진행할 수 있습니다")


if __name__ == "__main__":
    main()
