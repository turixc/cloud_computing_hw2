# loans/Dockerfile
FROM python:3

# Set the working directory
WORKDIR /app

# Copy the rest of the application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir Flask Flask-RESTful requests pymongo

# Expose the port that the app runs on
EXPOSE 5002

# Command to run the application
CMD ["python", "loans.py"]
