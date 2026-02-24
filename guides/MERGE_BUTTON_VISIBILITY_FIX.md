# Merge Button Visibility Fix

## Problem

The "Merge to Main" button was appearing in the workspace status even when a task was in plan review stage (before coding starts). This was confusing because there's nothing to merge until coding is complete.

**User report:** "The 'merge to main' button, should not appear if phase is human_review, but coding phase is not done or coding log is empty."

## Root Cause

The `WorkspaceStatus` component didn't have access to the task's `reviewReason` field, which indicates WHY a task is in `human_review` status:
- `reviewReason: "plan_review"` - Plan needs approval before coding starts (NO merge button)
- `reviewReason: "completed"` - Task finished successfully, ready to merge (YES merge button)
- `reviewReason: "errors"` - Task failed, needs fixes (YES merge button for fixing)

Without this information, the merge button was always shown regardless of whether coding had started.

## Changes Made

### 1. WorkspaceStatus Component (`apps/frontend-web/src/components/task-detail/task-review/WorkspaceStatus.tsx`)

**Added Task Import:**
```typescript
import type { WorktreeStatus, MergeConflict, MergeStats, GitConflictInfo, SupportedIDE, SupportedTerminal, Task } from '../../../shared/types';
```

**Updated Props Interface:**
```typescript
interface WorkspaceStatusProps {
  task: Task;  // Added
  worktreeStatus: WorktreeStatus;
  // ... rest of props
}
```

**Added Visibility Logic:**
```typescript
export function WorkspaceStatus({
  task,  // Added
  worktreeStatus,
  // ... rest of props
}: WorkspaceStatusProps) {
  // ... existing code ...

  // Don't show merge button if task is in plan review (coding hasn't started yet)
  // Only show merge button when coding is done or in progress
  const shouldShowMergeButton = task.reviewReason !== 'plan_review';
```

**Conditionally Render Actions Footer:**
```typescript
{/* Actions Footer */}
{shouldShowMergeButton && (  // Wrapped entire section
  <div className="px-4 py-3 bg-muted/20 border-t border-border space-y-3">
    {/* Stage Only Option */}
    {/* ... */}

    {/* Primary Actions */}
    <div className="flex gap-2">
      <Button /* Merge button */>
        {/* ... */}
      </Button>
      <Button /* Discard button */>
        {/* ... */}
      </Button>
    </div>
  </div>
)}
```

### 2. TaskReview Component (`apps/frontend-web/src/components/task-detail/TaskReview.tsx`)

**Passed Task Prop:**
```typescript
<WorkspaceStatus
  task={task}  // Added
  worktreeStatus={worktreeStatus}
  // ... rest of props
/>
```

## Behavior After Fix

### Plan Review Stage (reviewReason = 'plan_review')
- **Merge button:** Hidden ✅
- **Discard button:** Hidden ✅
- **Workspace info:** Still visible (branch, stats, IDE/terminal buttons)
- **Reason:** Coding hasn't started yet, nothing to merge

### Completed Stage (reviewReason = 'completed')
- **Merge button:** Visible ✅
- **Discard button:** Visible ✅
- **Workspace info:** Visible
- **Reason:** Coding is done, changes ready to merge

### Error Stage (reviewReason = 'errors')
- **Merge button:** Visible ✅
- **Discard button:** Visible ✅
- **Workspace info:** Visible
- **Reason:** User may want to merge partial work or discard

## Testing

### Test Case 1: Plan Review
1. Create a task with "Require review before coding" enabled
2. Wait for spec creation to complete
3. Open task in review tab
4. **Expected:** Workspace status shown but NO merge/discard buttons
5. **Actual:** ✅ Merge/discard buttons are hidden

### Test Case 2: Completed Task
1. Let a task complete coding and QA
2. Task transitions to human_review with reviewReason='completed'
3. Open task in review tab
4. **Expected:** Full workspace status with merge/discard buttons
5. **Actual:** ✅ All buttons visible

### Test Case 3: Failed Task
1. Start a task that will fail
2. Task transitions to human_review with reviewReason='errors'
3. Open task in review tab
4. **Expected:** Full workspace status with merge/discard buttons
5. **Actual:** ✅ All buttons visible

## Files Changed

- `apps/frontend-web/src/components/task-detail/task-review/WorkspaceStatus.tsx`
- `apps/frontend-web/src/components/task-detail/TaskReview.tsx`

## Related Improvements

This fix works in conjunction with the real-time tag update fix to ensure:
1. Task status updates in real-time (via WebSocket with reviewReason)
2. UI correctly shows/hides merge button based on reviewReason
3. User experience is consistent and intuitive

## Future Enhancements

Consider adding:
- Info message when merge button is hidden: "Complete plan review to start coding"
- Different workspace status styling for plan review stage
- Progress indicator showing "Plan Review → Coding → QA → Merge" flow
