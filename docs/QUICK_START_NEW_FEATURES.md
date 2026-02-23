# Quick Start: New Features Setup

## Installation (5 minutes)

### 1. Install Frontend Dependencies

```bash
cd frontend/apps/web
pnpm add react-pdf pdfjs-dist
```

### 2. Create Data Directories

```bash
cd /Users/Personal_Projects/PRISM
mkdir -p data/pdfs data/zvec_index
```

### 3. Update Environment Variables

Add to `backend/.env`:
```bash
# PDF Storage
PDF_STORAGE_PATH=./data/pdfs

# Reranking (should already be set)
ENABLE_RERANKING=true
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_TOP_K=20
FINAL_TOP_K=5
```

---

## Testing the Features

### 1. Start the Backend

```bash
# Terminal 1
make dev-services  # Start PostgreSQL & Redis
```

```bash
# Terminal 2
make dev-api  # Start FastAPI backend
```

Wait for:
```
INFO: Initializing vector store...
INFO: Initializing Literature Reviewer agent...
INFO: PRISM API started successfully
```

### 2. Start the Frontend

```bash
# Terminal 3
cd frontend/apps/web
pnpm dev
```

Open http://localhost:3000

---

### 3. Test Click-to-Source

#### Step 1: Upload a PDF

1. Go to **Documents** page
2. Drag & drop a research PDF (or click to upload)
3. Wait for "Processing complete"

**Note**: If you have existing PDFs, **delete and re-upload them** to get the new smart chunking.

#### Step 2: Create a Session

1. Go to **Sessions** page
2. Click "Create Session"
3. Name: "Test Session"
4. Topic: "Research"

#### Step 3: Ask a Query

Go to **Chat** page and ask:

```
What are the results of this paper?
```

**Expected Response**:
```
The paper reports X performance [c1] and Y improvement [c2] ...
```

- `[c1]` and `[c2]` should appear as green clickable badges
- Not as regular text!

#### Step 4: Hover Over Citation

Hover over `[c1]`:

**Expected Tooltip**:
```
┌─────────────────────────────┐
│ c1 • RESULTS      Page 8    │
├─────────────────────────────┤
│ The model achieves          │
│ impressive DICE scores...   │
├─────────────────────────────┤
│ Relevance: 87%              │
│ Click to view in PDF        │
└─────────────────────────────┘
```

- Should show section name (RESULTS, METHODS, etc.)
- Should show page number
- Should show text preview
- Should show relevance as 0-100% (not negative!)

#### Step 5: Click Citation

Click `[c1]`:

**Expected Behavior**:
1. Chat panel shrinks to left half
2. PDF viewer appears on right half
3. PDF jumps to page 8
4. Text is highlighted in yellow
5. Highlight pulses 2 times
6. Can navigate pages with prev/next
7. Can zoom in/out
8. Can close PDF viewer with X button

---

## Troubleshooting

### Issue: `pnpm add react-pdf` fails

**Fix**:
```bash
rm -rf node_modules pnpm-lock.yaml
pnpm install
pnpm add react-pdf pdfjs-dist
```

### Issue: Citations are not clickable (plain text)

**Cause**: Frontend not re-rendering after code changes

**Fix**:
1. Stop frontend (Ctrl+C)
2. Clear Next.js cache: `rm -rf .next`
3. Restart: `pnpm dev`

### Issue: PDF viewer shows "Error loading PDF"

**Cause**: PDF not stored on server

**Check**:
```bash
ls ./data/pdfs
# Should show {document_id}.pdf files
```

**Fix**: Re-upload the PDF

### Issue: Relevance scores still showing -458%

**Cause**: Backend not restarted after code changes

**Fix**:
1. Stop backend (Ctrl+C)
2. Restart: `make dev-api`
3. Delete document and re-upload

### Issue: Highlights not appearing in PDF

**Cause**: PDF is a scanned image (no text layer)

**Check**: Try to select text in the PDF. If you can't, it's a scanned PDF.

**Fix**: Use a text-based PDF (not scanned images)

### Issue: Section metadata not showing

**Cause**: PDF was processed before smart chunking was implemented

**Fix**:
1. Delete the document via API or UI
2. Re-upload the same PDF
3. New chunks will have section metadata

---

## Verification Checklist

- [ ] `pnpm add react-pdf pdfjs-dist` completed without errors
- [ ] `./data/pdfs` directory exists
- [ ] Backend starts without errors
- [ ] Frontend starts on http://localhost:3000
- [ ] Can upload PDF successfully
- [ ] Can create session successfully
- [ ] Chat response contains `[c1]` as clickable badge (not plain text)
- [ ] Hover shows tooltip with section, page, preview
- [ ] Relevance score is 0-100% (not negative)
- [ ] Click opens PDF viewer on right side
- [ ] PDF jumps to correct page
- [ ] Text is highlighted in yellow
- [ ] Can close PDF viewer

---

## Success Metrics

If all checks pass, you should see:

**Smart Chunking**:
- ✅ No mid-word truncations in sources
- ✅ All relevance scores 0-100%
- ✅ Section metadata on all chunks

**Section Boosting**:
- ✅ Query "What are the results?" retrieves chunks from RESULTS section
- ✅ Query "How did they do it?" retrieves chunks from METHODS section

**Click-to-Source**:
- ✅ Inline citations are clickable green badges
- ✅ Tooltips show section names
- ✅ PDF viewer opens with highlighted text
- ✅ Smooth animations and transitions

---

## Next: Try These Queries

### Query 1: Results-focused
```
What are the main results and performance metrics?
```

**Expected**: Citations from RESULTS section, high scores

### Query 2: Methods-focused
```
How did the authors implement the model?
```

**Expected**: Citations from METHODS/METHODOLOGY section

### Query 3: Background-focused
```
What is the context and motivation for this work?
```

**Expected**: Citations from INTRODUCTION/BACKGROUND section

### Query 4: Table reference
```
What datasets were used and how did they perform?
```

**Expected**: May include citations with `section_type: "table"`

---

## Demo Script (Show to Others)

1. **Upload**: Drag a research PDF → "Paper uploaded and indexed"
2. **Ask**: "What are the results?"
3. **Show Response**: Point out green `[c1]` badges
4. **Hover**: Show tooltip with section name
5. **Click**: PDF opens → page jumps → text highlights
6. **Navigate**: Show zoom, page navigation
7. **Close**: X button → layout returns to normal

**Wow factor**: "Every claim is instantly verifiable with one click!"

---

## Support

If issues persist:

1. Check logs in terminal for errors
2. Review `docs/CLICK_TO_SOURCE_FEATURE.md` for detailed docs
3. Open issue at https://github.com/your-repo/issues

---

**You're ready to go! 🚀**
