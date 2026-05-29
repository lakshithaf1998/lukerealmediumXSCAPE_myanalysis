Luke active source files v10.3

These are the active patched source files used by the successful Luke local realistic-medium smoke test.
They are included here for verification/provenance; replacing myanalysis alone does not rebuild X-SCAPE.

Expected X-SCAPE destinations if source re-application is needed before rebuilding:
- src/hydro/MusicWrapper.cc
- external_packages/music/src/evolve.cpp

Core fixes preserved:
- MusicWrapper.cc: InitialProfile 13/131 string-source branch is handled before the generic no-pre-equilibrium path; GetHydroInfo falls back to direct MUSIC memory query when JETSCAPE bulk_info is empty.
- evolve.cpp: Cornelius zero-intersection/all-frozen guard plus equal-tau fallback surface generation for no-surface events.
