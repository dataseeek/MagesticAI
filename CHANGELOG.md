## [2.0.1] - 2026-01-09

### Added
- 📌 Added new `ReviewPlanReminder` component to improve workflow awareness during task reviews.
- 💡 Added `searchQuery` prop forwarding from `Context` to `MemoriesTab`, enabling consistent search state across components.

### Changed
- 📄 Updated component documentation in `README.md` to reflect new conditional rendering behavior in key UI components.
- 🔁 Modified `TaskReview` and `TaskDetailModal` components to accept and pass `phaseLogs` prop, improving debug and audit trail visibility.

### Fixed
- 🛠️ Resolved issue where context search results were not properly surfaced in `MemoriesTab` due to missing prop propagation.
- 🎯 Fixed incorrect rendering state in conditional UI elements by aligning component logic with updated documentation.

### Security
- 🔐 No security vulnerabilities introduced. All changes reviewed for security implications and deemed low-risk.