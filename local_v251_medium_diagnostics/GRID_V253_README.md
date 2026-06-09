# GRID V253 README

Grid-review package for the validated pp 13 TeV v253 medium-activation workflow. This package is for WSU smoke review only. Do not launch 1M-event production from it yet.

## Validated Context

`report/V253_PAIRED_VALIDATION_REPORT.md` validated the v252 MusicWrapper medium-activation fix across 13 accepted paired local events. All accepted medium events queried the JETSCAPE framework hydro history with zero MUSIC fallback queries. Vacuum and medium final-state parton/hadron outputs were not byte-identical.

## Changed Original X-SCAPE/JETSCAPE Source Files

- `src/hydro/MusicWrapper.cc`
  - Enables `PassHydroEvolutionHistoryToFramework()` for `InitialProfile=13/131` string-source pp workflows even when source terms exist.
  - Treats copied histories with `neta <= 1` as eta-collapsed/boost-invariant for framework interpolation.
  - Adds hydro-history and hydro-query path QA logs.
- `src/hydro/MusicWrapper.h`
  - Adds local hydro-query path QA counters and method declarations.
- `src/jet/Matter.cc`
  - Adds MATTER hydro-query QA counters for positive-T and above-Tc checks.
- `src/jet/Matter.h`
  - Adds local MATTER QA counters and method declarations.
- `external_packages/music/src/music.h`
  - Already contains required y-grid forwarding getters: `get_ny()`, `get_hydro_y_max()`, and `get_hydro_dy()`.

## Changed Workflow Files

- `config/jetscape_user_pp_realistic_vac_grid.xml`
  - Grid template copied from the v250 workflow reference and updated with explicit `<surface_in_memory>0</surface_in_memory>`.
- `config/jetscape_user_pp_realistic_medium_grid.xml`
  - Grid template copied from the v250 workflow reference and updated with explicit `<surface_in_memory>0</surface_in_memory>`.
- `myanalysis/music_input_Luke`
  - Confirmed pp/Rhob consistency: `Include_Rhob_Yes_1_No_0 0`.
- `myanalysis/iSS_parameters.dat`
  - Confirmed consistent with MUSIC: `turn_on_rhob = 0`.
- `ini_configurations/jetscape_v253_grid_smoke_vacuum.ini`
  - Tiny smoke INI: pThat 30-50 and 80-120, 20 jobs per slice, 1 event/XML.
- `ini_configurations/jetscape_v253_grid_smoke_medium.ini`
  - Paired tiny smoke INI with the same `BASE_SEED=253900000`.

## Exact Grid Rebuild Command

Run this on the grid checkout after applying the source patches:

```bash
cd ~/research/xscape/X-SCAPE/build
make -j18 PythiaIsrMUSIC
```

Adjust `-j18` downward only if the grid login/build node policy requires fewer cores.

## Exact Tiny Smoke Run Commands

From the grid workflow directory that contains `submit_sliced_sim.sh`, `config/`, `myanalysis/`, and `ini_configurations/`:

```bash
INI_PATH="$PWD/ini_configurations/jetscape_v253_grid_smoke_vacuum.ini" ./submit_sliced_sim.sh
```

```bash
INI_PATH="$PWD/ini_configurations/jetscape_v253_grid_smoke_medium.ini" ./submit_sliced_sim.sh
```

The two smoke INIs intentionally use:

```bash
NUM_EVENTS=1
PT_LO=(30 80)
PT_HI=(50 120)
JOBS=(20 20)
Multiplier=1
MaxActiveJobs=1000
PythiaIsrMaxAttemptsPerTask=30
PythiaIsrRetrySeedStride=7919
BASE_SEED=253900000
```

## Warnings

- Do not run 1M events yet.
- Keep `NUM_EVENTS=1`. The 10-events/XML reset path has not been validated for grid production.
- Do not enable hydro reuse.
- Do not tune qhat, Q0, `hydro_Tc`, medium strength, b range, MUSIC grid, or sqrt(s) for this review step.
- Do not treat pure PYTHIA controls, diagnostic qhat/Tc XMLs, bmax2 files, or 12 fm MUSIC-grid diagnostics as production.
- Do not copy local `run_outputs/` to WSU grid.

## Safe To Copy For Grid Review

- The four source patches/files listed above.
- `config/jetscape_user_pp_realistic_vac_grid.xml`
- `config/jetscape_user_pp_realistic_medium_grid.xml`
- `myanalysis/music_input_Luke`
- `myanalysis/iSS_parameters.dat`
- `ini_configurations/jetscape_v253_grid_smoke_vacuum.ini`
- `ini_configurations/jetscape_v253_grid_smoke_medium.ini`
- `report/V252_MEDIUM_ACTIVATION_REPORT.md`
- `report/V253_PAIRED_VALIDATION_REPORT.md`
- `patches/v252_medium_activation_MusicWrapper.patch`
- `patches/v252_medium_activation_MatterQA.patch`
- `patches/v252_medium_activation_combined.patch`

## Not For Grid Production Copy

- `run_outputs/`
- `generated_xml/medium_Tc*_diagnostic_*`
- `generated_xml/medium_Q0_dynamic_diagnostic_*`
- `generated_xml/*_10evt_*`
- `generated_xml/pure_pythia_*`
- `myanalysis/mcglauber_bmax2_diagnostic.input`
- `myanalysis/music_input_grid12_diagnostic`
