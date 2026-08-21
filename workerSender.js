async function sendToWorkerOrReply(ctx, payload) {
  const WORKER_1_URL = process.env.WORKER_1_URL;
  const MASTER_TOKEN = process.env.MASTER_TOKEN;
  const SHOULD_FORWARD = process.env.ENABLE_WORKER_FORWARD === 'true';

  if (SHOULD_FORWARD && WORKER_1_URL) {
    try {
      const res = await fetch(WORKER_1_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-master-token': MASTER_TOKEN || ''
        },
        body: JSON.stringify(payload)
      });

      console.log(`[Forwarded] Sent to Worker 1. Status: ${res.status}`);
      await ctx.reply('मैसेज क्लाउडफ्लेयर वर्कर के पास भेज दिया गया है!');
    } catch (err) {
      console.error('[Error] Worker Forward Failed:', err.message);
      await ctx.reply('वर्कर को मैसेज भेजने में एरर आया।');
    }
  } else {
    console.log('[Info] Worker forwarding disabled. Sending text reply.');
    await ctx.reply('नमस्ते! आपका मैसेज मिल गया है। (वर्कर फ़ॉरवर्डिंग अभी ऑफ है)');
  }
}

module.exports = { sendToWorkerOrReply };

