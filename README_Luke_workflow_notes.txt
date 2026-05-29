==============================
Luke local realistic pp workflow v10.7 notes
==============================
Version: v10.7
Updated: 2026-05-28

Purpose
-------
This `myanalysis/` folder is the current working local realistic pp vacuum/medium smoke-test workflow for the Luke/Codex iMATTER + MCGlauber + MUSIC + iSS chain in X-SCAPE.

This package is intended to be unpacked into the X-SCAPE repository root as `myanalysis/`.

v10.7 changes
-------------
- Uses the 2024 paper MUSIC timing/input baseline after the v10.6 A/B test showed no degradation relative to the local-stability timing.
- `music_input_Luke` now uses the paper input values:
  - `Initial_time_tau_0 0.6`
  - `Delta_Tau 0.02`
  - `average_surface_over_this_many_time_steps 5`
- The vac and medium XML MUSIC override tags were also synchronized so they do not override the paper timing:
  - `<Initial_time_tau_0>0.6</Initial_time_tau_0>`
  - `<average_surface_over_this_many_time_steps>5</average_surface_over_this_many_time_steps>`
- `jetscape_main_Luke.xml` defaults were synchronized to the same paper timing.
- Removed the non-paper `freeze_out_tau_start_max` line from `music_input_Luke` because the v10.6 A/B test showed no effect with or without it.
- Kept the successful v10.5 retry driver that rejects stochastic pp zero-surface/iSS-empty attempts and tries new seeds until it collects accepted events.

13 TeV analysis settings preserved
----------------------------------
Applied to both `jetscape_user_pp_realistic_vac_Luke.xml` and `jetscape_user_pp_realistic_medium_Luke.xml`:

- `nEvents = 1` per XML.
- `setReuseHydro = false`, `nReuseHydro = 1`.
- hard `PythiaGun/eCM = 13000.0`.
- hard `pTHatMin = 30.0`, `pTHatMax = 3000.0`.
- `softMomentumCutoff = 2.0`.
- `JetScapeWriterAscii = off`.
- `JetScapeWriterFinalStateHadronsAscii = on`.
- `JetHadronization/eCMforHadronization = 6500.0`.
- Kept paper/Luke MATTER settings: `Q0=2.0`, `vir_factor=0.25`, `maxT=50`, `recoil_on=0`, `broadening_on=0`.
- Kept paper/Luke PYTHIA bias block, including `MultipartonInteractions:pTmin = 8.0`. This was not changed to 30 because it is not the same as the primary hard `pTHatMin`.

Applied to shared local files:

- `mcglauber.input`: `roots 13000.`
- `jetscape_main_Luke.xml`: defaults use `nEvents=1`, no hydro reuse, final-state hadrons on, MCGlauber `sqrts=13000`, default PythiaGun `eCM=13000`, `eCMforHadronization=6500`, and paper MUSIC timing.

Vac vs medium XML difference kept intentionally
-----------------------------------------------
The vacuum and medium XMLs share the same hard-process energy, pThat range, hadron output settings, MCGlauber+MUSIC+iSS soft chain, and hadronization settings. The controlled difference is the hard-shower treatment:

- Vacuum XML:
  - `Matter/in_vac = 1`
  - hydro memory output remains off for the hard shower path
  - MATTER evolves the hard shower as vacuum-like, so the hard partons do not use the local MUSIC medium fields.

- Medium XML:
  - `Matter/in_vac = 0`
  - `QhatParametrizationType = 1`
  - `hydro_Tc = 0.16`
  - MUSIC evolution memory output is enabled so MATTER can query local hydro cells.
  - MATTER can use the local temperature/flow history from MUSIC to apply medium-dependent shower evolution.

This means the medium run is not just a different output label: the medium XML gives MATTER access to the dynamically generated pp hydro background and turns on the medium-dependent mode. Whether a specific final-state hadron observable shows a large difference still must be checked with statistics and with the hadronization/status treatment.

Known stochastic pp zero-surface behavior
-----------------------------------------
Some pp MCGlauber+MUSIC events produce no usable freeze-out surface. The typical failure is:

- `total number of cells: 0`
- followed by iSS reporting `Every line should have 36 variables, but we got -1 variables in total`.

The v10.5/v10.7 run driver treats this as a rejected stochastic pp attempt, preserves the failed attempt logs, and retries with a new seed until accepted-event targets are reached or the maximum retry count is exhausted.

Latest run script
-----------------
Use:

- `run_local_pp_realistic_pair_10x.sh`

Default behavior:

- Runs until it collects 10 accepted vacuum events and 10 accepted medium events.
- Every XML is one event with a unique seed and unique output prefix.
- Runs sequentially.
- Uses Docker container `xscape_mac` automatically when the host `build/PythiaIsrMUSIC` is an ELF/Linux binary on macOS.
- Stages each attempt in its own folder under `run_logs/`.
- Uses `myanalysis/EOS` plus `build/tables` and `build/iSS_tables` through symlinks.
- Compiles `tools/cluster_check.cpp` with `fastjet-config` when available.
- Clusters every nonempty final-state hadron file with anti-kT R=0.4 and records the top jets.
- Creates a return tarball under `diagnostic_zips/`.

Output diagnostics include:

- `attempt_summary.tsv`
- `accepted_summary.tsv`
- `run_driver.log`
- `terminal_transcript.log`
- per-attempt `attempt.log`
- per-attempt XMLs
- per-attempt `cluster_check.log` when hadron files are produced

ISS zero-surface/source-term fixes preserved for provenance
-----------------------------------------------------------
Active source files are copied into:

- `active_source_files/src/hydro/MusicWrapper.cc`
- `active_source_files/external_packages/music/src/evolve.cpp`

Replacing `myanalysis/` alone does not rebuild X-SCAPE. The run script checks whether the active source copies match the files currently in the X-SCAPE source tree and writes the result into the diagnostic tarball.

Core source fixes preserved:

- `MusicWrapper.cc`: handles InitialProfile 13/131 QCD string source terms before the generic no-pre-equilibrium path, then falls back to direct MUSIC hydro queries when JETSCAPE `bulk_info` is empty but MUSIC evolution memory output is enabled.
- `evolve.cpp`: protects against false all-frozen zero-intersection Cornelius outcomes and adds equal-tau fallback surface writing when a no-surface case would otherwise break iSS.

Reference inputs kept
---------------------
The original paper inputs are preserved under `reference_inputs/`:

- `jetscape_user_iMATTERMCGlauberMUSIC_2024_paper_original.xml`
- `music_input_2024_paper_original`
- `iSS_parameters_2024_paper_original.dat`
- `mcglauber_input_2024_paper_original`

GitHub helper
-------------
A helper script is included at:

- `tools/create_github_repo_from_myanalysis.sh`

It creates a temporary standalone repository containing the contents of `myanalysis/` and pushes it using the GitHub CLI. It requires `gh auth login` to already be completed.
