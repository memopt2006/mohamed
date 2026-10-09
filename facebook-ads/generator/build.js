// Builds 7 Facebook ad designs (1080x1350, 4:5 feed) per screenshot.
const fs = require('fs');
const path = require('path');
const { chromium } = require('/opt/node-tools/node_modules/playwright');

const S = path.resolve(__dirname, '..');  // expects ../screenshots, writes ../designs
const SRC = path.join(S, 'screenshots');
const OUT = path.join(S, 'designs');
const HTML = path.join(require('os').tmpdir(), 'fb-ads-html');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(HTML, { recursive: true });

const W = 1080, H = 1350;
const IMG_W = 1290, IMG_H = 2796;
const NAVY = '#13215c', NAVY2 = '#1d2f86', GOLD = '#b38b4d', GOLD_L = '#e7c992', CREAM = '#fbf3e4';

const shots = require('./copy.js');

// ---------- phone mockup ----------
const FRAMES = {
  blue:   'linear-gradient(135deg,#3b4a6b 0%,#1e2a44 30%,#56688f 55%,#1b2640 80%,#41537a 100%)',
  silver: 'linear-gradient(135deg,#f4f5f7 0%,#c9ccd2 30%,#ffffff 55%,#b7bbc3 80%,#e6e8ec 100%)',
  orange: 'linear-gradient(135deg,#ff9a4d 0%,#d9601a 30%,#ffb27a 55%,#c4520f 80%,#f07a2e 100%)',
};
function phoneGeom(w) {
  const f = w * 0.034;
  const sw = w - 2 * f;
  const sh = sw * IMG_H / IMG_W;
  return { w, f, sw, sh, h: sh + 2 * f, r: w * 0.165 };
}
// highlights: [{x0,x1,y0,y1,n}] boxes drawn on the screen; dim: dim everything else
function phone(img, w, color = 'blue', opts = {}) {
  const g = phoneGeom(w);
  const hl = (opts.highlights || []).map(b => `
    <div class="hl" style="left:${b.x0 * 100}%;top:${b.y0 * 100}%;width:${(b.x1 - b.x0) * 100}%;height:${(b.y1 - b.y0) * 100}%;
      border-radius:${g.sw * 0.045}px;${opts.dim ? 'box-shadow:0 0 0 9999px rgba(10,16,48,.62),0 0 0 4px ' + GOLD_L + ';' : 'box-shadow:0 0 0 4px ' + GOLD_L + ',0 0 28px 6px rgba(231,201,146,.55);'}">
      ${b.n ? `<span class="hln">${b.n}</span>` : ''}
    </div>`).join('');
  const btn = (side, top, len) => `<div class="pbtn" style="${side}:-${w * 0.008}px;top:${top}px;height:${len}px;width:${w * 0.012}px;background:${FRAMES[color]}"></div>`;
  return `
  <div class="phone" style="width:${g.w}px;height:${g.h}px;border-radius:${g.r}px;background:${FRAMES[color]};${opts.style || ''}">
    ${btn('left', g.h * 0.17, g.h * 0.045)}${btn('left', g.h * 0.24, g.h * 0.075)}${btn('left', g.h * 0.33, g.h * 0.075)}
    ${btn('right', g.h * 0.27, g.h * 0.11)}${btn('right', g.h * 0.62, g.h * 0.07)}
    <div class="bezel" style="inset:${w * 0.011}px;border-radius:${g.r - w * 0.011}px"></div>
    <div class="screen" style="inset:${g.f}px;border-radius:${g.r - g.f}px">
      <img src="${img}">
      ${hl}
      <div class="island" style="width:${g.sw * 0.29}px;height:${g.sw * 0.085}px;top:${g.sw * 0.026}px"></div>
    </div>
  </div>`;
}
// page coords of a screen fraction point for an unrotated phone placed at (left,top)
function pt(left, top, w, fx, fy) {
  const g = phoneGeom(w);
  return [left + g.f + fx * g.sw, top + g.f + fy * g.sh];
}
// magnified crop of the screenshot
function zoom(img, b, bw, extra = '') {
  const sc = bw / ((b.x1 - b.x0) * IMG_W);
  return `<div class="zoom" style="width:${bw}px;height:${(b.y1 - b.y0) * IMG_H * sc}px;
    background-image:url('${img}');background-size:${IMG_W * sc}px auto;
    background-position:${-b.x0 * IMG_W * sc}px ${-b.y0 * IMG_H * sc}px;${extra}"></div>`;
}

const logo = (dark) => `<div class="logo ${dark ? 'dark' : ''}"><span class="mark">EDX</span><span>EduCross NPTE</span></div>`;
const cta = (txt, kind = 'gold') => `<div class="cta ${kind}">${txt} <span class="arr">→</span></div>`;

const BASE_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:${W}px;height:${H}px;overflow:hidden}
body{font-family:'Plus Jakarta Sans','Inter',sans-serif;position:relative;-webkit-font-smoothing:antialiased}
.abs{position:absolute}
.phone{position:absolute;box-shadow:0 50px 90px -20px rgba(5,10,40,.55),0 20px 40px -10px rgba(5,10,40,.35),inset 0 0 0 1.5px rgba(255,255,255,.25)}
.pbtn{position:absolute;border-radius:4px}
.bezel{position:absolute;background:#050505}
.screen{position:absolute;overflow:hidden;background:#f4f5fa}
.screen img{width:100%;height:100%;display:block}
.island{position:absolute;left:50%;transform:translateX(-50%);background:#000;border-radius:999px;z-index:5}
.hl{position:absolute;z-index:3}
.hln{position:absolute;left:-8px;top:-12px;width:40px;height:40px;border-radius:50%;background:${GOLD};color:#fff;font-weight:800;font-size:22px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(0,0,0,.3)}
.zoom{border-radius:26px;background-repeat:no-repeat;box-shadow:0 30px 60px -15px rgba(10,20,70,.45),0 0 0 6px #fff}
.logo{display:flex;align-items:center;gap:12px;font-weight:700;font-size:26px;color:#fff;letter-spacing:.2px}
.logo.dark{color:${NAVY}}
.logo .mark{background:${GOLD};color:#fff;font-weight:800;padding:6px 12px;border-radius:10px;font-size:24px;letter-spacing:1px}
.eyebrow{font-weight:800;letter-spacing:4px;font-size:22px;text-transform:uppercase;color:${GOLD}}
h1{font-weight:800;letter-spacing:-1.5px;line-height:1.04}
.cta{display:inline-flex;align-items:center;gap:14px;font-weight:800;font-size:30px;padding:22px 40px;border-radius:999px}
.cta.gold{background:${GOLD};color:#fff;box-shadow:0 14px 30px -10px rgba(179,139,77,.8)}
.cta.navy{background:${NAVY};color:#fff;box-shadow:0 14px 30px -10px rgba(19,33,92,.7)}
.cta.white{background:#fff;color:${NAVY}}
.card{position:absolute;background:#fff;border-radius:26px;padding:24px 28px;box-shadow:0 24px 50px -16px rgba(5,10,40,.45)}
.card .t{font-weight:800;font-size:30px;color:${NAVY};line-height:1.15}
.card .d{font-weight:500;font-size:22px;color:#4a5272;line-height:1.35;margin-top:8px}
.num{display:inline-flex;width:44px;height:44px;border-radius:50%;background:${GOLD};color:#fff;font-weight:800;font-size:24px;align-items:center;justify-content:center;flex:none}
.gl{color:${GOLD_L}}
.gd{color:${GOLD}}
`;

function svgLines(lines, color) {
  return `<svg class="abs" style="left:0;top:0;z-index:6" width="${W}" height="${H}">${lines.map(([x1, y1, x2, y2]) => `
    <path d="M${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}" stroke="${color}" stroke-width="4" fill="none" stroke-dasharray="2 10" stroke-linecap="round"/>
    <circle cx="${x2}" cy="${y2}" r="12" fill="${color}" opacity=".35"/><circle cx="${x2}" cy="${y2}" r="7" fill="${color}"/>`).join('')}</svg>`;
}
const mid = b => [(b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2];

const HERO_THEMES = {
  navy: { bg: `radial-gradient(circle at 85% 8%,#2c3f9e 0,transparent 40%),radial-gradient(circle at 10% 90%,#3a2f6a 0,transparent 45%),${NAVY}`,
    ring: 'rgba(231,201,146,.18)', dark: false, eyebrow: GOLD_L, h1: '#fff', frame: 'blue', line: GOLD_L, cta: 'gold' },
  cream: { bg: `radial-gradient(circle at 85% 8%,#f6dfb3 0,transparent 42%),radial-gradient(circle at 10% 90%,#f1d8a8 0,transparent 45%),linear-gradient(160deg,${CREAM} 0%,#f3e3c4 100%)`,
    ring: 'rgba(179,139,77,.3)', dark: true, eyebrow: GOLD, h1: NAVY, frame: 'silver', line: GOLD, cta: 'navy' },
};
const hero = (theme) => (s, img) => {
  const t = HERO_THEMES[theme];
    const pw = 390, pl = (W - pw) / 2, ptop = 360;
    const [a, b] = s.items;
    const ya = pt(pl, ptop, pw, 0, mid(a.box)[1])[1], yb = pt(pl, ptop, pw, 0, mid(b.box)[1])[1];
    const ca = Math.min(Math.max(ya - 90, 380), 1060), cb = Math.min(Math.max(yb - 90, 380), 1060);
    return `<body style="background:${t.bg}">
      <div class="abs" style="left:-200px;top:-260px;width:620px;height:620px;border-radius:50%;border:2px solid ${t.ring}"></div>
      <div class="abs" style="left:64px;top:56px">${logo(t.dark)}</div>
      <div class="abs" style="left:64px;right:64px;top:140px;text-align:center">
        <div class="eyebrow" style="color:${t.eyebrow}">${s.eyebrow}</div>
        <h1 style="color:${t.h1};font-size:76px;margin-top:16px">${s.h[0]}</h1>
      </div>
      ${phone(img, pw, t.frame, { highlights: [a.box, b.box], style: `left:${pl}px;top:${ptop}px` })}
      ${svgLines([[290, ca + 70, pt(pl, ptop, pw, a.box.x0 + 0.04, 0)[0], ya], [W - 290, cb + 70, pt(pl, ptop, pw, b.box.x1 - 0.04, 0)[0], yb]], t.line)}
      <div class="card" style="left:36px;top:${ca}px;width:270px;z-index:7"><div class="t">${a.t}</div><div class="d">${a.d}</div></div>
      <div class="card" style="right:36px;top:${cb}px;width:270px;z-index:7"><div class="t">${b.t}</div><div class="d">${b.d}</div></div>
      <div class="abs" style="left:0;right:0;bottom:44px;text-align:center;z-index:8">${cta('Download now', t.cta)}</div>
    </body>`;
  };

// ---------- 7 designs ----------
const designs = [
  // 1. Navy hero with connector callouts (cream theme: see hero('cream') below)
  (s, img) => hero('navy')(s, img),
  // 2. Cream split, tilted phone right, numbered list left
  (s, img) => `<body style="background:linear-gradient(160deg,${CREAM} 0%,#f3e3c4 100%)">
      <div class="abs" style="right:-260px;top:120px;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,#f0d9ae 0,#f6e7cb 60%,transparent 61%)"></div>
      <div class="abs" style="left:64px;top:60px">${logo(true)}</div>
      <div class="abs" style="left:64px;top:170px;width:520px">
        <div class="eyebrow">${s.eyebrow}</div>
        <h1 style="color:${NAVY};font-size:72px;margin-top:18px">${s.h[1]}</h1>
        ${s.items.map((it, i) => `<div style="display:flex;gap:20px;margin-top:${i ? 34 : 56}px">
          <span class="num" style="width:56px;height:56px;font-size:28px">${i + 1}</span>
          <div><div style="font-weight:800;font-size:34px;color:${NAVY};line-height:1.15">${it.t}</div>
          <div style="font-weight:500;font-size:25px;color:#5b5446;line-height:1.4;margin-top:6px">${it.d}</div></div></div>`).join('')}
        <div style="margin-top:56px">${cta('Get the app', 'navy')}</div>
      </div>
      ${phone(img, 440, 'silver', { highlights: s.items.map((it, i) => ({ ...it.box, n: i + 1 })), style: 'left:600px;top:200px;transform:rotate(7deg)' })}
    </body>`,
  // 3. Zoom lens: phone left, magnified crops right
  (s, img) => {
    const pw = 400, pl = 60, ptop = 330;
    const [a, b] = s.items;
    const zw = 520, zl = 500;
    const sc = (bx) => zw / ((bx.x1 - bx.x0) * IMG_W);
    const za = Math.min((a.box.y1 - a.box.y0) * IMG_H * sc(a.box), 300), zb = Math.min((b.box.y1 - b.box.y0) * IMG_H * sc(b.box), 300);
    const clampBox = (bx) => { const h = 300 / (IMG_H * sc(bx)); return (bx.y1 - bx.y0) > h ? { ...bx, y1: bx.y0 + h } : bx; };
    const ta = 360, tb = ta + za + 160;
    return `<body style="background:#f2f4fb">
      <div class="abs" style="left:64px;top:56px">${logo(true)}</div>
      <div class="abs" style="left:64px;right:64px;top:130px">
        <h1 style="color:${NAVY};font-size:68px">${s.h[2]}</h1>
      </div>
      ${phone(img, pw, 'blue', { highlights: [a.box, b.box], style: `left:${pl}px;top:${ptop}px` })}
      ${svgLines([[pt(pl, ptop, pw, a.box.x1, 0)[0], pt(pl, ptop, pw, 0, mid(a.box)[1])[1], zl - 10, ta + za / 2], [pt(pl, ptop, pw, b.box.x1, 0)[0], pt(pl, ptop, pw, 0, mid(b.box)[1])[1], zl - 10, tb + zb / 2]], GOLD)}
      <div class="abs" style="left:${zl}px;top:${ta}px;z-index:7">${zoom(img, clampBox(a.box), zw)}
        <div style="margin-top:22px;display:flex;gap:14px;align-items:center"><span class="num">1</span><span style="font-weight:800;font-size:32px;color:${NAVY}">${a.t}</span></div></div>
      <div class="abs" style="left:${zl}px;top:${tb}px;z-index:7">${zoom(img, clampBox(b.box), zw)}
        <div style="margin-top:22px;display:flex;gap:14px;align-items:center"><span class="num">2</span><span style="font-weight:800;font-size:32px;color:${NAVY}">${b.t}</span></div></div>
      <div class="abs" style="left:${zl}px;bottom:52px;z-index:8">${cta('Start practicing')}</div>
    </body>`;
  },
  // 4. Bold gradient, huge headline, phone bleeding off bottom, sticker pills
  (s, img) => {
    const [a, b] = s.items;
    const top = 470;
    // shrink the phone if an item would be cut off by the bottom edge
    const lowest = Math.max(a.box.y1, b.box.y1);
    const pw = Math.min(560, (H - 50 - top) / (lowest * IMG_H / IMG_W + 0.034 * (1 - 2 * lowest * IMG_H / IMG_W) + 0.034) | 0), pl = (W - pw) / 2;
    const ya = pt(pl, top, pw, 0, mid(a.box)[1])[1], yb = pt(pl, top, pw, 0, mid(b.box)[1])[1];
    return `<body style="background:linear-gradient(150deg,#2340c9 0%,#1a2a8a 45%,#4b1f8f 100%)">
      <div class="abs" style="inset:0;background:repeating-linear-gradient(115deg,rgba(255,255,255,.035) 0 2px,transparent 2px 46px)"></div>
      <div class="abs" style="left:64px;top:56px">${logo()}</div>
      <div class="abs" style="left:64px;right:64px;top:140px;text-align:center">
        <h1 style="color:#fff;font-size:${s.h[3].length > 34 ? 80 : 92}px;letter-spacing:-2.5px">${s.h[3]}</h1>
      </div>
      ${phone(img, pw, 'orange', { highlights: [a.box, b.box], style: `left:${pl}px;top:${top}px` })}
      <div class="abs" style="left:28px;top:${ya - 50}px;z-index:8;transform:rotate(-5deg);background:${GOLD_L};color:${NAVY};font-weight:800;font-size:30px;padding:18px 28px;border-radius:22px;box-shadow:0 18px 30px -10px rgba(0,0,0,.45);max-width:330px">① ${a.t}</div>
      <div class="abs" style="right:28px;top:${yb - 50}px;z-index:8;transform:rotate(4deg);background:#fff;color:${NAVY};font-weight:800;font-size:30px;padding:18px 28px;border-radius:22px;box-shadow:0 18px 30px -10px rgba(0,0,0,.45);max-width:330px">② ${b.t}</div>
    </body>`;
  },
  // 5. Dark premium with glass cards overlapping phone edges
  (s, img) => {
    const pw = 420, pl = (W - pw) / 2, ptop = 310;
    const [a, b] = s.items;
    const ya = pt(pl, ptop, pw, 0, mid(a.box)[1])[1], yb = pt(pl, ptop, pw, 0, mid(b.box)[1])[1];
    const ca = Math.min(Math.max(ya - 80, 360), 1000), cb = Math.min(Math.max(yb - 80, ca + 230), 1060);
    return `<body style="background:radial-gradient(ellipse at 50% 60%,#1f2c6e 0,#0b1030 60%,#070a1f 100%)">
      <div class="abs" style="left:50%;top:620px;width:760px;height:760px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(231,201,146,.28) 0,transparent 62%)"></div>
      <div class="abs" style="left:64px;top:56px">${logo()}</div>
      <div class="abs" style="left:64px;right:64px;top:132px;text-align:center">
        <h1 style="color:#fff;font-size:70px">${s.h[4].replace(/\*(.+?)\*/g, '<span class="gl">$1</span>')}</h1>
      </div>
      ${phone(img, pw, 'blue', { style: `left:${pl}px;top:${ptop}px` })}
      ${[[a, ca, 'left:40px'], [b, cb, 'right:40px']].map(([it, y, side], i) => `
      <div class="abs" style="${side};top:${y}px;width:360px;z-index:7;padding:26px 28px;border-radius:28px;background:rgba(22,32,92,.86);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border:1.5px solid rgba(255,255,255,.28);box-shadow:0 30px 60px -20px rgba(0,0,0,.6)">
        <div style="display:flex;gap:14px;align-items:center"><span class="num">${i + 1}</span><span style="font-weight:800;font-size:30px;color:#fff;line-height:1.15">${it.t}</span></div>
        <div style="font-weight:500;font-size:23px;color:#d7dcf3;line-height:1.4;margin-top:12px">${it.d}</div></div>`).join('')}
      <div class="abs" style="left:0;right:0;bottom:44px;text-align:center;z-index:8">${cta('Download now')}</div>
    </body>`;
  },
  // 6. Spotlight: rest of screen dimmed, numbered highlights, captions row below
  (s, img) => {
    const pw = 380, pl = (W - pw) / 2, ptop = 290;
    return `<body style="background:linear-gradient(180deg,#fff8ea 0%,#f6e6c6 100%)">
      <div class="abs" style="left:64px;top:52px;right:64px;display:flex;justify-content:space-between;align-items:center">${logo(true)}<span class="eyebrow" style="font-size:18px">${s.eyebrow}</span></div>
      <div class="abs" style="left:64px;right:64px;top:128px;text-align:center"><h1 style="color:${NAVY};font-size:54px">${s.h[5]}</h1></div>
      ${phone(img, pw, 'silver', { dim: true, highlights: s.items.map((it, i) => ({ ...it.box, n: i + 1 })), style: `left:${pl}px;top:${ptop}px` })}
      <div class="abs" style="left:0;right:0;top:0;height:${H}px;pointer-events:none"></div>
      <div class="abs" style="left:40px;right:40px;bottom:40px;display:flex;gap:24px;z-index:8">
        ${s.items.map((it, i) => `<div style="flex:1;background:${NAVY};border-radius:26px;padding:24px 26px;box-shadow:0 24px 40px -18px rgba(19,33,92,.7)">
          <div style="display:flex;gap:14px;align-items:center"><span class="num">${i + 1}</span><span style="font-weight:800;font-size:28px;color:#fff;line-height:1.15">${it.t}</span></div>
          <div style="font-weight:500;font-size:21px;color:#cfd5f2;line-height:1.4;margin-top:10px">${it.d}</div></div>`).join('')}
      </div>
    </body>`;
  },
  // 7. Big stat hook: number left, tilted phone right, CTA bar
  (s, img) => `<body style="background:${NAVY}">
      <div class="abs" style="right:-120px;top:-120px;width:760px;height:760px;border-radius:50%;background:${NAVY2}"></div>
      <div class="abs" style="left:-180px;bottom:-240px;width:620px;height:620px;border-radius:50%;border:3px solid rgba(179,139,77,.35)"></div>
      <div class="abs" style="left:64px;top:56px">${logo()}</div>
      <div class="abs" style="left:64px;top:170px;width:520px;z-index:4">
        <div style="font-weight:800;font-size:${s.stat[0].length > 4 ? 150 : 180}px;letter-spacing:-6px;line-height:.95;color:${GOLD_L}">${s.stat[0]}</div>
        <div style="font-weight:700;font-size:36px;color:#fff;line-height:1.2;margin-top:10px">${s.stat[1]}</div>
        <div style="height:4px;width:90px;background:${GOLD};margin:40px 0 34px;border-radius:2px"></div>
        ${s.items.map(it => `<div style="display:flex;gap:16px;margin-bottom:28px">
          <span style="flex:none;width:40px;height:40px;border-radius:50%;background:rgba(231,201,146,.18);color:${GOLD_L};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:24px">✓</span>
          <div><div style="font-weight:800;font-size:30px;color:#fff;line-height:1.15">${it.t}</div><div style="font-weight:500;font-size:22px;color:#b9c1e6;line-height:1.4;margin-top:4px">${it.d}</div></div></div>`).join('')}
      </div>
      ${phone(img, 420, 'orange', { highlights: s.items.map(it => it.box), style: 'left:600px;top:190px;transform:rotate(-6deg)' })}
      <div class="abs" style="left:0;right:0;bottom:0;height:150px;background:${GOLD};display:flex;align-items:center;justify-content:space-between;padding:0 64px;z-index:9">
        <span style="font-weight:800;font-size:36px;color:#fff">${s.h[6]}</span>${cta('Download', 'white')}
      </div>
    </body>`,
];

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  const only = process.argv[2];
  for (const s of shots) {
    const img = 'file://' + path.join(SRC, s.file);
    const all = designs.map((fn, i) => [`design${i + 1}`, fn]).concat([['design1-cream', hero('cream')]]);
    for (const [suffix, fn] of all) {
      const name = `${s.slug}_${suffix}`;
      if (only && !new RegExp(only).test(name)) continue;
      const html = `<!doctype html><html><head><meta charset="utf-8"><style>${BASE_CSS}</style></head>${fn(s, img)}</html>`;
      const hp = path.join(HTML, name + '.html');
      fs.writeFileSync(hp, html);
      await page.goto('file://' + hp, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: path.join(OUT, name + '.png') });
      console.log('ok', name);
    }
  }
  await browser.close();
})();
