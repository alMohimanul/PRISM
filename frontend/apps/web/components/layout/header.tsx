'use client';

import { Menu, Search, Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/lib/store';

export function Header() {
  const { toggleSidebar, currentSession } = useAppStore();

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 glass border-b border-matrix-border/50 px-6">
      {/* Mobile menu */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={toggleSidebar}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Session indicator */}
      {currentSession && (
        <div className="hidden md:flex items-center gap-2 text-sm">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
          <span className="text-muted-foreground">Session:</span>
          <span className="text-foreground font-medium">
            {currentSession.name}
          </span>
        </div>
      )}

      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            className="pl-10"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
