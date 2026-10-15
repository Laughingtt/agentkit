// 校验全书 markdown 里的 mermaid 图是否真的能解析。
//
// runnable: yes
// 用法：node tools/mermaid-check.mjs [目录]   （默认当前目录）
// 依赖：npm i -D jsdom mermaid
//
// 为什么需要它：静态正则查不出 mermaid 的词法错误（比如 stateDiagram-v2 的
// 状态 ID 里带连字符会被当成箭头，整张图渲染成空白却不报明显错误）。只有把
// 图喂给真正的解析器才能发现。全书 93 个图曾经有一张就是这样坏的。
//
// 用 jsdom 而不是浏览器：不起浏览器、不占内存、不需要截图，解析结果与
// GitHub / VitePress 渲染时一致。

import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

// 在导入 mermaid 之前把 DOM 环境铺好，否则 mermaid 初始化时会摸不到 window
const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true });
global.window = dom.window;
global.document = dom.window.document;
global.DOMPurify = undefined;
global.SVGElement = dom.window.SVGElement;
global.Element = dom.window.Element;
global.HTMLElement = dom.window.HTMLElement;
global.Node = dom.window.Node;
global.getComputedStyle = dom.window.getComputedStyle;
global.requestAnimationFrame = (cb) => cb();

const mermaid = (await import('mermaid')).default;
mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

const root = process.argv[2] || '.';

// 只扫正文目录：跳过隐藏目录与 node_modules
// （.superpowers/ 下是审查过程的笔记，里面的图片段是摘自正文的残片，不是完整图）
const SKIP = new Set(['node_modules', 'dist', '.git']);
const files = [];
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.') || SKIP.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name.endsWith('.md')) files.push(p);
  }
})(root);

let total = 0;
let bad = 0;
for (const f of files) {
  const lines = fs.readFileSync(f, 'utf8').split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() !== '```mermaid') continue;
    let j = i + 1;
    const block = [];
    while (j < lines.length && lines[j].trim() !== '```') { block.push(lines[j]); j++; }
    total++;
    try {
      await mermaid.parse(block.join('\n'));
    } catch (e) {
      bad++;
      const msg = (e.message || String(e)).split('\n').slice(0, 4).join(' ⏎ ');
      console.log(`✗ ${path.relative(root, f)}:${i + 1}  ${msg.slice(0, 220)}`);
      console.log('   首行: ' + block[0].trim());
    }
    i = j;
  }
}

console.log(`\n共 ${total} 个 mermaid 块，解析失败 ${bad} 个`);
// 解析失败时返回非零，便于挂进 CI 或提交前钩子
process.exit(bad ? 1 : 0);
