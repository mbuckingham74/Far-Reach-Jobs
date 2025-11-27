FROM mcr.microsoft.com/playwright:v1.57.0-jammy

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install --production

# Copy application code
COPY server.js ./

# Expose port
EXPOSE 3000

# Run as non-root user (playwright image includes pwuser)
USER pwuser

CMD ["npm", "start"]
