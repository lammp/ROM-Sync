const fs = require('fs'), http = require('http');
const src = fs.readFileSync('D:/Games/ROM-Sync/ui/app.js', 'utf8');
const block = src.slice(src.indexOf('const TWIN_ROMAN'), src.indexOf('function twinBadge'));
const S = { games: [] };
eval(block);
http.get(`http://127.0.0.1:${process.argv[2]}/api/library`, (res) => {
  let b = ''; res.on('data', d => b += d);
  res.on('end', () => {
    const lib = JSON.parse(b);
    S.games = lib.games;
    const t0 = Date.now(); buildTwins(); const ms = Date.now() - t0;
    let n = 0, loose = 0;
    for (const g of S.games) { const t = twinsOf(g); if (t.length) { n++; loose += t.filter(x => x.loose).length; } }
    console.log(`games ${S.games.length}, with twins ${n}, loose links ${loose}, ${ms} ms`);
    const show = (needle) => {
      const g = S.games.find(x => (x.title || x.name || '').toLowerCase().includes(needle));
      if (!g) return console.log(`  ${needle}: not in library`);
      const t = twinsOf(g);
      console.log(`  ${g.system} "${g.title || g.name}" -> ` +
        (t.length ? t.map(x => `${x.g.system}:${x.g.title || x.g.name}${x.loose ? ' [loose]' : ''}`).join(' | ') : '(none)'));
    };
    ['ocarina', "majora's mask", 'luigi\u2019s mansion', "luigi's mansion", 'donkey kong country returns',
     'earthworm jim', 'killer instinct', 'metroid prime', 'penny racers', 'battletoads'].forEach(show);
  });
}).on('error', e => { console.error(e.message); process.exit(2); });
