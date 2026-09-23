# Incident-area lifecycle task baseline

This change was deliberately introduced on 2026-09-23 as an evaluation scenario. It is not an inherited production defect. It adapts the user-supplied map-dialog lifecycle concept to Leaflet, which this repository already uses.

The feature is inside the existing dashboard's Ops map panel. There is no separate exercise page in this worktree. Create incident area opens a drawing/upload dialog; records use a separate SQLite table and do not affect operational incidents or dispatch resources. The drawing map uses a local coordinate grid, while the original Ops map remains unchanged.

## Single intentionally introduced defect

Reopening the dialog awaits Leaflet's already-fired one-shot load event and stays at Preparing map. Drawing cannot start on that opening. This is the only intentionally retained defect.

Early upload selection is preserved. Save/cancel completion is registered before the dialog is shown. A session guard prevents late initialization from changing a closed or newer dialog. Upload saves and cancellation remain usable even while the reopened drawing map is stuck. Cancellation is ignored during an in-flight save so it cannot race that save.

Initialization includes a documented 2.5 second delay plus 0.8 second setup delay to make timing reproducible. These are synthetic delays, not measured network performance.

## Reproduce

1. Reload the dashboard and scroll to Ops map. Click Create incident area and wait for Map ready.
2. Cancel, or create an area using Draw or Upload.
3. Open Create incident area again. Preparing map remains and drawing does not start.

## Preservation checks

- On a fresh page, choose Upload immediately. It must remain selected after map initialization.
- On a fresh page, upload the sample and save before initialization completes. The saved area must be selected and the workspace must stop waiting.
- Cancel during initialization. The workspace must stop waiting; late initialization must not change a later dialog.
- On a reopened, stuck dialog, Upload and Cancel must still work.

Both comparison models must start from the same reviewed commit and inputs. This baseline was prepared in the Astra worktree; the Gemini worktree must be updated to the same commit before either evaluation run starts. The older scrolling screenshots do not document these new defects.

## Scope and checks

The API validates single-ring Polygon coordinate bounds and closure, not full polygon topology. Local replay mode with RBAC disabled is the intended setup. Authenticated deployment is not verified. The API tests cover persistence, duplicate IDs, invalid boundaries and viewer permissions. Original dashboard services and real payments/dispatch are outside this task.
