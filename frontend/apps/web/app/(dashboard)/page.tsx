'use client';

import { ChatContainer } from '@/components/chat/chat-container';
import { Card } from '@/components/ui/card';

export default function HomePage() {
  return (
    <div className="grid h-[calc(100vh-8rem)] gap-6 lg:grid-cols-3">
      {/* Main chat area */}
      <Card className="lg:col-span-2 p-6 flex flex-col min-h-0">
        <div className="flex items-center gap-3 mb-4 border-b border-matrix-border/50 pb-4 flex-shrink-0">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
          <h1 className="text-xl font-bold text-glow">Research Assistant</h1>
        </div>
        <div className="flex-1 min-h-0">
          <ChatContainer />
        </div>
      </Card>

      {/* Sidebar info */}
      <div className="space-y-6">
        {/* Quick stats */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-muted-foreground mb-4">
            QUICK STATS
          </h2>
          <div className="space-y-4">
            <div>
              <div className="text-2xl font-bold text-primary">0</div>
              <div className="text-sm text-muted-foreground">Documents</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-secondary">0</div>
              <div className="text-sm text-muted-foreground">Sessions</div>
            </div>
          </div>
        </Card>

        {/* Recent activity */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-muted-foreground mb-4">
            RECENT ACTIVITY
          </h2>
          <div className="text-sm text-muted-foreground">
            No recent activity
          </div>
        </Card>
      </div>
    </div>
  );
}
