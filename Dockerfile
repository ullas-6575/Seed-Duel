FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    SDL_VIDEODRIVER=x11 \
    SDL_AUDIODRIVER=dummy \
    SDL_RENDER_DRIVER=software \
    SDL_VIDEO_WINDOW_POS=0,0 \
    LIBGL_ALWAYS_SOFTWARE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    libasound2 \
    libfreetype6 \
    libgl1 \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
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
    novnc \
    websockify \
    x11vnc \
    xvfb \
    && fc-cache -f \
    && printf '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=vnc.html?autoconnect=1&resize=scale"><title>Seed Duel</title>\n' > /usr/share/novnc/index.html \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 6080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6080/vnc.html', timeout=2)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
