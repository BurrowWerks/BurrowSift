# BurrowSift 0.2.0

BurrowSift is a Python-based document processing application designed to extract, analyse, organise, and index document content.

The application parses document metadata and text, generates structured output, and integrates with locally hosted language models through Ollama for document summarisation and classification.

BurrowSift combines AI-assisted document analysis with deterministic file handling, sorting, and indexing. Processed document information is stored in SQLite as the operational source of truth, while selected analytical data is synchronised to DuckDB for future analysis and reporting.

The project is being developed as a document-processing platform, with future releases planned to expand file-format support, introduce document chunking, add cloud AI integrations, improve logging and reporting, modularise the application, and provide a graphical user interface and Windows installer.

## Features

BurrowSift 0.2.0 currently includes:

* PDF, DOCX, and TXT document processing
* Document text extraction
* Document metadata extraction
* Character, word, and token counting
* Structured document processing
* Local AI integration through Ollama
* AI-generated document summaries
* AI-assisted document classification
* Controlled category and subcategory classification
* Structured JSON processing output
* Deterministic file sorting
* Document pair validation
* File-move rollback protection
* SQLite operational document indexing
* DuckDB analytical data storage
* Automatic SQLite-to-DuckDB synchronisation
* Automatic restoration of missing DuckDB records from SQLite
* Processing and inference statistics
* Automatic Ollama service detection
* Automatic Ollama startup when required
* Ownership-aware Ollama shutdown
* Managed SQLite and DuckDB connection lifecycle

## Requirements

BurrowSift 0.2.0 currently targets Windows.

Requirements include:

* Python 3.12+
* Ollama
* A compatible locally installed language model
* Sufficient local system memory and model storage
* Access to the configured BurrowSift storage directories

BurrowSift uses Ollama to perform language-model inference locally, allowing document content to be processed without requiring it to be sent to a third-party cloud AI provider.

The current 0.2.0 development configuration uses a locally hosted Gemma 4 12B model through Ollama.

Model selection, context configuration, and storage paths are currently defined within the application and are not yet exposed through a user configuration interface.

## Installation

Clone the repository:

```bash
git clone https://github.com/BurrowWerks/BurrowSift.git
cd BurrowSift
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install BurrowSift and its Python dependencies:

```powershell
pip install -e .
```

> BurrowSift is currently under active development. The 0.2.0 build is not yet intended as a general end-user installation.

## Ollama Setup

BurrowSift uses Ollama to provide local language-model inference.

Install Ollama separately before running BurrowSift.

BurrowSift checks whether the Ollama API is already available when the application starts.

If Ollama is already running, BurrowSift connects to the existing service and leaves it running when processing is complete.

If Ollama is not running, BurrowSift starts the Ollama service automatically using the configured runtime settings. When BurrowSift owns the Ollama process, it also shuts that process down when processing finishes.

A compatible language model must be installed in Ollama before document processing can occur.

The current development configuration expects the model configured within the BurrowSift source.

Future releases are planned to provide easier model selection and configuration.

## Supported Document Formats

BurrowSift 0.2.0 currently supports:

* `.pdf`
* `.docx`
* `.txt`

Additional file formats are planned for version 0.3.0.

## Project Structure

BurrowSift currently follows a source-based project layout:

```text
BurrowSift/
├── src/
│   └── ...
├── tests/
│   └── ...
├── pyproject.toml
├── README.md
├── LICENSE.txt
└── .gitignore
```

The current development implementation contains clearly separated processing stages, although substantial code modularisation is still planned before the 1.0.0 release.

Future refactoring will separate major responsibilities such as document parsing, AI processing, database operations, sorting, configuration, and application lifecycle management into dedicated modules.

## Processing Pipeline

At a high level, BurrowSift 0.2.0 processes documents through the following pipeline:

```text
Document Input
      │
      ▼
Text & Metadata Extraction
      │
      ▼
Character / Word / Token Analysis
      │
      ▼
Structured Document Data
      │
      ▼
Local AI Processing
  ├── Summary
  ├── Classification
  └── Tags
      │
      ▼
Structured JSON Output
      │
      ▼
Staging & Pair Validation
      │
      ▼
Deterministic Sorting
      │
      ▼
SQLite Operational Index
      │
      ▼
DuckDB Analytical Store
      │
      ▼
Organised & Indexed Document Output
```

BurrowSift intentionally combines AI-assisted interpretation with deterministic processing.

Language models are used where interpretation is useful, such as summarisation and classification.

Predictable operations such as file handling, database storage, document pairing, synchronisation, and sorting remain deterministic.

## Database Architecture

BurrowSift 0.2.0 uses two local databases with separate responsibilities.

### SQLite

SQLite acts as BurrowSift's operational source of truth.

It stores document records including:

* Document identifiers
* Source file information
* Original and current file paths
* JSON output paths
* File type and size
* Classification information
* Document summaries
* Processing timestamps
* AI model information
* Processing duration
* Token counts
* Inference statistics
* Context-window configuration

### DuckDB

DuckDB stores a derived analytical representation of selected document-processing data.

It is intended to support future analytics, reporting, and data-analysis functionality without replacing SQLite as the authoritative document index.

BurrowSift compares document identifiers between SQLite and DuckDB during startup.

If records exist in SQLite but are missing from DuckDB, BurrowSift automatically retrieves the corresponding analytical data from SQLite and restores the missing DuckDB records.

This means the DuckDB analytical database can recover from missing records while SQLite remains the authoritative source.

## Local AI Processing

BurrowSift sends structured document content to a locally hosted Ollama model.

The model is responsible for returning structured information containing:

* Category
* Subcategory
* Summary
* Tags

Classification is constrained by a predefined schema rather than allowing the model to freely invent filing categories.

The current top-level categories include:

* Employment
* Finance
* Business
* Technology
* Education
* Legal
* Government
* Health
* Property
* Insurance
* Personal
* Reference
* Entertainment
* Other

Documents that do not clearly fit an existing classification can fall back to:

```text
Other / Uncategorized
```

## Processing Limits

BurrowSift 0.2.0 currently processes documents as a single AI request.

The current document-processing ceiling is:

```text
180,000 document tokens
```

The configured local AI context window is larger than this limit to leave room for BurrowSift's prompt, metadata, classification instructions, and model output.

Documents exceeding the current processing limit are rejected before being sent to the AI model.

Document chunking is planned for version 0.3.0.

## Resource Management

BurrowSift 0.2.0 includes explicit lifecycle management for its local resources.

SQLite and DuckDB connections are closed when processing completes or when the application exits through an error path.

Ollama process ownership is also tracked.

If Ollama was already running before BurrowSift started, BurrowSift leaves it running.

If BurrowSift started Ollama itself, BurrowSift attempts a graceful shutdown when processing is complete and can force termination if the process does not exit within the expected period.

## Project Status

BurrowSift is currently under active development.

Version **0.2.0** establishes the complete local document-processing pipeline, including:

* Document parsing
* Metadata and content extraction
* Local AI classification and summarisation
* Structured JSON generation
* Deterministic document sorting
* SQLite operational indexing
* DuckDB analytical storage
* Automatic database synchronisation and recovery
* Processing analytics
* Managed database connections
* Managed Ollama process lifecycle

The project uses semantic versioning, with each pre-1.0 release representing a defined development milestone toward the first stable public release.

## Roadmap

### 0.3.0

Planned areas of development include:

* Additional supported file formats
* Document chunking
* Large-document processing
* Expanded document-processing pipeline
* Improvements to document ingestion and handling

### 0.4.0

Planned areas of development include:

* Cloud AI provider integration
* Configurable AI providers
* Additional AI-processing options
* Improved model configuration

### 0.5.0

Planned areas of development include:

* Application logging
* Processing reports
* Error reporting
* Retry tracking
* Processing-status tracking
* Failure recovery improvements
* Operational and reliability improvements

### 0.6.0

Planned areas of development include:

* Graphical user interface
* Windows installer
* Local AI setup assistance
* Improved configuration and onboarding

### 1.0.0

The target for version 1.0.0 is a stable public release suitable for general use.

Development before 1.0.0 will also include broader codebase modularisation and refactoring as the processing architecture stabilises.

## Development Goals

BurrowSift is being developed around several core principles:

* Local-first AI where practical
* User control over documents and data
* Deterministic processing where predictable behaviour is required
* Clear separation of processing responsibilities
* SQLite as the operational source of truth
* Rebuildable analytical data
* Extensibility for future local and cloud AI providers
* Transparent document-processing workflows
* Practical use for both personal and business document management
* Progressive modularisation as the application architecture matures

## Related BurrowWerks Projects

BurrowSift is part of the broader BurrowWerks project family.

Future BurrowWerks applications are intended to build on different parts of the document and data-processing workflow while remaining separate tools with clearly defined responsibilities.

BurrowSift's primary responsibility is:

```text
Ingest → Analyse → Classify → Sort → Index
```

Document search and retrieval are intended to remain separate from BurrowSift's core processing responsibilities.

## Version

Current development release:

```text
0.2.0
```

## Licence

See `LICENSE.txt` for licence information.
