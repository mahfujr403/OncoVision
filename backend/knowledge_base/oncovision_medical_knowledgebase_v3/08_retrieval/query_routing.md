# Query Routing

## Route 1 — Generic cancer/pathology
Keywords:
cancer, tumor, malignant, benign, carcinoma, adenocarcinoma, biopsy, pathology, H&E, histology, invasion, metastasis, grade, stage.

Use:
`00_general/*`

## Route 2 — Colon
Keywords:
colon, colorectal, crypt, goblet cell, adenoma, serrated, SSL, TSA, colon adenocarcinoma, MMR, MSI, KRAS, BRAF, CEA.

Use:
`01_colon/*`, `03_classes/*colon*`, `04_comparisons/colon*`

## Route 3 — Lung
Keywords:
lung, pulmonary, alveoli, pneumocyte, NSCLC, adenocarcinoma, squamous, keratinization, TTF-1, Napsin A, p40, EGFR, ALK, ROS1.

Use:
`02_lung/*`, `03_classes/*lung*`, `04_comparisons/lung*`

## Route 4 — Class explanation
If user provides `predicted_class`, prioritize matching `03_classes/<class>.md`, then the relevant detailed organ files.

## Route 5 — Differential question
Use pairwise comparison documents before generic disease documents.

## Route 6 — Treatment/staging
Use safety documents first, then NCI PDQ. Do not let a classifier label become an individualized recommendation.

## Retrieval metadata recommendation
Store:
- `organ`
- `class`
- `question_type`
- `source_tier`
- `source_url`
- `document_type`
- `freshness`
- `safety_level`
