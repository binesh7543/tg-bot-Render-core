const { sendToWorkerOrReply } = require('./workerSender');

async function processIncomingMessage(ctx) {
  const incomingUserId = ctx.from.id;
  const ALLOWED_ID = Number(process.env.ALLOWED_TELEGRAM_ID);

  if (incomingUserId === ALLOWED_ID) {
    console.log(`[Approved] Message from Owner ID: ${incomingUserId}`);
    
    const payload = {
      chat_id: ctx.chat.id,
      user: ctx.from,
      message: ctx.message
    };

    await sendToWorkerOrReply(ctx, payload);
  } else {
    console.log(`[Ignored] Unauthorized ID: ${incomingUserId}`);
  }
}

module.exports = { processIncomingMessage };

