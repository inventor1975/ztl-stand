# SOURCES-stress: references for certified stress/compliance bounds on solid parts

Date: 2026-11-10. Tags: [V] = read at the URL this session (fetched page, or the search-engine excerpt of that URL; a search excerpt is marked "(excerpt)"); [M] = from memory, unverified.
Honest limit: several PDFs were binary and unreadable by the fetch tool (AAW 2008, Aznaran 1706.09017, Mackenzie 2017, Ladevèze 1704.06688 PDF). Nothing below claims a quote from those.

## 1. Stress singularity at re-entrant corners/edges

- Williams 1952, J. Appl. Mech. 19(4):526-528, "Stress singularities resulting from various boundary conditions in angular corners of plates in extension": treats free-free, clamped-clamped, clamped-free corners; for angles < 180 deg unbounded stress only in the mixed case; for 180-360 deg all the cases considered may be singular; free-free case applies to V-notches. (excerpt) [V](https://authors.library.caltech.edu/records/2zph7-ee089)
- Williams-type eigen-solution form: displacement ~ r^lambda, so stress ~ r^(lambda-1), singular when Re(lambda) < 1; for the re-entrant (free-free) corner lambda < 1 once the interior angle exceeds 180 deg. This is the standard derivation, not stated in the pages I read. [M]
- Costabel-Dauge corner singularities have the form r^nu * phi(theta) near a conical point, nu a discrete set; isotropic Lame system treated in the computation note. (excerpt) [V](https://perso.univ-rennes1.fr/monique.dauge/publis/CoDa_comp.pdf)
- 3D edge singularities of elasticity: Costabel-Dauge-Yosibash (SIAM J. Math. Anal. 2004) compute coefficients of edge singularities along polyhedron edges, aimed at stress concentration along edges and crack fronts. (excerpt) [V](https://costabel.perso.math.cnrs.fr/publis/CoDaYo0306.pdf)
- Yosibash-Omer-Costabel-Dauge (Int. J. Fracture 2005): explicit isotropic elastic edge solution and edge stress intensity functions. (excerpt) [V](https://www.tau.ac.il/~yosibash/papers/IJF_05_YoOmCoDa.pdf)
- Vertex-edge singularities also arise where an edge meets a vertex; monograph Kozlov-Maz'ya-Rossmann, "Spectral problems associated with corner singularities of solutions to elliptic equations" (2001), is the standard reference. Existence of the monograph seen cited only (excerpt); content not read. [M]
- Consequence: in linear elasticity the pointwise max stress at a sharp re-entrant corner/edge is unbounded; energy estimates (finite energy) say nothing about it. Energy finiteness: r^(lambda-1) is in L2 iff lambda > 0. [M]

## 2. Guaranteed bounds for outputs of linear elasticity

- Paraschivoiu-Peraire-Patera, "A posteriori finite element bounds for linear-functional outputs of elliptic partial differential equations", Comput. Methods Appl. Mech. Engrg. 150 (1997) 289-312, DOI 10.1016/S0045-7825(97)00086-8: domain-decomposition technique giving lower and upper bounds on linear-functional outputs; symmetric or nonsymmetric second-order coercive PDEs, 2D in that paper. (excerpt) [V](https://portal.mardi4nfdi.de/wiki/Publication:1267879)
- Related: Paraschivoiu's 1998 MIT PhD thesis (coercive PDEs and Stokes); NASA report applies the bounds to Crouzeix-Raviart Stokes; Bonet-Huerta-Peraire extend to large-strain elasticity. (excerpt) [V](https://ntrs.nasa.gov/api/citations/19980219348/downloads/19980219348.pdf)
- Ladevèze-Pled-Chamoin: bounds on a linear quantity of interest I from CRE of the primal problem and of an adjoint problem: |I_ex - I_h - I_hh| <= (1/2) e_cre * e~_cre, with Prager-Synge equality and Cauchy-Schwarz; bounds are I_h + I_hh -/+ (1/2) e_cre e~_cre. Needs an admissible (statically admissible) stress pair. [V](https://ar5iv.labs.arxiv.org/html/1704.06688)
- Same paper: local quantities (e.g. mean of a stress component over a local region, displacement at a point) are written in global form via "extractors" (known prestress and body force fields) defining the adjoint problem. [V](https://ar5iv.labs.arxiv.org/html/1704.06688)
- Same paper: the classical bound can be poor ("large and low-quality local error bounds") when the reference-problem error lies mostly outside / far from the zone of interest; improvements (extraction/homothety) treat zone and remainder separately. [V](https://ar5iv.labs.arxiv.org/html/1704.06688)
- Same paper: constructing an admissible pair is an essential step for guaranteed bounds. [V](https://ar5iv.labs.arxiv.org/html/1704.06688)
- Guo-Zhong: strict upper and lower bounds for quantities of interest via CRE, also nonsymmetric forms. (excerpt) [V](https://arxiv.org/pdf/1611.05253)
- Prager-Synge equality / hypercircle: for an equilibrated flux (div = f, correct normal trace on Neumann part), error in energy norm is bounded above by a computable quantity; "depending on how the flux is built a lower bound can also be shown". (excerpt) [V](https://arxiv.org/pdf/2110.02160)
- Braess-Schoberl equilibrated-residual construction and Bertrand-Boffi review. (excerpt) [V](https://arxiv.org/pdf/1907.00440)
- Which outputs: compliance (energy) and any bounded linear functional with an H^-1-regular / L2-dual representer (average stress over a subdomain of positive measure, displacement averages). The product-form bound scales with the adjoint's CRE; as the averaging region shrinks, the adjoint data (extractor) gets more concentrated, adjoint energy grows and the bound widens; for a point value of stress at a singularity the functional is not bounded on the energy space, so no finite bound exists. This scaling is my reading of the structure, consistent with the "poor local bounds" statement above but not quoted from a source. [M]
- Pointwise max stress is NOT a bounded linear functional on H1; only regularised averages are certifiable. [M]

## 3. Equilibrated stress reconstructions on tetrahedra

- Arnold-Awanou-Winther, "Finite elements for symmetric tensors in three dimensions", Math. Comp. 77 (2008) 1229-1251: conforming symmetric H(div) elements on tetrahedra; first stable Hellinger-Reissner mixed elements in 3D; 3D analogue of Arnold-Winther 2D; polynomial elasticity complex on a tetrahedron proven exact; interpolation estimates. (excerpt) [V](https://www.ams.org/journals/mcom/2008-77-263/S0025-5718-08-02071-1/)
- Hu-Zhang: lower-order conforming symmetric H(div) spaces on simplices in any dimension (symmetric P_k, k >= n, plus face bubbles); lowest degrees k=3 (2D), k=4 (3D) in the original stable pair. (excerpt) [V](https://arxiv.org/abs/1412.0216v1)
- Zhu-Hu low-order elements: shape functions symmetric P_{k+d-1} with divergence in P_{k-1}. (excerpt) [V](https://arxiv.org/html/2310.13920v3)
- Johnson-Mercier-Krizek in any dimension (Gopalakrishnan-Guzman-Lee, arXiv 2403.13189): stress components piecewise P1 on the Alfeld split of each tetrahedron (4 subtets T_i = [z, other three vertices]); stress space symmetric, H(div); div maps onto piecewise constants on the Alfeld subtets; displacement P1 on T in that paper's pairing (the other pairing: piecewise constant on the Alfeld refinement). The paper defines the space on the physical tetrahedron; no Piola transform discussed in the first 100k chars I read. [V](https://arxiv.org/html/2403.13189v2)
- Dimension of this stress space: 42 on a tetrahedron (15 on a triangle) = 6 comps x 4 subtets x 4 nodal values minus continuity constraints... figure quoted from search excerpt. (excerpt) [V](https://arxiv.org/html/2403.13189v2)
- Johnson-Mercier original 2D element is on the Clough-Tocher split; the Alfeld version is the any-dim generalisation. (excerpt) [V](https://arxiv.org/abs/2403.13189)
- Hybridizable symmetric stress elements on barycentric refinement, arbitrary dimension: (excerpt) [V](https://arxiv.org/html/2501.02691v3)
- Double Piola, covariant: Y = J^-T Upsilon J^-1 preserves tangential-tangential continuity; contravariant (HHJ / normal-normal): Y = (1/det J)^2 J Upsilon J^T "preserving its normal-normal projection properties". Source says nothing explicit about symmetry or divergence preservation in the part read. [V](https://arxiv.org/html/2405.10402v2)
- Same paper abstract: the Hu-Zhang and Hu-Ma-Sun elements cannot be mapped from a reference simplex by standard double Piola maps (needs "polytopal template" tensors). Does NOT say this about Arnold-Winther or the Alfeld-split JM element. [V](https://arxiv.org/html/2405.10402v2)
- Aznaran-Farrell-Kirby-Rognes (arXiv 1706.09017, "A general approach to transforming finite elements"): Arnold-Winther elements need a transformation beyond the plain Piola map (it is the paper about this); pdf unreadable here. (excerpt) [V](https://arxiv.org/pdf/1706.09017)
- Own-math, to verify: tau = (1/det B) B s B^T with constant B. Symmetric if s symmetric (trivial: (B s B^T)^T = B s^T B^T). Divergence: each column of B s is a contravariant Piola image after a constant linear mix, so div tau = (1/det B) B (div s)(F^-1 x) up to the mixing by constant B^T, i.e. div is mapped and equilibrium (div tau = -f piecewise constant) is preserved. Note this single-1/det form is the H(div;S)-conforming one; the 1/det^2 form in the Aznaran text is the normal-normal (HHJ) variant. [M]
- Caveat: for the JM-Alfeld element, the Alfeld split maps to the Alfeld split under an affine map (barycenter to barycenter), so the piecewise structure is preserved. Normal-normal-only vs full normal continuity: the JM element has full normal traces continuous (H(div;S)), so the single-det Piola is the right one. [M]
- A statement of exactly "double Piola with 1/det preserves symmetry and divergence" for this element was NOT found at a URL. [M]

## 4. Engineering practice

- Stress linearization / classification: ASME VIII-2 defines primary, secondary, peak categories; local primary membrane = average across a section excluding concentrations; membrane + bending is the linearised value on the section; membrane constant, bending linear through thickness. (excerpt of Mackenzie, PVP2017) [V](https://strathprints.strath.ac.uk/60871/2/Mackenzie_PVP2017_Stress_linearization_concepts_and_restrictions_in_elastic_design_by_analysis.pdf)
- Stress classification line = through-thickness path; incorporated in 2007 ASME VIII-2 Annex 5.A as the stress classification plane method (secondary source). (excerpt) [V](https://help.solidworks.com/2020/english/solidworks/cworks/t_linearizing_Stress_Results.htm)
- Exact clause numbers (e.g. 5.2.2.2, 5.5.x limits, Annex 5-A) and wording: NOT read from the Code. [M]
- Linearization integrates the stress over a line, i.e. is a bounded linear functional of the stress, which is why it converges under refinement near a singularity while the peak does not. [M]
- IIW hot-spot stress: first principal stress at 0.4t and 1.0t from the weld toe, linear extrapolation sigma_HS = 1.67 sigma_0.4t - 0.67 sigma_1.0t; quadratic 0.4t/0.9t/1.4t with 2.52, -2.24, 0.72; fine mesh element size <= 0.4t; some class societies use 0.5t/1.5t; type b (plate edge) uses 4, 8, 12 mm. (excerpt) [V](https://www.twi-global.com/technical-knowledge/published-papers/recommended-hot-spot-stress-design-s-n-curves-for-fatigue-assessment-of-fpsos-june-2001)
- IIW linear/quadratic extrapolation formulas also given in (excerpt) [V](https://arxiv.org/pdf/2006.10151)
- Normative IIW document (Hobbacher, Recommendations for Fatigue Design of Welded Joints and Components) not read. [M]
- Peterson's Stress Concentration Factors, 4th ed., Pilkey-Pilkey-Bi, Wiley 2020 (ISBN 978-1-119-53251-4): charts and formulas for Kt. (excerpt) [V](https://www.wiley-vch.de/en/areas-interest/engineering/peterson-39-s-stress-concentration-factors-978-1-119-53251-4)
- Kt is defined with respect to a specific nominal stress and a linear-elastic homogeneous isotropic body; using a different cross-section or nominal basis gives a wrong answer. (secondary excerpt) [V](https://scienceinsights.org/how-to-find-stress-concentration-factor-kt/)
- Kt of a sharp re-entrant corner is infinite by definition, charts apply to finite fillet radii. [M]
- NAFEMS mesh convergence (knowledge base): plot a critical result vs mesh density, at least three runs needed; a corner with no radius has theoretically infinite stress which grows without limit as the mesh is refined. (excerpt) [V](https://www.nafems.org/publications/knowledge-base/the-importance-of-mesh-convergence-part-1/)
- Practitioner guidance for singularities: add fillet, read stress away from the corner, or linearise; Stevens suggests checking stress about one thickness from the corner or membrane+bending convergence. (excerpt) [V](https://medium.com/@nickjstevens/practical-tips-for-dealing-with-stress-singularities-nick-j-stevens-1fe6a57d55a9)
- Diverging stress with refinement indicates singularity (SolidWorks help). (excerpt) [V](https://help.solidworks.com/2017/english/solidworks/cworks/r_assessing_stress_hot_spots.htm)
- A specific NAFEMS guideline document on singularities was not found. [M]

## 5. SimJEB dataset (Whalen, Beyene, Mueller 2021, arXiv:2105.03534)

- Abstract: public dataset of crowdsourced mechanical brackets from the GrabCAD Jet Engine Bracket Challenge; 381 cleaned, categorized, meshed, simulated designs; consistent structural loads and supports. [V](https://arxiv.org/abs/2105.03534)
- Solver and meshing: HyperMesh for meshing, OptiStruct for analysis; each of four load cases run as linear-static FEA. [V](https://ar5iv.labs.arxiv.org/html/2105.03534)
- Mesh: first-order tetrahedral, average element size 2 mm; parameters in the paper's Table 1. [V](https://ar5iv.labs.arxiv.org/html/2105.03534)
- Loads: an RBE3 spider element distributes each of the four loads across the surfaces of the interface hole. [V](https://ar5iv.labs.arxiv.org/html/2105.03534)
- Supports: each bolt is a rigid RBE2 spider connected to mesh nodes on the bolt surfaces, with an SPC at the bolt center. [V](https://ar5iv.labs.arxiv.org/html/2105.03534)
- Material Ti-6Al-4V: E = 113.8 GPa, nu = 0.342, density 4.47e-3 g/mm^3 (= 4.47 g/cm^3 = 4470 kg/m^3). The paper's text gives 4.47; "4.43" does not appear in the text as read. [V](https://ar5iv.labs.arxiv.org/html/2105.03534)
- Caveat: the reading was done by the fetch tool's summariser on the ar5iv rendering; re-grep the PDF locally before putting 4.47 in a published table. [M]

## What is safe to state publicly (only [V])

1. Williams (1952) showed unbounded corner stresses in angular plate corners; for 180-360 deg all considered boundary conditions may be singular. (source: Caltech record)
2. Edge and corner singularities of 3D elasticity are studied by Costabel-Dauge-Yosibash and Yosibash et al.; singular functions have the form r^nu * phi.
3. Sharp re-entrant corners have theoretically infinite stress and mesh-refined peak stress grows without limit (NAFEMS knowledge base).
4. Practitioner remedies: fillet, evaluate away from the corner, linearise; show a convergence curve with at least three meshes.
5. Paraschivoiu-Peraire-Patera (1997) gave a-posteriori lower and upper bounds for linear-functional outputs of coercive elliptic PDEs.
6. The CRE method (Ladevèze et al.) bounds a linear quantity of interest by a product of primal and adjoint CRE (factor 1/2), requires a statically admissible stress pair, and its local bounds can be poor when the error lies away from the zone of interest.
7. Prager-Synge: an equilibrated flux gives a guaranteed, computable upper bound on the energy error.
8. Symmetric H(div) stress elements on tetrahedra exist (Arnold-Awanou-Winther 2008; Hu-Zhang; Johnson-Mercier extended to any dimension with piecewise-linear stress on the Alfeld split, div onto piecewise constants).
9. The double contravariant Piola map is Y = (1/det J)^2 J Upsilon J^T and preserves normal-normal projections; Hu-Zhang and Hu-Ma-Sun elements are reported not mappable by standard double Piola maps.
10. IIW hot-spot: 0.4t/1.0t linear extrapolation with weights 1.67/-0.67 (secondary source quoting the guideline).
11. ASME VIII-2 uses primary/secondary/peak categories and linearised membrane and bending stress on a classification line (secondary source).
12. SimJEB: 381 designs, HyperMesh + OptiStruct linear static, 4 load cases, RBE3 loads, RBE2 bolts + SPC, 2 mm first-order tets, Ti-6Al-4V E=113.8 GPa, nu=0.342, density 4.47 g/cm^3 (not 4.43 as read).

Do NOT state publicly without further checking: that the (1/det B) B s B^T map preserves symmetry and divergence for the Alfeld-split element (own derivation, no cited statement); anything about exact ASME clause numbers; any bound behaviour as the averaging region shrinks (my inference).
