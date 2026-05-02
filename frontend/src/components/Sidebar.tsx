/** Sidebar container for search form, saved searches, and history. */

import type React from "react";

interface SidebarProps {
  children: React.ReactNode;
}

export default function Sidebar({ children }: SidebarProps) {
  return (
    <aside
      className="w-80 bg-slate-50 border-r border-slate-200 overflow-y-auto flex-shrink-0 flex flex-col"
      data-testid="sidebar"
    >
      {children}
    </aside>
  );
}
