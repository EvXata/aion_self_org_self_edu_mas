# AION Populations — stdlib-only engine, so the image is tiny and the build never breaks.
FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .

EXPOSE 8092
# Default: run the demo, then serve the dashboard.
CMD ["sh", "-c", "aionpop demo && aionpop dashboard --port 8092"]
