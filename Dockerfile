# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# This includes main.py, static/, templates/, docs/
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, good practice)
ENV APP_MODULE main:app
ENV APP_HOST 0.0.0.0
ENV APP_PORT 8000

# Run main.py when the container launches
# Use reload for development, but for production this would be just `uvicorn main:app --host 0.0.0.0 --port 8000`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
