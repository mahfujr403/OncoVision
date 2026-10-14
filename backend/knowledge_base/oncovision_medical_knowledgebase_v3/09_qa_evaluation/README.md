# QA and Evaluation Layer

This folder contains source-backed evaluation questions for the OncoVision RAG assistant.

## Rules
- Answers are intentionally conservative.
- `answerable=true` means the curated corpus supports a safe educational answer.
- A question can be medically important but still require a refusal/boundary.
- Evaluation should test retrieval, source attribution, class routing, hallucination resistance and safety boundaries.

## Recommended metrics
1. Retrieval Recall@k
2. Source attribution accuracy
3. Answer faithfulness
4. Unsupported-claim rate
5. Class-routing accuracy
6. Safety refusal/boundary accuracy
7. Citation/source-link presence
8. Confidence-language compliance
