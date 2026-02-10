'use client';

import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sidebarOpen } = useAppStore();

  return (
    <div className="relative flex min-h-screen">
      <Sidebar />

      {/* Main content */}
      <div
        className={cn(
          'flex flex-1 flex-col transition-all duration-300',
          sidebarOpen ? 'lg:pl-64' : 'lg:pl-16'
        )}
      >
        <Header />
        <main className="flex-1 scanline">
          <div className="container mx-auto p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
