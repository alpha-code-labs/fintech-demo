const { BlobServiceClient } = require('@azure/storage-blob');

const CONTAINER_NAME = 'requirements';
const BLOB_NAME = 'data.json';

async function getBlobClient() {
  const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
  if (!connectionString) {
    throw new Error('AZURE_STORAGE_CONNECTION_STRING not configured');
  }
  const blobServiceClient = BlobServiceClient.fromConnectionString(connectionString);
  const containerClient = blobServiceClient.getContainerClient(CONTAINER_NAME);
  await containerClient.createIfNotExists();
  return containerClient.getBlockBlobClient(BLOB_NAME);
}

async function streamToString(stream) {
  const chunks = [];
  for await (const chunk of stream) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

async function readRequirements(blobClient) {
  try {
    const response = await blobClient.download(0);
    const text = await streamToString(response.readableStreamBody);
    return JSON.parse(text);
  } catch (err) {
    if (err.statusCode === 404) return [];
    throw err;
  }
}

module.exports = async function (context, req) {
  try {
    const blobClient = await getBlobClient();

    if (req.method === 'GET') {
      const requirements = await readRequirements(blobClient);
      context.res = {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: requirements,
      };
    } else if (req.method === 'POST') {
      const { text } = req.body || {};
      if (!text || !text.trim()) {
        context.res = {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
          body: { error: 'Requirement text is required' },
        };
        return;
      }

      const requirements = await readRequirements(blobClient);
      const newRequirement = {
        id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
        text: text.trim(),
        created_at: new Date().toISOString(),
      };
      requirements.unshift(newRequirement);

      const content = JSON.stringify(requirements, null, 2);
      await blobClient.upload(content, Buffer.byteLength(content), {
        blobHTTPHeaders: { blobContentType: 'application/json' },
        overwrite: true,
      });

      context.res = {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
        body: newRequirement,
      };
    }
  } catch (err) {
    context.log.error('Requirements API error:', err.message);
    context.res = {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
      body: { error: err.message || 'Internal server error' },
    };
  }
};
