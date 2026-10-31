# LuxData Stories

LuxData Stories monitors Luxembourg's open data portal ([data.public.lu](https://data.public.lu)) for dataset updates and automatically generates plain-language news stories that help residents understand what changed and why it matters.

## How It Works

The system runs three cooperative agents in a pipeline:

**Monitor Agent** — Polls the Luxembourg open data API every 6 hours, comparing dataset metadata against stored snapshots. When it detects a new or modified dataset, it flags it for analysis. It handles API failures gracefully and never processes more than 10 datasets per run.

**Analysis Agent** — Downloads the flagged dataset (CSV or JSON), parses the first 500 rows, computes basic statistics, and sends a structured prompt to Groq model. The model returns three focused bullets: what changed, who it affects, and one practical implication. All numbers come directly from the data.

**Writer Agent** — Takes the analysis bullets and generates a 120-150 word news story written in plain English. The story reads like journalism, not marketing copy. It includes specific figures and ends with a pointer to the source data. The agent also generates a concise headline.

## Project Structure

```
luxdata-stories/
├── .env                  # API keys (not committed)
├── .gitignore
├── requirements.txt
├── README.md
├── main.py               # FastAPI entry point
├── render.yaml           # Render.com deployment config
├── Procfile              # Process file for deployment
├── agents/
│   ├── __init__.py
│   ├── monitor_agent.py  # Checks data.public.lu for updates
│   ├── analysis_agent.py # Extracts insights from datasets
│   └── writer_agent.py   # Generates plain-language stories
├── core/
│   ├── __init__.py
│   ├── config.py         # Environment and constants
│   ├── database.py       # ChromaDB persistence layer
│   └── scheduler.py      # Pipeline orchestration
├── api/
│   ├── __init__.py
│   └── routes.py         # REST API endpoints
├── frontend/
│   ├── index.html        # Dashboard UI
│   ├── style.css         # Dark theme styles
│   └── app.js            # Vanilla JS controller
└── data/
    └── .gitkeep
```

## Getting Started

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd luxdata-stories
   ```
2. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**

   ```bash
   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```
4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
5. **Create your `.env` file**

   ```
   GROQ_API_KEY=your_key_here
   ```

   Get a key from [Google AI Studio](https://aistudio.google.com/apikey).
6. **Run the application**

   ```bash
   uvicorn main:app --reload
   ```
7. **Open the dashboard**

   ```
   http://localhost:8000
   ```

The pipeline runs automatically on startup and every 6 hours after that. You can also trigger a manual refresh from the dashboard.

## API Endpoints

| Method | Path                    | Description                                       |
| ------ | ----------------------- | ------------------------------------------------- |
| GET    | `/api/stories`        | List recent stories (optional `?topic=` filter) |
| GET    | `/api/stories/topics` | Topic list with story counts                      |
| GET    | `/api/stats`          | Dashboard statistics                              |
| POST   | `/api/refresh`        | Trigger pipeline manually                         |
| GET    | `/health`             | Health check                                      |

## Data Sources

- **Luxembourg Open Data Portal** — [data.public.lu](https://data.public.lu) (REST API v1)
- **MCP Server** — [mcp.data.public.lu](https://mcp.data.public.lu/mcp)

All data is sourced from publicly available government datasets.

## Tech Stack

- **Backend**: Python, FastAPI, uvicorn
- **Data Processing**: httpx (async HTTP), csv/json parsing
- **Language Model**: Groq  API
- **Storage**: ChromaDB (persistent local vector store)
- **Scheduling**: APScheduler (AsyncIOScheduler)
- **Frontend**: Vanilla HTML, CSS, JavaScript — no frameworks

## Deployment

The project includes configuration for [Render.com](https://render.com):

- `render.yaml` — service definition with build and start commands
- `Procfile` — process specification for web dynos

Set your `GEMINI_API_KEY` as an environment variable in the Render dashboard.

## License

MIT
