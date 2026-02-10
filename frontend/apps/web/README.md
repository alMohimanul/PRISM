# PRISM Frontend - Tech/Matrix Futuristic UI

Production-grade, futuristic research assistant interface built with Next.js 14, Shadcn/ui, and Tailwind CSS.

## Design Aesthetic

- **Tech/Matrix inspired** - Dark theme with code/terminal aesthetics
- Matrix-style green (#00ff41) and cyan (#00ffff) accents
- Grid pattern overlays and scanline effects
- Glass morphism cards with backdrop blur
- Terminal-style borders and command inputs
- Monospace fonts (JetBrains Mono / Fira Code)
- No emojis - pure professional interface

## Features

### ✓ Real-time Chat Interface
- Terminal-style chat window with monospace font
- Message streaming with typing indicators
- Source citations as expandable code blocks
- Command-style input with real-time responses
- Chat history with timestamps
- Markdown rendering for code snippets

### ✓ Document Library
- Grid/list toggle with animated transitions
- Drag-and-drop PDF upload zone
- Search and filter documents
- Processing status with visual feedback
- Metadata cards showing page count, size, and date
- Delete functionality with confirmation

### ✓ Session Management
- Create and manage research sessions
- Active session indicator with glow effect
- Quick switch between sessions
- Session metadata (document count, message count)
- Session-based conversation history

### ✓ Layout
- Collapsible sidebar navigation
- Responsive design (mobile-friendly)
- Matrix grid background effect
- Scanline animation overlay
- Glass morphism UI elements

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI Components**: Shadcn/ui (customized)
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Icons**: Lucide React
- **Markdown**: react-markdown with remark-gfm
- **TypeScript**: Strict mode enabled

## Setup Instructions

### Prerequisites

- Node.js 18+ installed
- pnpm 8+ installed
- Backend API running at `http://localhost:8000`

### Installation

1. **Navigate to the web app directory**
   ```bash
   cd frontend/apps/web
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env.local
   ```

4. **Configure environment variables**
   Edit `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

5. **Start the development server**
   ```bash
   pnpm dev
   ```

   The app will be available at `http://localhost:3000`

### Alternative: Run from root

From the project root:

```bash
# Install all dependencies
cd frontend && pnpm install

# Start the dev server
make dev-web
```

## Project Structure

```
frontend/apps/web/
├── app/
│   ├── (dashboard)/          # Dashboard layout group
│   │   ├── layout.tsx        # Shared layout with sidebar/header
│   │   ├── page.tsx          # Home/chat page
│   │   ├── documents/        # Document library page
│   │   └── sessions/         # Session management page
│   ├── globals.css           # Custom theme + animations
│   ├── layout.tsx            # Root layout
│   └── providers.tsx         # React Query provider
├── components/
│   ├── ui/                   # Shadcn components (customized)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── scroll-area.tsx
│   ├── chat/                 # Chat interface components
│   │   ├── chat-container.tsx
│   │   ├── chat-input.tsx
│   │   └── message.tsx
│   ├── documents/            # Document components
│   │   ├── upload-zone.tsx
│   │   └── document-card.tsx
│   └── layout/               # Layout components
│       ├── sidebar.tsx
│       └── header.tsx
├── lib/
│   ├── api.ts                # API client (axios)
│   ├── store.ts              # Zustand state management
│   └── utils.ts              # Helper functions
├── types/
│   └── index.ts              # TypeScript type definitions
├── tailwind.config.ts        # Tailwind configuration
└── next.config.js            # Next.js configuration
```

## Key Components

### Layout Components

- **Sidebar** (`components/layout/sidebar.tsx`)
  - Collapsible navigation
  - Active route highlighting with terminal borders
  - Matrix-style branding

- **Header** (`components/layout/header.tsx`)
  - Session indicator with pulse animation
  - Search functionality
  - Notification bell

### Chat Components

- **ChatContainer** (`components/chat/chat-container.tsx`)
  - Real-time message sending with TanStack Query
  - Loading states with typing indicators
  - Empty state handling

- **MessageBubble** (`components/chat/message.tsx`)
  - User/assistant message styling
  - Markdown rendering for assistant responses
  - Source citation display
  - Timestamps

- **ChatInput** (`components/chat/chat-input.tsx`)
  - Terminal-style input field
  - Enter to send, Shift+Enter for new line
  - Loading dots animation

### Document Components

- **UploadZone** (`components/documents/upload-zone.tsx`)
  - Drag-and-drop file upload
  - Visual feedback (uploading, success, error)
  - PDF validation

- **DocumentCard** (`components/documents/document-card.tsx`)
  - Grid and list view support
  - Metadata display
  - Delete functionality

## Custom Theme

### Colors

```css
/* Matrix-inspired palette */
--primary: #00ff41 (Matrix green)
--secondary: #00ffff (Cyan)
--background: #0a0e1a (Dark)
--surface: #1a1f2e (Dark blue-gray)
--border: #2a3f5f (Subtle cyan)
--text: #e0f2f7 (Light cyan-white)
```

### Custom Classes

- `.matrix-grid` - Grid pattern background
- `.scanline` - Scanline animation effect
- `.glow` - Matrix green glow effect
- `.glow-cyan` - Cyan glow effect
- `.terminal-border` - Terminal-style borders
- `.glass` - Glass morphism effect
- `.code-block` - Code block styling
- `.hover-glow` - Hover glow animation
- `.text-glow` - Text glow effect

### Animations

- `scanline` - Moving scanline effect
- `pulse-glow` - Pulsing glow animation
- `flicker` - Subtle flicker effect
- `grid-fade` - Grid pattern fade
- `loading-dots` - Three-dot loading animation

## API Integration

The frontend communicates with the PRISM backend API:

```typescript
// Document operations
await documentsApi.upload(file);
await documentsApi.list();
await documentsApi.delete(documentId);

// Session operations
await sessionsApi.create(name, topic);
await sessionsApi.list();
await sessionsApi.delete(sessionId);

// Chat operations
await chatApi.sendMessage(sessionId, message);
```

## State Management

Using Zustand for global state:

```typescript
const {
  currentSession,      // Active research session
  setCurrentSession,   // Set active session
  sidebarOpen,         // Sidebar collapsed state
  toggleSidebar,       // Toggle sidebar
  documentViewMode,    // Grid or list view
  selectedDocument,    // Currently viewed document
} = useAppStore();
```

## Development

### Build for production

```bash
pnpm build
```

### Run production build locally

```bash
pnpm start
```

### Linting

```bash
pnpm lint
```

### Type checking

```bash
pnpm typecheck
```

## Customization

### Changing Colors

Edit `tailwind.config.ts`:

```typescript
colors: {
  matrix: {
    green: '#00ff41',  // Primary accent
    cyan: '#00ffff',   // Secondary accent
    dark: '#0a0e1a',   // Background
    // ...
  },
}
```

### Adjusting Animations

Edit `app/globals.css`:

```css
@keyframes scanline {
  /* Customize scanline speed/effect */
}
```

### Modifying Grid Pattern

In `globals.css`, adjust `.matrix-grid`:

```css
.matrix-grid {
  background-size: 50px 50px; /* Grid cell size */
  /* ... */
}
```

## Keyboard Shortcuts

- `Enter` - Send message in chat
- `Shift+Enter` - New line in chat input
- `Cmd/Ctrl+K` - Focus search (coming soon)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari 14+

## Performance

- Code splitting with Next.js dynamic imports
- Optimistic UI updates
- React Query caching
- Image optimization with Next.js Image component
- Font optimization with next/font

## Accessibility

- Semantic HTML
- ARIA labels on interactive elements
- Keyboard navigation support
- Focus visible indicators
- Screen reader friendly

## Troubleshooting

### Port 3000 already in use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or run on different port
pnpm dev -- -p 3001
```

### Dependencies not installing

```bash
# Clear pnpm cache
pnpm store prune

# Remove node_modules and reinstall
rm -rf node_modules
pnpm install
```

### API connection errors

1. Ensure backend is running at `http://localhost:8000`
2. Check CORS settings in backend
3. Verify `NEXT_PUBLIC_API_URL` in `.env.local`

### TypeScript errors

```bash
# Regenerate types
pnpm typecheck
```

## Contributing

When adding new components:

1. Follow the existing component structure
2. Use Tailwind classes instead of custom CSS
3. Apply matrix theme colors and effects
4. Add TypeScript types
5. Include proper error handling

## License

MIT License
