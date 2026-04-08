# Base image for Python 3.11 environment
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy dependency requirements and install
# Layer cached to optimize build times
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code to the container
COPY . .

# Expose port for the FastAPI application
EXPOSE 8000

# Start the uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]