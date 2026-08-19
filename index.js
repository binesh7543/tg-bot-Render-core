const express = require('express');
const { Bot, webhookCallback } = require('grammy');

const app = express();
app.use(express.json());

// Telegram Bot Init
const bot = new Bot(process.env.BOT_TOKEN);

// Jab bhi user message bheje -> Hello World reply
bot.on('message', async (ctx) => {
  await ctx.reply('Hello World! 🌎🌍');
});

// Render Health Check URL
app.get('/', (req, res) => {
  res.send('Bot Server is Running Perfectly!');
});

// Telegram Webhook Route
app.use('/webhook', webhookCallback(bot, 'express'));

// Server Start
const PORT = process.env.PORT || 3000;
app.listen(PORT, async () => {
  console.log(`Server running on port ${PORT}`);
  
  if (process.env.RENDER_EXTERNAL_URL) {
    const webhookUrl = `${process.env.RENDER_EXTERNAL_URL}/webhook`;
    await bot.api.setWebhook(webhookUrl);
    console.log(`Webhook set to: ${webhookUrl}`);
  }
});

