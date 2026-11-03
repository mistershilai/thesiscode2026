# MSOM reference: standards, benchmark papers, reviewer prompt

Compiled 2026-10-09 by a literature-search agent. Journal-policy statements are paraphrased from search excerpts and benchmark-paper notes rely on abstracts only, so check anything load-bearing against the source.

**Caveats before you rely on this**

- `pubsonline.informs.org` returned HTTP 403 to every direct fetch (and web.archive.org is unreachable). Journal-policy statements below come from search-engine excerpts of the official pages, INFORMS blog posts I fetched, and MSOM Society business-meeting documents I extracted locally. They are close paraphrases, not checked against the live pages.
- Benchmark papers were verified through the RePEc listing of MSOM (title, authors, volume/issue/pages, DOI, abstract). I had no full text, so every per-paper bullet relies on the abstract.
- `main.tex` was edited while I worked (783 to 795 lines). It now lists three contributions and positions the theorems against Simchi-Levi et al. 2019, El Housni and Goyal 2021, Ardestani-Jaafari and Delage 2016, and Atamturk and Zhang 2007. Parts B and C reflect the newer text. I edited nothing.
- `main.pdf` is exactly 32 pages, the cap. Whether that build includes the newer intro text I could not tell.

---

## A. MSOM standards and benchmark papers

### A1. Journal standards (verified unless marked)

**Format**
- Main manuscript is capped at 32 pages including references, tables, figures and appendices; the online supplement is capped at 16 pages for new submissions. Source: [submission guidelines](https://pubsonline.informs.org/page/msom/submission-guidelines) via excerpt, corroborated by [Manusights guide](https://manusights.com/blog/manufacturing-and-service-operations-management-submission-guide) (secondary).
- Review is double-anonymous. The abstract is structured, at most 300 words, in three parts: problem definition, methodology/results, managerial implications. Authors nominate two preferred Department Editors. Same sources.

**Acceptance criteria**
- Editor-in-Chief Georgia Perakis (2021) says the journal wants "high impact papers that study important and relevant questions in the field of OM", with contributions that are "descriptive, predictive and/or prescriptive". The target is "fast acceptance, preferably in two rounds of review, with two reviewers". Source: [Editorial Statement and Journal Updates](https://www.informs.org/Blogs/M-SOM-Blogs/From-M-SOM-Journal-Editor/Editorial-Statement-and-Journal-Updates).
- The same statement lists five grounds weighed against a paper:
  1. serious errors "not fixable in preferably two rounds";
  2. a question "poorly motivated about its relevance to operations management and originality";
  3. results that are "incremental" and lack "the potential to be generalizable";
  4. work "poorly executed in terms of assumptions and approaches, with insufficient depth";
  5. work "poorly written in terms of structure ... and exposition".
- The earlier "2-2-2 / 3-3-4" policy (Christopher Tang, 2019) sets two reviewers, two cycles, and up to three major suggestions per reviewer. Papers should be rejected only for lack of OM relevance, lack of novelty, or lack of rigor that "would dramatically change the conclusions", with concrete examples and references. Source: [Review Less, Progress More Revisited](https://www.informs.org/Blogs/M-SOM-Blogs/From-M-SOM-Journal-Editor/Review-Less-Progress-More-Revisited-2-2-2-3-3-4).
- On fit, Tang (2016) says MSOM wants OM research "based on or motivated by real operational issues". Source: [Six Tips](https://www.informs.org/Blogs/M-SOM-Blogs/From-M-SOM-Journal-Editor/Six-Tips-for-Submitting-an-Article-to-M-SOM).

**Data and code**
- Search excerpts of the guidelines say all papers should make data and code available. Authors of accepted papers with numerical work, including simulations, must provide "the data, programs, and other details ... sufficient to permit replication" before production. Sources: [submission guidelines](https://pubsonline.informs.org/page/msom/submission-guidelines) and [INFORMS code and data disclosure policy](https://pubsonline.informs.org/page/mnsc/code-and-data-disclosure-policy).
- I could not confirm the exact MSOM wording or its exemption procedure for confidential data. This matters here because the CMS and point-prevalence-survey data are private.

**Departments and editors**
- Departments: Manufacturing and Supply Chain Operations; Services, Platforms and Revenue Management; Environment, Health and Society; Operational Innovation; Analytics in Operations; Practice Platform. Source: [editorial statement](https://pubsonline.informs.org/page/msom/editorial-statement) via excerpt.
- Environment, Health and Society "embraces research in areas related to sustainability and the environment as well as health and healthcare". Its current Department Editors are Atalay Atasu (INSEAD), Özlem Ergun (Northeastern) and Lauren Lu (Dartmouth). Sources: [editorial board](https://pubsonline.informs.org/page/msom/editorial-board) via excerpt and the [Fall 2025 business-meeting slides](https://higherlogicdownload.s3.amazonaws.com/INFORMS/f779d040-38c8-42bb-aa09-0911d651a7eb/UploadedImages/Fall_2025_MSOM_Business_Meeting_v12-compressed.pdf).
- Analytics in Operations: Melvyn Sim (NUS) and Huseyin Topaloglu (Cornell Tech). Practice Platform: Jérémie Gallien, Pavithra Harsha, Ananth Raman. Source: same slides. The slide layout is ambiguous for some other departments.
- Perakis's final term ends December 31, 2026. A search committee was to propose a successor by July 1, 2026; I found no announcement. Source: [call for nominations](https://connect.informs.org/discussion/call-for-nominations-editor-in-chief-msom-1).

**Statistics**
- 836 original submissions arrived January to September 2025; 161 (19.3%) went to Environment, Health and Society. Source: Fall 2025 slides.
- For externally reviewed papers, time to first decision averaged 105 days (median 97) and time to final decision averaged 183 days. Source: Fall 2025 slides.
- Acceptance rate was 16% in 2023, 19% in 2022, 15.7% in 2021. Source: [June 2024 minutes](https://higherlogicdownload.s3.amazonaws.com/INFORMS/f779d040-38c8-42bb-aa09-0911d651a7eb/UploadedImages/2024_Minutes_of_the_MSOM_Business_Meeting_June_2024.pdf).
- One search summary attributed a 29% desk-reject rate and 76-day decisions to MSOM. In the minutes those figures belong to Management Science and Operations Research. I found no official MSOM desk-reject rate.

**Special issue**
- "Operations Management for Developing Economies" (guest editors Mahyar Eftekhar, Serguei Netessine, Yanchong Zheng) had a June 1, 2026 deadline, with final decisions by June 1, 2027. It has closed. Source: [call for papers](https://pubsonline.informs.org/doi/10.1287/msom.2025.cfp.v27.n3) and Fall 2025 slides.
- The call sought work engaging "weak or informal institutions, infrastructure constraints, market frictions ... and resource limitations". My inference: a regular submission will likely be handled by editors and referees from this community.

**Practice-based work**
- The Practice-Based Research Competition does not require implementation, but "potential benefits to practice can be ascertained with a high level of confidence", and validity ("the extent to which the results presented do or would apply in practice") is a key criterion. Source: [competition page](https://www.informs.org/Recognizing-Excellence/Community-Prizes/Manufacturing-and-Service-Operations-Management/M-SOM-Practice-based-Research-Competition).

### A2. Benchmark papers (all MSOM; abstract only)

**(a) Health, global-health and humanitarian supply chains**

1. Karimi, Mishra, Natarajan, Sinha (2024). "Toward Advancing Women's Health in Least Developed Countries: Evaluating Contraceptive Distribution Models in Senegal." 26(3):873-892. https://doi.org/10.1287/msom.2021.0488
   - Compares pull and informed-push distribution for last-mile stockouts and health outcomes.
   - Empirical: triple-differences on a staggered national rollout with multi-source field data.
   - Adds a cost-benefit analysis and says which facility types should switch.
2. Gibson, Deo, Jónasson, Kachule, Palamountain (2023). "Redesigning Sample Transportation in Malawi Through Improved Data Sharing and Daily Route Optimization." 25(4):1209-1226. https://doi.org/10.1287/msom.2022.1182
   - Optimization plus a feature-phone data system, implemented with Riders for Health.
   - Field data on more than 20,000 samples: delays down about 25%, unnecessary trips down 55%.
   - Won the 2021 practice-based competition; this is the field-evidence ceiling for sub-Saharan work.
3. de Véricourt, Gallien, Ghosh (2026). "When Should Fractional-Dose Vaccines Be Used?" 28(2):594-609. https://doi.org/10.1287/msom.2024.1332
   - SIR model inside optimal control, with a structural characterization of the optimal policy.
   - Two real-scenario case studies; compares simple single-dose policies and tests robustness to efficacy uncertainty.
   - No deployment; insights are comparative statics.
4. Bennouna et al. (2023). "COVID-19: Prediction, Prevalence, and the Operations of Vaccine Allocation." 25(3):1013-1032. https://doi.org/10.1287/msom.2022.1160
   - Prediction, prevalence estimation and fair allocation optimization in one pipeline.
   - Credibility rests on external validation: the forecasts were used by the CDC and ranked among the best.
5. Alban, Blaettchen, de Vries, Van Wassenhove (2022). "Resource Allocation with Sigmoidal Demands: Mobile Healthcare Units and Service Adoption." 24(6):2944-2961. https://doi.org/10.1287/msom.2021.1020
   - NP-hard model with closed-form special cases that drive implementable heuristics.
   - Parameters estimated from practice data (family planning in Uganda); benchmark is the demand-proportional allocation used in practice.
6. Uichanco (2022). "A Model for Prepositioning Emergency Relief Items Before a Typhoon with an Uncertain Trajectory." 24(2):766-790. https://doi.org/10.1287/msom.2021.0980
   - Built with the Philippine social-welfare department.
   - Demand model estimated on 2008-2019 typhoon data and back-tested on historical typhoons against existing demand models.
7. Zhang, Ayer, White (2023). "Truncated Balancing Policy for Perishable Inventory Management." 25(6):2352-2370. https://doi.org/10.1287/msom.2022.0644
   - New policy with a worst-case bound of two and asymptotic optimality.
   - Calibrated study on partner-hospital platelet data against existing approximation policies.
8. Chan, Görgülü, Sarhangian (2024). "Inventory Management with Advance Booking Information: The Case of Surgical Supplies and Elective Surgeries." 26(3):931-951. https://doi.org/10.1287/msom.2021.0063
   - Quantifies the value of information as a function of how much is used.
   - Exact analysis of a simplified model plus a real-data case (up to 26% inventory reduction at unchanged service).
   - Closest template for a "value of the requisition signal" argument.

**(b) Robust and adaptive optimization**

9. Fu, Zhou, Lou, Xie, Sim, Tan (2026). "Analytics with Robust Epidemiological Compartmental Optimization Models." 28(4):1339-1357. https://doi.org/10.1287/msom.2024.0984
   - Robust optimization over stochastic SEIR dynamics with a tractable approximation and an open toolkit.
   - Singapore data; benchmark is the deterministic counterpart. The epidemic model is the core, not an appendix.
10. Li, Delage, Zhu, Pinedo, Ma (2024). "Distributional Robustness and Inequity Mitigation in Disaster Preparedness of Humanitarian Operations." 26(1):197-214. https://doi.org/10.1287/msom.2023.1230
    - Shortage, equity and uncertainty handled inside the optimization (lexicographic objective, exact branch-and-bound).
    - Exact and approximate adaptable reallocation; 2010 Yushu earthquake case. Equity is optimized, not only evaluated.
11. Castro, Bodur, Song (2026). "Markov Chain-Based Policies for Multistage Stochastic Integer Linear Programming with an Application to Disaster Relief Logistics." 28(3):956-974. https://doi.org/10.1287/msom.2023.0658
    - Linear decision rules with dual bounds that certify decision-rule quality.
    - Explicit trade-off among flexibility, quality and computation; the insight "adaptive planning is most valuable in constrained systems" is derived, not asserted.
12. Chen, Iyengar, Wang (2023). "Robust Inventory Management: A Cycle-Based Approach." 25(2):581-594. https://doi.org/10.1287/msom.2022.1168
    - Robust lost-sales and backlog inventory with lead times and fixed costs.
    - Complexity results and extensive computational comparison against established policies.
13. Hao, He, Hu, Jiang (2025). "Robust Capacity Planning with General Upgrading." 27(6):1975-1994. https://doi.org/10.1287/msom.2023.0670
    - Exact reformulation of a two-stage distributionally robust model.
    - Synthetic tests plus real company data against sample-average approximation, out of sample.
14. Cheng, Adulyasak, Rousseau (2024). "Robust Drone Delivery with Weather Information." 26(4):1402-1421. https://doi.org/10.1287/msom.2022.0339
    - Two-period adaptive robust model using a mid-day information update.
    - Out-of-sample tests on real wind data against classical models; solve times reported.
15. Ryu, Jiang (2025). "Nurse Staffing Under Absenteeism: A Distributionally Robust Optimization Approach." 27(2):624-639. https://doi.org/10.1287/msom.2023.0398
    - Decision-dependent uncertainty; partner-hospital case with out-of-sample evaluation.

**(c) Model plus data with a public-sector lens, and (d) counterfactual evidence without deployment**

16. Luo, Stellato (2024). "Frontiers in Operations: Equitable Data-Driven Facility Location and Resource Allocation to Fight the Opioid Epidemic." 26(4):1229-1244. https://doi.org/10.1287/msom.2023.0042
    - Epidemic model fitted to state data and embedded in a mixed-integer program; reports optimality gaps (mean 3.99%).
    - Effect sizes with intervals against population- and vulnerability-based benchmarks. No deployment.
17. Baucum, Harris, Kessler, Lu (2025). "Reducing Overdose Deaths and Mitigating County Disparities: Optimal Allocation of Substance Use Treatment Centers." 27(3):736-756. https://doi.org/10.1287/msom.2024.0963
    - Predict-then-optimize on more than 2,500 counties, with causal estimation by instrument.
    - Counterfactual reallocation of observed budgets; equity and efficiency shown as a Pareto frontier.
18. Akshat, Ma, Raghavan (2023). "Improving Broader Sharing to Address Geographic Inequity in Liver Transplantation." 25(4):1509-1526. https://doi.org/10.1287/msom.2023.1211
    - The simulation model is validated against history and beats the incumbent simulator before any counterfactual is run.
19. Balasubramanian, Drake, Acimovic, Fearing (2023). "Mobile Money Operations: Policies for Managing Cash and Digital Currency Inventories in the Developing World." 25(3):958-974. https://doi.org/10.1287/msom.2022.1175
    - Simple heuristic with a near-optimality result, back-tested on 35 million real transactions.
    - Reports where the heuristic deteriorates.
20. Keshvari Fard, Ljubić, Papier (2022). "Budgeting in International Humanitarian Organizations." 24(3):1562-1577. https://doi.org/10.1287/msom.2021.1016
    - Two-stage stochastic program on Red Cross data; benchmark is the expected-value solution (21.3% gain).
21. Zheng, Lyu, Ke, Teo (2022). "From Targeting to Transfer: Design of Allocation Rules in Cash Transfer Programs." 24(6):2901-2924. https://doi.org/10.1287/msom.2022.1101
    - Predictive, stochastic and robust allocation rules compared on real Malawi data.

Two papers outside MSOM that referees in this area will know, and that the manuscript does not cite:
- Gallien, Leung, Yadav (2021), "Inventory Policies for Pharmaceutical Distribution in Zambia: Improving Availability and Access Equity", Production and Operations Management 30(12):4501-4521. It evaluates the incumbent replenishment policy in a validated simulation.
- Chung et al. (2026), "Improving access to essential medicines via decision-aware machine learning", [Nature](https://www.nature.com/articles/s41586-026-10433-7). It reports nationwide deployment in Sierra Leone with an estimated 19% consumption increase.

### A3. Common pattern (my inference from A1 and A2)

**What accepted papers of this type have**
- A benchmark that is the incumbent practice or the strongest established method, not only a naive model (papers 2, 5, 6, 7, 16, 19).
- Evaluation on data not used to build the model, or a simulator validated against history first (6, 13, 14, 15, 18, 19).
- Theory that explains the numerical findings and is positioned against the nearest result (7, 8, 11, 12).
- A certificate of quality for approximations: bounds, optimality gaps, complexity, solve times (11, 12, 16).
- Managerial insights that are conditional and sometimes counterintuitive, not "our method is better" (5, 10, 11, 17).
- One identity. When an epidemic model or equity appears in the title, it is in the optimization (3, 9, 10, 16).

**What referees typically criticize**
- Strawman baselines, and policies compared under unequal information.
- Evidence called "real data" that is really calibrated simulation.
- Theorems on a stylized case that do not govern the numerical model.
- Unvalidated demand models.
- Omitted first-order operational features such as lead times and perishability.
- Incremental use of standard robust-optimization machinery.
- Titles and abstracts that promise more than the paper delivers.

---

## B. Reviewer agent prompt

Paste the base prompt, then append one persona block per agent.

```
ROLE
You are an anonymous referee for Manufacturing & Service Operations Management (M&SOM), an
INFORMS journal. Review the manuscript below exactly as you would a real double-anonymous
submission. The authors want the weaknesses a real referee would find, so they can fix them
before submitting. Generic praise is useless to them. Be as demanding as a real M&SOM referee.

WHAT TO READ
- /Users/elee/Documents/GitHub/thesiscode2026/botswana_paper/main.tex (the paper)
- /Users/elee/Documents/GitHub/thesiscode2026/botswana_paper/ecompanion.tex (online companion)
- You may open definitions.tex, bibliography.bib and files in figures/ in the same folder to
  check macros, references and figures.
- Read both .tex files in full, including every proof. Do not skim.
- Do NOT read anything else in the repository (code, notebooks, CLAUDE.md, AGENTS.md, notes,
  git history). A referee sees only the submission.
- Do NOT edit, create or delete any file. Do not search for the authors or use their identity
  or affiliations in your assessment. Do flag anything in the files that would break anonymity.

JOURNAL STANDARDS
- Audience: operations management scholars. The journal wants high-impact papers on important
  and relevant OM questions, motivated by real operational issues, with descriptive,
  predictive or prescriptive contributions.
- The editor's stated grounds against acceptance: (1) serious errors not fixable in about two
  rounds; (2) a question poorly motivated in OM relevance or originality; (3) results that are
  incremental and not generalizable; (4) poor execution of assumptions and approach, or
  insufficient depth; (5) poor structure and exposition.
- A reject recommendation must rest on lack of OM relevance, lack of novelty, or lack of rigor
  that would change the conclusions, supported by concrete examples and references.
- Format: main text at most 32 pages including references, tables, figures and appendices;
  online supplement at most 16 pages; structured abstract of at most 300 words (problem
  definition, methodology/results, managerial implications); double-anonymous. Accepted papers
  with numerical work must supply data and code sufficient for replication.
- Likely departments: Environment, Health and Society; Analytics in Operations; Manufacturing
  and Supply Chain Operations.

THE BAR SET BY RECENT M&SOM PAPERS
Hold the manuscript to what these published papers did. Name the relevant one when you say the
manuscript falls short.
- Gibson et al. 2023, sample transportation in Malawi (10.1287/msom.2022.1182): optimization
  implemented with a partner; field data show the effect.
- Karimi et al. 2024, contraceptive distribution in Senegal (10.1287/msom.2021.0488): causal
  evidence from a national rollout plus cost-benefit analysis.
- Uichanco 2022, typhoon prepositioning (10.1287/msom.2021.0980): demand model estimated on
  history and back-tested against existing demand models with a government partner.
- Alban et al. 2022, mobile healthcare units (10.1287/msom.2021.1020): closed-form insight;
  benchmark is the allocation rule used in practice.
- Chan et al. 2024, surgical supplies (10.1287/msom.2021.0063): quantifies the value of
  information explicitly; real-data case.
- Zhang, Ayer, White 2023, perishable inventory (10.1287/msom.2022.0644): new policy with a
  worst-case bound, tested on hospital data against established policies.
- Fu et al. 2026, robust epidemiological optimization (10.1287/msom.2024.0984): robustness is
  built into the epidemic model; real data; deterministic benchmark.
- Li et al. 2024, disaster preparedness (10.1287/msom.2023.1230): equity is optimized inside
  the model, and adaptable reallocation is solved exactly and approximately.
- Castro, Bodur, Song 2026, disaster relief (10.1287/msom.2023.0658): linear decision rules
  with dual bounds certifying their quality.
- Chen, Iyengar, Wang 2023, robust inventory (10.1287/msom.2022.1168): lead times, lost sales,
  complexity results, extensive comparison against established policies.
- Cheng et al. 2024 (10.1287/msom.2022.0339) and Hao et al. 2025 (10.1287/msom.2023.0670):
  robust models judged out of sample on real data against standard alternatives, with solve
  times.
- Luo and Stellato 2024, opioid facility location (10.1287/msom.2023.0042) and Baucum et al.
  2025 (10.1287/msom.2024.0963): counterfactual studies without deployment that fit the model
  to data, report optimality gaps and intervals, and compare against policy-relevant
  benchmarks.
- Akshat et al. 2023, liver allocation (10.1287/msom.2023.1211): the simulator is validated
  against history before counterfactuals are run.
What these share: an incumbent-practice or strongest-alternative baseline; evaluation on data
not used to build the model; theory that explains the numerical results and is positioned
against the nearest prior result; certified approximation quality; conditional managerial
insights; first-order operational features modeled or shown not to matter.

HOW TO REVIEW
1. Verify, do not trust. Re-derive every theorem and proposition from its proof. For each,
   state whether the proof is correct, which hypotheses it truly needs, and whether the
   numerical model satisfies them. Check every headline number in the abstract and
   introduction against the tables and text, and report inconsistencies.
2. For each policy compared, write down what information it observes and when, what budget and
   stock it may use, and how it is re-solved. Decide whether the comparison is fair. Ask what
   incumbent practice would do, what a standard inventory rule with safety stock would do,
   what a policy with the same information but no robust machinery would do, and what a
   perfect-information bound would be. Say which are missing and what each would reveal.
3. Separate what is observed from what is assumed or simulated. For every claim described as
   resting on "real data", identify which quantities are real records and which are drawn from
   a fitted model. Ask whether the demand model and the simulator were validated against
   anything they were not fitted to.
4. Test each claimed contribution for novelty against the literature the paper cites and the
   literature you know. State the closest prior result and what is new beyond it.
5. Check whether the theory governs the numerical study: assumptions that fail in the
   numerical model, predictions the simulations contradict, and whether the stated guarantee
   holds for the demand actually simulated.
6. Judge scope and omissions: which omitted features (lead times, expiry, capacities,
   integrality, pooling across districts, forecast error) could reverse or shrink the
   conclusions.
7. Check that title, abstract, contribution list, related work, results and conclusion tell
   the same story about what the paper contributes.
8. Check compliance: length, abstract structure, anonymity, replicability of the numerical
   study from the text, and data and code availability.
Mark every statement as VERIFIED (you checked it in the files; give section, equation, table
or line) or JUDGMENT (your assessment). If you could not check something, say so. Do not cite
a paper you are not sure exists; describe the kind of work instead.

REPORT FORMAT (plain text, these headings, in this order)
1. Summary of the paper in your own words (one paragraph; no evaluation).
2. Contribution and novelty relative to the literature (per claimed contribution).
3. Technical correctness: model formulation, each theorem and proposition, and consistency
   between the model in the paper and the model solved numerically.
4. Numerical study: baselines, information available to each policy, experimental design,
   replications and uncertainty reporting, sensitivity, computation.
5. Data and validation: provenance, what is real versus simulated, demand-model credibility.
6. Clarity and structure.
7. Fit to M&SOM and the most suitable department.
8. Major concerns: numbered; each with (a) the problem, (b) where it appears, (c) why it
   matters for the conclusions, (d) a concrete request the authors could act on.
9. Minor concerns: numbered; each with a concrete request.
10. The single most likely reason this paper would be rejected, in two or three sentences.
11. What would change your recommendation: the smallest set of additions that would move it up
    one level.
12. Recommendation: reject / major revision / minor revision / accept, with confidence (low /
    medium / high) and one sentence on what limits your confidence.
Rules for the report: no praise without a specific referent; no concern without a concrete
request; put the most damaging concerns first; do not soften the recommendation.
```

**Persona (i): robust-optimization methodologist**

```
PERSONA
You publish on robust and adjustable robust optimization, decision rules and their optimality
(Operations Research, Management Science, Mathematics of Operations Research) and review for
M&SOM's Analytics in Operations department. Spend most of your effort on report sections 2, 3
and 4.
- Check every proof in the e-companion line by line. For the tree result, check both
  directions: that the lower bound is necessary for every policy in the stated class, and that
  the constructed affine rule is feasible for every realization in the set, including
  nonnegativity and the case where a node's own deviation bound is zero.
- Decide whether "optimal among destination-dependent rules" is meaningful. How much does that
  class lose against fully adaptive policies and against affine rules that see all deviations?
  Does the paper quantify the loss? Would a referee call the first theorem elementary?
- Compare the theorems with the nearest known results the paper cites: affine optimality on
  tree networks under node-wise budgets, affine optimality for one-dimensional systems,
  approximation bounds for affine policies under budgeted sets, and the known
  budget-independence of static robust solutions. Is what remains new or a corollary?
- Check that the uncertainty set in the theorems (one budget shared across the network) is the
  set used in the solved model (robust counterpart taken constraint by constraint), and what
  the difference does to the claims.
- Check the hypotheses against the calibration: for which demand levels and dispersion values
  does "nominal demand at least the deviation bound" fail, and how often would that occur
  among facility-product pairs?
- The theorems are single-period, single-class, procurement-only, zero-unmet-demand statements
  on a tree. The numerical model is multi-period with inventory, a non-tree network, a budget
  cap and simulated demand that usually leaves the uncertainty set. Decide whether the theory
  explains the numerical findings, and weigh that the simulations contradict the theorem's
  prediction about the uncertainty budget.
- Assess the reformulation claim: is it more than textbook duality, is "exact" right once
  shipments are truncated at zero and integrality is relaxed, and are problem sizes, solve
  times and gaps reported?
- Ask for the missing methodological baselines: stochastic programming or sample average
  approximation, distributionally robust or robust-satisficing alternatives, a richer decision
  rule, a folding-horizon deterministic policy with the same information, and a
  perfect-information bound.
```

**Persona (ii): healthcare-operations and global-health empirical researcher**

```
PERSONA
You work on public-sector health supply chains in low- and middle-income countries, with field
partners, and publish empirical and practice-based work in M&SOM's Environment, Health and
Society department. You know how central medical stores, district warehouses and facility
requisition systems actually operate. Spend most of your effort on report sections 4, 5 and 8.
- Establish what is real. For each results section, state which inputs are observed records
  and which come from a fitted distribution. Is "results on real procurement data" accurate,
  or is it simulation with real prices and average consumption? Is any result compared with
  observed stockouts or observed service levels?
- Scrutinize the demand estimator: one cross-sectional inpatient survey of ten hospitals,
  extended to clinics and health posts by catchment population; no out-of-sample validation;
  consumption records censored by stockouts; national figures disaggregated to facilities;
  a dispersion parameter estimated near 2.5 while the headline results use 10. Say what
  validation you would require and what data could plausibly provide it.
- Compare with incumbent practice. What stock policy does the agency use now (maximum-minimum
  levels, review periods, requisition or allocation)? Is that the baseline? Is the
  deterministic baseline, which holds no safety stock, something any agency would do? Is the
  minimum-stock experiment in the companion the right comparison, and why is it not in the
  main text?
- Judge operational realism: procurement that arrives in the period ordered, no expiry, no
  storage cap, a per-period budget defined from the forecast and not from the agency's actual
  budget, a separate budget and no pooling across districts, transport at about one percent of
  cost, one fortnightly period of look-ahead. Which of these could reverse the conclusions,
  given that the paper itself says the motivating emergency was partly a procurement failure?
- Judge implementability: can facilities report a requisition signal each fortnight, in time,
  for 84 products? What does the policy need that the agency lacks? Is there any evidence of
  partner use beyond a prototype screenshot?
- Assess the equity claims: equity is evaluated, not optimized, and the paper says part of the
  district-level gain comes from the decomposition and separate budgets, not from the policy.
  Is district the right unit, or should it be facility tier or remoteness?
- Assess the epidemic and resistance material: is it calibrated to anything local, does it
  support any claim in the title or abstract, and should it be in this paper at all?
- Ask whether the managerial implications tell a medical-stores manager something they would
  not already know, and whether the cost-per-unit-served figures are credible.
```

**Persona (iii): department editor screening for desk rejection and fit**

```
PERSONA
You are a Department Editor at M&SOM doing the initial read. You have a few days and many
submissions. Decide whether this goes to an Associate Editor and two referees or is returned
without review. Read the title, abstract, introduction, contribution list, related work, main
tables and figures, the limitations paragraph and the conclusion closely; read the rest fast.
Still produce the full report, but keep sections 3 to 6 brief and make sections 2, 7, 10 and
12 decisive.
- State in two sentences what the paper claims to add and whether you believe it after the
  introduction.
- Decide which kind of paper this is: methodology, theory, empirical or practice-based. Is it
  competitive in that category, or does it spread thin across a model, three theorems, a
  demand estimator, a case study, an epidemic extension, an equity analysis and a software
  prototype?
- Check that title, abstract, keywords, contributions and related work describe the same
  paper. Flag any place where something is claimed as a contribution in one section and
  disclaimed in another, and any title word the body does not deliver.
- Check the headline numbers: are they measured against a baseline a referee will accept, and
  does the abstract disclose the conditions under which they hold?
- Judge novelty at the level an editor would: standard robust-optimization machinery applied
  to a new setting, with theory on a stylized special case and evidence from simulation. Is
  that above the bar set by recent M&SOM papers in this area, several of which have field
  implementation or back-tests on real outcomes?
- Check compliance that triggers an administrative return: page limits, structured abstract,
  anonymization (author block, affiliations, partner names, screenshots, self-citations),
  journal template, data and code availability when the data are confidential.
- Name the department and the type of referees you would choose, and predict what each would
  say first.
- Your recommendation must be one of: desk reject; desk reject with encouragement to resubmit
  after specific changes; send for review (then also give your predicted outcome among reject
  / major revision / minor revision / accept). Give a confidence level, and list the three
  changes that would most improve the paper's chances before submission.
```

---

## C. Top 10 changes to reduce rejection risk (my inference, ordered by importance)

1. **Equalize information across policies, or measure its value.** ARO-ADR sees the period's requisition signal before dispatch; the deterministic and static robust policies "ignore the requisition signal" (Section 3.3). The headline 95-96% and 84-86% gains therefore mix hedging with an information advantage. Add a deterministic and a safety-stock policy that re-optimize dispatch after seeing the same signal, and a perfect-information bound. Report the value of information and the value of the affine rule separately (compare paper 8).

2. **Add the incumbent-practice baseline to the main text.** The deterministic policy holds no safety stock and "never spends more than serving the forecast requires". No agency plans that way, and no benchmark paper uses only a naive baseline. Model the stock policy the agency actually runs, such as min-max cover. The minimum-stock experiment in EC.5 is closest but is applied only to the deterministic policy and sits in the companion.

3. **Stop calling simulation "results on real procurement data", or back-test.** Section 6.3 uses real prices and average monthly consumption, but demand is still drawn from the fitted negative binomial, and 2026-27 is a planning scenario. Either back-test on historical time series and compare with observed stockouts, or relabel throughout (abstract, contribution 3, the Section 6.3 title) as simulation calibrated to those records. Papers 2, 6, 18 and 19 set this bar.

4. **Validate the demand estimator.** It rests on one inpatient survey of ten hospitals extended to 564 clinics and health posts. No out-of-sample check appears, and Section 5 offers only a textbook consistency argument. Compare its predictions with facility- or district-level consumption or issues data. Explain how it relates to the consumption records that drive Section 6.3. Run the headline at the estimated dispersion (about 2.5), not 10.

5. **Tighten the theory-to-numerics link.** The theorems are single-period, single-class, procurement-only, zero-unmet-demand results on a tree, optimal only among destination-dependent rules. The paper concedes the network is not a tree, that realizations leave the set "in most periods", and that the simulations contradict the Γ prediction. Add:
   - the gap to fully adaptive policies, by a bound or computed on small instances;
   - a numerical check of the closed-form budget on the tree reduction of the real network;
   - how often the hypothesis that nominal demand is at least σ fails across facility-product pairs (by EC.2 it needs demand of about 1.1 units at κ=10, and by the same algebra about 1.7 at κ=2.5);
   - a plain statement of what is new beyond the cited tree result.
   
   Theorem 4.1 is short enough that a referee may call it elementary; consider making it a proposition.

6. **Model procurement lead time, and preferably expiry.** The paper names these as "the most important features we omit" and says the 2025 emergency was "in part a procurement failure". With zero lead time and a one-period rolling horizon the problem is close to a sequence of single-period safety-stock problems. A referee will ask whether the multi-period, multi-echelon apparatus matters, especially with transport at about 1.3% of cost and integrality relaxed. Add a lead-time version on at least the Gaborone instance (compare paper 12).

7. **Give the paper one identity.** The title promises "Supply Chain Design" and "Epidemiological Demand Uncertainty", but the paper studies allocation and puts the epidemic coupling in the companion as "a stress test ... rather than a contribution". Meanwhile the new intro and the related-work section still claim endogenous demand as a gap addressed and as the second addition. "Antimicrobial resistance" is a keyword although no resistance result is claimed. Retitle and align abstract, contributions, related work and keywords. Either cut the epidemic material or build it into the model, as papers 9 and 16 do.

8. **Make the budget and equity claims defensible.** The budget is 1.25 times a forecast-derived reference, per district, not the agency's real budget. The policies use 59%, 74% and 79% of it, so they are not compared at equal spend. The paper admits part of the district gain comes from the decomposition. Add a service-versus-spend frontier for all policies, a pooled-budget run to isolate the decomposition effect, and either optimize an equity criterion or scale back the equity framing (compare papers 10 and 17).

9. **Report the experimental design to replication standard.** State replications for the national and CMS runs (Gaborone has 12; the national runs give T=20 with no replication count and intervals across districts only). Add solve times, problem sizes, hardware and the effect of the integrality relaxation. Put the unfavorable regimes in the abstract or introduction: at budgets of 0.75 of the reference or below, the deterministic policy is best in five of six cases, and static robust beats ARO-ADR under a stationary forecast with seasonal demand. Prepare a replication package with a synthetic or de-identified substitute for the private data.

10. **Fix submission compliance and literature coverage.**
    - Anonymize: the author block, affiliations and app screenshots identify the team.
    - Move to the INFORMS MSOM template and recheck length; the PDF is exactly 32 pages and the intro has grown.
    - Engage recent MSOM work a referee will expect (papers 1, 2, 5, 6, 9, 10, 11 above) plus Gallien, Leung and Yadav (2021) and Chung et al. (2026). The current related work cites almost nothing from MSOM after 2022.

One note outside the blind prompt: paper 16 is co-authored by the manuscript's senior author. It is the closest template for counterfactual evidence without deployment, so matching its reporting of optimality gaps, intervals and policy-relevant benchmarks is a concrete target.
