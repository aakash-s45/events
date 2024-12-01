# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Set the working directory
WORKDIR /app

# Install dependencies required for building packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy the application source code
COPY . .

# Stage 2: Final stage
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only the necessary runtime files from the builder stage
COPY --from=builder /install /usr/local
COPY . .

# Expose the application port
EXPOSE 8004

# Command to run the app
CMD ["uvicorn", "main:app", "--reload", "--port", "8004", "--host", "0.0.0.0"]
