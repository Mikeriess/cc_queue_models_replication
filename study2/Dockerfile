FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulation.py run_experiments.py generate_plots.py ./

# Opret results-mappe (monteres også som volume udefra)
RUN mkdir -p /app/results

# Standard: kør eksperiment med 24 kerner og gem i /app/results/
CMD ["python", "run_experiments.py", \
     "--workers", "24", \
     "--replications", "100", \
     "--days", "365", \
     "--output", "/app/results/results.csv"]
