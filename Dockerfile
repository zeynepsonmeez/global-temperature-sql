# The Streamlit app only. The data pipeline (download, load, models) runs on the host and
# writes to the database; the app just reads it through the read-only role.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /srv

# Dependencies first, so code changes do not reinstall them (layer caching).
COPY requirements-app.txt .
RUN pip install -r requirements-app.txt

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser app/ app/
COPY --chown=appuser sql/ sql/
COPY --chown=appuser .streamlit/ .streamlit/
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
