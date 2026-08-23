# CivicLens

**AI-Assisted Civic Issue Reporting, Intelligence & Resolution**

[![Live Demo](https://img.shields.io/badge/%F0%9F%8C%90_Live_Demo-Render-blue?style=for-the-badge&logo=render)](https://civiclens-frontend-bow7.onrender.com)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Render_Managed-4169E1?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Tests Passing](https://img.shields.io/badge/Pytest-242_Passed-brightgreen?style=for-the-badge&logo=pytest)](prototype/civic-lens-ai/tests)

---

## 🌐 Live Demo

The production prototype is fully deployed and accessible online:

👉 **[Launch CivicLens Live Application](https://civiclens-frontend-bow7.onrender.com)**

### Cloud Deployment Infrastructure
* **Frontend**: Render Static Site (Vite + React 19 + Tailwind CSS)
* **Backend**: Render Web Service (FastAPI + Uvicorn + Google GenAI SDK)
* **Production Database**: Managed Render PostgreSQL (with pgvector support)

---

## 📌 1. The Problem

Municipal administration in modern cities faces critical communication and operational bottlenecks:

* **Reporting Barriers**: Citizens often do not know which department handles a specific problem or struggle to fill complex reporting forms.
* **Incomplete Complaints**: Vague descriptions, missing exact locations, or unverified images delay action.
* **Duplicate Flood**: Multiple citizens independently report the same physical civic issue (e.g., a single large pothole reported 20 times), leading to cluttered municipal queues and fragmented resources.
* **Lack of Visibility**: Citizens rarely get real-time tracking or proof that action was taken.
* **SLA & Evidence Gaps**: Municipal supervisors lack automated tools to audit resolution quality and verify evidence submitted by field teams.

---

## 💡 2. The CivicLens Solution

CivicLens bridges the gap between citizens and municipal authorities using an AI-assisted, spatial-aware intelligence platform:

```
    Citizen Observation
             │
             ▼
 📥 Multimodal Submission (Text, Voice, Image, GIS Location)
             │
             ▼
 🧠 AI Engine (Gemini 3.6 Flash: Structured Extraction & Multilingual STT)
             │
             ▼
 📍 Location Intelligence (Bhubaneswar Gazette & Nominatim Geocoder)
             │
             ▼
 🔍 Multi-Signal Duplicate Detection (Vector Cosine + BM25 + Proximity + Time Decay)
             │
 ┌───────────┴───────────┐
 ▼                       ▼
[Merge into Master Issue] [Create New Master Issue]
 │                       │
 └───────────┬───────────┘
             ▼
 🚦 SLA & Department Routing Engine
             │
             ▼
 👷 Field Operator Action & Evidence Upload (SHA-256 Integrity Verified)
             │
             ▼
 🔍 Supervisor Verification & Citizen Audit Timeline
```

---

## 🏙️ 3. Real-World Scenario

**Location**: Patia, Bhubaneswar, Odisha  
**Problem**: An open garbage dump blocking a drainage channel.

1. **Citizen Submission**: A resident uploads a photo, records an Odia/English voice note saying *"Huge pile of uncollected garbage near KIIT Square blocking the drain"*, and attaches GPS coordinates.
2. **AI Understanding**: The Gemini 3.6 Flash engine transcribes the audio, detects the language, extracts category (`WASTE_MANAGEMENT`), subcategory (`UNCOLLECTED_GARBAGE`), assigns a severity score (`4/5`), and flags a safety hazard (`safety_risk: true`).
3. **Location Resolution**: The local Bhubaneswar GIS gazetteer matches *"KIIT Square"* with high confidence ($0.95$) and retrieves spatial vulnerability indicators (proximity to educational institutions).
4. **Duplicate Deduplication**: The candidate engine compares the report against active issues within a 500m radius. Finding an existing master issue with similarity score $> 0.82$, it automatically merges the report and increments the citizen reporter count.
5. **Municipal Action**: The issue is routed to the Waste Management Department. An operator is assigned, clears the dump, and uploads an "After" photo.
6. **Integrity & Verification**: The system verifies SHA-256 checksums, sanitizes EXIF data, and enqueues the resolution for supervisor approval before marking the issue resolved on the public timeline.

---

## ⭐ 4. Key Implemented Features

| Feature | Description | Implementation Status |
| :--- | :--- | :--- |
| **Multimodal Reporting** | Submit reports using raw text, recorded audio/voice notes, or photos. | ✅ Implemented |
| **Speech-to-Text (STT)** | Voice transcription and multilingual detection via Gemini STT (`gemini-3.6-flash`). | ✅ Implemented |
| **Vision Analysis** | Image hazard identification, visual verification, and context extraction. | ✅ Implemented |
| **Local GIS Gazetteer** | Sub-millisecond local location resolution using a Bhubaneswar SQLite spatial index. | ✅ Implemented |
| **External Geocoding** | Nominatim OSM fallback with custom municipal jurisdiction scoring. | ✅ Implemented |
| **Spatial Vulnerability** | Haversine distance decay rating proximity to hospitals, schools, and high-density zones. | ✅ Implemented |
| **Multi-Signal Deduplication**| Vector similarity, BM25, spatial distance, category matching, and time decay. | ✅ Implemented |
| **Hybrid Search & RAG** | Policy QA over municipal documents using Reciprocal Rank Fusion (RRF) and 3072-dim vectors. | ✅ Implemented |
| **SLA & Escalation** | Automated SLA tracking, status lifecycles, and escalation state machines. | ✅ Implemented |
| **Evidence Protection** | Resolution proof uploads with SHA-256 checksum validation and EXIF sanitization. | ✅ Implemented |
| **Role-Based Access (RBAC)**| Isolated views and capabilities for Citizens, Field Operators, Supervisors, and Admins. | ✅ Implemented |
| **Participatory Budgeting**| Citizen proposal creation, RAG evidence panels, and voting allocation modules. | ✅ Implemented |
| **Civic Analytics** | Hotspot cluster identification and municipal analytics dashboards using Recharts. | ✅ Implemented |

---

## ⚙️ 5. How CivicLens Works

```
01 — Citizen Reports      📥 Submits complaint via text, audio, image, or location coordinates.
02 — AI Analysis          🧠 Gemini 3.6 Flash extracts structured category, severity & safety risk.
03 — Location Engine      📍 Resolves canonical landmarks via local Bhubaneswar index or Nominatim.
04 — Duplicate Check      🔍 Ranks active issues via multi-signal scoring (500m hard geo-fence).
05 — Issue Clustering     📦 Merges duplicate reports into a unified Master Issue cluster.
06 — Department Routing   🚦 Assigns issue to primary department based on municipal routing rules.
07 — Evidence Upload      📷 Operator submits resolution evidence with SHA-256 checksum audit.
08 — Verification & Audit 🔍 Supervisor approves resolution; citizen tracks update on public timeline.
```

---

## 🏗️ 6. System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Render Static Site)"]
        UI["React 19 + Vite Frontend<br/>(Tailwind CSS, React-Leaflet, Recharts)"]
    end

    subgraph APIGateway ["API & Service Layer (Render Web Service)"]
        FastAPI["FastAPI Application Server<br/>(Uvicorn, Pydantic v2)"]
        AuthModule["Auth & RBAC<br/>(JWT, HTTP-Only Cookies, Bcrypt)"]
    end

    subgraph AIEngine ["AI & Intelligence Engine"]
        GeminiLLM["Gemini 3.6 Flash<br/>(LLM Text & Multimodal Engine)"]
        GeminiEmbed["Gemini Embedding 001<br/>(768d / 3072d Dense Vector Model)"]
        LocalGIS["Bhubaneswar Local Index<br/>(SQLite In-Memory Gazetteer)"]
        Nominatim["Nominatim Geocoder<br/>(OSM Fallback)"]
    end

    subgraph LogicEngines ["Core Domain Engines"]
        DupEngine["Multi-Signal Duplicate Engine<br/>(Vector + BM25 + Proximity + Time Decay)"]
        RAGEngine["Hybrid RAG Search Engine<br/>(RRF Fusion: Cosine + Lexical BM25)"]
        RoutingEngine["SLA & Department Router<br/>(Lifecycle State Machine)"]
    end

    subgraph StorageLayer ["Persistence Layer"]
        PostgreSQL[("Render PostgreSQL Database<br/>(SQLAlchemy 2.0 ORM, pgvector)")]
    end

    UI -->|HTTP / REST API| FastAPI
    FastAPI --> AuthModule
    FastAPI --> GeminiLLM
    FastAPI --> GeminiEmbed
    FastAPI --> LocalGIS
    LocalGIS -.->|Fallback| Nominatim
    FastAPI --> DupEngine
    FastAPI --> RAGEngine
    FastAPI --> RoutingEngine
    DupEngine --> PostgreSQL
    RAGEngine --> PostgreSQL
    RoutingEngine --> PostgreSQL
```

---

## 🤖 7. AI Analysis Pipeline

When a complaint is submitted, the AI analysis pipeline evaluates the input and returns a structured JSON result matching the backend Pydantic schema:

### Pipeline Execution Flow
1. **Input Normalization**: Multi-script text/audio input is language-detected (`langdetect` + script heuristics).
2. **LLM Extraction**: `gemini-3.6-flash` extracts key structured fields under strict Pydantic taxonomy constraints.
3. **Validation Safeguards**: Invalid categories or subcategories are automatically coerced to safe fallback bounds (`OTHER`).

### Sanitized Output JSON Example
```json
{
  "original_text": "Heavy waterlogging near Jayadev Vihar overbridge blocking traffic",
  "original_language": "en",
  "normalized_text": "Heavy waterlogging near Jayadev Vihar overbridge blocking traffic",
  "language": "en",
  "category": "DRAINAGE",
  "subcategory": "WATERLOGGING",
  "severity": 4,
  "safety_risk": true,
  "public_impact": 4,
  "location_description": "near Jayadev Vihar overbridge",
  "detailed_description": "Substantial water accumulation causing road blockage.",
  "summary": "Waterlogging blocking traffic near Jayadev Vihar overbridge",
  "confidence": 0.94,
  "confidence_status": "ACCEPTED",
  "language_confidence": 0.99,
  "language_detector": "unicode_script_heuristic",
  "language_disagreement": false
}
```

---

## 🔄 8. Duplicate Detection & Search Engine

CivicLens uses a multi-signal candidate ranking engine to identify duplicate citizen reports:

### Technical Specifications
* **Embedding Model**: `gemini-embedding-001` via the official `google-genai` SDK.
* **Vector Dimensions**: 
  * **768 Dimensions**: Used for complaint deduplication, master issue clustering, and candidate ranking.
  * **3072 Dimensions**: Supported in municipal document chunk ingestion for fine-grained RAG search.

### Multi-Signal Hybrid Scoring Equation
$$\text{Total Score} = w_{\text{geo}} \cdot S_{\text{geo}} + w_{\text{sem}} \cdot S_{\text{sem}} + w_{\text{cat}} \cdot S_{\text{cat}} + w_{\text{time}} \cdot S_{\text{time}} + w_{\text{img}} \cdot S_{\text{img}}$$

* **Hard Spatial Guardrail**: Any candidate further than **500 meters** ($\text{Distance} > 500\text{ m}$) is immediately assigned $S_{\text{geo}} = 0.0$ and disqualified.
* **Distance Score ($S_{\text{geo}}$)**: $S_{\text{geo}} = \max\left(0.0, 1.0 - \frac{\text{Distance}}{500.0}\right)$
* **Semantic Score ($S_{\text{sem}}$)**: Cosine similarity between 768-dim embedding vectors.
* **Temporal Decay ($S_{\text{time}}$)**: Exponential decay over a 30-day half-life: $S_{\text{time}} = \exp\left(-\frac{\Delta t_{\text{days}}}{30.0}\right)$.

### Decision Threshold Matrix
| Composite Score | Subcategory State | System Action (`DuplicateAction`) | Action Taken |
| :--- | :--- | :--- | :--- |
| $\ge 0.82$ | Matching Subcategory | `AUTOMATIC_MERGE` | Merges report into candidate & updates running centroid coordinates. |
| $0.65 - 0.82$ | Any | `HUMAN_REVIEW_RECOMMENDED` | Enqueues record into review queue for operator approval. |
| $\ge 0.82$ | Subcategory Conflict | `HUMAN_REVIEW_RECOMMENDED` | Subcategory conflict guardrail triggers manual human review. |
| $< 0.65$ | Any | `NEW_MASTER_ISSUE` | Creates a new Master Issue cluster. |

---

## 📍 9. Location Intelligence & GIS Architecture

CivicLens features a two-tiered spatial lookup system:

### 1. Static Local Bhubaneswar Index (`data/bhubaneswar_locations.db`)
* **Technology**: Local SQLite spatial gazetteer loaded in-memory.
* **Purpose**: Provides sub-millisecond local landmark lookup for Bhubaneswar without external API dependency.
* **Cascading Matcher**: 3-stage resolution (Exact Alias Match $\to$ Whole-Word Phrase Match $\to$ Sequence Matcher Fuzzy Substring).

### 2. Production Database (`PostgreSQL`)
* **Technology**: Managed Render PostgreSQL (configured via `DATABASE_URL`).
* **Purpose**: Stores all runtime operational application data (users, master issues, duplicate reviews, routing decisions, lifecycle logs, evidence records).

---

## 📊 10. Technology Stack

| Layer | Technology | Version / Specification | Primary Function |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | React | `v19.2` | Interactive Single Page Application (SPA) |
| **Frontend Build Tool** | Vite | `v8.2` | Modern HMR dev server & asset bundler |
| **Frontend Language** | TypeScript | `v6.0` | Type-safe user interface development |
| **Styling & UI** | Tailwind CSS | `v4.3` | Modern responsive styling system |
| **GIS Mapping** | Leaflet / React-Leaflet | `v1.9` / `v5.0` | Interactive map visualizer & spatial selector |
| **Data Visualization** | Recharts | `v3.10` | Municipal analytics & hotspot charting |
| **State & Fetching** | TanStack React Query / Axios | `v5.101` / `v1.19` | Async API request management & caching |
| **Backend Framework** | FastAPI | `>=0.100` | High-performance Python web application framework |
| **Server** | Uvicorn | `>=0.22` | Asynchronous ASGI Web Server |
| **AI Provider SDK** | Google GenAI | `>=0.1.1` | Official `google-genai` SDK for Gemini 3.6 Flash |
| **Database ORM** | SQLAlchemy | `>=2.0` | Object-Relational Mapping & connection pooling |
| **Production Database** | PostgreSQL | Render Managed | Primary relational store (with `pgvector` support) |
| **Local Database** | SQLite | Python Native | Local development fallback & in-memory spatial index |
| **Test Suite** | Pytest / Pytest-Asyncio | `>=7.0` / `>=0.21` | Unit, integration & regression test framework |
| **Deployment Platform**| Render | Cloud PaaS | Host for static frontend, API backend, & PostgreSQL |

---

## 📁 11. Repository Structure

```
CivicLens/
├── prototype/
│   ├── civic-lens-frontend/          # React + Vite Frontend Application
│   │   ├── src/                      # Source components, pages, hooks & API clients
│   │   ├── public/                   # Static web assets
│   │   ├── package.json              # Frontend npm dependencies & scripts
│   │   └── vite.config.ts            # Vite bundler & dev server configuration
│   │
│   └── civic-lens-ai/                # FastAPI Backend Service
│       ├── app/                      # Core backend codebase
│       │   ├── analytics/            # Municipal analytics & hotspot engines
│       │   ├── assignment/           # Work assignment & dispatch logic
│       │   ├── auth/                 # JWT auth, password hashing & RBAC
│       │   ├── database/             # SQLAlchemy ORM models, connection & seeds
│       │   ├── duplicates/           # Multi-signal duplicate detection engine
│       │   ├── embeddings/           # Gemini embedding provider integration
│       │   ├── escalation/           # Issue lifecycle state machine & SLA policies
│       │   ├── evidence/             # SHA-256 evidence integrity & verification
│       │   ├── gis/                  # Bhubaneswar gazetteer & Nominatim geocoder
│       │   ├── llm/                  # Gemini 3.6 Flash structured LLM provider
│       │   ├── priority/             # Multi-factor priority calculation engine
│       │   ├── privacy/              # Public anonymization & timeline transformers
│       │   ├── rag/                  # Hybrid RAG search engine (RRF fusion)
│       │   ├── routing/              # Department registry & routing engine
│       │   ├── sla/                  # SLA policy evaluation models
│       │   ├── stt/                  # Gemini speech-to-text transcription
│       │   ├── vision/               # Gemini vision image analysis engine
│       │   ├── config.py             # App settings (Pydantic BaseSettings)
│       │   ├── main.py               # FastAPI entry point & API route handlers
│       │   ├── pipeline.py           # End-to-end complaint ingestion pipeline
│       │   └── schemas.py            # Pydantic request/response validation schemas
│       │
│       ├── data/                     # Spatial data files
│       │   └── bhubaneswar_locations.db # In-memory SQLite local gazetteer
│       │
│       ├── docs/                     # Detailed technical architecture documentation
│       │   └── EMBEDDING_SEARCH_LOCATION_DOCS.md
│       │
│       ├── tests/                    # Pytest suite (242 verified passing tests)
│       └── requirements.txt          # Python backend dependencies
│
└── README.md                         # Main repository documentation
```

---

## 🔌 12. API Overview

FastAPI automatically generates interactive OpenAPI/Swagger documentation at `/docs` when running the backend.

| Tag / Area | Method | Endpoint Path | Description |
| :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/health` | Application & AI provider health status |
| **Health** | `GET` | `/health/db` | Database connectivity & scheme check |
| **Authentication** | `POST` | `/api/v1/auth/register` | Register new user account |
| **Authentication** | `POST` | `/api/v1/auth/login` | Authenticate & issue JWT cookie/token |
| **Authentication** | `GET` | `/api/v1/auth/me` | Fetch authenticated user profile |
| **AI Engine** | `POST` | `/api/v1/ai/analyze` | Analyze text complaint |
| **AI Engine** | `POST` | `/api/v1/ai/analyze-audio` | Transcribe & analyze voice complaint |
| **AI Engine** | `POST` | `/api/v1/ai/extract-location`| Extract & geocode locations from text |
| **AI Engine** | `POST` | `/api/v1/ai/analyze-image` | Multimodal complaint analysis |
| **Duplicate Engine**| `POST` | `/api/v1/ai/duplicates/check`| Check complaint against active candidates |
| **Duplicate Engine**| `GET` | `/api/v1/ai/master-issues` | Retrieve active Master Issue clusters |
| **Citizen Reporting**| `POST` | `/api/v1/issues/citizen-report`| Full pipeline ingestion & master issue routing |
| **Resolution Evidence**|`POST` | `/api/v1/evidence/upload` | Upload resolution proof (SHA-256 integrity) |
| **Resolution Evidence**|`POST` | `/api/v1/evidence/{id}/verify`| Supervisor evidence review |
| **Public Tracking** | `GET` | `/api/v1/public/issues/{id}` | Privacy-sanitized public issue view |
| **Civic Knowledge RAG**|`POST` | `/api/v1/rag/query` | Grounded municipal policy Q&A |
| **Civic Analytics** | `GET` | `/api/v1/analytics/summary` | Municipal overview analytics |
| **Civic Analytics** | `GET` | `/api/v1/analytics/hotspots`| Spatial issue cluster hotspots |

---

## 👥 13. User Roles & Access Control

CivicLens enforces strict Role-Based Access Control (RBAC):

* 👤 **CITIZEN**: Can report issues (text/voice/image), view public issue timelines, track status via anonymized tokens, and participate in civic proposal voting.
* 👷 **OPERATOR**: Municipal field personnel who receive work assignments, start resolution tasks, and upload completion evidence.
* 🕵️ **SUPERVISOR**: Municipal managers who review duplicate merge queues, verify uploaded resolution evidence, and manage SLA policy definitions.
* 🔑 **ADMIN**: System administrators with full access to user management, RAG document ingestion, and global configuration.

---

## 💻 14. Local Development Setup

### Prerequisites
* **Git**
* **Python**: `v3.11` or higher (Python 3.13 recommended)
* **Node.js**: `v18` or higher
* **npm**: `v9` or higher

### Step 1: Clone Repository
```bash
git clone https://github.com/Adityakaushik4/Civiclens.git
cd Civiclens
```

### Step 2: Backend Setup
```bash
# Navigate to backend directory
cd prototype/civic-lens-ai

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables (create .env file)
cp .env.example .env

# Start FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend server will run at `http://127.0.0.1:8000`. Access Swagger docs at `http://127.0.0.1:8000/docs`.

### Step 3: Frontend Setup
```bash
# Open a new terminal and navigate to frontend directory
cd prototype/civic-lens-frontend

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```
The frontend application will start at `http://localhost:5173`.

---

## 🔐 15. Environment Variables

Create `.env` in `prototype/civic-lens-ai/` for backend configuration:

| Variable | Description | Required | Default Value / Placeholder |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Production PostgreSQL connection string | No (falls back to SQLite) | `postgresql://USER:PASSWORD@HOST:5432/DATABASE` |
| `GEMINI_API_KEY` | Google Gemini API key for LLM, Vision, STT & Embeddings | Yes (for live AI calls) | `your_gemini_api_key_here` |
| `LLM_MODEL` | Gemini LLM model identifier | No | `gemini-3.6-flash` |
| `STT_MODEL` | Gemini Speech-to-Text model identifier | No | `gemini-3.6-flash` |
| `VISION_MODEL` | Gemini Vision model identifier | No | `gemini-3.6-flash` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | Yes | `your_super_secret_jwt_key_here` |
| `JURISDICTION_CITY` | Primary target municipal jurisdiction city | No | `Bhubaneswar` |
| `JURISDICTION_STATE`| Primary target state | No | `Odisha` |

Create `.env` in `prototype/civic-lens-frontend/` for frontend configuration:

| Variable | Description | Required | Default Value |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL pointing to FastAPI backend | Production | `http://localhost:8000` (Local) / Render Web Service URL |

> [!CAUTION]
> Never commit actual API keys, database passwords, or JWT secrets to version control. Always use environment variable files (`.env`).

---

## 🗄️ 16. Database Setup & Initialization

### Production Database (PostgreSQL)
When `DATABASE_URL` is configured with a valid PostgreSQL URL (e.g. on Render):
1. CivicLens connects via SQLAlchemy 2.0 with connection pooling (`DATABASE_POOL_SIZE=10`).
2. `init_db()` automatically runs `CREATE EXTENSION IF NOT EXISTS vector;` to enable `pgvector`.
3. SQLAlchemy automatically creates all database tables via `Base.metadata.create_all()`.

### Development Baseline Accounts
Upon database initialization (`init_db()`), baseline test accounts are automatically seeded:

| Email | Password | Role | Purpose |
| :--- | :--- | :--- | :--- |
| `admin@civiclens.gov` | `admin123` | `ADMIN` | System Administrator |
| `supervisor@civiclens.gov` | `supervisor123` | `SUPERVISOR` | Municipal Supervisor |
| `operator@civiclens.gov` | `operator123` | `OPERATOR` | Field Operations Crew |
| `citizen@civiclens.gov` | `citizen123` | `CITIZEN` | Citizen Reporter |

*Note: For future production database schema management, database migration tools such as Alembic should be incorporated.*

---

## 🧪 17. Testing & Verification

CivicLens maintains an extensive, automated test suite covering unit, integration, spatial, and AI regression cases.

### Running Pytest Suite
```bash
cd prototype/civic-lens-ai
python -m pytest
```

### Verified Test Results
```text
================= 242 passed, 5 warnings in 62.19s =================
```

* **Offline Test Execution**: External AI provider API calls (Gemini LLM, Vision, STT) are mocked in pytest using isolated fixtures, ensuring deterministic and offline-executable test execution.

---

## 🚀 18. Deployment Architecture

```
                  ┌─────────────────────────────────────┐
                  │          Render Cloud               │
                  │                                     │
                  │  ┌───────────────────────────────┐  │
                  │  │  Frontend Static Site         │  │
                  │  │  (Vite + React 19 SPA)        │  │
                  │  └──────────────┬────────────────┘  │
                  │                 │ HTTPS             │
                  │                 ▼                   │
                  │  ┌───────────────────────────────┐  │
                  │  │  Backend Web Service          │  │
                  │  │  (FastAPI ASGI Application)   │  │
                  │  └──────────────┬────────────────┘  │
                  │                 │ TCP/SSL           │
                  │                 ▼                   │
                  │  ┌───────────────────────────────┐  │
                  │  │  Managed PostgreSQL DB        │  │
                  │  │  (PostgreSQL + pgvector)      │  │
                  │  └───────────────────────────────┘  │
                  └─────────────────────────────────────┘
```

* **Live Demo URL**: [https://civiclens-frontend-bow7.onrender.com](https://civiclens-frontend-bow7.onrender.com)
* **Frontend Service**: Render Static Site configured to build from `prototype/civic-lens-frontend`.
* **Backend Service**: Render Web Service configured to run `uvicorn app.main:app --host 0.0.0.0 --port $PORT` in `prototype/civic-lens-ai`.

---

## 🔒 19. Security & Privacy

* **Authentication**: JWT access tokens stored in secure, `HTTP-Only`, `SameSite=Lax` cookies.
* **Credential Protection**: Passwords hashed using `bcrypt`.
* **Citizen Anonymization**: Public tracking endpoints use anonymized cryptographic hashes to prevent citizen PII exposure.
* **Evidence Integrity**: Uploaded resolution files are validated against SHA-256 checksums, and EXIF metadata is stripped to protect user location privacy.
* **RBAC Enforcement**: API route dependencies verify user role and jurisdiction privileges before granting operational access.

---

## 🌟 20. Why CivicLens Is Different

1. **True Multimodal AI Ingestion**: Citizens report issues in plain text, local language voice notes, or photos without needing specialized technical knowledge.
2. **Deterministic Spatial Deduplication**: Combines dense vector semantic similarity with spatial distance decay and hard 500m geofencing to prevent duplicate issue creation.
3. **Local Gazette Speed**: Incorporates an in-memory local gazetteer index for instant municipal location resolution without external network bottlenecks.
4. **End-to-End Evidence Loop**: Requires field teams to upload verified evidence, which is audited by supervisors before an issue can be closed.

---

## 🔮 21. Future Scope

* 🏙️ **Multi-City Expansion**: Scale the local spatial gazetteer index to major municipal corporations across India.
* 📱 **Native Mobile Apps**: Develop iOS and Android applications with offline-first complaint syncing.
* 📡 **IoT Sensor Integration**: Connect smart city drainage and waste management sensors directly to the automatic issue reporting pipeline.
* 🌐 **Expanded Vernacular Support**: Direct fine-tuning for regional Indian dialects and speech nuances.

---

## 👥 22. Team & Contributors

Developed for Smart India Hackathon (SIH) evaluation and municipal innovation:
* **Aditya Kaushik** & Team CivicLens

---

## 🤝 23. Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 24. License

Licensing information for this repository has not yet been specified.

---

## 🙏 25. Acknowledgements

* [FastAPI](https://fastapi.tiangolo.com/) for high-performance Python ASGI backend architecture.
* [React](https://react.dev/) & [Vite](https://vitejs.dev/) for fast frontend user experience.
* [Google GenAI SDK](https://github.com/googleapis/python-genai) for Gemini 3.6 Flash & embedding capabilities.
* [OpenStreetMap & Nominatim](https://nominatim.org/) for open geographic data services.
* [Render](https://render.com/) for cloud platform hosting.
