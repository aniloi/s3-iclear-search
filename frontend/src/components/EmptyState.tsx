/** Empty state shown when no search tabs are open. */

export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-slate-400" data-testid="empty-state">
      <div className="text-5xl mb-4">🔍</div>
      <h2 className="text-lg font-medium text-slate-600 mb-2">No active searches</h2>
      <p className="text-sm">Use the search form on the left to start a new search.</p>
    </div>
  );
}
