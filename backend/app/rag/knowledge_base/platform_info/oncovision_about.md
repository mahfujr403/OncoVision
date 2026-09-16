# OncoVision AI Platform Overview & Project Scope

## Creator and Lead Developer
OncoVision AI was designed, architected, and developed by **Md. Mahfujur Rahman**, a Machine Learning Engineer and AI Researcher specializing in biomedical computer vision and deep learning. 
- **Developer Profile:** Md. Mahfujur Rahman ([Portfolio](https://md-mahfujur-rahman.vercel.app/) | [GitHub](https://github.com/mahfujr403) | [LinkedIn](https://linkedin.com/in/mahfujr403) | [Google Scholar](https://scholar.google.com/citations?user=ssuw-WEAAAAJ&hl=en))
- **Primary Research Base:** The core classification models are based on Md. Mahfujur Rahman's peer-reviewed IEEE ICCIT 2025 research titled *"Polyarchitectural Deep Ensemble with Multimodal Feature Fusion for Histopathological Stratification of Colon and Lung Cancer"* (DOI: 10.1109/ICCIT68739.2025.11491066).

## What is OncoVision AI?
OncoVision AI is an enterprise-oriented, AI-assisted clinical decision support system (CDSS) specifically built for digital pathology and cancer histopathology diagnostics. By combining polyarchitectural convolutional neural networks (CNNs), deep feature fusion, and generative retrieval-augmented generation (RAG), OncoVision analyzes microscopic biopsy tissue images to deliver rapid, reliable second opinions to pathologists and oncologists.

## Project Scope and Objectives
1. **Reduce Diagnostic Turnaround Time:** Traditional histopathological examination of stained tissue biopsies is labor-intensive and time-consuming. OncoVision processes image patches in real-time, providing immediate classifications to accelerate clinical workflows.
2. **Mitigate Inter-Observer Variability:** Pathological interpretations can vary between practitioners, especially for borderline or poorly differentiated carcinomas. OncoVision provides an objective consensus prediction backed by multi-model agreement scoring.
3. **Prioritize Critical & Malignant Cases:** Automated triage flags malignant samples (adenocarcinomas and squamous cell carcinomas) for urgent human review, ensuring patients receive timely interventions.
4. **Interactive Pathological Intelligence (RAG):** Beyond raw numeric probabilities, OncoVision integrates an interactive clinical AI assistant powered by pgvector RAG and Google Gemini Flash, enabling clinicians to query histopathological findings, tumor biology, and literature evidence directly within the dashboard.
5. **Clinical Auditability and Reporting:** The platform maintains complete audit trails of all prediction runs, supports customized PDF diagnostic report generation, and facilitates multi-center data exports.

## Deep Learning Architecture: The Polyarchitectural Ensemble
To achieve industry-leading reliability and generalizability, OncoVision does not depend on a single model. Instead, it utilizes an adaptive ensemble combining three distinct deep learning architectures optimized via TensorFlow Lite:

1. **MobileNetV2 (Accuracy: 99.92%):** A lightweight, inverted residual CNN architecture optimized for fast inference and low memory footprint, providing rapid baseline feature extraction.
2. **DenseNet121 (Accuracy: 99.44%):** Utilizes dense iterative layer connections that preserve feature maps across deep layers, excelling at capturing subtle morphological transitions in cellular chromatin and glandular structures.
3. **EfficientNetV2B0 + ResNet50 Feature Fusion (Accuracy: 99.97%):** The premier flagship model that fuses compound-scaled feature extractors with deep residual representations. This feature fusion architecture achieves near-flawless discrimination between malignant and benign tissues.
4. **Weighted Consensus Engine (Overall Ensemble Accuracy: up to 99.99%):** The ensemble aggregates independent predictions through confidence weighting, yielding a unified consensus score.

## Target Classification Classes
OncoVision currently specializes in high-incidence pulmonary and colorectal histopathology, categorizing Hematoxylin & Eosin (H&E) stained tissue images into 5 clinical classes:
- **Lung Adenocarcinoma:** Malignant glandular epithelial neoplasm of the lung.
- **Lung Squamous Cell Carcinoma:** Malignant epithelial tumor of bronchial origin showing keratinization or intercellular bridges.
- **Lung Benign Tissue:** Healthy non-neoplastic pulmonary parenchyma and alveoli.
- **Colon Adenocarcinoma:** Malignant mucosal glandular tumor of the large intestine.
- **Colon Benign Tissue:** Normal colonic mucosa with preserved crypt architecture and goblet cells.

## Confidence and Agreement Metrics
Every diagnostic inference produces two transparent clinical metrics:
- **Confidence Score (%):** The probabilistic certainty assigned by the weighted ensemble algorithm.
- **Model Agreement Score (%):** The proportion of independent models in the ensemble that reached the exact same classification (e.g., 3/3 = 100% full consensus).

## Technical Architecture & Ecosystem
- **Backend:** FastAPI (Python 3.10), SQLAlchemy 2.0 asyncpg, PostgreSQL with pgvector extension, TensorFlow Lite runtime.
- **RAG Knowledge Base:** Normalized 768-dimensional vector embeddings powered by Google Gemini Embedding 2 and Gemini 3.5 Flash Lite for sub-2-second clinical queries.
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide icons, Framer Motion animations.
- **Infrastructure:** Containerized via Docker, hosted on Render and Netlify with automated CI/CD and Alembic database migrations.

## Clinical Assistive Scope & Ethical Guardrails
**IMPORTANT:** OncoVision AI is an assistive Clinical Decision Support System (CDSS) and research platform. It is designed to augment and empower board-certified pathologists, not replace licensed medical judgment. All automated findings must be clinically correlated with patient history and full microscopic slide examination.

