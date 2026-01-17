FROM node:22-alpine

RUN apk update && apk add --no-cache \
  git \
  curl \
  netcat-openbsd \
  && rm -rf /var/cache/apk/*

WORKDIR /app

COPY --from=ghcr.io/blaxel-ai/sandbox:latest /sandbox-api /usr/local/bin/sandbox-api

# Option 1: Start with a fresh Next.js project
RUN mkdir -p /app \
  && npx create-next-app@latest /app --use-npm --typescript --eslint --tailwind --src-dir --app --import-alias "@/*" --no-git --yes --no-turbopack \
  && npm install @anthropic-ai/claude-code@latest \
  && npm install -g ts-node typescript @types/node

# Copy tsconfig.json to configure TypeScript module resolution
COPY tsconfig.json /app/tsconfig.json

# Copy Gmail API files (into /app/src/gmail/)
COPY src/gmail /app/src/gmail

# Expose ports for Next.js dev server
EXPOSE 3000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add npm global modules to PATH
ENV PATH="/usr/local/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]