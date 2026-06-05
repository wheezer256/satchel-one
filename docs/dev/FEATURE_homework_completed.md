# Feature request: `satchel_one_homework_completed` event

**Why:** the parent's Home Assistant build sends each child a realtime "thanks for
doing your homework!" push the moment they mark a task complete in Satchel, and
reflects completion on dashboards. HA needs an event to trigger on.

## What to add

Mirror the existing new-homework delta pattern in `HomeworkCoordinator`
(`coordinator.py`) — it already tracks `self._seen_ids` and fires
`EVENT_HOMEWORK_NEW` for newly-appeared todos, guarded by `self._first_fetch`.

Add a parallel **completion** delta:

1. **`const.py`** — add:
   ```python
   EVENT_HOMEWORK_COMPLETED = "satchel_one_homework_completed"
   ```

2. **`coordinator.py` `HomeworkCoordinator`** — track which todo ids are currently
   completed, and fire when a todo transitions `completed` false→true between polls:
   - add `self._completed_ids: set[int] = set()` in `__init__`.
   - in `_async_update_data`, after fetching `homework`:
     ```python
     completed_now = {h.id for h in homework if h.completed}
     newly_completed = [h for h in homework if h.completed and h.id not in self._completed_ids]

     if not self._first_fetch:
         for hw in newly_completed:
             self.hass.bus.async_fire(
                 EVENT_HOMEWORK_COMPLETED,
                 {
                     "task_id": hw.id,
                     "title": hw.title,
                     "subject": hw.subject,
                     "person": self._linked_person,
                 },
             )
     self._completed_ids = completed_now
     ```
   - **Critical:** keep this under the same `if not self._first_fetch:` guard as
     new-homework. On the very first poll (and after every restart) ~256 todos are
     already complete — without the guard that's a 256-notification storm.
   - `self._first_fetch` is already set to `False` at the end of the method; the
     existing line stays as-is (set it after both deltas are processed).

## Payload contract (what the HA automation consumes)

```
satchel_one_homework_completed
  task_id : int
  title   : str
  subject : str
  person  : str | null   # the linked person.* entity_id, used to route the push
```

## Notes
- `completed` reflects "marked complete in Satchel" (by whoever) — that's the
  intended signal.
- A child bulk-marking several at once over one poll window fires one event each
  (per-task is desired here).
- Tests: add a coordinator test that (a) does NOT fire on first fetch with
  pre-completed todos, and (b) fires exactly once when a todo flips to completed on
  a subsequent fetch. Follow the existing new-homework coordinator test.
```
