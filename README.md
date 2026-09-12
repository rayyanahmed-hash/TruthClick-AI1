# TruthClick AI

**Does the video deliver what the title promises?**

TruthClick AI analyzes a YouTube video's **title, thumbnail, and transcript** to evaluate whether the actual content supports the promise made to viewers.

## Workflow

YouTube URL → metadata + thumbnail → transcript → promise extraction → semantic comparison → evidence → verdict.

## Verdicts

- **CLICKBAIT**
- **NON_CLICKBAIT**
- **INCONCLUSIVE**

This is not a fact-checking system. It does not determine whether underlying claims are objectively true or false.

## Features

- YouTube URL validation
- Video title, channel, duration and thumbnail retrieval
- Thumbnail-aware AI promise analysis
- Main claim extraction
- Timestamped transcript analysis
- Semantic promise-vs-content comparison
- Evidence and timestamps
- Confidence score
- Professional themed Streamlit UI
- Error handling

## Files

```text
app.py
youtube.py
transcript.py
claim_analyzer.py
content_analyzer.py
verdict.py
prompts.py
requirements.txt
.env.example
.gitignore
README.md
```

## Local setup

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Install:
```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq API key.

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=your_supported_model
MAX_TRANSCRIPT_CHUNKS=12
```

Run:

```bash
streamlit run app.py
```

## Streamlit Cloud

Upload the project files to GitHub. In Streamlit Cloud, choose `app.py` as the main file and add these values under **Secrets**:

```toml
GROQ_API_KEY = "your_real_groq_api_key"
GROQ_MODEL = "your_supported_model"
MAX_TRANSCRIPT_CHUNKS = "12"
```

Never upload `.env` or a real API key to GitHub.

## Important model note

The configured Groq model must support the required text and image input capabilities for thumbnail analysis. If your Groq account uses another currently supported vision-capable model, change `GROQ_MODEL` in `.env` or Streamlit Secrets.

## Limitations

- Some videos have no accessible transcript.
- Private, restricted or unavailable videos may fail.
- Thumbnail analysis requires a vision-capable model.
- AI confidence is an estimate.
- A clickbait verdict does not mean the video's underlying claim is false.
- Transcript analysis only covers information available in the retrieved transcript.
