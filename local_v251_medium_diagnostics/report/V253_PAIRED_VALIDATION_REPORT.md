# V253 Paired Validation Report

Local validation of the v252 MusicWrapper medium-activation fix for pp 13 TeV X-SCAPE/JETSCAPE. This pass did not tune qhat, Q0, `hydro_Tc`, medium strength, b range, MUSIC grid, or sqrt(s), and did not use hydro reuse.

## Inputs And Patch State

Confirmed patch files are present:

- `local_v251_medium_diagnostics/patches/v252_medium_activation_MusicWrapper.patch`
- `local_v251_medium_diagnostics/patches/v252_medium_activation_MatterQA.patch`
- `local_v251_medium_diagnostics/patches/v252_medium_activation_combined.patch`

Confirmed source behavior:

- `src/hydro/MusicWrapper.cc`: `PassHydroEvolutionHistoryToFramework()` runs for `InitialProfile=13/131` string-source workflows even when source terms exist.
- `src/hydro/MusicWrapper.cc`: copied histories with `neta <= 1` are treated as eta-collapsed/boost-invariant for JETSCAPE interpolation.
- `src/jet/Matter.cc`: MATTER hydro-query QA still records positive-T and above-Tc query counts.

Rebuild command:

```bash
docker exec xscape_mac bash -lc 'cd /home/jetscape-user/X-SCAPE/build && make -j18 PythiaIsrMUSIC'
```

Build completed successfully.

## New Local Files

- `local_v251_medium_diagnostics/scripts/run_v253_paired_validation.sh`
- `local_v251_medium_diagnostics/scripts/v253_compare_outputs.py`
- `local_v251_medium_diagnostics/qa/v253_paired_validation/paired_event_summary.csv`
- `local_v251_medium_diagnostics/qa/v253_paired_validation/paired_comparison_summary.csv`
- `local_v251_medium_diagnostics/qa/v253_paired_validation/medium_activation_summary.csv`
- `local_v251_medium_diagnostics/logs/v253_paired_validation/summary.log`
- `local_v251_medium_diagnostics/logs/v253_paired_validation/seed_launches.csv`

The new scripts are local workflow tooling only. No new upstream X-SCAPE/JETSCAPE source file was changed in this v253 pass.

## Run Command

```bash
docker exec xscape_mac bash -lc 'cd /home/jetscape-user/X-SCAPE && ./local_v251_medium_diagnostics/scripts/run_v253_paired_validation.sh'
```

The runner uses paired seeds, 1 event/XML, no hydro reuse, and deterministic retry. A pair is accepted only when both vacuum and medium complete for the same seed.

## Accepted Sample

Target:

- pThat 30-50: 10 accepted paired events
- pThat 80-120: 5 accepted paired events

Result:

- pThat 30-50: 10/10 accepted paired events
- pThat 80-120: 3/5 accepted paired events
- Total: 13 accepted paired events

The two pThat 80-120 misses exhausted the configured 8 attempts/pair because the vacuum side repeatedly hit zero-string/zero-surface retry classifications. No retry was hidden; all attempted seeds are in `seed_launches.csv`.

## Medium Activation Summary

Across all 13 accepted medium events:

- `music_fallback_queries = 0` for every accepted event.
- `framework_queries > 0` for every accepted event.
- Hydro histories were copied for every accepted event.
- Hydro max temperature range: `0.161488` to `0.275557 GeV`.
- Hydro cells with `T > 0.160 GeV` range: `2` to `3399`.

pThat 30-50:

- 10 accepted medium events.
- 10/10 used the JETSCAPE framework history, not MUSIC fallback.
- 8/10 had MATTER samples with `T >= hydro_Tc`.
- 2/10 had hot hydro histories but no MATTER query with `T >= hydro_Tc`; these were marginal events with only 2 hydro cells above 160 MeV and MATTER interpolation max below Tc.

pThat 80-120:

- 3 accepted medium events.
- 3/3 used the JETSCAPE framework history, not MUSIC fallback.
- 3/3 had MATTER samples with `T >= hydro_Tc`.

The two pThat 30-50 no-above-Tc rows were:

```text
pthat30_50 pair 4 seed 253330501: hydro Tmax 0.161706, cells_T_gt_0p160 2, MATTER Tmax 0.15263, queries_T_ge_Tc 0
pthat30_50 pair 5 seed 253438420: hydro Tmax 0.161488, cells_T_gt_0p160 2, MATTER Tmax 0.152425, queries_T_ge_Tc 0
```

This is not the v252 blocker recurring. The framework hydro path is active; these two accepted pp events are simply too marginal along the sampled MATTER paths to cross `hydro_Tc`.

## Output Difference Summary

Across the 13 accepted paired seeds:

- Hadron output byte-identical pairs: 0/13
- Parton output byte-identical pairs: 0/13
- Charged hadron count difference range, medium minus vacuum: `-6` to `24`
- Charged scalar sum-pT difference range, medium minus vacuum: `-22.7374` to `66.6415 GeV`
- Leading charged hadron pT difference range, medium minus vacuum: `-12.2366` to `7.09143 GeV`

These are tiny-statistics QA differences only. They should not be interpreted as a physics conclusion.

## CSV Outputs

`paired_event_summary.csv` contains one row per accepted mode/event:

- pThat bin
- seed
- mode
- Nstrings and b
- final-state hadron and parton file sizes/hashes
- final hadron count
- charged hadron count
- charged scalar sum pT
- leading charged pT
- rough full/charged jet input counts

`paired_comparison_summary.csv` contains one row per accepted pair:

- byte-identical checks for hadron and parton files
- medium-minus-vacuum count and scalar-pT differences

`medium_activation_summary.csv` contains one row per accepted medium event:

- seed and pThat bin
- hydro history cells
- hydro Tmax
- cells above 160 MeV
- framework/MUSIC fallback query counts
- inside-range and above-160 query counts
- aggregated MATTER query and above-Tc counts

## 10-Event/XML Reset Test

The optional 10-event/XML reset test was not run in this v253 pass. The validation target was the paired 1-event/XML sample, and pThat 80-120 already exhausted retry budgets for two requested pairs. Keep 1 event/XML as the recommended local/grid-safe mode until a separate reset test proves hydro, iSS, SMASH, and MATTER reset cleanly across multiple events in one XML.

## Recommendation

The v252 MusicWrapper patch is safe to prepare for WSU grid review:

- It keeps sqrt(s)=13 TeV.
- It does not use hydro reuse.
- It does not alter qhat, Q0, `hydro_Tc`, or medium strength.
- It fixes the hydro-history path needed for `InitialProfile=13/131` pp string-source workflows.
- It was validated beyond a single accepted seed: 13 accepted paired events all used framework hydro history with zero MUSIC fallback queries.

Do not use this small sample to claim a physical jet-quenching effect. It is a workflow and plumbing validation sample.
