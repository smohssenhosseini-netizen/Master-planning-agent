# AI Master Planning Optimization Agent

Clean deployment package for the Streamlit version of the master planning agent.

## Files

- `app.py` - Streamlit app and Python calculation model.
- `requirements.txt` - Python packages needed by the hosted app.
- `.streamlit/secrets.toml.example` - Example secret format. Do not commit a real API key.

## Streamlit Cloud Secret

Add this in Streamlit Cloud under app secrets:

```toml
OPENAI_API_KEY = "your-real-key"
```

## Run Locally

```powershell
streamlit run app.py
```
