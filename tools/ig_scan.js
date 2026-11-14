// Correr en un perfil de Instagram abierto (Chrome con sesión iniciada) con la herramienta javascript de Claude in Chrome.
// Devuelve un JSON con estadísticas públicas de las últimas 12 publicaciones.
await new Promise(r => setTimeout(r, 2500));
const og = document.querySelector('meta[property="og:description"]')?.content || '';
const P = {
  "IA y herramientas": /\bia\b|\bai\b|inteligencia artificial|chatgpt|gemini|claude|prompt|agente|copilot|automatiza/i,
  "Promoción y precios": /descuento|oferta|gratis|free|% ?off|promo|black friday|cyber|precio|suscri|inscríbete|últimas horas|sale\b/i,
  "Tips y tutoriales": /tips?|paso a paso|cómo|como hacer|aprende|guía|truco|errores|claves|herramientas/i,
  "Carrera y empleo": /empleo|trabajo|cv|linkedin|entrevista|salario|carrera|career|job/i,
  "Comunidad y eventos": /live|en vivo|conf|evento|comunidad|webinar|estudiantes|graduad|historia de/i,
};
const num = x => { if (!x) return 0; x = String(x).replace(/,/g, ''); return /K$/i.test(x) ? Math.round(parseFloat(x) * 1e3) : /M$/i.test(x) ? Math.round(parseFloat(x) * 1e6) : parseInt(x) || 0; };
const owner = location.pathname.split('/').filter(Boolean)[0];
const links = [...new Set([...document.querySelectorAll('main a[href*="/p/"],main a[href*="/reel/"]')].map(a => a.getAttribute('href')))]
  .filter(l => l.startsWith('/' + owner + '/') || /^\/(p|reel)\//.test(l)).slice(0, 12);
const it = [];
for (const l of links) {
  const h = await (await fetch(l)).text();
  const m = h.match(/property="og:description"[^>]*content="([^"]+)"/) || h.match(/content="([^"]+)"[^>]*property="og:description"/);
  const s = (m ? m[1] : '').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&amp;/g, '&');
  const lk = s.match(/^([\d,.KM]+) likes?/i); const cm = s.match(/([\d,.KM]+) comments?/i); const dt = s.match(/ on ([A-Z][a-z]+ \d{1,2}, \d{4})/);
  const cap = (s.split(': "')[1] || '');
  if (!lk) continue;
  it.push({ t: l.includes('/reel/') ? 'Reel' : 'Post', l: num(lk[1]), c: num(cm && cm[1]), d: dt ? Date.parse(dt[1]) : null,
            p: Object.keys(P).find(k => P[k].test(cap)) || 'Otros' });
}
const avg = a => a.length ? Math.round(a.reduce((s, x) => s + x.l + x.c, 0) / a.length) : 0;
const avgC = a => a.length ? Math.round(a.reduce((s, x) => s + x.c, 0) / a.length) : 0;
const ds = it.map(x => x.d).filter(Boolean); const span = ds.length > 1 ? (Math.max(...ds) - Math.min(...ds)) / 86400000 : null;
const pc = {}; it.forEach(x => pc[x.p] = (pc[x.p] || 0) + 1);
JSON.stringify({ og: og.split(' - ')[0], n: it.length, reels: it.filter(x => x.t == 'Reel').length, avgEng: avg(it), avgCom: avgC(it),
  avgReel: avg(it.filter(x => x.t == 'Reel')), avgPost: avg(it.filter(x => x.t == 'Post')),
  perWeek: span ? +(it.length / (span / 7)).toFixed(1) : null, last: ds.length ? new Date(Math.max(...ds)).toISOString().slice(0, 10) : null,
  pil: pc, pilEng: Object.fromEntries(Object.keys(pc).map(k => [k, avg(it.filter(x => x.p == k))])) });
