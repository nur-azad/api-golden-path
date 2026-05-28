FROM node:20-slim

WORKDIR /workspace

RUN npm install -g @stoplight/spectral-cli@6.8.0

ENTRYPOINT ["spectral", "lint"]
