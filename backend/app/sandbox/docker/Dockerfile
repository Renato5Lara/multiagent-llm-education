FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/sandbox

RUN useradd --create-home --shell /usr/sbin/nologin sandbox
WORKDIR /sandbox

COPY runner_payload.py /sandbox/runner_payload.py

USER sandbox:sandbox
ENTRYPOINT ["python", "/sandbox/runner_payload.py"]
