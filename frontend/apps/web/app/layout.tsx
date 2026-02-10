import type { Metadata } from 'next';
import { JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'PRISM - Personal Research Intelligence & Synthesis Manager',
  description: 'AI-powered research assistant for managing and analyzing academic papers',
  keywords: ['research', 'AI', 'papers', 'academic', 'assistant'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${jetbrainsMono.variable} font-mono antialiased`}>
        <Providers>
          <div className="relative min-h-screen matrix-grid">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
