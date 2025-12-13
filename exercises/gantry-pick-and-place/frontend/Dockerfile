FROM node:24-alpine

WORKDIR /app

COPY . .

RUN npm ci

RUN npm install -g serve

EXPOSE 3000

CMD ["sh", "-c", "npm run codegen && npm run build && serve -s dist -l 3000"]
