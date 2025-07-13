FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy code and dependencies
COPY retrieval.py .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for GCP compatibility
ENV PORT=8080

# Expose GCP-required port
EXPOSE 8080

# Start the app using uvicorn
CMD ["uvicorn", "retrieval:app", "--host", "0.0.0.0", "--port", "8080"]
