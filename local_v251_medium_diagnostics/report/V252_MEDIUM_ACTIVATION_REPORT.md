# V252 Medium Activation Report

Local diagnostic update for the pp 13 TeV X-SCAPE/JETSCAPE medium-activation blocker.

## Scope

This pass only diagnosed and fixed why MATTER saw zero-temperature hydro cells in the accepted medium smoke run. It did not tune qhat, change medium strength, change sqrt(s), enable hydro reuse, change pThat slicing, shrink the MUSIC grid, or modify analysis plots.

## Files Read

- `src/hydro/MusicWrapper.cc`
- `src/hydro/MusicWrapper.h`
- `external_packages/music/src/HydroinfoMUSIC.cpp`
- `external_packages/music/src/HydroinfoMUSIC.h`
- `external_packages/music/src/music.cpp`
- `external_packages/music/src/music.h`
- `src/framework/JetScapeSignalManager.cc`
- `src/framework/JetScapeSignalManager.h`
- `src/framework/FluidEvolutionHistory.cc`
- `src/framework/FluidEvolutionHistory.h`
- `src/jet/Matter.cc`
- `src/jet/Matter.h`
- `local_v251_medium_diagnostics/scripts/run_local_smoke.sh`

## Source Files Changed

These are original X-SCAPE/JETSCAPE source files:

- `src/hydro/MusicWrapper.cc`
- `src/hydro/MusicWrapper.h`
- `src/jet/Matter.cc`
- `src/jet/Matter.h`

No qhat, hydro parameter, collision-energy, or medium-strength values were changed.

## Patch Files

- `local_v251_medium_diagnostics/patches/v252_medium_activation_MusicWrapper.patch`
- `local_v251_medium_diagnostics/patches/v252_medium_activation_MatterQA.patch`
- `local_v251_medium_diagnostics/patches/v252_medium_activation_combined.patch`

## Why MATTER Saw T=0 Before

The medium XML had MATTER in medium mode and MATTER made hydro queries, but the framework hydro history was empty for the 3D-Glauber string-source pp workflow.

The relevant path is:

- `JetScapeSignalManager::ConnectGetHydroCellSignal()` connects MATTER hydro queries to `FluidDynamics::GetHydroCell()`.
- For this executable, MATTER reaches `MpiMusic::GetHydroInfo()`.
- `MpiMusic::GetHydroInfo()` can query the JETSCAPE `FluidEvolutionHistory` copy or fall back to live MUSIC memory.
- In `MpiMusic::EvolveHydro()`, `PassHydroEvolutionHistoryToFramework()` was only called when `!has_source_terms`.
- This workflow uses `InitialProfile=13`, where the pp 3D-Glauber strings are source terms. The completed MUSIC evolution therefore was not copied into `bulk_info`.
- MATTER fell back to live MUSIC memory. In this workflow that path produced zero active temperatures for MATTER, consistent with the previous QA showing many queries but `temperature_max = 0`.

After enabling the copy for `InitialProfile=13/131`, a second metadata problem appeared: the copied history had `neta=1` but `boost_invariant=false`, so `FluidEvolutionHistory::CheckInRange()` rejected the eta coordinate for essentially every MATTER query. The fix treats a one-bin eta history as eta-collapsed for interpolation.

## Exact Code Changes

`src/hydro/MusicWrapper.cc` and `src/hydro/MusicWrapper.h`:

- Allow `PassHydroEvolutionHistoryToFramework()` for `InitialProfile=13` and `InitialProfile=131` even when source terms exist.
- Preserve the old skip behavior for other source-term workflows and log a warning.
- Route `GetHydroInfo()` to JETSCAPE `bulk_info` when copied history exists, otherwise fall back to MUSIC memory only when configured.
- Fix y-grid metadata forwarding to use MUSIC y getters.
- Treat `neta <= 1` copied histories as eta-collapsed/boost-invariant for framework interpolation.
- Add local QA files:
  - `medium_activation_hydro_history_QA.txt`
  - `medium_activation_hydro_query_path_QA.txt`
  - `medium_activation_hydro_query_samples.txt`

`src/jet/Matter.cc` and `src/jet/Matter.h`:

- Add MATTER query QA counters and first-query samples.
- Classify positive-T, above-Tc, zero-T, outside-light-cone, and post-start zero-T queries.
- Leave qhat formulas and shower physics unchanged.

## Build And Smoke Test

Build command:

```bash
docker exec xscape_mac bash -lc 'cd /home/jetscape-user/X-SCAPE/build && make -j18 PythiaIsrMUSIC'
```

Smoke command:

```bash
docker exec xscape_mac bash -lc 'cd /home/jetscape-user/X-SCAPE && ./local_v251_medium_diagnostics/scripts/run_local_smoke.sh'
```

Smoke result:

```text
[retry] vacuum_pthat30_50_1evt_seed251000000 attempt=1 seed=251000001 zero_surface_retry,0
[ok] vacuum_pthat30_50_1evt_seed251000000 attempt=2 seed=251007920
[retry] medium_default_pthat30_50_1evt_seed251000000 attempt=1 seed=251000001 zero_surface_retry,0
[ok] medium_default_pthat30_50_1evt_seed251000000 attempt=2 seed=251007920
```

This preserves deterministic seed retry and does not use hydro reuse.

## Accepted Medium Event

Accepted medium attempt:

```text
local_v251_medium_diagnostics/run_outputs/docker_smoke/medium_default_pthat30_50_1evt_seed251000000/attempt_002
```

Seed and event:

```text
seed = 251007920
pThat = 30-50
Npart = 2
Ncoll = 1
Nstrings = 1
b = 2.3185 fm
```

## Hydro History QA

Copied MUSIC history now exists in JETSCAPE:

```text
cells = 740000
ntau = 74
nx = 100
ny = 100
neta = 1
tau0 = 0.48
dtau = 0.02
tau_max = 1.94
temperature_min_GeV = 0.000694586
temperature_mean_GeV = 0.00614307
temperature_max_GeV = 0.206891
cells_T_gt_0 = 740000
cells_T_gt_0p155 = 1263
cells_T_gt_0p160 = 861
```

Framework query path QA:

```text
framework_queries = 805000
music_fallback_queries = 0
no_framework_history_queries = 0
before_tau0_queries = 106485
after_tau_max_queries = 401848
outside_xy_queries = 1725
outside_eta_queries = 0
inside_range_queries = 295629
inside_range_T_gt_0 = 295629
inside_range_T_ge_0p155 = 96670
inside_range_T_ge_0p160 = 75608
```

This shows MATTER now reaches the copied JETSCAPE hydro history, not stale MUSIC fallback memory.

## MATTER QA

The accepted medium run now has nonzero above-Tc MATTER hydro queries. Multiple MATTER QA blocks are written because multiple MATTER objects/paths write their destructors. Representative blocks:

```text
queries = 75651
queries_T_ge_Tc = 11044
queries_T_gt_0 = 56230
fraction_T_ge_Tc = 0.145986
temperature_max_GeV = 0.185594
```

```text
queries = 207497
queries_T_ge_Tc = 43275
queries_T_gt_0 = 151873
fraction_T_ge_Tc = 0.208557
temperature_max_GeV = 0.181882
```

The medium-activation blocker is therefore fixed for the accepted 1-event pThat 30-50 smoke event.

## Important Caveats

- Many queries are before hydro tau0 or after hydro tau max. This was counted, not hidden or clamped.
- No tau clamping was introduced.
- This proves the hydro-history plumbing for the accepted seed. It does not by itself establish a final physics effect or justify any qhat scan.
- The one-bin eta handling is appropriate for this copied single-eta history. A true 3D eta-resolved production history should be checked separately and should not rely on this as a substitute for correct eta metadata.

## Files Preserved For QA

Compact accepted QA/log files are copied to:

```text
local_v251_medium_diagnostics/qa/medium_activation/
local_v251_medium_diagnostics/logs/medium_activation/
```

Included files:

- `medium_activation_hydro_history_QA.txt`
- `medium_activation_hydro_query_path_QA.txt`
- `medium_activation_hydro_query_samples.txt`
- `medium_hydro_query_QA.txt`
- `medium_hydro_query_samples.txt`
- `events_summary.dat`
- `summary.log`
- `seed_launches.csv`
- `attempt.log`

## WSU Grid Port Recommendation

Port the source patches only after reviewing them against the exact WSU checkout:

- `v252_medium_activation_MusicWrapper.patch`
- `v252_medium_activation_MatterQA.patch`

The MusicWrapper patch is the required fix. The MATTER patch is diagnostic QA and can remain local unless the grid run should also emit hydro-query QA.

Safe-to-port reasons:

- It does not alter qhat or medium-strength values.
- It does not enable hydro reuse.
- It preserves sqrt(s)=13 TeV in the workflow.
- It is constrained to copying completed MUSIC history for `InitialProfile=13/131`, the pp string-source path needed by this workflow.

Do not copy large local `run_outputs/` directories to grid.
