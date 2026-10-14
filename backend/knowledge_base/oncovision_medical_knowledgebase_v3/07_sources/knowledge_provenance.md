# Knowledge Provenance

## Provenance rule
Every production chunk should carry:
- `source_title`
- `source_url`
- `source_tier`
- `topic`
- `organ`
- `class`
- `knowledge_type`
- `last_reviewed`
- `medical_sensitivity`
- `claim_scope`

## Example
```json
{
  "source_title": "Lung Adenocarcinoma - StatPearls",
  "source_url": "https://www.ncbi.nlm.nih.gov/books/NBK519578/",
  "source_tier": 2,
  "topic": "histomorphology",
  "organ": "lung",
  "class": "lung_adenocarcinoma",
  "knowledge_type": "disease",
  "last_reviewed": "2026-10-06",
  "medical_sensitivity": "high",
  "claim_scope": "educational"
}
```

## Conflict handling
When sources disagree:
1. Prefer current official guidance for clinical management.
2. Prefer CAP for reporting/checklist elements.
3. Use peer-reviewed reviews for morphology.
4. Record uncertainty rather than silently merging conflicting claims.
