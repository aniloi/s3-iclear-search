/** Profile selector dropdown with grouped options. */

import type { ProfileOption } from "../types";

interface ProfileDropdownProps {
  profiles: ProfileOption[];
  value: string;
  onChange: (profile: string) => void;
  error?: string;
}

export default function ProfileDropdown({
  profiles,
  value,
  onChange,
  error,
}: ProfileDropdownProps) {
  const known = profiles.filter((p) => p.is_known);
  const other = profiles.filter((p) => !p.is_known);
  const selected = profiles.find((p) => p.name === value);

  return (
    <div>
      <label htmlFor="profile-select" className="block text-sm font-medium text-slate-700 mb-1">
        AWS Profile <span className="text-red-500">*</span>
      </label>
      <select
        id="profile-select"
        className={`w-full px-3 py-2 border rounded text-sm ${
          error ? "border-red-400" : "border-slate-300"
        } focus:outline-none focus:ring-2 focus:ring-blue-400`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid="profile-dropdown"
      >
        <option value="">Select a profile...</option>
        {known.length > 0 && (
          <optgroup label="Known Environments">
            {known.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} → {p.resolved_bucket}
              </option>
            ))}
          </optgroup>
        )}
        {other.length > 0 && (
          <optgroup label="Other Profiles">
            {other.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
                {p.resolved_bucket ? ` → ${p.resolved_bucket}` : ""}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      {selected?.resolved_bucket && (
        <p className="text-xs text-slate-500 mt-1">
          Bucket: <span className="font-mono">{selected.resolved_bucket}</span>
        </p>
      )}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
