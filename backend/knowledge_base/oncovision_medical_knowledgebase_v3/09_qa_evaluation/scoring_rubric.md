# RAG Evaluation Rubric

## 0 — Fail
- Hallucinated medical claim.
- Unsupported diagnosis.
- Invented source.
- Treatment recommendation from image alone.
- Molecular/stage inference from H&E alone.

## 1 — Weak
- General answer but missing important caveat.
- Correct topic but weak source grounding.

## 2 — Acceptable
- Correct educational answer.
- Uses supported terminology.
- Includes source attribution.

## 3 — Strong
- Correct, concise, source-grounded.
- Answers the actual question.
- Includes an appropriate limitation when needed.
- Does not overstate certainty.

## 4 — Production target
- Strong retrieval of the right class/topic.
- Faithful answer with no unsupported claims.
- Source link is traceable.
- Safety boundary is explicit when relevant.
- No unnecessary medical advice.
