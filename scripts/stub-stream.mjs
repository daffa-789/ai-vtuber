// Server tiruan untuk menguji jalur streaming tanpa API key. Sementara saja.
import { createServer } from 'node:http';

const POTONGAN = ['[se', 'nyum] Halo ', 'Daffa.', ' [sebal] kok', ' diam sih'];

createServer((req, res) => {
  if (req.url === '/api/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, model: 'stub', key: true }));
    return;
  }
  res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' });
  let i = 0;
  const kirim = () => {
    if (i >= POTONGAN.length) return res.end();
    res.write(POTONGAN[i++]);
    setTimeout(kirim, 120);
  };
  req.resume();
  req.on('end', kirim);
}).listen(8787, '127.0.0.1', () => console.log('stub di 8787'));
