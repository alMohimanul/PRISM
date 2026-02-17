# Two-Step Generation with Grounding Validation

## Overview

This feature implements a two-step LangGraph pipeline that generates answers with explicit citations and validates their grounding in source documents. The system provides transparency through confidence scores, evidence tracking, and visual indicators.

## Architecture

### Backend: LangGraph Two-Step Pipeline

**File:** `backend/apps/api/src/agents/literature_reviewer.py`

The agent now uses a 3-node graph:

```
[retrieve] → [draft] → [validate] → [END]
```

#### Node 1: Retrieve (unchanged)
- Fetches top-5 relevant chunks from FAISS
- Assigns chunk IDs (`c1`, `c2`, etc.)
- Stores chunks in state

#### Node 2: Draft Answer Generation
- **Prompt:** Instructs LLM to answer ONLY using provided chunks
- **Output Format:** JSON with `{ answer, used_chunks }`
- **Temperature:** 0.3 (lower for focused responses)
- **Fallback:** Regex extraction of chunk IDs if JSON parsing fails

#### Node 3: Grounding Validation
- **Input:** Draft answer + referenced chunks
- **Process:** Second LLM call checks if each sentence is supported
- **Output:**
  - `confidence` (0-1): supported_sentences / total_sentences
  - `unsupported_spans`: List of claims not found in chunks
- **Temperature:** 0.1 (very low for factual validation)
- **Fallback:** Default to 0.5 confidence on error

### API Response Schema

**File:** `backend/apps/api/src/models/response.py`

New models:
```python
class EvidenceSource(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    page: Optional[int]

class UnsupportedSpan(BaseModel):
    text: str
    reason: str

class ChatResponse(BaseModel):
    # ... existing fields
    sources: Optional[List[EvidenceSource]]
    confidence: float
    unsupported_spans: List[UnsupportedSpan]
```

### Frontend Components

#### 1. Confidence Badge Component
**File:** `frontend/apps/web/components/chat/confidence-badge.tsx`

Three-level indicator:
- 🟢 **Well supported** (≥75%): Green shield icon
- 🟡 **Partial** (40-74%): Yellow warning triangle
- 🔴 **Weak evidence** (<40%): Red alert circle

Features:
- Displays percentage
- Shows unsupported spans with reasons
- Color-coded borders and backgrounds

#### 2. Enhanced Message Component
**File:** `frontend/apps/web/components/chat/message.tsx`

Features:
- Confidence badge display (assistant messages only)
- Chunk ID badges (`[c1]`, `[c2]`, etc.)
- Hover tooltips showing:
  - Full chunk text (line-clamped to 4 lines)
  - Relevance score
  - Page number (if available)
- Click handler placeholder for PDF scroll
- "Evidence" section with file icon

#### 3. Updated Types
**File:** `frontend/apps/web/types/index.ts`

```typescript
interface EvidenceSource {
  chunk_id: string;
  document_id: string;
  text: string;
  score: number;
  page?: number;
}

interface Message {
  metadata?: {
    sources?: EvidenceSource[];
    confidence?: number;
    unsupported_spans?: UnsupportedSpan[];
  };
}
```

## User Experience Flow

1. **User asks a question**
2. **System retrieves** top-5 chunks from FAISS
3. **LLM drafts answer** with explicit chunk citations
4. **Validator checks** each sentence against chunks
5. **User sees:**
   - Answer with inline citations (`[c1]`, `[c2]`)
   - Confidence badge (green/yellow/red)
   - Clickable evidence chips
   - Hover tooltips with source text
   - Warning badges for unsupported claims

## Implementation Details

### Key Design Decisions

1. **Two LLM calls:** Trade latency for accuracy and transparency
2. **Structured JSON output:** Ensures parseable citations
3. **Fallback regex extraction:** Graceful degradation if JSON fails
4. **Visual hierarchy:** Confidence → Evidence → Details
5. **Hover vs Click:** Hover for preview, click for navigation

### Prompt Engineering

**Draft Prompt:**
- Emphasizes ONLY using provided chunks
- Requires explicit chunk ID citations
- Structured JSON output format
- Low temperature (0.3) for focus

**Validation Prompt:**
- Fact-checking expert persona
- Sentence-by-sentence verification
- Confidence calculation formula
- Very low temperature (0.1) for consistency

### Error Handling

- JSON parse failures → regex fallback
- Missing chunks → 0.2 confidence
- Validation errors → 0.5 default confidence
- Empty results → appropriate empty state

## Pending Work

### PDF Viewer Integration
**File:** `frontend/apps/web/components/chat/message.tsx:19`

```typescript
const handleSourceClick = (chunkId: string, page?: number) => {
  // TODO: Implement PDF scroll to page
  // 1. Get PDF viewer ref from context/store
  // 2. Call viewer.scrollToPage(page)
  // 3. Optionally highlight chunk text
}
```

### Backend Enhancements Needed

1. **Page extraction in PDF processor:**
   - Modify `backend/apps/api/src/services/pdf_processor.py`
   - Store page numbers in chunk metadata
   - Pass through to vector store

2. **Document ID to filename mapping:**
   - API endpoint or store enhancement
   - Enable "Click to open document" feature

## Testing Checklist

- [ ] Upload a test PDF
- [ ] Ask a question well-covered by the document
- [ ] Verify green confidence badge (>75%)
- [ ] Hover over chunk badges, verify tooltip
- [ ] Ask a partially covered question
- [ ] Verify yellow badge (40-75%)
- [ ] Check unsupported spans display
- [ ] Ask an off-topic question
- [ ] Verify red badge (<40%)
- [ ] Test with empty vector store
- [ ] Verify graceful fallback

## Performance Considerations

- **Latency:** Two LLM calls add ~1-2s total
- **Token usage:** ~1.5x compared to single-step
- **Accuracy gain:** Estimated 20-30% reduction in hallucinations
- **User trust:** Significant increase due to transparency

## Future Enhancements

1. **Streaming responses:** Show draft immediately, validation after
2. **Chunk highlighting:** Highlight exact text span in PDF
3. **Interactive editing:** User can mark spans as supported/unsupported
4. **Citation export:** Export answer with bibliography
5. **Batch validation:** Validate multiple answers in parallel
