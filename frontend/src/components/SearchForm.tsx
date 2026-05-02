/** Complete search form with validation. */

import { useState, type FormEvent } from "react";
import type { ProfileOption, SearchFormData } from "../types";
import IdTextarea from "./IdTextarea";
import ProfileDropdown from "./ProfileDropdown";
import FileTypeMultiSelect from "./FileTypeMultiSelect";

interface SearchFormProps {
  profiles: ProfileOption[];
  fileTypes: string[];
  onSubmit: (params: SearchFormData) => void;
  isSubmitting: boolean;
  initialValues?: Partial<SearchFormData>;
}

const DEFAULT_FORM: SearchFormData = {
  date: "",
  ids: "",
  profile: "",
  fileTypes: [],
  bucket: "",
  contextLines: 3,
};

function validate(data: SearchFormData): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!data.date.trim()) {
    errors.date = "Date is required";
  } else if (data.date.toLowerCase() !== "today" && !/^\d{8}$/.test(data.date.trim())) {
    errors.date = "Must be YYYYMMDD or 'today'";
  }
  const ids = data.ids
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith("#"));
  if (ids.length === 0) {
    errors.ids = "At least one ID is required";
  }
  if (!data.profile) {
    errors.profile = "Profile is required";
  }
  return errors;
}

export default function SearchForm({
  profiles,
  fileTypes,
  onSubmit,
  isSubmitting,
  initialValues,
}: SearchFormProps) {
  const [form, setForm] = useState<SearchFormData>({ ...DEFAULT_FORM, ...initialValues });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validate(form);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-4" data-testid="search-form">
      <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wide">Search</h2>

      {/* Date */}
      <div>
        <label htmlFor="search-date" className="block text-sm font-medium text-slate-700 mb-1">
          Date <span className="text-red-500">*</span>
        </label>
        <input
          id="search-date"
          type="text"
          className={`w-full px-3 py-2 border rounded text-sm ${
            errors.date ? "border-red-400" : "border-slate-300"
          } focus:outline-none focus:ring-2 focus:ring-blue-400`}
          placeholder="YYYYMMDD or today"
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
          data-testid="search-date-input"
        />
        {errors.date && <p className="text-xs text-red-500 mt-1">{errors.date}</p>}
      </div>

      {/* IDs */}
      <IdTextarea
        value={form.ids}
        onChange={(ids) => setForm({ ...form, ids })}
        error={errors.ids}
      />

      {/* Profile */}
      <ProfileDropdown
        profiles={profiles}
        value={form.profile}
        onChange={(profile) => setForm({ ...form, profile })}
        error={errors.profile}
      />

      {/* File Types */}
      <FileTypeMultiSelect
        fileTypes={fileTypes}
        selected={form.fileTypes}
        onChange={(fileTypes) => setForm({ ...form, fileTypes })}
      />

      {/* Advanced toggle */}
      <button
        type="button"
        className="text-xs text-blue-600 hover:underline"
        onClick={() => setShowAdvanced(!showAdvanced)}
        data-testid="advanced-toggle"
      >
        {showAdvanced ? "▾ Hide advanced" : "▸ Show advanced"}
      </button>

      {showAdvanced && (
        <div className="space-y-3 pl-2 border-l-2 border-slate-200">
          {/* Bucket override */}
          <div>
            <label htmlFor="bucket-override" className="block text-xs font-medium text-slate-600 mb-1">
              Bucket Override
            </label>
            <input
              id="bucket-override"
              type="text"
              className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="Leave empty for auto-resolve"
              value={form.bucket}
              onChange={(e) => setForm({ ...form, bucket: e.target.value })}
              data-testid="bucket-override-input"
            />
          </div>

          {/* Context lines */}
          <div>
            <label htmlFor="context-lines" className="block text-xs font-medium text-slate-600 mb-1">
              Context Lines
            </label>
            <input
              id="context-lines"
              type="number"
              min={0}
              max={20}
              className="w-20 px-3 py-1.5 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              value={form.contextLines}
              onChange={(e) => setForm({ ...form, contextLines: parseInt(e.target.value, 10) || 0 })}
              data-testid="context-lines-input"
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        data-testid="search-submit-button"
      >
        {isSubmitting ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
