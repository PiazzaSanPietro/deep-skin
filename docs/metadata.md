# Metadata: Korean Skin Condition Measurement Data Set

## 1. General Information

### 1.1. Meta Information
* **Domain:** Healthcare, Computer Vision, Beauty, Face
* **Data Type:** Image
* **Data Volume:** 125,424 items
* **Raw Data Format:** JPG, TXT
* **Labeling Format:** JSON
* **Labeling Type:** Bounding Box (Image), Measurement Data (Text)
* **Data Source:** Self-collected
* **Year Built:** 2023
* **Building Institution (General):** Kailos Lab Co., Ltd.
* **Processing Institution:** IEC Korea Co., Ltd.
* **Inspection Institution:** Dankook University Industry-Academic Cooperation Foundation

### 1.2. Contact Information
* **Institution:** Kailos Lab Co., Ltd.
* **Contact Person:** Jun-chae Na
* **Phone:** 070-4699-7340
* **Email:** david@kailoslab.com

---

## 2. Dataset Overview

### 2.1. Introduction
This dataset is designed to predict skin conditions by recognizing facial images of Koreans. It consists of 13,936 facial images, 84,688 skin condition measurement records, and 125,424 labeled data items.
* **Keywords:** Healthcare health service, Computer Vision, Skin condition, Beauty, Face

### 2.2. Building Purpose
The dataset utilizes multi-angle facial images and precise skin condition measurement data to be applied in various fields, including facial area detection, personalized skin condition prediction, skin condition analysis and evaluation, and skin health research.

### 2.3. Data Description
* **Raw Data:**
  * Over 13,000 high-quality facial images taken from various angles.
  * Over 75,000 skin condition measurement results collected using 4 types of precise skin measurement equipment.
  * Collected items include moisture, elasticity, wrinkles, pigmentation, and pores (entire face / specific areas).
* **Labeling Data:**
  * Bounding box labeling for facial area processing within the images.
  * Over 80,000 processed facial area data items collected.
  * Labeled based on diagnoses by 6 or more experts (including 5 dermatologists) regarding the location and type of acne lesions (comedones, papules, pustules, nodules), wrinkles, pigmentation, pores, dryness, and jawline sagging.
* **Metadata:**
  * Skin measurement equipment information (model, measurement items, etc.).
  * Personal characteristic data such as gender and age group.

---

## 3. Dataset Statistics

**Total Construction Volume:** 13,936 high-resolution multi-angle facial images, 84,688 skin condition measurement data items, and 6,432 metadata items.

### 3.1. Gender Distribution
| Category | Count | Ratio (%) |
| :--- | :--- | :--- |
| Male | 62,478 | 49.81 |
| Female | 62,946 | 50.19 |
| **Total** | **125,424** | **100.00** |

### 3.2. Age Distribution
| Category | Count | Ratio (%) |
| :--- | :--- | :--- |
| 10s | 12,402 | 9.89 |
| 20s | 22,815 | 18.19 |
| 30s | 22,815 | 18.19 |
| 40s | 22,932 | 18.28 |
| 50s | 22,698 | 18.10 |
| 60s and above | 21,762 | 17.35 |
| **Total** | **125,424** | **100.00** |

### 3.3. Shooting Angle Distribution
| Category | Count | Ratio (%) |
| :--- | :--- | :--- |
| Digital Camera Front | 9,648 | 7.69 |
| Digital Camera Left 15° | 9,648 | 7.69 |
| Digital Camera Left 30° | 9,648 | 7.69 |
| Digital Camera Right 15° | 9,648 | 7.69 |
| Digital Camera Right 30° | 9,648 | 7.69 |
| Digital Camera Up | 9,648 | 7.69 |
| Digital Camera Down | 9,648 | 7.69 |
| Smartpad Front | 9,648 | 7.69 |
| Smartpad Left | 9,648 | 7.69 |
| Smartpad Right | 9,648 | 7.69 |
| Smartphone Front | 9,648 | 7.69 |
| Smartphone Left | 9,648 | 7.69 |
| Smartphone Right | 9,648 | 7.69 |
| **Total** | **13,936*** | **100.00** |
*(Note: Total count in the source document is listed as 13,936 for images).*

### 3.4. Facial Area Location Distribution
| Category | Count | Ratio (%) |
| :--- | :--- | :--- |
| Entire Face | 13,936 | 11.11 |
| Forehead | 13,936 | 11.11 |
| Glabella | 13,936 | 11.11 |
| Eye Area (Left) | 13,936 | 11.11 |
| Eye Area (Right) | 13,936 | 11.11 |
| Cheek (Left) | 13,936 | 11.11 |
| Cheek (Right) | 13,936 | 11.11 |
| Lips | 13,936 | 11.11 |
| Chin | 13,936 | 11.11 |
| **Total** | **125,424** | **100.00** |

---

## 4. Dataset Structure & Format

### 4.1. Data Dictionary
| No | Item Name | Type | Requirement | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `filename` | string | Mandatory | Raw data filename | `"0001_01_F.jpg"` |
| 2 | `id` | number | Mandatory | ID | `0001` |
| 3 | `date` | string | Optional | Shooting date | `"2023.05.13"` |
| 4 | `format` | string | Mandatory | File format | `"jpg"` |
| 5 | `imgsize` | string | Mandatory | File size (MB) | `"5.6"` |
| 6 | `width` | number | Mandatory | Image width | `1920` |
| 7 | `height` | number | Mandatory | Image height | `1080` |
| 8 | `device` | string | Mandatory | Shooting device info | `"01"` |
| 9 | `angle` | string | Mandatory | Shooting angle | `"F"` |
| 10 | `gender` | string | Mandatory | Gender | `"M"` |
| 11 | `birth` | number | Mandatory | Date of birth | `960129` |
| 12 | `facepart` | number | Mandatory | Facial part code (See table below) | `1` |
| 13 | `face_box` | number | Mandatory | Facial bounding box coordinates | `{"h":698.14, "w":690.14, "x":189.11, "y":520.97}` |
| 14 | `moisture` | number | Optional | Measured moisture value | |
| 15 | `elasticity` | number | Optional | Measured elasticity value | |
| 16 | `pigmentation` | number | Optional | Measured pigmentation | |
| 17 | `pore` | number | Optional | Measured pore value | |
| 18 | `expert` | number | Optional | Expert diagnosis (e.g., Forehead: wrinkle grade, Lips: dryness, Cheek: pigmentation) | |

**Facial Part (`facepart`) Codes:**
1: Forehead | 2: Glabella | 3: Eye Area (R) | 4: Eye Area (L) | 5: Cheek (R) | 6: Cheek (L) | 7: Lips | 8: Chin

### 4.2. Data Format by Processing Stage
| Category | Acquisition/Collection Stage | Refining Stage | Processing Stage |
| :--- | :--- | :--- | :--- |
| **Data Classification** | Raw Data, Source Data | Source Data | Labeling Data |
| **Data Type** | Shooting - Image (Digital File)<br>Measurement - Data (Digital File) | Image (Digital File)<br>Text (Digital File) | JSON File |
| **Data Format** | Image Spec: JPG (2136*3216 or higher)<br>Text | Image Spec: JPG (2136*3216 or higher)<br>Text | File Spec: JSON |

### 4.3. JSON File Example
```json
{
  "info": {
    "filename": "0001_01_R15.jpg",
    "id": "0001",
    "gender": "F",
    "age": 13,
    "date": "2023-08-17",
    "skin_type": 0,
    "sensitive": 0
  },
  "images": {
    "device": 0,
    "width": 2136,
    "height": 3216,
    "angle": 5,
    "facepart": 1,
    "bbox": [712, 676, 1835, 1139]
  },
  "annotations": {
    "forehead_pigmentation": 1,
    "forehead_wrinkle": 3
  },
  "equipment": {
    "forehead_moisture": 53.0,
    "forehead_elasticity_R0": 0.167,
    "forehead_elasticity_R1": 0.058,
    "forehead_elasticity_R2": 0.653,
    "forehead_elasticity_R3": 0.208,
    "forehead_elasticity_R4": 0.085,
    "forehead_elasticity_R5": 0.765,
    "forehead_elasticity_R6": 0.965,
    "forehead_elasticity_R7": 0.389,
    "forehead_elasticity_R8": 0.109,
    "forehead_elasticity_R9": 0.041,
    "forehead_elasticity_Q0": 33.4,
    "forehead_elasticity_Q1": 0.589,
    "forehead_elasticity_Q2": 0.478,
    "forehead_elasticity_Q3": 0.111
  }
}
```