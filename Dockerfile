# Use an official Python image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies: BLAST and Prodigal
RUN apt-get update && apt-get install -y \
    prodigal \
    ncbi-blast+

# Copy all project files into the container
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for Render
ENV PORT=8080

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
