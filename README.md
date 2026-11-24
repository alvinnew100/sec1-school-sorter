# Sec 1 School Shortlist Sorter

A one-page planner for Singapore's Secondary 1 posting. Enter a PSLE score, filter schools (gender, zone, town, mother tongue taught), see four years of cut-off points alongside an estimated next cut-off, then build and test a list of 6 choices.

**Live:** https://alvinnew100.github.io/sec1-school-sorter/

## What it does
- 2023–2026 intake cut-offs for 139 schools (IP, G3, G2, G1 and affiliated)
- An estimated 2027 cut-off range, with a chance-of-admission for each school
- A simulation of your 6 choices, showing where you'd likely be posted. The tie-breaker order (citizenship → choice rank → ballot) is applied, and cut-offs move together across schools
- Checks against MOE guidance: uses all 6 choices, includes 2–3 safer schools, affiliated school placed 1st
- JC filter: affiliated JC (from MOE SchoolFinder) and where each IP programme continues
- Mother tongue filter (data.gov.sg), with SAP schools hidden for non-Chinese mother tongues
- Share link and copy-as-text

## Data and method
- Cut-offs: sgschooling.com (2023, 2025, 2026 intakes) and skoolopedia.com (2024 intake), in `tools/raw/`
- School details and mother tongues offered: data.gov.sg *General Information of Schools*
- `tools/build.py` merges the data, backtests several prediction rules on 2025 and 2026, and writes `data.js`. "Same as last year" had the lowest error, so estimates are centred on the latest cut-off. The spread comes from past errors, split into a year-wide component and a per-school component.

Rebuild after new cut-offs come out: add `tools/raw/cop2027.csv`, extend `YEARS` in `build.py`, then run `python3 tools/build.py`.

Not an MOE tool. Estimates are not guarantees.
