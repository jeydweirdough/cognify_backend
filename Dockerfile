# Use an official Python 3.12 slim image
FROM python:3.12-slim

# Create a folder INSIDE the container to hold your code
WORKDIR /app

# Copy your requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your ENTIRE project (main.py, ml, etc.) into that /app folder
COPY . .

# Run your app from inside the /app folder
# This now looks for 'main.py' in the root, which is correct
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]