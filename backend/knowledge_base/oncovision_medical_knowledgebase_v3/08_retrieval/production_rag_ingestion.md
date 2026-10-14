# Production RAG Ingestion Guide

## Chunking
Recommended starting point:
- 350–700 tokens per chunk
- 50–100 token overlap
- never split a source citation away from its claims
- keep headings in chunk text

## Metadata filters
Filter by:
1. organ
2. predicted class
3. question type
4. safety level
5. source tier
6. freshness

## Ranking
Recommended retrieval flow:
1. classify query intent
2. detect organ/class
3. metadata filter
4. vector search
5. optional keyword reranking
6. source diversity check
7. answer generation
8. citation validation

## Source diversity
For high-stakes answers, prefer more than one independent source when practical. Do not manufacture consensus.

## Medical freshness
Use NCI/CAP as preferred sources for changing clinical/reporting information. Re-review biomarker and treatment documents whenever guidance changes.
