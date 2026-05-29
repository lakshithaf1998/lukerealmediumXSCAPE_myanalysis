# grid XML paper rapidity-loss patch v10.11

This patch updates only the two Wayne-grid realistic pp XML templates:

- `config/jetscape_user_pp_realistic_vac_grid.xml`
- `config/jetscape_user_pp_realistic_medium_grid.xml`

Change:
- added `<ylossParam4At6>2.15</ylossParam4At6>`
- added `<ylossParam4At10>2.15</ylossParam4At10>`

Reason:
- restores the full MCGlauber rapidity-loss parameter set used by the 2024 paper XML.
- no rebuild is required because this is an XML/config-only patch.
