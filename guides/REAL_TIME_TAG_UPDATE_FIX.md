# Real-Time Tag Update Fix

## Problem

Tasks transitioning from coding phase to "Human Review" (completed) were not updating their tags/status in real-time. The UI only updated after a page refresh.

**User report:** "Tasks in Human Review are not updating tags from coding phase to need review, only with refresh page the status changes."

## Root Cause

The WebSocket `task:status` event was only sending `{ taskId, status }` without the `reviewReason` field. This caused the frontend to not know WHY a task was in `human_review` status:
- **Plan review**: `reviewReason: "plan_review"` (needs plan approval before coding)
- **Completed review**: `reviewReason: "completed"` (finished successfully, needs final approval)
- **Error review**: `reviewReason: "errors"` (failed, needs human intervention)

Without the `reviewReason`, the task store couldn't properly update the tags/labels for the task.

## Changes Made

### Backend Changes

1. **`apps/web-server/server/websockets/events.py`** (lines 87-95)
   - Modified `emit_task_status()` to accept optional `review_reason` parameter
   - Includes `reviewReason` in WebSocket payload when provided
   - Logs reviewReason for debugging

2. **`apps/web-server/server/services/agent_service.py`** (lines 52-67)
   - Created new `phase_to_review_reason()` function
   - Maps TaskPhase to appropriate reviewReason:
     - `PLAN_REVIEW` → `"plan_review"`
     - `COMPLETED` → `"completed"`
     - `FAILED` → `"errors"`

3. **`apps/web-server/server/services/agent_service.py`** (lines 661-665)
   - Updated phase transition logic to get reviewReason from phase
   - Passes reviewReason to `emit_task_status()`

4. **`apps/web-server/server/services/agent_service.py`** (lines 1193-1208)
   - Updated `_update_plan_status()` to set reviewReason in implementation_plan.json
   - Maps status to reviewReason when updating plan files
   - Emits reviewReason in WebSocket event

### Frontend Changes

1. **`apps/frontend-web/src/lib/api-adapter.ts`** (lines 309-314)
   - Updated `onTaskStatusChange` callback to accept `reviewReason` parameter
   - Extracts `reviewReason` from WebSocket payload
   - Passes `reviewReason` to callback

2. **`apps/frontend-web/src/hooks/useIpc.ts`** (lines 13-19)
   - Added `reviewReason?: string` to `BatchedUpdate` interface

3. **`apps/frontend-web/src/hooks/useIpc.ts`** (lines 25-29)
   - Updated `StoreActions` interface to include reviewReason parameter

4. **`apps/frontend-web/src/hooks/useIpc.ts`** (lines 152-169)
   - Updated status change handler to accept and queue reviewReason
   - Logs reviewReason for debugging

5. **`apps/frontend-web/src/hooks/useIpc.ts`** (lines 67-68)
   - Updated flush logic to pass reviewReason to store's `updateTaskStatus()`

6. **`apps/frontend-web/src/shared/types/ipc.ts`** (line 196)
   - Updated `onTaskStatusChange` type signature to include optional reviewReason parameter

## Testing

### Test Case 1: Task Completion
1. Start a task
2. Wait for it to complete the coding phase
3. **Expected:** Task should immediately transition to "Human Review" column with "Completed" tag
4. **Before fix:** Tag doesn't update until page refresh
5. **After fix:** Tag updates in real-time via WebSocket

### Test Case 2: Plan Review
1. Create a task with "Require review before coding" enabled
2. Wait for spec creation to complete
3. **Expected:** Task should immediately show "Plan Review" tag
4. **Before fix:** Tag doesn't update until page refresh
5. **After fix:** Tag updates in real-time via WebSocket

### Test Case 3: Failed Task
1. Start a task that will fail (e.g., invalid config)
2. Wait for failure
3. **Expected:** Task should immediately show "Errors" tag
4. **Before fix:** Tag doesn't update until page refresh
5. **After fix:** Tag updates in real-time via WebSocket

## Verification Steps

1. Restart backend server to load new code:
   ```bash
   cd apps/web-server
   python -m server.main
   ```

2. Check backend logs for new WebSocket emissions:
   ```
   [WebSocket] Emitting task:status - taskId: XXX, status: human_review, reviewReason: completed
   ```

3. Check frontend console for received events:
   ```
   [useIpc] Status event received: task-id status: human_review reviewReason: completed
   ```

4. Verify task store is updated with reviewReason:
   ```
   [task-store] updateTaskStatus: task-id new status: human_review reviewReason: completed
   ```

## Files Changed

**Backend:**
- `apps/web-server/server/websockets/events.py`
- `apps/web-server/server/services/agent_service.py`

**Frontend:**
- `apps/frontend-web/src/lib/api-adapter.ts`
- `apps/frontend-web/src/hooks/useIpc.ts`
- `apps/frontend-web/src/shared/types/ipc.ts`

## Related Issues

This fix ensures consistency with the phase transition fix from earlier:
- Tasks waiting for plan approval correctly show "Plan Review" tag
- Tasks that completed successfully show "Completed" tag
- Tasks that failed show "Errors" tag
- All tag updates happen in real-time without page refresh

## Rollback

If issues arise, revert the following commits:
1. Backend: `agent_service.py` and `events.py` changes
2. Frontend: `api-adapter.ts`, `useIpc.ts`, `ipc.ts` changes

The changes are isolated to WebSocket event handling and can be safely reverted.
