# Retrieval Quality Upgrade: Reranking Feature

## Overview

This feature implements a two-stage retrieval pipeline with cross-encoder reranking to significantly improve the quality of retrieved documents in the RAG (Retrieval Augmented Generation) system.

## Problem Statement

**Embedding similarity ≠ relevance for the question**

Traditional single-stage retrieval using vector databases with embedding similarity often retrieves semantically similar chunks that may not be the most relevant for answering the specific query. This is a common failure mode in RAG systems.

## Solution: Two-Stage Retrieval Pipeline

### Architecture

```
User Query
    ↓
[Stage 1: zvec Vector Search]
    → Retrieve top 20 candidates using embedding similarity
    ↓
[Stage 2: Cross-Encoder Reranking]
    → Score query-document pairs with cross-encoder
    → Rank by relevance score
    ↓
Return top 5 most relevant chunks
```

### Pipeline Details

1. **Stage 1 - zvec Vector Search (Recall)**
   - Model: `sentence-transformers/all-MiniLM-L6-v2` (bi-encoder)
   - Retrieves top 20 candidates using similarity search
   - Fast approximate search (2x faster than FAISS)
   - High recall, lower precision

2. **Stage 2 - Cross-Encoder Reranking (Precision)**
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Scores each query-document pair directly
   - Much more accurate relevance scoring
   - Returns top 5 most relevant chunks

## Implementation

### New Components

#### 1. RerankerService (`src/services/reranker.py`)

```python
from sentence_transformers import CrossEncoder

class RerankerService:
    def rerank(self, query: str, documents: List[Dict], top_k: int = 5):
        # Score all query-document pairs
        pairs = [[query, doc["text"]] for doc in documents]
        scores = self.model.predict(pairs)

        # Return top_k by rerank score
        return sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)[:top_k]
```

#### 2. Updated VectorStoreService

- Added `enable_reranking` and `reranker_model` parameters
- Modified `search()` method to support two-stage retrieval
- Returns both `retrieval_score` (zvec) and `rerank_score` (cross-encoder)

#### 3. Configuration (`src/config.py`)

New environment variables:
- `ENABLE_RERANKING` (default: `true`)
- `RERANKER_MODEL` (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- `RERANKER_TOP_K` (default: `20`)
- `FINAL_TOP_K` (default: `5`)

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Reranking Configuration
ENABLE_RERANKING=true
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_TOP_K=20
FINAL_TOP_K=5
```

### Disabling Reranking

To disable reranking and use only zvec retrieval:

```bash
ENABLE_RERANKING=false
```

## Performance Considerations

### Latency Trade-offs

- **Without reranking**: ~25-50ms (zvec only - 2x faster than FAISS)
- **With reranking**: ~150-300ms (zvec + cross-encoder)

The additional latency is acceptable for the significant quality improvement.

### Model Sizes

- Embedding model (bi-encoder): ~90MB
- Reranker model (cross-encoder): ~80MB

Both models are loaded into memory at startup.

## Benefits

1. **Better Answer Quality**: Cross-encoder reranking provides much more accurate relevance scoring than embedding similarity alone.

2. **Improved Context**: The LLM receives the most relevant chunks, not just semantically similar ones.

3. **Higher Confidence**: Better context leads to more grounded answers with higher confidence scores.

4. **Flexible Configuration**: Can be toggled on/off via environment variables.

## Example Impact

### Before (Vector search only)

Query: "What are the main findings about climate change?"

Retrieved chunks might include:
- Chunks mentioning "climate" but discussing climate models
- Chunks about data collection methods
- Tangentially related background information

### After (zvec + Reranking)

Same query retrieves:
- Chunks specifically discussing research findings
- Results and conclusions sections
- Key statistical findings about climate change

## Technical Details

### Cross-Encoder vs Bi-Encoder

**Bi-Encoder (zvec embedding model)**:
- Encodes query and documents separately
- Fast similarity search (dot product/L2 distance)
- Good for recall, lower precision

**Cross-Encoder (Reranker)**:
- Encodes query and document together
- Direct relevance scoring
- Much more accurate but slower
- Perfect for reranking a small candidate set

### Score Fields

Each retrieved chunk now contains:
- `retrieval_score`: Original zvec similarity score
- `rerank_score`: Cross-encoder relevance score (higher = more relevant)
- `score`: Primary score used for ranking (= `rerank_score` when reranking is enabled)

## Monitoring

The reranking pipeline can be monitored through:

1. **Logs**: Reranking is logged during vector store initialization
2. **Response Metadata**: Check the `retrieval_score` vs `rerank_score` in search results
3. **Confidence Scores**: Higher confidence scores indicate better retrieval quality

## Future Improvements

1. **Hybrid Search**: Combine dense (embedding) and sparse (BM25) retrieval before reranking
2. **LLM-based Reranking**: Use small LLM for even more accurate scoring
3. **Adaptive Reranking**: Dynamically adjust `RERANKER_TOP_K` based on query complexity
4. **Caching**: Cache reranking results for frequently asked questions

## References

- Cross-Encoder Model: [ms-marco-MiniLM-L-6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)
- MS MARCO Dataset: Microsoft Machine Reading Comprehension dataset used for training
- Sentence Transformers: [Documentation](https://www.sbert.net/)

## Why P0

**Most RAG errors come from bad context, not bad generation.**

Improving retrieval quality has a multiplicative effect on the entire system:
- Better context → Better answers
- Better answers → Higher confidence
- Higher confidence → Better user trust
- More relevant chunks → Fewer hallucinations

This feature directly addresses the root cause of RAG failures.
