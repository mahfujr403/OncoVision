# OncoVision Medical Knowledge Base v2

## Purpose
Source-backed retrieval knowledge for the OncoVision 5-class histopathology classifier:

1. Colon Adenocarcinoma
2. Benign Colonic Tissue
3. Lung Adenocarcinoma
4. Benign Lung Tissue
5. Lung Squamous Cell Carcinoma

This corpus is designed for an explanatory RAG assistant, not for autonomous diagnosis or treatment.

## Design principles
- Each domain is separated so retrieval can be routed by anatomy + class + question type.
- Disease/class documents distinguish morphology, differential diagnosis, IHC, molecular context, pathology reporting, clinical context, and limitations.
- Source links are included in every major document so a user can open the underlying source.
- Current clinical guidance is separated from relatively stable histology concepts.
- The five-class label semantics are anchored to the LC25000 dataset because the labels match exactly.

## Important boundary
The classifier predicts one of the five supported image classes. RAG explains the completed prediction and provides educational context. RAG must not:
- diagnose a patient from symptoms alone,
- infer TNM stage from an image patch,
- infer molecular status from H&E appearance,
- prescribe or select treatment,
- claim a pathology diagnosis from an isolated AI prediction,
- treat a "benign" class as proof that a patient has no disease.

## Suggested ingestion
Use Markdown files as source documents. Preserve the `Source` and `Scope` sections in chunk metadata if possible.
