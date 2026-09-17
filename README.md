# BurrowSift 0.2.0

BurrowSift is a Python-based document processing application designed to extract, analyse, organise, and index document content.

The application parses document metadata and text, generates structured output, and integrates with locally hosted language models through Ollama for document summarisation and classification.

BurrowSift also includes deterministic file sorting and indexing functionality, allowing processed documents to be transformed from unstructured files into organised and searchable information.

The project is being developed as a modular document-processing platform, with future releases planned to expand file-format support, introduce document chunking, add cloud AI integrations, improve logging and reporting, and provide a graphical user interface and Windows installer.

## Features

BurrowSift 0.2.0 currently includes:

* Document text extraction
* Document metadata extraction
* Structured document processing
* Local AI integration through Ollama
* AI-generated document summaries
* AI-assisted document classification
* Deterministic file sorting
* Document indexing
* Structured processing output
* Modular Python architecture

## Requirements

* Python 3.12+
* Ollama
* A locally installed Ollama-compatible language model

Ollama can be used to run supported language models locally without requiring document content to be sent to a third-party cloud AI provider.

## Installation

Clone the repository:

```bash
git clone https://github.com/BurrowWerks/BurrowSift.git
cd BurrowSift
```

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

### Linux / macOS

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install BurrowSift and its Python dependencies:

```bash
pip install -e .
```

## Ollama Setup

BurrowSift uses Ollama to provide local language-model inference.

Install Ollama separately and ensure the Ollama service is running before starting BurrowSift.

A compatible language model must also be installed through Ollama.

For example:

```bash
ollama pull <model-name>
```

Replace `<model-name>` with the model configured for your BurrowSift installation.

## Project Structure

BurrowSift follows a modular source layout:

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

The application is divided into separate components responsible for document parsing, metadata extraction, AI processing, sorting, indexing, and related operations.

This structure is intended to allow individual parts of the processing pipeline to be expanded or replaced as the project develops.

## Processing Pipeline

At a high level, BurrowSift processes documents through several stages:

```text
Document Input
      │
      ▼
Text & Metadata Extraction
      │
      ▼
Structured Document Data
      │
      ▼
Local AI Processing
  ├── Summary
  └── Classification
      │
      ▼
Deterministic Sorting
      │
      ▼
Indexing
      │
      ▼
Organised Document Output
```

BurrowSift intentionally combines AI-assisted analysis with deterministic processing.

Language models are used where interpretation is useful, such as summarisation and classification, while predictable operations such as file handling and sorting remain deterministic.

## Project Status

BurrowSift is currently under active development.

Version **0.2.0** establishes the core document-processing, local AI, sorting, and indexing pipeline.

The project uses semantic versioning, with each pre-1.0 release representing a defined development milestone toward the first stable release.

## Roadmap

### 0.3.0

Planned areas of development include:

* Additional supported file formats
* Document chunking
* Expanded document-processing pipeline
* Improvements to document ingestion and handling

### 0.4.0

Planned areas of development include:

* Cloud AI provider integration
* Configurable AI providers
* Additional AI-processing options

### 0.5.0

Planned areas of development include:

* Application logging
* Processing reports
* Error reporting
* Operational and reliability improvements

### 0.6.0

Planned areas of development include:

* Graphical user interface
* Windows installer
* Local AI setup assistance
* Improved configuration and onboarding

### 1.0.0

The target for version 1.0.0 is a stable public release suitable for general use.

## Development Goals

BurrowSift is being developed around several core principles:

* Local-first AI where practical
* User control over documents and data
* Deterministic processing where predictable behaviour is required
* Modular architecture
* Clear separation between document extraction, AI analysis, sorting, and indexing
* Extensibility for future local and cloud AI providers
* Practical document-processing workflows for both personal and business use

## Version

Current release:

```text
0.2.0
```

## Licence

See `LICENSE.txt` for licence information.
