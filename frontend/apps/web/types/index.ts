export interface Document {
  document_id: string;
  filename: string;
  title?: string;
  authors?: string[];
  abstract?: string;
  page_count: number;
  size_bytes: number;
  upload_date: string;
  processing_status: string;
}

export interface Session {
  session_id: string;
  name: string;
  topic?: string;
  description?: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  message_count: number;
}

export interface EvidenceSource {
  chunk_id: string;
  document_id: string;
  text: string;
  score: number;
  page?: number;
}

export interface UnsupportedSpan {
  text: string;
  reason: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    sources?: EvidenceSource[];
    confidence?: number;
    unsupported_spans?: UnsupportedSpan[];
  };
}

export interface Source {
  document_id: string;
  text: string;
  score: number;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  agent_type: string;
  sources?: EvidenceSource[];
  confidence: number;
  unsupported_spans: UnsupportedSpan[];
  timestamp: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  size_bytes: number;
  status: string;
}

// Debate types
export interface DebateCitation {
  chunk_id: string;
  document_id: string;
  text: string;
  page?: number;
}

export interface DebateArgument {
  argument: string;
  citations: DebateCitation[];
  verified: boolean;
  tone: string;
}

export interface DebateRound {
  round: number;
  topic: string;
  team_a: DebateArgument;
  team_b: DebateArgument;
  moderator_comment: string;
  winner: 'team_a' | 'team_b' | 'tie' | null;
  scores: {
    team_a: number;
    team_b: number;
  };
}

export interface DebateTeam {
  name: string;
  documents: string[];
  score: number;
}

export interface DebateResponse {
  team_a: DebateTeam;
  team_b: DebateTeam;
  rounds: DebateRound[];
  final_verdict: string;
  error?: string;
}

// Literature Review types
export interface PaperMetadata {
  document_id: string;
  title: string;
  year: number;
  key_contribution: string;
  authors: string;
}

export interface EvolutionSection {
  era: string;
  content: string;
}

export interface ReviewSections {
  problem: string;
  evolution: EvolutionSection[];
  sota: string;
  gaps: string[];
  conclusion: string;
}

export interface LiteratureReviewResponse {
  full_review: string;
  papers: PaperMetadata[];
  sections: ReviewSections;
  error?: string;
}
