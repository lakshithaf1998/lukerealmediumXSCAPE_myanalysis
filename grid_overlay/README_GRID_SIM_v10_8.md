# X-SCAPE realistic pp grid simulation overlay v10.8

This overlay updates only the simulation layer for the realistic pp PythiaIsrMUSIC smoke test on the Wayne State grid.

## Files installed into X-SCAPE root

- `jetscape.ini` — v6.0 realistic pp defaults for the first 25-job smoke test.
- `submit_sliced_sim.sh` — v8.3 manager compatibility header update; manager behavior is otherwise preserved.
- `submit_jetscape_sliced.slurm` — v6.9 worker with staged PythiaIsrMUSIC runtime and internal retry loop.
- `config/jetscape_main.xml` — Luke main XML renamed for grid use.
- `config/jetscape_user_pp_realistic_vac_grid.xml` — sliced-grid vacuum template.
- `config/jetscape_user_pp_realistic_medium_grid.xml` — sliced-grid medium template.
- `myanalysis/mcglauber.input` — 13 TeV input (`roots 13000.`).
- `myanalysis/music_input_Luke` — paper-timing MUSIC input (`tau0=0.6`, `Delta_Tau=0.02`, `average_surface=5`).
- `myanalysis/iSS_parameters.dat` — validated iSS parameters.
- `myanalysis/EOS/` — finite-muB EOS files needed by EOS 14.

## Default smoke-test setup

The default `jetscape.ini` is configured for the vacuum run:

- `RUN_TAG="pprealistic_vac_25test"`
- `XML_TEMPLATE="jetscape_user_pp_realistic_vac_grid.xml"`
- `EXE_NAME="PythiaIsrMUSIC"`
- `NUM_EVENTS=1`
- `JOBS=(25)`
- `Multiplier=1`
- `MultiSimEnabled=0`
- `PT_LO=(30)`
- `PT_HI=(3000)`
- `BASE_SEED=13000000`

The worker writes the same canonical downstream file name as before:

`$HOME/xscape_runs/<RUN_TAG>/sim/30-3000/<SIM_BATCH_ID>/job<TASK>_final_state_hadrons.dat`

This keeps analysis and merge scripts compatible with the previous sliced workflow.

## To switch to medium

Edit only these `jetscape.ini` values:

```bash
RUN_TAG="pprealistic_medium_25test"
XML_TEMPLATE="jetscape_user_pp_realistic_medium_grid.xml"
RealisticPPMode="medium"
BASE_SEED=23000000
```

Keep `NUM_EVENTS=1`, `JOBS=(25)`, and `Multiplier=1` until the smoke test passes.

## Run on Wayne grid

From the X-SCAPE root:

```bash
cd /wsu/home/hv/hv04/hv0429/xscape
bash submit_sliced_sim.sh
```

The manager will submit at most 25 worker jobs for the smoke test. Later, after validation, increase `JOBS=(1000)` but do not exceed 1000 active primary-QOS jobs at once.

## Retry behavior

Each worker internally retries failed PythiaIsrMUSIC attempts up to `PythiaIsrMaxAttemptsPerTask=30`, using fresh seeds. This is intended for stochastic pp hydro/iSS zero-surface failures like:

- `total number of cells: 0`
- `Every line should have 36 variables, but we got -1 variables in total`

Only a successful attempt with a nonempty final-state hadron file is installed as the canonical `job<TASK>_final_state_hadrons.dat`.
