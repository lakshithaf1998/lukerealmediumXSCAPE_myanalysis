# v10.12 MCGlauber XML cleanup patch

This patch updates only the two grid XML templates:

- `config/jetscape_user_pp_realistic_vac_grid.xml`
- `config/jetscape_user_pp_realistic_medium_grid.xml`

## Purpose

Remove XML-level MCGlauber overrides that are harder to defend against the 2024 paper XML:

- removed `b_min`
- removed `b_max`
- removed `N_sea_partons`
- removed `useQuarks`

The required workflow-control tag `generateOnlyPositions=1` is retained. The 1000-trial local A/B test showed removing `generateOnlyPositions=1` produced 0 valid events for this PythiaIsrMUSIC + MCGlauber + MUSIC + iSS workflow.

## Input files

No input-file update is required in this patch. `myanalysis/mcglauber.input` remains the place where fallback/default MCGlauber values such as `b_min`, `b_max`, and `useQuarks` are controlled.

## No rebuild required

This is an XML-only patch. No C++ rebuild is required.
