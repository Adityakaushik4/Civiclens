# CivicLens AI Engine: Technical Documentation
## Embedding Models, Search Ranking Algorithms, and Location Comparison Architecture

This document provides a comprehensive technical breakdown of how **CivicLens** handles text & multimodal embeddings, performs hybrid search and candidate duplicate ranking, and executes spatial location resolution and proximity comparisons.

---

## 1. Embedding Model Architecture (`app/embeddings/`)

### Overview
CivicLens uses dense vector embeddings for semantic search, multilingual complaint deduplication, and Retrieval-Augmented Generation (RAG) over municipal policies and documents.

```
                  +-----------------------------------+
                  |        Input Text / Query         |
                  |  (English, Hindi, Odia, etc.)     |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |     EmbeddingProvider Factory     |
                  |   (app/embeddings/factory.py)     |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |     GeminiEmbeddingProvider       |
                  | (app/embeddings/gemini_embedding) |
                  +-----------------------------------+
                                    |
            Google GenAI API (gemini-embedding-001)
                                    |
                                    v
                  +-----------------------------------+
                  |  768-dim / 3072-dim Vector Array  |
                  +-----------------------------------+
```

### Key Technical Specifications
* **Base Model**: `gemini-embedding-001` via the official `google-genai` SDK.
* **Vector Dimensions**: 
  * **768 Dimensions**: Used for complaint deduplication, master issue clustering, and semantic similarity scoring ([`app/duplicates/engine.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/duplicates/engine.py)).
  * **3072 Dimensions**: Supported in the document ingestion pipeline and vector store for fine-grained chunk embeddings in the RAG system ([`app/rag/ingestion.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/ingestion.py#L93), [`app/rag/store.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/store.py#L16)).
* **Multilingual Capability**: Operates natively on multilingual input (English, Hindi, Odia, etc.) without requiring destructive pre-translation, capturing cross-lingual semantic equivalence.
* **Abstraction & Extensibility**:
  * [`EmbeddingProvider`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/base.py#L10-L24): Abstract base class defining the `async generate_embedding(text: str) -> List[float]` contract.
  * [`GeminiEmbeddingProvider`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/gemini_embedding.py#L12-L46): Production implementation utilizing `genai.Client(api_key=...).models.embed_content()`.
  * [`get_embedding_provider()`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/factory.py#L6-L14): Factory function instantiating the configured provider (`settings.LLM_PROVIDER`).

---

## 2. Search & Candidate Ranking Algorithms

CivicLens incorporates two distinct search ranking mechanisms:
1. **Hybrid RAG Knowledge Search Ranking** for retrieving civic policy context.
2. **Deterministic Multi-Signal Duplicate Search Ranking** for clustering incoming citizen complaints.

---

### 2.1 Hybrid RAG Knowledge Search Ranking (`app/rag/retrieval.py`)

When a user queries municipal policies, guidelines, or SOP documents, CivicLens executes a **Hybrid Search** strategy combining dense vector similarity with lexical keyword matching, fused via **Reciprocal Rank Fusion (RRF)**.

```
                           +------------------------+
                           |      User Query        |
                           +------------------------+
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
     Dense Vector Embedding                       Lexical BM25 Scoring
(Cosine Similarity vs Chunks)                   (Keyword Match Density)
                |                                             |
                v                                             v
       Vector Ranked List                             BM25 Ranked List
                |                                             |
                +----------------------+----------------------+
                                       |
                                       v
                        Reciprocal Rank Fusion (RRF)
                                       +
                           Reranking Multipliers
                    (Authority Boost + Section Match Boost)
                                       |
                                       v
                            Final Top-K Chunks
```

#### Ranking Pipeline Steps
1. **Pre-Filtering**: Chunks are pre-filtered by `jurisdiction_id` and `access_level` (e.g. `PUBLIC`, `INTERNAL`) in [`rag_vector_store.get_filtered_chunks()`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/store.py#L85).
2. **Dense Vector Score (Cosine Similarity)**:
   $$\text{CosineSimilarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} = \frac{\sum_{i=1}^n u_i v_i}{\sqrt{\sum_{i=1}^n u_i^2} \sqrt{\sum_{i=1}^n v_i^2}}$$
3. **Lexical BM25 Score**:
   $$\text{BM25Score}(Q, D) = \frac{\text{Count of matching query words in } D}{\text{Total word count of } D + 10.0}$$
4. **Reciprocal Rank Fusion (RRF)**:
   $$\text{RRFScore}(c) = \frac{1}{60.0 + \text{Rank}_{\text{vector}}(c)} + \frac{1}{60.0 + \text{Rank}_{\text{BM25}}(c)}$$
5. **Reranking Multipliers**:
   * **Authority Status Booster**: $\times 1.20$ if chunk belongs to an authoritative document (`AuthorityStatus.AUTHORITATIVE`).
   * **Section Match Booster**: $\times 1.15$ if query terms match the chunk's section title.
6. **Blended Score Calculation**:
   $$\text{Final Score} = (\text{RRFScore} \times 30.0) + (\text{CosineSimilarity} \times 0.70)$$

---

### 2.2 Duplicate Issue Search & Multi-Signal Candidate Ranking (`app/duplicates/engine.py`)

When a citizen submits a report, CivicLens checks all active master issues within geographic bounds to rank candidates and determine whether to **merge**, request **human review**, or create a **new master issue**.

#### Hard Geo-Fence Guardrail
* Candidates located further than **500 meters** ($\text{Distance} > 500\text{ m}$) are immediately assigned a spatial score of $0.0$ and disqualified ($\text{Total Score} = 0.0$).

#### Multi-Signal Hybrid Scoring Equation
$$\text{Total Score} = w_{\text{geo}} \cdot S_{\text{geo}} + w_{\text{sem}} \cdot S_{\text{sem}} + w_{\text{cat}} \cdot S_{\text{cat}} + w_{\text{time}} \cdot S_{\text{time}} + w_{\text{img}} \cdot S_{\text{img}}$$

#### Individual Signal Calculations:
1. **Spatial Distance Score ($S_{\text{geo}}$)**:
   $$S_{\text{geo}} = \max\left(0.0, 1.0 - \frac{\text{Distance in meters}}{500.0}\right)$$
2. **Semantic Text Similarity ($S_{\text{sem}}$)**: Cosine similarity between 768-dim query vector and candidate master issue embedding vector.
3. **Categorical Match Score ($S_{\text{cat}}$)**:
   * $1.0$ if both `Category` and `Subcategory` match exactly.
   * $0.7$ if only `Category` matches.
   * $0.0$ if categories differ.
4. **Temporal Proximity Score ($S_{\text{time}}$)**: Exponential time decay over a 30-day half-life:
   $$S_{\text{time}} = \exp\left(-\frac{\Delta t_{\text{days}}}{30.0}\right)$$
5. **Image Similarity ($S_{\text{img}}$)**: Cosine similarity of multimodal image embeddings (if present).

#### Dynamic Signal Weight Normalization
* **With Image Embedding**: Weights are set to $w_{\text{geo}}=0.35$, $w_{\text{sem}}=0.35$, $w_{\text{cat}}=0.15$, $w_{\text{time}}=0.10$, $w_{\text{img}}=0.05$ ($\sum w = 1.0$).
* **Without Image Embedding**: Active weights are automatically re-scaled so their sum equals $1.0$:
  $$w_i' = \frac{w_i}{\sum_{\text{active}} w_k} \implies w_{\text{geo}} \approx 0.368, \, w_{\text{sem}} \approx 0.368, \, w_{\text{cat}} \approx 0.158, \, w_{\text{time}} \approx 0.105$$

#### Decision Threshold Matrix
| Score Condition | Subcategory State | System Action (`DuplicateAction`) | Action Taken |
| :--- | :--- | :--- | :--- |
| $\text{Score} \ge 0.82$ | Matching Subcategory | `AUTOMATIC_MERGE` | Merges complaint into candidate & updates running centroid coordinates. |
| $0.65 \le \text{Score} < 0.82$ | Any | `HUMAN_REVIEW_RECOMMENDED` | Enqueues record into [`DuplicateReviewRecord`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/duplicates/store.py#L22) store for reviewer approval. |
| $\text{Score} \ge 0.82$ | Subcategory Conflict | `HUMAN_REVIEW_RECOMMENDED` | Subcategory conflict safety guardrail triggers manual human review. |
| $\text{Score} < 0.65$ | Any | `NEW_MASTER_ISSUE` | Creates a new Master Issue cluster. |

---

## 3. Location Resolution & Comparison Architecture (`app/gis/`)

CivicLens uses a multi-tier location processing engine to resolve spatial queries, compare location proximity, and assess spatial vulnerability risks.

```
                    +------------------------------------+
                    |       Location Text / Coordinates  |
                    +------------------------------------+
                                      |
                                      v
          +-------------------------------------------------------+
          | Tier 1: Local Bhubaneswar Index (In-Memory Gazette)  |
          |           (app/gis/local_index.py)                    |
          +-------------------------------------------------------+
                     | Exact / Subphrase / Fuzzy Matches
                     v (Confidence >= 0.85)
          +-------------------------------------------------------+
          | Tier 2: Nominatim Geocoder & Jurisdiction Ranking     |
          |           (app/gis/geocoder.py)                       |
          +-------------------------------------------------------+
                                      |
                                      v
          +-------------------------------------------------------+
          | Tier 3: Spatial Distance & Vulnerability Assessment   |
          |     (Haversine Distance & Proximity Decay Engine)     |
          |          (app/gis/vulnerability.py)                  |
          +-------------------------------------------------------+
```

---

### 3.1 Sub-Millisecond Local Index Resolution (`app/gis/local_index.py`)

To ensure instant response times and offline capability for municipal locations, CivicLens embeds an in-memory SQLite gazetteer cache loaded from `data/bhubaneswar_locations.db`.

#### 3-Stage Cascading Matching Logic:
1. **Exact Alias Match**: Direct lookup in `_alias_map`. Returns confidence $0.98$ for verified registry aliases and $0.95$ for standard aliases.
2. **Whole-Word / Subphrase Match**: Regex word-boundary matching ($\text{\textbackslash b} \text{alias} \text{\textbackslash b}$) against candidate phrases.
   * Multi-word alias match (e.g. "Silicon Institute", "SUM Hospital"): Confidence $0.92 - 0.96$.
   * Single-word landmark match (e.g. "Patia", "KIIT"): Confidence $0.88 - 0.92$.
3. **Safe Fuzzy Substring Match**: Safe sequence similarity scan using Python's `difflib.SequenceMatcher`:
   $$\text{Ratio} = \text{SequenceMatcher}(\text{phrase}, \text{alias}).\text{ratio}() \ge 0.85$$
   Disallows fuzzy comparisons on strings shorter than 4 characters or string length differences $> 4$ characters to prevent false positives.

#### Reverse Geocoding via Spatial Index (`reverse_resolve_coordinates`)
Given $(Lat, Lon)$, finds the nearest canonical location in the registry using spatial Haversine distance within a maximum search radius of $0.5\text{ km}$ ($500\text{ meters}$).

---

### 3.2 External Geocoding & Jurisdiction Scoring (`app/gis/geocoder.py`)

If the local index returns no candidate with confidence $\ge 0.85$, the engine falls back to Nominatim OSM geocoding with query landmark expansion.

#### Custom Jurisdiction Scoring Formula
Candidates returned by Nominatim are scored and ranked according to municipal boundaries:

$$\text{JurisdictionScore} = \text{Score}_{\text{city}} + \text{Score}_{\text{state}} + \text{Score}_{\text{country}} + \text{Score}_{\text{query}} + \text{Score}_{\text{importance}}$$

* **City Match ($\text{Score}_{\text{city}}$)**: $+0.45$ if city/municipality matches target jurisdiction (e.g. "Bhubaneswar").
* **State Match ($\text{Score}_{\text{state}}$)**: $+0.30$ if state matches (e.g. "Odisha").
* **Country Match ($\text{Score}_{\text{country}}$)**: $+0.15$ if country matches (e.g. "India").
* **Query Similarity ($\text{Score}_{\text{query}}$)**: $+0.05 \times \frac{\text{Matched Tokens}}{\text{Total Query Tokens}}$.
* **OSM Importance ($\text{Score}_{\text{importance}}$)**: Up to $+0.05$ tiebreaker based on base OSM importance factor.

---

### 3.3 Geodesic Distance Calculation (Haversine Formula)

For spatial comparison between complaint points, candidate master issues, and sensitive assets, CivicLens uses the **Haversine Geodesic Distance Formula** on a spherical Earth model ($R = 6,371,000 \text{ meters}$):

$$\Delta \phi = \text{radians}(Lat_2 - Lat_1), \quad \Delta \lambda = \text{radians}(Lon_2 - Lon_1)$$

$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\text{radians}(Lat_1)) \cdot \cos(\text{radians}(Lat_2)) \cdot \sin^2\left(\frac{\Delta \lambda}{2}\right)$$

$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1 - a}\right)$$

$$\text{Distance (meters)} = R \cdot c$$

---

### 3.4 Spatial Vulnerability & Risk Evaluation (`app/gis/vulnerability.py`)

CivicLens evaluates issue locations against registered sensitive infrastructure (schools, hospitals, transit hubs, elderly care, high-density residential areas) to determine spatial risk multipliers.

#### Sensitive Asset Categories & Base Weights ($W_{\text{base}}$)
* **Hospital**: $0.35$
* **School**: $0.30$
* **Elderly Care**: $0.25$
* **High-Density Residential**: $0.20$
* **Public Transport Interchange**: $0.15$

#### Distance Decay Function ($F_{\text{decay}}$)
For an asset located at geodesic distance $d_{\text{eff}} = \max(0, d - r_{\text{campus}})$:

$$F_{\text{decay}}(d_{\text{eff}}) = \begin{cases} 
1.0 & \text{if } d_{\text{eff}} \le 50\text{ meters} \\
0.5 & \text{if } 50\text{m} < d_{\text{eff}} \le 150\text{ meters} \\
0.2 & \text{if } 150\text{m} < d_{\text{eff}} \le 300\text{ meters} \\
0.0 & \text{if } d_{\text{eff}} > 300\text{ meters}
\end{cases}$$

#### Vulnerability Risk Multiplier ($M_{\text{vuln}}$)
$$\text{Raw Bonus} = \sum_{a \in \text{Assets}} W_{\text{base}}(a) \cdot F_{\text{decay}}(d_{\text{eff}, a})$$

$$M_{\text{vuln}} = 1.0 + \min(0.50, \text{Raw Bonus}) \quad \implies \quad 1.0 \le M_{\text{vuln}} \le 1.50$$

#### Automatic Severity Escalation Rule
If $M_{\text{vuln}} > 1.20$, the issue's severity score is automatically escalated by **+1 level** (capped at maximum severity 5):
$$\text{Severity}_{\text{final}} = \min(5, \text{Severity}_{\text{base}} + 1)$$

---

## 4. Key Source Code Directory Index

| Module Component | File Path | Primary Function |
| :--- | :--- | :--- |
| **Embedding Base Interface** | [`app/embeddings/base.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/base.py) | Abstract provider base class and custom exceptions |
| **Gemini Embedding Implementation** | [`app/embeddings/gemini_embedding.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/gemini_embedding.py) | Google GenAI `gemini-embedding-001` integration |
| **Embedding Provider Factory** | [`app/embeddings/factory.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/embeddings/factory.py) | Factory function instantiating embedding provider |
| **Hybrid RAG Retrieval Engine** | [`app/rag/retrieval.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/retrieval.py) | Cosine + BM25 Reciprocal Rank Fusion & document search |
| **RAG Ingestion & Vector Store** | [`app/rag/ingestion.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/ingestion.py), [`app/rag/store.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/rag/store.py) | Chunk embedding storage & filtered candidates retrieval |
| **Duplicate Candidate Ranking Engine** | [`app/duplicates/engine.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/duplicates/engine.py) | Multi-signal duplicate search ranking & automatic merge thresholds |
| **Local Gazetteer Location Index** | [`app/gis/local_index.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/gis/local_index.py) | In-memory cached Bhubaneswar location resolver & reverse geocoding |
| **Geocoder & Jurisdiction Scorer** | [`app/gis/geocoder.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/gis/geocoder.py) | Nominatim fallback, landmark expansion & jurisdiction ranking |
| **Spatial Vulnerability Evaluator** | [`app/gis/vulnerability.py`](file:///c:/Users/adity/Downloads/CivicLens_FOR_TEAMMATE_20260818/prototype/civic-lens-ai/app/gis/vulnerability.py) | Proximity decay calculation & spatial severity multiplier |
