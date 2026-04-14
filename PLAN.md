# Plan: Lokales LLM Fine-Tuning für DOCX Fachkonzepte (ppsneo-docmodel)

*Prompt*

In einen großen Web Projekt haben wir hunderte DOCX Fachkonzepte über die Jahre erstellt. Darin werden Features in den verschiedenen Versionen beschrieben. Die Aufgabe ist ein geeignetes Modell mit diesen DOCX lokal zu trainieren um dieses später dazu zu per Web UI befragen. Nutze explizit kein RAG. Leider kann ich noch keines davon bereitstellen, da wir keine Freigabe für Cloud KIs haben. 


## Kontext

Hunderte DOCX-Fachkonzepte beschreiben Features eines großen Web-Projekts (PPS neo) über verschiedene Release-Versionen hinweg. Ziel ist es, ein lokales LLM (kein Cloud-Zugriff) auf diese Dokumente zu **fine-tunen** und es dann per Web UI befragen zu können. Hardware: Apple Silicon Mac mit 36GB unified memory.

**Wichtiger Hinweis zu Modellgröße:** Messungen zeigen, dass 20B-Modelle während des LoRA-Trainings bis zu 46GB Speicher benötigen — das übersteigt 36GB. Empfehlung: **Llama 3.1 8B** (sicher, schnell, gutes Deutsch) oder **Qwen2.5-14B** mit `--grad-checkpoint` (grenzwertig, aber möglich). Die Architektur ist modellunabhängig.

---

## Dateinamen-Muster

```
P4123256_PPS_neo-Organisation-Fachspezifikation_EE20.4_V0.1.docx
│         │        │              │               │       └── Dokumentversion
│         │        │              │               └── Software-Release (EE20.4)
│         │        │              └── Dokumenttyp (Fachspezifikation)
│         │        └── Modul (Organisation)
│         └── Projektname (PPS_neo)
└── Ticket-ID (optional)

R22.1_V1.1.docx
│      └── Dokumentversion
└── Release (R22.1) 
```

---

## Pipeline-Überblick

```
DOCX-Dateien
    ↓ Phase 1
Textextraktion (python-docx, Struktur + Tabellen erhalten)
    ↓ Phase 2
Q&A-Datengenerierung (Ollama-LLM erstellt Frage-Antwort-Paare aus Chunks)
    ↓
train.jsonl / valid.jsonl (MLX-LM Chat-Format)
    ↓ Phase 3
Fine-Tuning mit MLX-LM LoRA (Apple Silicon, Metal GPU)
    ↓ Phase 4
Adapter fusionieren → Modell bereitstellen (mlx_lm.server)
    ↓ Phase 5
FastAPI Backend + Web UI (Chat-Interface)
```

---

## Tech Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| LLM-Basis | `mlx-community/Llama-3.1-8B-Instruct-4bit` | Passt sicher in 36GB, gutes Deutsch, Metal GPU |
| Fine-Tuning | MLX-LM LoRA (`mlx-lm` Paket) | Apple-native, keine CUDA nötig |
| Q&A-Generierung | Ollama + Llama 3.1 8B | Lokale Datengenerierung aus DOCX-Chunks |
| DOCX-Parsing | python-docx | Tabellen + Struktur erhalten |
| Modell-Serving | `mlx_lm.server` (OpenAI-kompatibel, Port 8080) | Leichtgewichtig, kein Ollama-Konvertierungsschritt nötig |
| Backend | FastAPI | Proxy zu mlx_lm.server, Streaming |
| Frontend | Vanilla HTML/JS | Kein Build-Toolchain, `EventSource` SSE |

---

## Projektstruktur

```
ppsneo-docmodel/
├── .env                          # Konfiguration (Modell, Pfade, Ports)
├── .gitignore
├── requirements.txt              # Python-Abhängigkeiten
├── config/settings.py            # Pydantic Settings
│
├── data/
│   ├── raw/                      # DOCX-Dateien (git-ignored)
│   ├── extracted/                # Extrahierter Text als .txt/.json (git-ignored)
│   └── training/                 # Generierte JSONL-Dateien
│       ├── train.jsonl
│       └── valid.jsonl
│
├── extraction/
│   ├── docx_extractor.py         # DOCX → strukturierter Text + Metadaten
│   ├── filename_parser.py        # Modul/Release/Version aus Dateinamen
│   └── chunker.py                # Text → Chunks (512 Token, 64 Overlap)
│
├── training_data/
│   ├── qa_generator.py           # Ollama LLM generiert Q&A aus Chunks
│   ├── dataset_builder.py        # Q&A → train.jsonl / valid.jsonl (80/20 Split)
│   └── prompt_templates.py       # Prompts für Q&A-Generierung (Deutsch)
│
├── model/
│   ├── download_base.py          # Basis-Modell von HuggingFace laden
│   └── fuse_adapter.py           # LoRA-Adapter in Basismodell fusionieren
│
├── api/
│   ├── main.py                   # FastAPI App + Static Files
│   └── routes/
│       ├── chat.py               # POST /api/chat (Proxy zu mlx_lm.server)
│       └── health.py             # GET /api/health
│
├── ui/
│   ├── index.html                # Chat-Interface
│   ├── style.css
│   └── app.js                    # Fetch API für Chat
│
└── scripts/
    ├── 1_extract.py              # DOCX → extracted/
    ├── 2_generate_qa.py          # extracted/ → training/train.jsonl
    ├── 3_train.sh                # mlx_lm.lora Fine-Tuning-Kommando
    ├── 4_fuse.sh                 # mlx_lm.fuse Adapter fusionieren
    ├── 5_serve.sh                # mlx_lm.server starten
    └── check_setup.py            # Ollama + mlx-lm Installation prüfen
```

---

## Implementierungsphasen

### Phase 0: Umgebung einrichten

```bash
# MLX-LM installieren
pip install mlx-lm python-docx httpx tqdm fastapi uvicorn pydantic-settings

# Ollama für Q&A-Generierung (während Datenvorbereitung)
brew install ollama
ollama pull llama3.1:8b

# Basismodell laden (scripts/download_base.py)
mlx_lm.convert --hf-path meta-llama/Llama-3.1-8B-Instruct \
                --mlx-path ./models/llama3.1-8b-base \
                -q --q-bits 4
```

### Phase 1: DOCX-Extraktion (`scripts/1_extract.py`)

`extraction/filename_parser.py`:
- Regex für beide Muster: `P4123256_PPS_neo-{Modul}-{Typ}_{Release}_V{Version}` und `R{Release}_V{Version}`
- Extrahiert: `module`, `release`, `doc_version`, `doc_type`, `ticket_id`

`extraction/docx_extractor.py`:
- Iteriert `document.element.body` in Dokumentreihenfolge (Absätze + Tabellen)
- Tabellen als strukturierten Text: `"TABELLE:\nSpalte1 | Spalte2\nWert1 | Wert2"`
- Gibt `DocumentContent` dataclass zurück mit Abschnitten und Metadaten
- Output: `data/extracted/{filename}.json`

`extraction/chunker.py`:
- 512 Token / 64 Token Overlap (tiktoken, cl100k_base)
- Behält Section-Heading als Metadatum pro Chunk

### Phase 2: Trainingsdaten generieren (`scripts/2_generate_qa.py`)

`training_data/qa_generator.py`:
- Iteriert Chunks aus `data/extracted/`
- Sendet jeden Chunk an Ollama (llama3.1:8b) mit deutschem Prompt:
  ```
  Erstelle 3 spezifische Frage-Antwort-Paare auf Deutsch zu folgendem Fachkonzept-Abschnitt.
  Die Fragen sollen praxisnah sein (wie ein Entwickler oder Fachexperte sie stellen würde).
  Antworte im JSON-Format: [{"frage": "...", "antwort": "..."}]
  
  Abschnitt: {chunk_text}
  ```
- Fehlertoleranz: bei JSON-Parse-Fehlern den Chunk überspringen

`training_data/dataset_builder.py`:
- Q&A-Paare → MLX-LM Chat-Format:
  ```json
  {"messages": [
    {"role": "system", "content": "Du bist ein Experte für das PPS neo System..."},
    {"role": "user", "content": "{frage}"},
    {"role": "assistant", "content": "{antwort}"}
  ]}
  ```
- 80/20 Split → `data/training/train.jsonl` + `data/training/valid.jsonl`
- Ziel: ~3.000–10.000 Q&A-Paare aus den Fachkonzepten

### Phase 3: Fine-Tuning (`scripts/3_train.sh`)

```bash
mlx_lm.lora \
  --model ./models/llama3.1-8b-base \
  --train \
  --data data/training/ \
  --batch-size 4 \
  --grad-checkpoint \
  --iters 2000 \
  --steps-per-eval 100 \
  --val-batches 25 \
  --learning-rate 1e-5 \
  --lora-layers 16 \
  --adapter-path ./models/adapters/
```

`--grad-checkpoint` ist pflicht: Tauscht Rechenzeit gegen Speicher, halbiert den RAM-Bedarf.  
Erwartete Trainingszeit: ~2–4 Stunden für 2000 Iterationen auf M-series.

### Phase 4: Adapter fusionieren (`scripts/4_fuse.sh`)

```bash
mlx_lm.fuse \
  --model ./models/llama3.1-8b-base \
  --adapter-path ./models/adapters/ \
  --save-path ./models/ppsneo-finetuned/
```

### Phase 5: Modell bereitstellen (`scripts/5_serve.sh`)

```bash
mlx_lm.server \
  --model ./models/ppsneo-finetuned/ \
  --port 8080
```

Stellt OpenAI-kompatible API bereit: `POST http://localhost:8080/v1/chat/completions`

### Phase 6: FastAPI + Web UI

`api/routes/chat.py` — Proxy zu `mlx_lm.server` mit SSE-Streaming:
```python
# POST /api/chat → weiterleiten an localhost:8080/v1/chat/completions
# Streaming via httpx AsyncClient
```

`ui/index.html` — Chat-Interface mit:
- Einfaches Chat-Fenster mit Nachrichtenverlauf
- Streaming-Antworten via `fetch` mit `ReadableStream`
- `localStorage` für Chat-History

---

## Schlüssel-Konfiguration (`.env`)

```ini
BASE_MODEL_PATH=./models/llama3.1-8b-base
FINETUNED_MODEL_PATH=./models/ppsneo-finetuned
ADAPTER_PATH=./models/adapters
MLX_SERVER_PORT=8080
API_PORT=8000
OLLAMA_BASE_URL=http://localhost:11434
QA_GENERATOR_MODEL=llama3.1:8b
CHUNK_SIZE=512
CHUNK_OVERLAP=64
QA_PER_CHUNK=3
TRAIN_SPLIT=0.8
```

---

## Modellauswahl: Speicheranforderungen

| Modell | 4-bit Größe | Training RAM (LoRA) | Empfehlung |
|---|---|---|---|
| Llama 3.1 8B | ~5 GB | ~18–22 GB | ✅ Sicher auf 36 GB |
| Qwen2.5-14B | ~8 GB | ~28–34 GB | ⚠️ Eng, `--grad-checkpoint` pflicht |
| Mistral 22B / 20B | ~12 GB | ~44–50 GB | ❌ Übersteigt 36 GB |

**Empfehlung:** Mit Llama 3.1 8B starten. Qualität und Trainingsgeschwindigkeit sind auf Apple Silicon sehr gut.

---

## Kritische Dateien

- `extraction/docx_extractor.py` — Tabellen-Erhalt entscheidend für Fachkonzepte
- `extraction/filename_parser.py` — PPS-Namensschema (zwei Muster!)
- `training_data/qa_generator.py` — Qualität der Q&A bestimmt Fine-Tuning-Erfolg
- `training_data/dataset_builder.py` — MLX Chat-Format korrekt erzeugen
- `scripts/3_train.sh` — `--grad-checkpoint` nicht vergessen

---

## Verifikation

1. `python scripts/check_setup.py` — Ollama + mlx-lm installiert, Modelle vorhanden
2. `python scripts/1_extract.py data/raw/` — 2–3 Test-DOCX extrahieren, Output prüfen
3. `python scripts/2_generate_qa.py --limit 5` — Q&A für 5 Chunks generieren, JSONL prüfen
4. `bash scripts/3_train.sh` — Training starten, Validation Loss beobachten
5. `bash scripts/5_serve.sh` → `curl localhost:8080/v1/chat/completions` — Modell antworten lassen
6. `uvicorn api.main:app` + Browser → Chat testen

---

## Ablaufsequenz

| Schritt | Skript | Einmalig/Wiederholt |
|---|---|---|
| DOCX extrahieren | `scripts/1_extract.py` | Wiederholt bei neuen Docs |
| Q&A generieren | `scripts/2_generate_qa.py` | Wiederholt bei neuen Docs |
| Fine-Tunen | `scripts/3_train.sh` | Bei neuen Trainingsdaten |
| Fusionieren | `scripts/4_fuse.sh` | Nach jedem Training |
| Servieren | `scripts/5_serve.sh` | Dauerhaft |
