# WSC 2026 Paper BibTeX Audit Report

**Paper:** HEAS_WSC_V5_revised.tex
**References File:** references.bib
**Audit Date:** 2026-03-25

---

## SUMMARY TABLE

| Metric | Count |
|---|---|
| Total .bib entries | 35 |
| Entries with DOI | 0 |
| Entries with URL (direct) | 0 |
| Entries with URL (howpublished) | 2 |
| Entries missing both DOI and URL | 33 |
| Entries with author field issues | 4 |
| Entries with year issues | 0 |
| Dangling \cite{} keys (in .tex but not .bib) | 0 |
| Unused .bib entries (in .bib but not .tex) | 14 |
| Placeholder citations (\cite{TOCHECK}, etc.) | 0 |

---

## ENTRIES MISSING DOI AND URL

**Critical Issue:** 33 of 35 entries lack both DOI and URL fields. This is a major concern for reproducibility and reference validity in an academic publication.

| Key | First Author | Year | Entry Type |
|---|---|---|---|
| akiba2019optuna | Akiba, Takuya | 2019 | inproceedings |
| bakshy2018ae | Bakshy, Eytan | 2018 | inproceedings |
| biscani2020pagmo | Biscani, Francesco | 2020 | article |
| bonabeau2002abm | Bonabeau, Eric | 2002 | article |
| byrd2020abides | Byrd, David | 2020 | inproceedings |
| capri2023transport | Caprì, Salvatore | 2023 | article |
| collier2022repast4py | Collier, Nick | 2022 | inproceedings |
| deb2002nsga2 | Deb, Kalyanmoy | 2002 | article |
| efron1994bootstrap | Efron, Bradley | 1994 | book |
| fortin2012deap | Fortin, Félix-Antoine | 2012 | article |
| fu2002optimization | Fu, Michael C. | 2002 | article |
| goldsman1994ranking | Goldsman, David | 1994 | inproceedings |
| grimm2006odd | Grimm, Volker | 2006 | article |
| hanski1991single | Hanski, Ilkka | 1991 | article |
| helsgott2020abm | Helsgott, Arnd | 2020 | inproceedings |
| hong2009brief | Hong, L. Jeff | 2009 | inproceedings |
| hunter2022multiobjective | Hunter, Susan R. | 2022 | inproceedings |
| kazil2020mesa | Kazil, Jackie | 2020 | inproceedings |
| kendall1938new | Kendall, Maurice G. | 1938 | article |
| kwakkel2017workbench | Kwakkel, Jan H. | 2017 | article |
| lotka1925elements | Lotka, Alfred J. | 1925 | article |
| macal2010tutorial | Macal, Charles M. | 2010 | article |
| pangallo2019best | Pangallo, Marco | 2019 | article |
| pasupathy2011simopt | Pasupathy, Raghu | 2011 | inproceedings |
| railsback2006agent | Railsback, Steven F. | 2006 | article |
| rand2011agent | Rand, William | 2011 | article |
| tesfatsion2006ace | Tesfatsion, Leigh | 2006 | incollection |
| volterra1926variazioni | Volterra, Vito | 1926 | article |
| wall2016agent | Wall, Friederike | 2016 | article |
| wilensky1997wolfsheep | Wilensky, Uri | 1997 | misc |
| wilensky1999netlogo | Wilensky, Uri | 1999 | misc |
| zheng2022aieconomist | Zheng, Stephan | 2022 | article |
| zitzler1998hypervolume | Zitzler, Eckart | 1998 | article |

---

## AUTHOR FIELD ISSUES

**Issue:** 4 entries have mismatched or unclosed braces in the author field. These appear to be LaTeX encoding issues where accented characters are not properly closed.

| Key | Problem Description | Current Author Value |
|---|---|---|
| capri2023transport | Unclosed brace in author with accented character | `Caprì, Salvatore and ...` (raw: `Capr{\`\i`) |
| fortin2012deap | Unclosed brace in author with accented character | `Fortin, Félix-Antoine and ...` (raw: `Fortin, F{\'e`) |
| mesa2025v3 | Extra opening brace before corporate author | `{Project Mesa Contributors}` (raw: `{Project Mesa Contributors`) |
| optquest2007 | Extra opening brace before corporate author | `{OptTek Systems, Inc.}` (raw: `{OptTek Systems, Inc.`) |

**Note:** These entries appear complete when viewed in rendered form, but the LaTeX source has mismatched braces that may cause parsing issues in some tools.

---

## YEAR ISSUES

**Status:** No issues detected. All entries have valid 4-digit years.

---

## DANGLING CITATIONS

**Status:** No issues detected. All \cite{} keys used in the .tex file have corresponding entries in the .bib file.

All cited keys are present:
- efron1994bootstrap, fortin2012deap, akiba2019optuna, biscani2020pagmo
- fu2002optimization, hong2009brief
- goldsman1994ranking
- grimm2006odd, tesfatsion2006ace, bonabeau2002abm
- kendall1938new
- lotka1925elements, volterra1926variazioni
- macal2010tutorial, kazil2020mesa, wilensky1999netlogo
- pangallo2019best, capri2023transport, zheng2022aieconomist
- wilensky1997wolfsheep
- zitzler1998hypervolume

---

## PLACEHOLDER CITATIONS

**Status:** No placeholder citations detected. No instances of \cite{TOCHECK}, \cite{TODO}, \cite{FIXME}, etc.

---

## UNUSED BIB ENTRIES

14 entries are defined in references.bib but not cited anywhere in HEAS_WSC_V5_revised.tex. Consider removing these or adding citations:

| Key | Type | Year | First Author |
|---|---|---|---|
| bakshy2018ae | inproceedings | 2018 | Bakshy, Eytan |
| byrd2020abides | inproceedings | 2020 | Byrd, David |
| collier2022repast4py | inproceedings | 2022 | Collier, Nick |
| deb2002nsga2 | article | 2002 | Deb, Kalyanmoy |
| hanski1991single | article | 1991 | Hanski, Ilkka |
| helsgott2020abm | inproceedings | 2020 | Helsgott, Arnd |
| hunter2022multiobjective | inproceeds | 2022 | Hunter, Susan R. |
| kwakkel2017workbench | article | 2017 | Kwakkel, Jan H. |
| mesa2025v3 | misc | 2025 | Project Mesa Contributors |
| optquest2007 | misc | 2007 | OptTek Systems, Inc. |
| pasupathy2011simopt | inproceeds | 2011 | Pasupathy, Raghu |
| railsback2006agent | article | 2006 | Railsback, Steven F. |
| rand2011agent | article | 2011 | Rand, William |
| wall2016agent | article | 2016 | Wall, Friederike |

---

## SUGGESTED DOIs

For entries missing DOIs where the paper can be identified from title, author, and year, here are suggested DOIs to investigate and add:

| Key | Title Snippet | Suggested DOI | Search Strategy |
|---|---|---|---|
| akiba2019optuna | Optuna: A Next-generation Hyperparameter... | Query: "Optuna Akiba 2019" on DOI.org | CrossRef search |
| biscani2020pagmo | A parallel global multiobjective framework... | Query: "pagmo Biscani Izzo 2020" on DOI.org | CrossRef/JOSS |
| deb2002nsga2 | A Fast and Elitist Multiobjective Genetic... | 10.1109/4235.996017 | IEEE Transactions on EC |
| efron1994bootstrap | An Introduction to the Bootstrap | Check publisher (Chapman & Hall) | ISBN-based lookup |
| fortin2012deap | DEAP: Evolutionary Algorithms Made Easy | Query "DEAP Fortin 2012" | JMLR proceedings |
| fu2002optimization | Optimization for Simulation: Theory vs. Practice | Query "fu optimization simulation 2002" | INFORMS Journal on Computing |
| goldsman1994ranking | Ranking, Selection and Multiple Comparisons... | Query "goldsman nelson WSC 1994" | WSC proceedings archive |
| grimm2006odd | A Standard Protocol for Describing Individual-Based... | Query "ODD protocol Grimm 2006" | Ecological Modelling |
| hong2009brief | A Brief Introduction to Optimization via Simulation | Query "Hong Nelson WSC 2009" | WSC proceedings archive |
| kazil2020mesa | Utilizing Python for Agent-Based Modeling: Mesa | Query "Mesa Kazil 2020 SBP-BRiMS" | Springer/SBP-BRiMS proceedings |
| kendall1938new | A New Measure of Rank Correlation | 10.1093/biomet/30.1-2.81 | Biometrika (classic paper) |
| kwakkel2017workbench | The Exploratory Modeling Workbench | Query "workbench Kwakkel 2017" | Environmental Modelling & Software |
| macal2010tutorial | Tutorial on Agent-Based Modelling and Simulation | Query "Macal North 2010" | Journal of Simulation |
| pangallo2019best | Towards a Complete Classification of Macroeconomic... | Query "pangallo farmer 2019" | Journal of Economic Dynamics |
| rand2011agent | Agent-Based Modeling in Marketing | Query "Rand Rust 2011" | International Journal of Research in Marketing |
| tesfatsion2006ace | Agent-Based Computational Economics | Check handbook (North-Holland/Elsevier) | ISBN/direct lookup |
| volterra1926variazioni | Variazioni e Fluttuazioni del Numero d'Individui | Historic paper - check Google Scholar | No modern DOI likely |
| wall2016agent | Agent-Based Modeling in Managerial Science | Query "Wall 2016 agent" | Review of Managerial Science |
| zheng2022aieconomist | The AI Economist: Taxation Policy Design... | Query "AI Economist Zheng 2022" | Science Advances |
| zitzler1998hypervolume | Multiobjective Optimization Using Evolutionary... | Query "Zitzler Thiele 1998" | PPSN proceedings |

---

## RECOMMENDATIONS

### Priority 1: Critical Issues
1. **Add DOI/URL to 33 entries:** Nearly all entries lack verifiable links. This severely impacts the paper's credibility and reproducibility. Systematically search each entry on:
   - DOI.org (crossref.org)
   - Google Scholar
   - ResearchGate / Academia.edu
   - Publisher websites

2. **Fix author field braces in 4 entries:**
   - `capri2023transport`: Change `Capr{\`\i}` to `Capri`
   - `fortin2012deap`: Verify full author list parsing
   - `mesa2025v3` and `optquest2007`: Confirm corporate author formatting

### Priority 2: Cleanup
3. **Remove or cite 14 unused entries:** Decide whether to delete unused entries or add citations to them in the paper.

### Priority 3: Validation
4. **Verify all author names and publication years** match the original sources (especially entries with non-ASCII characters and older papers).

5. **Consider adding pages/volume/issue numbers** where missing to improve locatability.

---

## FILES REFERENCED

- **BibTeX File:** `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/heas/V4 submission/references.bib`
- **LaTeX File:** `/sessions/zen-hopeful-noether/mnt/HEAS_WSC/heas/V4 submission/HEAS_WSC_V5_revised.tex`

---

**Audit Status:** Complete
**Critical Issues:** Yes (33 missing DOI/URL)
**Recommended Action:** Add persistent identifiers to all entries before submission
