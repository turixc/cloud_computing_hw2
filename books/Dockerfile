# books/Dockerfile
FROM python:3

# Set the working directory
WORKDIR /app

# Copy the rest of the application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir Flask flask_restful requests pymongo

COPY check_db.py /app

# Expose the port that the app runs on
EXPOSE 5001

# Command to run the application
CMD ["python", "books.py"]
