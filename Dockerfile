FROM python:3.11-slim

WORKDIR /app

# Nur die für den Webdienst benötigten Pakete
COPY requirements.txt .
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    pydantic-settings \
    python-dotenv

# Anwendungscode
COPY api/       api/
COPY config/    config/
COPY training_data/prompt_templates.py training_data/prompt_templates.py
COPY training_data/__init__.py         training_data/__init__.py
COPY ui/        ui/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
