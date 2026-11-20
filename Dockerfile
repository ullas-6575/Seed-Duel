FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    SDL_VIDEODRIVER=x11 \
    SDL_AUDIODRIVER=dummy
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    libgl1 \
    libsdl2-2.0-0 \
    libx11-6 \
    libxcursor1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxxf86vm1 \
    fontconfig \
    novnc \
    websockify \
    x11vnc \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 6080
CMD ["sh", "docker-entrypoint.sh"]
