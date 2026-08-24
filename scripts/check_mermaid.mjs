#!/usr/bin/env node
/**
 * Validate every ```mermaid fence in the repo's markdown against the real
 * Mermaid parser.
 *
 * Why this exists: GitHub renders Mermaid client-side, so a diagram with a
 * syntax error doesn't fail loudly at commit time — it ships, and readers get a
 * red "Unable to render rich display" box where the diagram should be. The
 * STYLE_GUIDE rule ("open the file on GitHub and verify rendering") is
 * self-attested and was silently skipped at least once, which is how a
 * reserved-word node id (`call`, the `click X call fn()` keyword) reached main
 * in META_ARCHITECTURE §3. This is the check behind that rule.
 *
 * Parses with securityLevel 'strict' to match GitHub's own configuration.
 * docs/llms-full.txt is not scanned directly — it is generated from the five
 * markdown sources and gated by llms-full-check, so clean sources make it clean.
 *
 * Usage:
 *   node scripts/check_mermaid.mjs            # whole repo
 *   node scripts/check_mermaid.mjs A.md B.md  # only these files
 *
 * Requires: npm install --no-save mermaid jsdom
 */
import fs from 'node:fs';
import path from 'node:path';

const SKIP_DIRS = new Set(['.git', 'node_modules', '__pycache__', '.github/ISSUE_TEMPLATE']);
const FENCE = /^([ \t]*)```mermaid[ \t]*$\n([\s\S]*?)^\1```[ \t]*$/gm;

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.md')) out.push(p);
  }
  return out;
}

// Mermaid needs a DOM even to parse. jsdom is enough; a headless browser is not
// required because we never render to SVG.
const { JSDOM } = await import('jsdom');
const dom = new JSDOM('<!doctype html><html><body></body></html>', { pretendToBeVisual: true });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
// navigator is a getter-only property on the Node global; defineProperty is the
// only way to shim it.
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
for (const k of ['HTMLElement', 'SVGElement', 'Element', 'Node', 'DOMParser']) globalThis[k] = dom.window[k];

const mermaid = (await import('mermaid')).default;
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });

const files = process.argv.length > 2 ? process.argv.slice(2) : walk('.');
let blocks = 0;
const failures = [];

for (const file of files) {
  if (!fs.existsSync(file)) continue;
  const src = fs.readFileSync(file, 'utf8');
  for (const m of src.matchAll(FENCE)) {
    blocks++;
    // 1-indexed line of the opening fence, so the error is clickable.
    const line = src.slice(0, m.index).split('\n').length;
    try {
      await mermaid.parse(m[2], { suppressErrors: false });
    } catch (e) {
      failures.push({ file, line, message: String(e?.message ?? e).trim() });
    }
  }
}

for (const f of failures) {
  console.error(`\n${f.file}:${f.line} — mermaid parse error`);
  console.error(f.message.split('\n').map((l) => '    ' + l).join('\n'));
}

const scanned = process.argv.length > 2 ? `${files.length} file(s)` : 'the repo';
if (failures.length) {
  console.error(`\n${failures.length} of ${blocks} mermaid block(s) failed to parse.`);
  process.exit(1);
}
console.log(`${blocks} mermaid block(s) in ${scanned}: all parse.`);
