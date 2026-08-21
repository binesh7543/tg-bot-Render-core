
const express = require('express');
const { Bot, webhookCallback } = require('grammy');
const { processIncomingMessage } = require('./idChecker');

const app = express();
app.use(express.json());

const bot = new Bot(process.env.BOT_TOKEN);

bot.on('message', async (ctx) => {
  await processIncomingMessage(ctx);
});

app.use('/webhook', webhookCallback(bot, 'express'));

app.get('/', (req, res) => res.send('Router Server Active'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

