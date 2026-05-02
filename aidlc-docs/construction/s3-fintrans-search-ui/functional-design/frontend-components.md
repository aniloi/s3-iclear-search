# Frontend Components — S3 Fintrans Search UI

## Component Hierarchy

```
App
 +-> AppLayout
      +-> Header
      |    +-> AppTitle
      |    +-> TabBar
      |         +-> Tab (repeated)
      |         +-> NewSearchButton
      +-> Sidebar
      |    +-> SearchForm
      |    |    +-> DateInput
      |    |    +-> IdTextarea
      |    |    +-> ProfileDropdown
      |    |    +-> FileTypeMultiSelect
      |    |    +-> AdvancedToggle
      |    |    |    +-> BucketInput
      |    |    |    +-> ContextLinesInput
      |    |    +-> SubmitButton
      |    +-> SavedSearches
      |    |    +-> SaveSearchButton
      |    |    +-> SavedSearchList
      |    |         +-> SavedSearchItem (repeated)
      |    +-> HistoryPanel
      |         +-> HistoryList
      |              +-> HistoryItem (repeated)
      +-> MainContent
           +-> EmptyState (when no tabs)
           +-> SearchProgress (when tab is searching)
           |    +-> ProgressSteps
           |    +-> ProgressBar
           +-> ResultsView (when tab is complete)
                +-> ResultsHeader
                +-> WarningsBanner
                +-> ResultsToolbar
                |    +-> StatusFilter
                |    +-> SearchBox
                |    +-> ExportButtons
                +-> ResultsTable
                     +-> TableHeader (sortable columns)
                     +-> TableRow (repeated)
                          +-> ExpandedContext (when expanded)
                               +-> FileMatchGroup (repeated)
                                    +-> MatchLine (repeated)
```

---

## Component Specifications

### App

Root component. Manages global state.

```typescript
State:
  tabs: SearchTab[]
  activeTabId: string | null
  profiles: ProfileOption[]       // Loaded once on mount from GET /api/profiles
  fileTypes: string[]             // Loaded once on mount from GET /api/file-types
  savedSearches: SavedSearch[]    // Loaded once on mount from GET /api/saved-searches
  history: SearchHistoryEntry[]   // Loaded once on mount, updated after each search

Effects:
  onMount: fetch profiles, file types, saved searches, history
```

### SearchForm

The search parameter form. Always visible in the sidebar.

```typescript
Props:
  profiles: ProfileOption[]
  fileTypes: string[]
  onSubmit: (params: SearchFormData) => void
  initialValues?: SearchFormData   // For loading saved searches

State:
  formData: SearchFormData
  errors: Record<string, string>   // Field-level validation errors
  isSubmitting: boolean

Validation (on blur + on submit):
  date: required, must match /^\d{8}$/ or be 'today'
  ids: required, must produce at least 1 ID after parsing
  profile: required, must be selected
  fileTypes: optional (empty = all)
  bucket: optional
  contextLines: optional, must be integer >= 0
```

### ProfileDropdown

Dropdown for selecting AWS profile.

```typescript
Props:
  profiles: ProfileOption[]
  value: string
  onChange: (profile: string) => void
  error?: string

Rendering:
  - Grouped: "Known Environments" section (dev, qa, uat, prod) and "Other Profiles" section
  - Each option shows: profile name + resolved bucket (if known)
  - Includes a free-text input option at the bottom for unlisted profiles
  - Shows auto-resolved bucket below the dropdown when a profile is selected
```

### FileTypeMultiSelect

Multi-select for file type filters.

```typescript
Props:
  fileTypes: string[]             // Available types from API
  selected: string[]              // Currently selected
  onChange: (selected: string[]) => void

Rendering:
  - Checkbox list or pill-style multi-select
  - "Select All" / "Clear" buttons
  - Empty selection = all types (no filter)
```

### IdTextarea

Textarea for entering search IDs.

```typescript
Props:
  value: string
  onChange: (value: string) => void
  error?: string

Rendering:
  - Multi-line textarea
  - Below: "N IDs detected" count (parsed in real-time)
  - Placeholder: "Enter IDs, one per line or comma-separated"
  - Supports # comments (shown in lighter color or parsed out)
```

### TabBar

Horizontal tab bar in the header.

```typescript
Props:
  tabs: SearchTab[]
  activeTabId: string | null
  onSelectTab: (tabId: string) => void
  onCloseTab: (tabId: string) => void
  onNewSearch: () => void

Rendering:
  - Each tab shows: label ("{date} / {profile}")
  - Active tab is highlighted
  - Each tab has an "×" close button
  - Status icon: spinner (searching), checkmark (complete), warning (error), dash (cancelled)
  - "+" button at the end to focus the search form
```

### SearchProgress

Shown when a tab's search is in progress.

```typescript
Props:
  tab: SearchTab

Rendering:
  - Step indicators: Auth → Discovery → Search → Complete
  - Current step highlighted
  - Progress bar: "{completed}/{total} files ({percentage}%)"
  - Current file name below progress bar
  - Cancel button: calls DELETE /api/search/{id}
```

### ResultsView

Shown when a tab's search is complete (or cancelled with partial results).

```typescript
Props:
  tab: SearchTab
  onExport: (format: 'json' | 'csv') => void

Rendering:
  - ResultsHeader: date, bucket, profile, files searched, files failed
  - WarningsBanner: collapsible list of file-level warnings
  - ResultsToolbar: status filter, search box, export buttons
  - ResultsTable: interactive table with sortable columns
```

### ResultsHeader

Metadata about the search.

```typescript
Props:
  report: SearchReport

Rendering:
  - "Search Results for {date}"
  - "Bucket: {bucket} | Profile: {profile}"
  - "Files searched: {files_searched}" + "Files failed: {files_failed}" (if > 0, in warning color)
  - Summary: "{found}/{total} IDs found"
```

### ResultsTable

Interactive, sortable, filterable results table.

```typescript
Props:
  results: SearchResult[]
  contextLines: number
  statusFilter: 'all' | 'found' | 'not_found'
  searchQuery: string
  sortColumn: string
  sortDirection: 'asc' | 'desc'
  onSort: (column: string) => void
  expandedRows: Set<string>       // Set of expanded result IDs
  onToggleExpand: (id: string) => void

Columns:
  | Column      | Sortable | Description                          |
  |-------------|----------|--------------------------------------|
  | ID          | Yes      | Search term                          |
  | Status      | Yes      | Found (green) / Not Found (red)      |
  | Files       | Yes      | Comma-separated matching filenames   |
  | Match Count | Yes      | Total matching lines across all files |

Row expansion:
  When expanded, show ExpandedContext below the row
  Grouped by file: filename header, then matching lines with line numbers
```

### ExpandedContext

Expanded detail view for a single search result.

```typescript
Props:
  result: SearchResult
  contextLines: number

Rendering:
  FOR each FileMatch in result.file_matches:
    - File header: "{filename} ({match_count} matches)"
    - FOR each MatchLine (up to contextLines):
      - "Line {line_number}: {line_content}"
      - Line content in monospace font, horizontally scrollable
    - If more matches than contextLines:
      - "+{remaining} more matches"
```

### HistoryPanel

Sidebar section showing search history.

```typescript
Props:
  history: SearchHistoryEntry[]
  onReopen: (searchId: string) => void

Rendering:
  - List of history entries, most recent first
  - Each entry shows:
    - Timestamp (relative: "2 min ago", "1 hour ago")
    - "{date} / {profile}"
    - "{found}/{total} IDs found"
    - Status badge (completed, cancelled, failed)
  - Click to re-open results in a new tab
```

### SavedSearches

Sidebar section for saved search presets.

```typescript
Props:
  savedSearches: SavedSearch[]
  onLoad: (params: SearchSessionRequest) => void
  onDelete: (id: string) => void
  onSave: (name: string) => void
  currentFormData: SearchFormData

Rendering:
  - "Save Current" button (opens name input dialog)
  - List of saved searches
  - Each entry shows: name, profile, date (if set)
  - Click to load into form
  - Delete button (×) on each entry
```

---

## State Management

### Global State (App level, via Context + useReducer)

```typescript
AppState:
  // Tab management
  tabs: SearchTab[]
  activeTabId: string | null

  // Reference data (loaded once)
  profiles: ProfileOption[]
  fileTypes: string[]

  // Session data
  history: SearchHistoryEntry[]
  savedSearches: SavedSearch[]

Actions:
  ADD_TAB(tab: SearchTab)
  REMOVE_TAB(tabId: string)
  SET_ACTIVE_TAB(tabId: string)
  UPDATE_TAB(tabId: string, updates: Partial<SearchTab>)
  SET_PROFILES(profiles: ProfileOption[])
  SET_FILE_TYPES(types: string[])
  ADD_HISTORY(entry: SearchHistoryEntry)
  SET_HISTORY(entries: SearchHistoryEntry[])
  ADD_SAVED_SEARCH(search: SavedSearch)
  REMOVE_SAVED_SEARCH(id: string)
  SET_SAVED_SEARCHES(searches: SavedSearch[])
```

### Per-Tab State (managed within SearchTab object)

Each tab's state is updated via the `UPDATE_TAB` action as SSE events arrive. The SSE event handler dispatches updates to the reducer.

### Custom Hooks

```typescript
useSearch():
  - Handles POST /api/search + SSE connection lifecycle
  - Returns: { startSearch, cancelSearch }
  - Manages EventSource creation, event handling, cleanup

useProfiles():
  - Fetches profiles on mount
  - Returns: { profiles, loading, error }

useFileTypes():
  - Fetches file types on mount
  - Returns: { fileTypes, loading, error }

useHistory():
  - Fetches history on mount, provides refresh
  - Returns: { history, refresh, loading }

useSavedSearches():
  - CRUD operations for saved searches
  - Returns: { savedSearches, save, load, remove }
```
