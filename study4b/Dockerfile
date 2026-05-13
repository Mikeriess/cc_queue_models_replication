FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulation.py run_experiments.py generate_plots.py ./
COPY results/calibration.json ./results/calibration.json
COPY results/empirical_nps_multinomial.json ./results/empirical_nps_multinomial.json

RUN mkdir -p /app/results

CMD ["python", "run_experiments.py", \
     "--workers", "24", \
     "--replications", "100", \
     "--days", "365", \
     "--output", "/app/results/results.csv"]
