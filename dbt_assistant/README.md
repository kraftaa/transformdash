# TransformDash AI Search Assistant

AI-powered semantic search for TransformDash models using sentence embeddings and FAISS.

## Overview

The AI Search Assistant enables natural language queries to find relevant models in your TransformDash project. Instead of searching by exact keywords, you can ask questions like "models related to customer revenue" and get semantically similar results.

## Features

- **Semantic Search**: Uses sentence transformers to understand the meaning of your queries
- **FAISS Vector Search**: Fast similarity search across all models
- **Model Metadata Extraction**: Automatically parses SQL models to extract descriptions, dependencies, and layers
- **Similarity Scores**: See how well each result matches your query
- **Optional**: TransformDash works perfectly fine without this module

## Installation

The AI search dependencies are optional. Install them when you want to enable AI-powered search:

```bash
pip install -r dbt_assistant/requirements.txt
```

This installs:
- `sentence-transformers>=2.2.0` - For generating text embeddings (~80MB model)
- `faiss-cpu>=1.7.4` - For fast vector similarity search
- `numpy>=1.21.0` - For numerical operations

## Usage

### In the UI

1. Navigate to the Models view in TransformDash
2. If AI search is available, you'll see an "AI Search" button next to the search box
3. Click "AI Search" to toggle AI mode (button turns blue when active)
4. Type natural language queries like:
   - "customer revenue models"
   - "staging tables for orders"
   - "fact tables in the gold layer"
5. Click on any result to highlight and scroll to that model in the main list

### Programmatically

```python
from dbt_assistant import DbtAssistant

# Initialize with your models directory
assistant = DbtAssistant(models_dir="./models")

# Search for models
results = assistant.search("customer revenue", top_k=5)

# Results include similarity scores
for match in results['embedding_matches']:
    print(f"{match['name']}: {match['similarity_score']:.2%} match")
    print(f"  Description: {match['description']}")
    print(f"  Layer: {match['layer']}")
```

## How It Works

1. **Model Parsing** (`parser.py`):
   - Scans all `.sql` files in the models directory
   - Extracts metadata from SQL comments and config blocks
   - Identifies dependencies using `ref()` and `source()` patterns
   - Determines layer (bronze/silver/gold) from file paths and naming conventions

2. **Embedding Generation** (`embed_search.py`):
   - Uses the `all-MiniLM-L6-v2` model to convert model metadata into vectors
   - Combines model name, description, and layer for comprehensive search
   - Normalizes embeddings for cosine similarity comparison

3. **Vector Search**:
   - FAISS IndexFlatIP for exact similarity search
   - Returns top-k results ranked by similarity score
   - Fast even with thousands of models

## Model Layer Detection

The parser automatically detects model layers based on:

- **Bronze (Staging)**: Files in `staging/` directories or starting with `stg_`
- **Silver (Intermediate)**: Files in `intermediate/` directories or starting with `int_`
- **Gold (Marts)**: Files in `marts/` directories or starting with `fct_` or `dim_`

## Architecture

```
dbt_assistant/
├── __init__.py          # Optional import with graceful fallback
├── core.py              # Main DbtAssistant class
├── parser.py            # SQL model parser
├── embed_search.py      # FAISS semantic search
├── requirements.txt     # Optional dependencies
└── README.md           # This file
```

## API Endpoint

TransformDash exposes the AI search via REST API:

```bash
GET /api/ai/search?q=customer+revenue&top_k=5
```

Response:
```json
{
  "query": "customer revenue",
  "embedding_matches": [
    {
      "name": "fct_customer_revenue",
      "description": "Customer revenue facts by month",
      "layer": "gold",
      "materialized": "table",
      "similarity_score": 0.87,
      "depends_on": ["int_orders", "stg_customers"],
      "file_path": "models/marts/fct_customer_revenue.sql"
    }
  ],
  "total_results": 5
}
```

## Performance

- **Model Loading**: ~80MB download on first run (cached locally)
- **Index Building**: ~1-2 seconds for 100 models
- **Search Speed**: <100ms per query
- **Memory Usage**: ~200MB for the model + index

## Graceful Degradation

If dependencies aren't installed:
- TransformDash continues to work normally
- The AI Search button doesn't appear in the UI
- API endpoint returns 503 with installation instructions
- No errors or crashes - fully optional feature

## Credits

Inspired by [dbt_assistant](https://github.com/kraftaa/dbt_assistant) by kraftaa.
