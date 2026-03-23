Now I have comprehensive results. Let me compile the structured summary.

---

# Structural Isomorphisms Between Economics and Machine Learning/AI
## Research Survey

---

## 1. Direct Mapping Papers: Economic Concepts to ML Concepts

### 1A. Gradient Descent as Tatonnement (Walrasian Price Adjustment)

| Field | Detail |
|-------|--------|
| **Authors** | Yun Kuen Cheung, Richard Cole, Nikhil Devanur |
| **Title** | "Tatonnement Beyond Gross Substitutes? Gradient Descent to the Rescue" |
| **Venue** | STOC 2013; later Games and Economic Behavior, vol. 123, 2020 |
| **Key Mapping** | Walrasian tatonnement (price groping toward equilibrium) is *formally equivalent* to gradient descent on a convex potential function whose gradient equals negative excess demand. This is not an analogy but a proven mathematical isomorphism. |
| **Relevance** | Provides the strongest formal bridge between optimization (ML) and market equilibrium (economics). The entire gradient descent toolbox (convergence rates, step-size analysis) transfers directly to economic price adjustment. |

Sources: [Cheung, Cole, Devanur (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0899825619300491), [NYU CS version](https://cs.nyu.edu/~cole/papers/STOC13_full_paper.pdf)

### 1B. Loss Function = Negative Utility Function

| Field | Detail |
|-------|--------|
| **Status** | Well-established equivalence across fields |
| **Key Mapping** | Minimizing a loss function in ML is formally identical to maximizing a utility function in economics. Both encode preferences/objectives as scalar functions over outcomes. Von Neumann-Morgenstern expected utility maximization maps directly to expected loss minimization under uncertainty. |
| **Relevance** | This is the foundational isomorphism. Every supervised learning problem has an economic decision-theory dual. |

Sources: [Wikipedia: Loss Function](https://en.wikipedia.org/wiki/Loss_function), [Springer: User's Guide to Economic Utility Functions](https://link.springer.com/article/10.1007/s11166-024-09443-5)

### 1C. Regularization as Taxation / Reward Shaping

| Field | Detail |
|-------|--------|
| **Authors** | Stephan Zheng, Alexander Trott, Sunil Srinivasa, David C. Parkes, Richard Socher (Salesforce Research) |
| **Title** | "The AI Economist: Taxation Policy Design via Two-Level Deep Multiagent Reinforcement Learning" |
| **Venue** | Science Advances, May 2022 |
| **Key Mapping** | Taxation in multi-agent economies operates as reward shaping / entropy regularization. The paper uses entropy-based regularization on the planner's RL policy, which mirrors how taxation constrains economic agents to prevent socially undesirable outcomes (tragedy of the commons). Regularization prevents overfitting to local optima; taxation prevents exploitation of market power. |
| **Relevance** | Directly operationalizes the regularization-taxation analogy in a working computational system. The AI Economist improved equality-productivity tradeoff by 16% over the Saez tax framework. |

Sources: [Science Advances (2022)](https://www.science.org/doi/10.1126/sciadv.abk2607), [arXiv preprint](https://arxiv.org/abs/2004.13332), [Salesforce GitHub](https://github.com/salesforce/ai-economist)

### 1D. ML as Natural Monopoly (Overfitting as Market Concentration)

| Field | Detail |
|-------|--------|
| **Author** | Tejas N. Narechania |
| **Title** | "Machine Learning as Natural Monopoly" |
| **Venue** | Iowa Law Review, vol. 107, issue 4, 2022 |
| **Key Mapping** | ML-based applications exhibit natural monopoly conditions: high fixed costs of development, economies of scale in data/compute, and network effects. This parallels how overfitting to a dominant strategy crowds out diversity. Where natural monopolies exist, regulation (analogous to regularization) is needed. |
| **Relevance** | Does not draw the overfitting-monopoly analogy directly at the mathematical level, but establishes the structural argument that ML systems *create* monopoly conditions through the same dynamics that cause overfitting (data concentration, capacity dominance). |

Sources: [Iowa Law Review](https://ilr.law.uiowa.edu/print/volume-107-issue-4/machine-learning-as-natural-monopoly), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3810366)

### 1E. The Neural Marketplace: Neurons as Market Producers

| Field | Detail |
|-------|--------|
| **Source** | bioRxiv preprint |
| **Title** | "The Neural Marketplace: General Formalism and Linear Theory" |
| **Key Mapping** | Neurons are treated as producers of an information product that they "sell" to downstream cells. Networks of neurons self-organize into functional networks similarly to supply networks in a free-market economy. Price signals in markets map to activation signals in neural networks. |
| **Relevance** | A neuroscience paper that explicitly models neural computation as a market process, providing the biological grounding for the backpropagation-as-price-signal analogy. |

Source: [bioRxiv](https://www.biorxiv.org/content/10.1101/013185v1.full)

---

## 2. Reverse Mapping Papers: ML Concepts Applied to Economics

### 2A. Attention Mechanisms and Bounded Rationality

| Field | Detail |
|-------|--------|
| **Lineage** | Herbert Simon (1955) -> Kahneman dual-process theory -> modern attention economics |
| **Key Mapping** | Attention mechanisms in transformers allocate finite computational resources to the most relevant inputs, which is structurally identical to bounded rationality: agents with limited cognitive resources selectively attend to information. "Attention economics" (inheriting from Simon) treats attention as a scarce resource that is allocated suboptimally due to cognitive constraints, exactly as transformer attention heads allocate weights across token positions. |
| **Status** | The conceptual link is well-established in behavioral economics and cognitive science. Formal computational models exist (e.g., "Computational rationality: linking mechanism and behavior through bounded utility maximization," Gershman et al., 2015). No single paper draws the transformer-attention to bounded-rationality mapping explicitly, but the intellectual ingredients are all present. |

Sources: [Stanford Encyclopedia of Philosophy: Bounded Rationality](https://plato.stanford.edu/entries/bounded-rationality/), [Attention Economics (CSSN)](http://english.cssn.cn/skw_research/economics/202408/t20240819_5772590.shtml), [PubMed: Computational Rationality](https://pubmed.ncbi.nlm.nih.gov/24648415/)

### 2B. GANs as Game-Theoretic Economic Models

| Field | Detail |
|-------|--------|
| **Authors** | Mahdi Rahbar et al. |
| **Title** | "Games of GANs: Game-Theoretical Models for Generative Adversarial Networks" |
| **Venue** | Artificial Intelligence Review (Springer), 2023 |
| **Key Mapping** | GANs are formally two-player zero-sum minimax games seeking Nash equilibrium. This framework has been extended to compute generalized Nash equilibria in environmental economic models (Kyoto mechanism), Arrow-Debreu competitive economies, and general pseudo-games. The generator-discriminator dynamic maps to counterfeiter-regulator or firm-regulator adversarial dynamics. |
| **Additional** | "Generative Adversarial Equilibrium Solvers" (OpenReview) applies GAN architecture to solve for competitive equilibria in Arrow-Debreu economies. |

Sources: [Springer: Games of GANs](https://link.springer.com/article/10.1007/s10462-023-10395-6), [arXiv: Game of GANs](https://arxiv.org/abs/2106.06976), [OpenReview: Generative Adversarial Equilibrium Solvers](https://openreview.net/forum?id=TlyiaPXaVN)

### 2C. RL Exploration-Exploitation as Industrial Policy / Social Dilemma

| Field | Detail |
|-------|--------|
| **Author** | Max Simchowitz et al. |
| **Title** | "Exploration and Incentives in Reinforcement Learning" |
| **Venue** | arXiv:2103.00360 |
| **Key Mapping** | A population of self-interested agents collectively faces the exploration-exploitation tradeoff. Individual agents are not incentivized to bear exploration costs for others, resulting in under-exploration -- a classic public goods / social dilemma problem. This maps directly to industrial policy debates: governments must incentivize exploration (R&D, infant industries) because private firms under-invest relative to the social optimum. |

Sources: [arXiv](https://arxiv.org/abs/2103.00360), [Wikipedia: Exploration-Exploitation](https://en.wikipedia.org/wiki/Exploration%E2%80%93exploitation_dilemma)

### 2D. Mechanism Design Reduced to Algorithm Design via ML

| Field | Detail |
|-------|--------|
| **Authors** | Maria-Florina Balcan, Avrim Blum, Jason Hartline, Yishay Mansour |
| **Title** | "Reducing Mechanism Design to Algorithm Design via Machine Learning" |
| **Venue** | FOCS 2005; Journal of Computer and System Sciences, 2008 |
| **Key Mapping** | Incentive-compatible mechanism design problems can be formally reduced to standard algorithmic pricing problems using sample-complexity techniques from ML. Given an optimal algorithm, it can be converted into an approximation for the mechanism design problem. This is a rigorous mathematical reduction, not merely an analogy. |
| **Additional** | "Deep Mechanism Design" (PNAS, 2024) by Dafoe et al. uses deep learning to learn social and economic policies directly. |

Sources: [CMU Paper](https://www.cs.cmu.edu/~ninamf/papers/md_ml_jcss.pdf), [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0022000007001249), [PNAS: Deep Mechanism Design](https://www.pnas.org/doi/10.1073/pnas.2319949121)

---

## 3. Cross-Domain Analogy Frameworks

### 3A. Gentner's Structure-Mapping Theory (The Standard Framework)

| Field | Detail |
|-------|--------|
| **Author** | Dedre Gentner |
| **Title** | "Structure-Mapping: A Theoretical Framework for Analogy" |
| **Venue** | Cognitive Science, vol. 7, no. 2, 1983 |
| **Key Idea** | Analogies work by mapping *relational structure* (not surface attributes) from a base domain to a target domain. The systematicity principle states that people prefer to map systems of predicates containing higher-order relations rather than isolated predicates. This is the de facto standard theory of analogy in cognitive science. |
| **Application** | Any economics-ML isomorphism should be evaluated by whether it maps relational structures (e.g., "regularization constrains model complexity" maps to "taxation constrains economic concentration") rather than surface features. |

Sources: [Northwestern Paper](https://groups.psych.northwestern.edu/gentner/papers/Gentner83.2b.pdf), [Wikipedia](https://en.wikipedia.org/wiki/Structure-mapping_theory)

### 3B. Category Theory as Formal Analogy Framework

| Field | Detail |
|-------|--------|
| **Authors** | Various (MDPI journal, PLoS Computational Biology) |
| **Title** | "Structural Similarity: Formalizing Analogies Using Category Theory" |
| **Key Idea** | Domains are defined as objects in the category of colored multigraphs; analogies are morphisms (structure-preserving maps) between them. Category-theoretic constructs like pullback and pushout can generate new analogical blends. This provides the most rigorous mathematical formalization of cross-domain analogy. |
| **Application** | An economics-ML isomorphism could be formalized as a functor between the category of economic structures and the category of ML structures, with natural transformations capturing the systematic correspondences. |

Sources: [MDPI: Structural Similarity](https://www.mdpi.com/2813-0405/3/4/12), [PLoS Comp Bio: Category Theory and Analogy](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005683)

### 3C. Transfer Learning by Structural Analogy

| Field | Detail |
|-------|--------|
| **Author** | Huayan Wang (Carnegie Mellon) |
| **Title** | "Transfer Learning by Structural Analogy" |
| **Venue** | AAAI 2011 |
| **Key Idea** | Formalizes transfer learning as structural analogy between source and target domains, extending Gentner's theory into a computational ML framework. |

Source: [AAAI Paper](https://cdn.aaai.org/ojs/7907/7907-13-11435-1-2-20201228.pdf)

---

## 4. Key Researchers and Labs

| Researcher / Lab | Affiliation | Focus Area |
|-----------------|-------------|------------|
| **Susan Athey & Guido Imbens** | Stanford GSB | ML methods for causal inference in economics; Nobel-adjacent work bridging ML and econometrics |
| **Hal Varian** | Google / UC Berkeley | ML-economics bidirectional lessons; "Big Data: New Tricks for Econometrics" (JEP 2014) |
| **Stephan Zheng, Alexander Trott** | Salesforce Research | The AI Economist -- RL for tax policy design |
| **Jon Kleinberg & Sendhil Mullainathan** | Cornell / Chicago Booth | Algorithmic fairness from an economic perspective; ML-economics regulatory frameworks |
| **Maria-Florina Balcan** | CMU | Mechanism design reduced to algorithm design via ML |
| **Richard Cole, Nikhil Devanur** | NYU / Microsoft Research | Tatonnement-gradient descent equivalence |
| **Dedre Gentner** | Northwestern | Structure-mapping theory (the foundational analogy framework) |
| **Friedrich Hayek** (historical) | LSE / Chicago | "The Sensory Order" (1952) -- independently conceived connectionist model; price system as distributed information processing (1945) |
| **David Parkes** | Harvard | Deep mechanism design, multi-agent RL for economic policy |

Source: [Athey research page](https://gsb-faculty.stanford.edu/susan-athey/research/), [Varian JEP 2014](https://www.aeaweb.org/articles?id=10.1257%2Fjep.28.2.3), [Hayek and Connectionism](https://web-archive.southampton.ac.uk/cogprints.org/306/1/connect.html), [Hayek Market Algorithm (JEP 2017)](https://www.aeaweb.org/articles?id=10.1257/jep.31.3.215)

---

## 5. Consolidated Isomorphism Table

This table synthesizes all findings. Mappings marked with a star have formal/mathematical backing in the literature. Others are conceptually supported but not yet formalized as theorems.

| ML Concept | Economic Concept | Formal Status | Key Reference |
|-----------|-----------------|---------------|---------------|
| Gradient descent | Walrasian tatonnement | Proven equivalence (star) | Cheung, Cole, Devanur 2013/2020 |
| Loss function | Negative utility function | Definitional equivalence (star) | Standard decision theory |
| Regularization (L1/L2) | Taxation / regulation | Operational analogy (star) | Zheng et al. 2022 (AI Economist) |
| Overfitting | Monopoly / market concentration | Structural analogy | Narechania 2022 |
| Dropout | Creative destruction (Schumpeter) | **Novel -- no formal paper found** | Conceptual gap in literature |
| Ensemble methods | Market pluralism / diversity of models | Conceptual parallel | Pluralism in economics literature |
| Attention mechanism | Bounded rationality / scarce attention | Strong conceptual link | Simon 1955; attention economics |
| GAN (generator vs discriminator) | Firm vs regulator adversarial game | Formal game theory (star) | Rahbar et al. 2023 |
| RL exploration-exploitation | Industrial policy / public goods R&D | Formal incentive model | Simchowitz et al. 2021 |
| Backpropagation / error signals | Price signals in markets | Structural analogy | Neural Marketplace (bioRxiv); Hayek 1945/1952 |
| Batch normalization | Automatic fiscal stabilizers | **Novel -- no formal paper found** | Conceptual gap in literature |
| Mechanism design | Algorithm design | Formal reduction (star) | Balcan et al. 2005/2008 |
| Neural network self-organization | Market self-organization | Hayek's connectionism | Hayek 1952; JEP retrospective 2017 |
| Bias-variance tradeoff | Efficiency-equity tradeoff | Conceptual parallel | AI Economist framework |

---

## 6. Gaps and Opportunities

The following mappings from your original list have **no established formal treatment** in the literature and represent potential original contributions:

1. **Dropout as Creative Destruction**: Hinton's original dropout paper (2014) analogizes to sexual reproduction and bank teller rotation, but nobody has formalized the Schumpeterian creative destruction parallel -- where randomly destroying network capacity forces robust, innovation-like adaptation.

2. **Batch Normalization as Automatic Stabilizers**: No literature connects the internal distribution stabilization of batch norm to macroeconomic automatic stabilizers (unemployment insurance, progressive taxation) that dampen cyclical volatility. The structural parallel is strong: both normalize internal signals to prevent runaway dynamics.

3. **Ensemble as Market Pluralism**: While diversity in ensemble methods and pluralism in economic thought are both well-studied independently, no paper formally maps one to the other using structure-mapping or category theory.

These gaps suggest a genuinely novel research contribution could be made by formalizing these analogies, particularly using Gentner's structure-mapping framework or category-theoretic morphisms as the formal apparatus.

---

## Summary of Key Sources

- [Cheung, Cole, Devanur -- Tatonnement as Gradient Descent (ScienceDirect 2020)](https://www.sciencedirect.com/science/article/abs/pii/S0899825619300491)
- [Zheng et al. -- The AI Economist (Science Advances 2022)](https://www.science.org/doi/10.1126/sciadv.abk2607)
- [Narechania -- ML as Natural Monopoly (Iowa Law Review 2022)](https://ilr.law.uiowa.edu/print/volume-107-issue-4/machine-learning-as-natural-monopoly)
- [Rahbar et al. -- Games of GANs (Springer 2023)](https://link.springer.com/article/10.1007/s10462-023-10395-6)
- [Balcan et al. -- Mechanism Design via ML (JCSS 2008)](https://www.sciencedirect.com/science/article/pii/S0022000007001249)
- [Gentner -- Structure-Mapping Theory (Cognitive Science 1983)](https://groups.psych.northwestern.edu/gentner/papers/Gentner83.2b.pdf)
- [Category Theory and Analogy (MDPI)](https://www.mdpi.com/2813-0405/3/4/12)
- [Hayek and Connectionism](https://web-archive.southampton.ac.uk/cogprints.org/306/1/connect.html)
- [Hayek and the Market Algorithm (JEP 2017)](https://www.aeaweb.org/articles?id=10.1257/jep.31.3.215)
- [Neural Marketplace (bioRxiv)](https://www.biorxiv.org/content/10.1101/013185v1.full)
- [Athey & Imbens -- ML Methods for Economists (Annual Reviews)](https://www.annualreviews.org/content/journals/10.1146/annurev-economics-080217-053433)
- [Varian -- Big Data: New Tricks for Econometrics (JEP 2014)](https://www.aeaweb.org/articles?id=10.1257%2Fjep.28.2.3)
- [Kleinberg & Mullainathan -- Algorithmic Fairness (AEA 2018)](https://www.cs.cornell.edu/home/kleinber/aer18-fairness.pdf)
- [Simchowitz -- Exploration and Incentives in RL (arXiv 2021)](https://arxiv.org/abs/2103.00360)
- [Deep Mechanism Design (PNAS 2024)](https://www.pnas.org/doi/10.1073/pnas.2319949121)
- [Srivastava & Hinton -- Dropout (JMLR 2014)](https://www.jmlr.org/papers/v15/srivastava14a.html)
- [PLoS: Category Theory Approach to Analogy](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005683)
- [Attention Economics (CSSN)](http://english.cssn.cn/skw_research/economics/202408/t20240819_5772590.shtml)