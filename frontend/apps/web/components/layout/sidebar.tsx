'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  FileText,
  MessageSquare,
  FolderOpen,
  Settings,
  ChevronLeft,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

const navigation = [
  { name: 'Chat', href: '/', icon: MessageSquare },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Sessions', href: '/sessions', icon: FolderOpen },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useAppStore();

  return (
    <>
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col glass border-r border-matrix-border/50 transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-16'
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-matrix-border/50 px-4">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <span className="text-lg font-bold text-background">P</span>
              </div>
              <span className="text-lg font-bold text-glow">PRISM</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-8 w-8"
          >
            <ChevronLeft
              className={cn(
                'h-4 w-4 transition-transform',
                !sidebarOpen && 'rotate-180'
              )}
            />
          </Button>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 px-3 py-4">
          <nav className="flex flex-col gap-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all',
                    isActive
                      ? 'terminal-border bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent/10 hover:text-foreground'
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {sidebarOpen && <span>{item.name}</span>}
                </Link>
              );
            })}
          </nav>
        </ScrollArea>

        {/* Footer */}
        {sidebarOpen && (
          <div className="border-t border-matrix-border/50 p-4">
            <Button className="w-full" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Session
            </Button>
          </div>
        )}
      </aside>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={toggleSidebar}
        />
      )}
    </>
  );
}
