FROM n8nio/n8n:latest
USER root

RUN npm install -g pdf-parse mammoth pdf2json \
    && npm cache clean --force

ENV NODE_PATH=/usr/local/lib/node_modules
USER node