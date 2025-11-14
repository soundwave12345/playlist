FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY create_playlist.py ./

RUN pip install --no-cache-dir mutagen watchdog requests schedule thefuzz fuzzywuzzy python-Levenshtein

RUN mkdir -p /app/music 

VOLUME ["/app/music"]
VOLUME ["/app/mancanti"]

CMD ["tail", "-f", "/dev/null"]
