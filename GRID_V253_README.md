# GRID V253 README

Grid-review entry point for the validated pp 13 TeV v253 medium-activation workflow. The workflow package lives under `local_v251_medium_diagnostics/`. This is for WSU smoke review only; do not launch 1M-event production from it yet.

## Validated Context

`local_v251_medium_diagnostics/report/V253_PAIRED_VALIDATION_REPORT.md` validated the v252 MusicWrapper medium-activation fix across 13 accepted paired local events. All accepted medium events queried the JETSCAPE framework hydro history with zero MUSIC fallback queries. Vacuum and medium final-state parton/hadron outputs were not byte-identical.

## Changed Original X-SCAPE/JETSCAPE Source Files

- `src/hydro/MusicWrapper.cc`
- `src/hydro/MusicWrapper.h`
- `src/jet/Matter.cc`
- `src/jet/Matter.h`

`external_packages/music/src/music.h` already contains the required forwarding getters: `get_ny()`, `get_hydro_y_max()`, and `get_hydro_dy()`.

## Changed Workflow Files

- `local_v251_medium_diagnostics/config/jetscape_user_pp_realistic_vac_grid.xml`
- `local_v251_medium_diagnostics/config/jetscape_user_pp_realistic_medium_grid.xml`
- `local_v251_medium_diagnostics/myanalysis/music_input_Luke`
- `local_v251_medium_diagnostics/myanalysis/iSS_parameters.dat`
- `local_v251_medium_diagnostics/ini_configurations/jetscape_v253_grid_smoke_vacuum.ini`
- `local_v251_medium_diagnostics/ini_configurations/jetscape_v253_grid_smoke_medium.ini`
- `local_v251_medium_diagnostics/GRID_V253_README.md`

## Exact Grid Rebuild Command

```bash
cd ~/research/xscape/X-SCAPE/build
make -j18 PythiaIsrMUSIC
```

## Exact Tiny Smoke Run Commands

After copying the workflow package contents to the WSU workflow directory that contains `submit_sliced_sim.sh`, `config/`, `myanalysis/`, and `ini_configurations/`:

```bash
INI_PATH="$PWD/ini_configurations/jetscape_v253_grid_smoke_vacuum.ini" ./submit_sliced_sim.sh
```

```bash
INI_PATH="$PWD/ini_configurations/jetscape_v253_grid_smoke_medium.ini" ./submit_sliced_sim.sh
```

## Required Smoke INI Settings

Both v253 smoke INIs use:

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
- Keep `NUM_EVENTS=1`; the 10-events/XML reset path is not grid-production validated.
- Do not enable hydro reuse.
- Do not tune qhat, Q0, `hydro_Tc`, medium strength, b range, MUSIC grid, or sqrt(s).
- Do not copy local `run_outputs/` to WSU grid.
