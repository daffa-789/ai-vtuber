// Server tiruan untuk menguji jalur streaming tanpa API key. Sementara saja.
// Port mengikuti VTUBER_PORT supaya bisa jalan berdampingan dengan sidecar asli.
import { createServer } from 'node:http';

const PORT = Number(process.env.VTUBER_PORT ?? 8787);

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
}).listen(PORT, '127.0.0.1', () => console.log(`stub di ${PORT}`));
