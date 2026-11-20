# R with the KST packages, plus Python for the platform core.
FROM rocker/r-ver:4.4.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN Rscript -e 'install.packages(c("jsonlite", "sets", "relations", "kst", "pks", "DAKS"))' \
    && Rscript -e 'for (p in c("jsonlite", "kst", "pks", "DAKS")) library(p, character.only = TRUE)'

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml ./
COPY core ./core
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["pytest", "-q"]
