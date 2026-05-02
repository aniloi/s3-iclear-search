/** Main application layout: header + tab bar + sidebar + content. */

import type React from "react";

interface AppLayoutProps {
  header: React.ReactNode;
  tabBar: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

export default function AppLayout({ header, tabBar, sidebar, children }: AppLayoutProps) {
  return (
    <div className="h-screen flex flex-col" data-testid="app-layout">
      {header}
      {tabBar}
      <div className="flex flex-1 overflow-hidden">
        {sidebar}
        <main className="flex-1 overflow-y-auto p-6 bg-white" data-testid="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
