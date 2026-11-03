import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const host = process.env.HOST ?? '127.0.0.1';
const port = Number(process.env.PORT ?? '8765');
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535.');
}

const snarkPackage = JSON.parse(await readFile(new URL('node_modules/snarkjs/package.json', root), 'utf8'));
if (snarkPackage.version !== '0.7.6') {
  throw new Error(`This benchmark requires snarkjs 0.7.6; found ${snarkPackage.version}. Run npm ci.`);
}

// Only these exact routes are served. There is no user-controlled filesystem path.
const routes = new Map([
  ['/', ['browser/index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['browser/index.html', 'text/html; charset=utf-8']],
  ['/worker.js', ['browser/worker.js', 'text/javascript; charset=utf-8']],
  ['/vendor/snarkjs.min.js', ['node_modules/snarkjs/build/snarkjs.min.js', 'text/javascript; charset=utf-8']],
  ['/assets/access.wasm', ['build/access_js/access.wasm', 'application/wasm']],
  ['/assets/access_final.zkey', ['build/access_final.zkey', 'application/octet-stream']],
  ['/assets/verification_key.json', ['build/verification_key.json', 'application/json; charset=utf-8']],
  ['/assets/browser_input.json', ['build/browser_input.json', 'application/json; charset=utf-8']],
]);

const server = createServer(async (request, response) => {
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('Referrer-Policy', 'no-referrer');
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; worker-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'");
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { Allow: 'GET, HEAD', 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Method not allowed.');
    return;
  }

  // Deliberately do not decode or normalize request paths before the allowlist lookup.
  const requestPath = (request.url ?? '').split('?')[0];
  const route = routes.get(requestPath);
  if (!route) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not found.');
    return;
  }

  const [relativePath, contentType] = route;
  const file = new URL(relativePath, root);
  try {
    const metadata = await stat(file);
    if (!metadata.isFile()) throw new Error('Not a regular file.');
    response.writeHead(200, { 'Content-Type': contentType, 'Content-Length': metadata.size });
    if (request.method === 'HEAD') {
      response.end();
      return;
    }
    const stream = createReadStream(file);
    stream.on('error', () => response.destroy());
    response.on('close', () => stream.destroy());
    stream.pipe(response);
  } catch {
    response.writeHead(503, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Benchmark asset unavailable. Run the example setup and generate build/browser_input.json.');
  }
});

server.on('error', (error) => {
  console.error(`Browser benchmark server: ${error.message}`);
  process.exitCode = 1;
});
server.listen(port, host, () => {
  console.log(`PETs4DeFi synthetic browser benchmark: http://${host.includes(':') ? `[${host}]` : host}:${port}/`);
  console.log(`Serving an explicit asset allowlist from ${fileURLToPath(root)}`);
  if (host !== '127.0.0.1' && host !== '::1' && host !== 'localhost') {
    console.log('HOST is non-loopback. Only synthetic demo assets should be present in the served build files.');
  }
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
