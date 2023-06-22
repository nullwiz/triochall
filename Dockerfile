# Use the official Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql redis-server libpq-dev gcc

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .  

# Expose the FastAPI port
EXPOSE 5000 

# Set environment variables for database and Redis connection
ENV DB_HOST=postgres
ENV REDIS_HOST=redis
# switch databases here
ENV UOW=sqlalchemy

# If we were deploying in prod, for these we would use AWS Secrets Manager
# given we are using ECS, or any other secret manager. 
ENV AWS_ACCESS_KEY_ID=AKIAQBJ4TNAQEC2LJE4V
ENV AWS_SECRET_ACCESS_KEY=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
ENV AWS_DEFAULT_REGION=us-west-1
# Switch this to anything ig you want to use mailhog instead of AWS Simple Email Service.
ENV environment="dev"
# JWT
ENV SECRET_KEY="d3717b2a1a2a47fe59ce201c199243f16f2d54f8428edddb15afe324b1a81a19"
# Run the FastAPI application with Uvicorn
CMD ["uvicorn", "api.entrypoints.app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
