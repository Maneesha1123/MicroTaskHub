FROM node:20-alpine

ENV NODE_ENV=production
WORKDIR /app

COPY package*.json ./
RUN npm install --production --silent

COPY public ./public
COPY server.js ./

EXPOSE 3000

CMD ["npm", "start"]
