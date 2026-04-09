FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulation.py run_experiments.py ./

# Opret results-mappe (monteres også som volume udefra)
RUN mkdir -p /app/results

CMD ["python", "run_experiments.py"]
