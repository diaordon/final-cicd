FROM python:3.11-slim
WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole FastAPI package
COPY app ./app

# (optional) if you want the app to see your .env at runtime:
# COPY .env ./

ENV PORT=8000
EXPOSE 8000

# Start the FastAPI app (module: app.main, object: app)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

