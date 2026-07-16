# Use the official Apache Airflow image as the base
FROM apache/airflow:2.8.1-python3.9

# Switch to root to perform updates or install system dependencies
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         build-essential \
  && apt-get autoremove -y --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Switch back to the non-root 'airflow' user
USER airflow

# Copy the requirements file and install python packages
COPY --chown=airflow:root requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir --user -r /opt/airflow/requirements.txt

# Copy source code, dags, and config
COPY --chown=airflow:root src/ /opt/airflow/src/
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root config/ /opt/airflow/config/
COPY --chown=airflow:root scripts/ /opt/airflow/scripts/

# Set Python Path to find our src modules
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"
