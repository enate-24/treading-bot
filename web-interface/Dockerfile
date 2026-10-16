# Multi-stage build for HFT Monitor
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY server/package*.json ./server/
COPY client/package*.json ./client/

# Install dependencies
RUN npm ci --only=production
RUN cd server && npm ci --only=production
RUN cd client && npm ci

# Copy source code
COPY server/ ./server/
COPY client/ ./client/

# Build client
RUN cd client && npm run build

# Production stage
FROM node:18-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create app user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S hftmonitor -u 1001

# Set working directory
WORKDIR /app

# Copy built application
COPY --from=builder --chown=hftmonitor:nodejs /app/server ./server
COPY --from=builder --chown=hftmonitor:nodejs /app/client/build ./client/build
COPY --from=builder --chown=hftmonitor:nodejs /app/server/node_modules ./server/node_modules

# Create directories for logs and config
RUN mkdir -p /app/logs /app/config /app/data
RUN chown -R hftmonitor:nodejs /app

# Switch to non-root user
USER hftmonitor

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:5000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) }).on('error', () => process.exit(1))"

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5000

# Start application
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server/index.js"]