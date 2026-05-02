/** Multi-select for file type filters. */

interface FileTypeMultiSelectProps {
  fileTypes: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function FileTypeMultiSelect({
  fileTypes,
  selected,
  onChange,
}: FileTypeMultiSelectProps) {
  const toggle = (ft: string) => {
    if (selected.includes(ft)) {
      onChange(selected.filter((s) => s !== ft));
    } else {
      onChange([...selected, ft]);
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">File Types</label>
      <div className="flex flex-wrap gap-1.5" data-testid="file-type-multiselect">
        {fileTypes.map((ft) => (
          <button
            key={ft}
            type="button"
            className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
              selected.includes(ft)
                ? "bg-blue-100 border-blue-400 text-blue-700"
                : "bg-white border-slate-300 text-slate-600 hover:border-slate-400"
            }`}
            onClick={() => toggle(ft)}
            data-testid={`file-type-${ft}`}
            aria-pressed={selected.includes(ft)}
          >
            {ft}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500 mt-1">
        {selected.length === 0 ? "All types (no filter)" : `${selected.length} selected`}
      </p>
    </div>
  );
}
