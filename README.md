# PPS neo Fachkonzept-Assistent

Lokales Fine-Tuning-System für DOCX-Fachkonzepte. Trainiert ein LLM auf den internen Spezifikationsdokumenten und stellt es über eine Web-Chat-UI zur Verfügung. Kein Cloud-Zugriff erforderlich.

## Funktionsweise

```
DOCX-Dateien
    ↓ Extraktion
Chunks (512 Token)
    ↓ Q&A-Generierung (Ollama, lokal)
train.jsonl / valid.jsonl
    ↓ LoRA Fine-Tuning (MLX, Apple Silicon)
Fine-Tuned Modell
    ↓ mlx_lm.server
Web Chat UI (http://localhost:8000)
```

## Voraussetzungen

- **Mac mit Apple Silicon** (M1/M2/M3/M4) und mindestens 16 GB RAM (empfohlen: 36 GB)
- Python 3.11+
- [Ollama](https://ollama.com) (für die Q&A-Datengenerierung)

## Installation

```bash
# 1. Python-Umgebung einrichten
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Ollama installieren und Modell laden
brew install ollama
ollama serve &
ollama pull llama3.1:8b

# 3. Konfiguration (optional anpassen)
cp .env .env.local   # oder .env direkt bearbeiten

# 4. Setup prüfen
python scripts/check_setup.py
```

## Schritt-für-Schritt

### Schritt 1 — Basismodell laden

```bash
python model/download_base.py
```

Lädt `Meta-Llama-3.1-8B-Instruct` (4-bit quantisiert, ~5 GB) nach `models/llama3.1-8b-base/`.

Für ein anderes Modell:

```bash
python model/download_base.py --model qwen2.5-14b
```

Verfügbare Kurznamen: `llama3.1-8b` (Standard), `llama3.2-3b`, `qwen2.5-14b`, `mistral-7b`

---

### Schritt 2 — DOCX-Dateien extrahieren

DOCX-Dokumente nach `data/raw/` kopieren, dann:

```bash
python scripts/1_extract.py
```

Ergebnis: strukturierte JSON-Dateien in `data/extracted/` mit Chunks, Abschnittsinformationen und Metadaten aus dem Dateinamen.

Unterstützte Dateinamen-Muster:

```
P4123256_PPS_neo-Organisation-Fachspezifikation_EE20.4_V0.1.docx
R22.1_V1.1.docx
```

---

### Schritt 3 — Trainingsdaten generieren

```bash
python scripts/2_generate_qa.py
```

Für jeden Chunk werden via Ollama 3 Frage-Antwort-Paare auf Deutsch generiert. Bei 500 Dokumenten (~50.000 Chunks) dauert dies mehrere Stunden — einmalig ausführen.

Schnelltest mit wenigen Chunks:

```bash
python scripts/2_generate_qa.py --limit 20
```

Ergebnis: `data/training/train.jsonl` und `data/training/valid.jsonl`

---

### Schritt 4 — Fine-Tuning

```bash
bash scripts/3_train.sh
```

Führt LoRA Fine-Tuning mit MLX auf Apple Silicon durch (~2–4 Stunden für 2000 Iterationen). Der Validation Loss wird alle 100 Schritte ausgegeben — er sollte sinken.

Parameter anpassen (z. B. für schnellen Test):

```bash
bash scripts/3_train.sh --iters 500 --batch-size 2
```

---

### Schritt 5 — Adapter fusionieren

```bash
bash scripts/4_fuse.sh
```

Backt den LoRA-Adapter in das Basismodell ein. Ergebnis: `models/ppsneo-finetuned/`

---

### Schritt 6 — Modell starten

In zwei Terminals:

```bash
# Terminal 1: Modell-Server
bash scripts/5_serve.sh

# Terminal 2: Web-API
source .venv/bin/activate
uvicorn api.main:app --reload
```

Web UI öffnen: **http://localhost:8000**

---

## Projektstruktur

```
ppsneo-docmodel/
├── .env                        Konfiguration (Modelle, Pfade, Ports)
├── requirements.txt
│
├── config/
│   └── settings.py             Zentrale Einstellungen (Pydantic)
│
├── data/
│   ├── raw/                    DOCX-Quelldateien (nicht versioniert)
│   ├── extracted/              Extrahierte JSON-Daten (nicht versioniert)
│   └── training/               Generierte JSONL-Trainingsdaten
│
├── extraction/
│   ├── filename_parser.py      Metadaten aus Dateinamen (Modul, Release, Version)
│   ├── docx_extractor.py       DOCX → Text + Tabellen
│   └── chunker.py              Text → 512-Token-Chunks
│
├── training_data/
│   ├── qa_generator.py         Ollama-basierte Q&A-Generierung
│   ├── dataset_builder.py      Q&A → MLX-LM JSONL-Format
│   └── prompt_templates.py     Deutsche Prompts
│
├── model/
│   └── download_base.py        Basismodell von HuggingFace laden
│
├── api/
│   ├── main.py                 FastAPI-App
│   └── routes/
│       ├── chat.py             POST /api/chat/stream (SSE)
│       └── health.py           GET /api/health
│
├── ui/
│   ├── index.html              Chat-Interface
│   ├── style.css
│   └── app.js
│
└── scripts/
    ├── check_setup.py          Voraussetzungen prüfen
    ├── 1_extract.py            Phase 1: Extraktion
    ├── 2_generate_qa.py        Phase 2: Datengenerierung
    ├── 3_train.sh              Phase 3: Fine-Tuning
    ├── 4_fuse.sh               Phase 4: Adapter fusionieren
    └── 5_serve.sh              Phase 5: Modell bereitstellen
```

## Konfiguration (`.env`)

| Variable | Standard | Beschreibung |
|---|---|---|
| `BASE_MODEL_PATH` | `./models/llama3.1-8b-base` | Pfad zum Basismodell |
| `FINETUNED_MODEL_PATH` | `./models/ppsneo-finetuned` | Pfad zum fertig trainierten Modell |
| `ADAPTER_PATH` | `./models/adapters` | LoRA-Adapter während des Trainings |
| `MLX_SERVER_PORT` | `8080` | Port des Modell-Servers |
| `API_PORT` | `8000` | Port der Web-API |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama-Adresse |
| `QA_GENERATOR_MODEL` | `llama3.1:8b` | Modell für Q&A-Generierung |
| `CHUNK_SIZE` | `512` | Token pro Chunk |
| `CHUNK_OVERLAP` | `64` | Überlappung zwischen Chunks |
| `QA_PER_CHUNK` | `3` | Q&A-Paare pro Chunk |
| `TRAIN_SPLIT` | `0.8` | Anteil Trainingsdaten (80 %) |

## Modellauswahl und Speicherbedarf

| Modell | Modellgröße | RAM für Training | Empfehlung |
|---|---|---|---|
| Llama 3.1 8B | ~5 GB | ~18–22 GB | Gut für 16–36 GB |
| Qwen 2.5 14B | ~8 GB | ~28–34 GB | 36 GB, mit `--grad-checkpoint` |
| Mistral 22B+ | ~12 GB | ~44–50 GB | Überschreitet 36 GB |

`--grad-checkpoint` ist im Trainings-Skript standardmäßig aktiviert. Es halbiert den RAM-Bedarf auf Kosten etwas längerer Trainingszeit.

## Neue Dokumente hinzufügen

```bash
# Neue DOCX-Dateien nach data/raw/ kopieren
python scripts/1_extract.py path/to/neue_datei.docx
python scripts/2_generate_qa.py   # generiert nur fehlende Q&A (--resume)
bash scripts/3_train.sh           # erneut trainieren
bash scripts/4_fuse.sh
```

## API-Referenz

### `POST /api/chat/stream`

Streaming-Chat via Server-Sent Events.

```json
{
  "message": "Was ist das Berechtigungskonzept in EE20.4?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response: `text/event-stream`

```
data: {"token": "Das"}
data: {"token": " Berechtigungskonzept"}
...
data: [DONE]
```

### `GET /api/health`

```json
{"status": "ok", "mlx_server": true}
```

## Fehlerbehebung

**`mlx_lm.lora` läuft in einen Speicherfehler**
→ `--batch-size 2` und `--grad-checkpoint` setzen (ist bereits Standard im Skript)

**Ollama antwortet nicht**
→ `ollama serve` in einem separaten Terminal starten

**MLX-Server nicht erreichbar (503 in der UI)**
→ `bash scripts/5_serve.sh` ausführen, warten bis "Server started" erscheint

**DOCX-Datei wird nicht korrekt geparst**
→ Dateinamen-Muster in `extraction/filename_parser.py` prüfen; Metadaten werden auch ohne korrektes Muster extrahiert (Fallback)
