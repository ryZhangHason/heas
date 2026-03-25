# BibTeX Final Verification Report

**Generated:** March 25, 2026

---

## Coverage Summary

| Metric | Count |
|--------|-------|
| **Total entries** | 35 |
| **Entries WITH doi** | 23 |
| **Entries WITH url (but no doi)** | 9 |
| **Entries missing BOTH doi and url** | 3 |

---

## Remaining Issues (action required before submission)

| Key | Type | Issue | Action Needed |
|-----|------|-------|---------------|
| `helsgott2020abm` | inproceedings | **PHANTOM REFERENCE - NOT CITED** | Safe to delete. Entry has exact title match to Macal & North 2010 (legitimate article with DOI), no pages/doi, not used anywhere in paper. This is a duplicate/orphan entry. |
| `capri2023transport` | article | **MISSING DOI/URL - ACTIVELY CITED** | CRITICAL: This entry is cited twice in paper (lines appear in HEAS_WSC_V5_revised.tex). Has complete publication metadata (journal: Transportation Research Procedia, vol. 69, pp. 613-620, 2023) but lacks DOI. Locatable via publisher. Recommend: acquire DOI from CrossRef or Transportation Research Procedia. |
| `volterra1926variazioni` | article | **MISSING DOI/URL - HISTORICAL** | Entry has note "no DOI available for 1926 publication" — acceptable for classic works. Has complete publication metadata (journal, volume, pages). Not a concern. |

---

## Coverage by Entry (Complete Inventory)

### WITH DOI (23 entries)
- `akiba2019optuna` — inproceedings
- `biscani2020pagmo` — article
- `bonabeau2002abm` — article
- `byrd2020abides` — inproceedings
- `collier2022repast4py` — inproceedings
- `deb2002nsga2` — article
- `fu2002optimization` — article
- `goldsman1994ranking` — inproceedings
- `grimm2006odd` — article
- `hanski1991single` — article
- `hunter2022multiobjective` — inproceedings
- `kazil2020mesa` — inproceedings
- `kendall1938new` — article
- `kwakkel2017workbench` — article
- `macal2010tutorial` — article
- `pangallo2019best` — article
- `pasupathy2011simopt` — inproceedings
- `railsback2006agent` — article
- `rand2011agent` — article
- `tesfatsion2006ace` — incollection
- `wall2016agent` — article
- `zheng2022aieconomist` — article
- `zitzler1998hypervolume` — article

### WITH URL (no DOI) (9 entries)
- `bakshy2018ae` — inproceedings (URL in note field)
- `efron1994bootstrap` — book
- `fortin2012deap` — article
- `hong2009brief` — inproceedings
- `lotka1925elements` — book
- `mesa2025v3` — misc
- `optquest2007` — misc
- `wilensky1997wolfsheep` — misc
- `wilensky1999netlogo` — misc

---

## Citation Status Check

**Phantom Reference Alert:**
- ✗ `helsgott2020abm` — **NOT CITED** in paper. Orphan entry, safe to remove.

**Actively Cited Entries Missing Identifiers:**
- ✓ `capri2023transport` — **CITED TWICE** in paper:
  - Line in HEAS_WSC_V5_revised.tex: "workflows~\cite{pangallo2019best,capri2023transport}."
  - Line in HEAS_WSC_V5_revised.tex: "code~\cite{pangallo2019best,capri2023transport,zheng2022aieconomist}."

---

## Duplicate/Fabricated Entry Investigation

**`helsgott2020abm` Findings:**

| Attribute | helsgott2020abm | macal2010tutorial |
|-----------|-----------------|-------------------|
| Title | "Tutorial on Agent-Based Modeling and Simulation" | "Tutorial on Agent-Based Modelling and Simulation" |
| Authors | Helsgott, Arnd and Macal, Charles M. | Macal, Charles M. and North, Michael J. |
| Year | 2020 | 2010 |
| Publication | Proceedings of 2020 WSC, IEEE Press | Journal of Simulation, vol. 4, no. 3, pp. 151-162 |
| Pages | **MISSING** | 151-162 |
| DOI | **MISSING** | 10.1057/jos.2010.3 |
| Status | **FLAGGED AS POTENTIALLY FABRICATED** | Legitimate, verified |

**Conclusion:** Same title, different year/author/venue. The `helsgott2020abm` entry lacks pages and DOI which would verify its existence. The 2010 Macal & North article is the canonical reference on ABM tutorials. **Recommendation: DELETE `helsgott2020abm`.**

---

## Publication Info Assessment

**`capri2023transport` — Sufficient for Location:**
- Journal: Transportation Research Procedia ✓
- Year: 2023 ✓
- Volume: 69 ✓
- Pages: 613–620 ✓
- Note: Conference identifier provided (AIIT 3rd International Conference on Transport Infrastructure and Systems, TIS ROMA 2022)
- **Assessment:** Entry is locatable via journal and volume even without DOI. However, **DOI should be acquired** since this is a recent (2023) conference proceedings paper and likely has one in CrossRef.

---

## Summary & Recommendations

### Before Submission:
1. **DELETE** `helsgott2020abm` — phantom/fabricated entry, not cited, potential duplicate of Macal 2010
2. **ACQUIRE DOI** for `capri2023transport` — actively cited, recent publication, likely indexed
3. **ACCEPT** `volterra1926variazioni` as-is — historical work, no modern DOI exists, complete metadata present

### Coverage Summary:
- **66% of entries have DOI** (23/35) — good coverage
- **26% have URL fallback** (9/35) — acceptable
- **9% still missing** (3/35) — but only 1 is problematic (capri); helsgott can be deleted; volterra is acceptable as historical

### Final Status:
✓ **Recommended for submission** after addressing the 2 priority issues above.

---

*Report prepared for WSC V4 submission quality assurance*
