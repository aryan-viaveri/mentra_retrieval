# Use a slim Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy code and requirements
COPY retrieval.py .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set default command
CMD ["python", "retrieval.py"]
