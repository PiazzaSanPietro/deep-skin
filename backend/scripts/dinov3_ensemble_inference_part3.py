# -*- coding: utf-8 -*-
"""
DINOv3 Ensemble Inference Script for Face Part 3 (Perocular).
Loads a backbone and an ensemble of k-fold heads to predict grades on raw images.
"""

import os
import sys
import json
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

# Script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# DINOv3 repo path
_DINOV3_REPO = os.path.join(SCRIPT_DIR, "dinov3")
if os.path.isdir(_DINOV3_REPO):
    sys.path.insert(0, _DINOV3_REPO)

try:
    from dinov3.models.vision_transformer import DinoVisionTransformer
except ImportError:
    print(f"Error: DINOv3 repository not found at {_DINOV3_REPO}.")
    sys.exit(1)

# ===================================================================
# Config
# ===================================================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGE_SIZE = 448
BBOX_MARGIN = 0.15
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
USE_TTA = True

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKBONE_CKPT = os.path.join(SCRIPT_DIR, "dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth")
HEADS_DIR = os.path.join(BASE_DIR, "ckpt_kfold_vits_part3")
INPUT_DIR = os.path.join(SCRIPT_DIR, "facepart_03_test")

# ViT-S Params
VIT_PARAMS = {"embed_dim": 384, "depth": 12, "num_heads": 6}

# ===================================================================
# Model Definitions
# ===================================================================
class LinearHead(nn.Module):
    def __init__(self, feature_dim, num_classes, dropout=0.1):
        super().__init__()
        self.norm = nn.LayerNorm(feature_dim)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(feature_dim, num_classes)

    def forward(self, x):
        return self.classifier(self.dropout(self.norm(x)))

def build_backbone(checkpoint_path):
    print(f"Loading backbone from {checkpoint_path}...")
    backbone = DinoVisionTransformer(
        img_size=IMAGE_SIZE, patch_size=16, in_chans=3,
        pos_embed_rope_base=100.0,
        pos_embed_rope_normalize_coords="separate",
        pos_embed_rope_rescale_coords=2.0,
        pos_embed_rope_dtype="fp32",
        embed_dim=VIT_PARAMS['embed_dim'], 
        depth=VIT_PARAMS['depth'], 
        num_heads=VIT_PARAMS['num_heads'], 
        ffn_ratio=6,
        qkv_bias=True, drop_path_rate=0.0, layerscale_init=1e-5,
        norm_layer="layernormbf16", ffn_layer="swiglu",
        ffn_bias=True, proj_bias=True,
        n_storage_tokens=4, mask_k_bias=True,
    )
    if os.path.exists(checkpoint_path):
        sd = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        backbone.load_state_dict(sd, strict=False)
    else:
        raise FileNotFoundError(f"Backbone checkpoint not found: {checkpoint_path}")
    
    backbone = backbone.to(DEVICE).eval()
    for p in backbone.parameters():
        p.requires_grad = False
    return backbone

# ===================================================================
# Preprocessing
# ===================================================================
def expand_bbox(x, y, w, h, margin, img_w, img_h):
    mx = int(round(w * margin))
    my = int(round(h * margin))
    return (max(0, x - mx), max(0, y - my),
            min(img_w, x + w + mx), min(img_h, y + h + my))

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])

# ===================================================================
# Inference Pipeline
# ===================================================================
@torch.no_grad()
def run_inference():
    # 1. Load Backbone
    backbone = build_backbone(BACKBONE_CKPT)
    
    # 2. Load Ensemble Heads
    head_paths = [os.path.join(HEADS_DIR, f"head_fold{i+1}.pth") for i in range(5)]
    heads = []
    num_classes = 0
    for hp in head_paths:
        if not os.path.exists(hp):
            print(f"Warning: Head checkpoint not found: {hp}")
            continue
        sd = torch.load(hp, map_location=DEVICE, weights_only=True)
        if num_classes == 0:
            num_classes = sd["num_classes"]
            feature_dim = sd["feature_dim"]
        
        model = LinearHead(feature_dim, num_classes).to(DEVICE)
        model.load_state_dict(sd["head_state"])
        model.eval()
        heads.append(model)
    
    if not heads:
        print("Error: No heads loaded.")
        return

    print(f"Loaded {len(heads)} models for ensemble. Target classes: {num_classes}")

    # 3. Find Images
    img_exts = (".jpg", ".jpeg", ".png")
    image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(img_exts)]
    
    results = []

    # 4. Process each image
    for img_name in tqdm(image_files, desc="Inference"):
        img_path = os.path.join(INPUT_DIR, img_name)
        json_path = os.path.join(INPUT_DIR, os.path.splitext(img_name)[0] + "_03.json")
        
        if not os.path.exists(json_path):
            # Try matching part 3 specific json naming if different
            # Based on user example: 0001_01_F.jpg -> 0001_01_F_03.json
            pass
        
        if not os.path.exists(json_path):
            continue
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            bbox = data["images"]["bbox"] # [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox
            w, h = x2 - x1, y2 - y1
            
            img = Image.open(img_path).convert("RGB")
            W, H = img.size
            
            # Crop with margin
            crop_coords = expand_bbox(x1, y1, w, h, BBOX_MARGIN, W, H)
            cropped_img = img.crop(crop_coords)
            
            # Prepare inputs
            input_tensor = eval_transform(cropped_img).unsqueeze(0).to(DEVICE)
            
            # Extract Feature
            # Note: Using half precision if possible for speed
            with torch.amp.autocast(device_type='cuda', dtype=torch.bfloat16) if DEVICE.type == 'cuda' else torch.no_grad():
                feat = backbone(input_tensor)
            
            feat = feat.float()
            
            # Ensemble Predictions
            all_probs = []
            for model in heads:
                logits = model(feat)
                probs = torch.softmax(logits, dim=-1)
                
                if USE_TTA:
                    # Horizontal Flip TTA
                    flipped_img = cropped_img.transpose(Image.FLIP_LEFT_RIGHT)
                    flipped_tensor = eval_transform(flipped_img).unsqueeze(0).to(DEVICE)
                    with torch.amp.autocast(device_type='cuda', dtype=torch.bfloat16) if DEVICE.type == 'cuda' else torch.no_grad():
                        feat_flip = backbone(flipped_tensor)
                    feat_flip = feat_flip.float()
                    logits_flip = model(feat_flip)
                    probs_flip = torch.softmax(logits_flip, dim=-1)
                    probs = (probs + probs_flip) / 2
                
                all_probs.append(probs)
            
            ensemble_probs = torch.stack(all_probs).mean(dim=0) # [1, num_classes]
            probs_np = ensemble_probs[0].cpu().numpy()
            
            # Get Top 2
            top2_indices = np.argsort(probs_np)[::-1][:2]
            pred_class = top2_indices[0]
            conf = probs_np[pred_class]
            
            pred_class2 = top2_indices[1]
            conf2 = probs_np[pred_class2]
            
            results.append({
                "filename": img_name,
                "prediction": int(pred_class),
                "confidence": float(conf),
                "prediction2": int(pred_class2),
                "confidence2": float(conf2),
                "probs": probs_np.tolist()
            })
            
        except Exception as e:
            print(f"Error processing {img_name}: {e}")
            continue

    # 5. Output Results
    print("\n" + "="*80)
    print(f"{'Filename':<25} | {'1st Grade (Conf)':<18} | {'2nd Grade (Conf)':<18}")
    print("-" * 80)
    for res in results:
        p1_str = f"{res['prediction']} ({res['confidence']:.4f})"
        p2_str = f"{res['prediction2']} ({res['confidence2']:.4f})"
        print(f"{res['filename']:<25} | {p1_str:<18} | {p2_str:<18}")
    print("="*80)
    
    # Optionally save to CSV
    import pandas as pd
    df_res = pd.DataFrame(results)
    csv_out = os.path.join(BASE_DIR, "inference_results_part3.csv")
    df_res.to_csv(csv_out, index=False)
    print(f"Results saved to {csv_out}")

if __name__ == "__main__":
    run_inference()
