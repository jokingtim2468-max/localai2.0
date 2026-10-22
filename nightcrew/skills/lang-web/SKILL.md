---
name: lang-web
description: JavaScript / TypeScript, React, Vite, Node, Three.js
domain: web
triggers: [javascript, js, typescript, ts, react, vite, node, npm, html, css, three.js, threejs, website]
---
- New app: `npm create vite@latest app -- --template react-ts`, then `npm install`, `npm run build` (type errors show here), `npm run dev`.
- Check types: `npx tsc --noEmit`. Node script: `node file.js`.
- Three.js game loop: renderer.setAnimationLoop(tick); use clock.getDelta() for frame-independent motion.
- Traps: ESM vs CommonJS ("type":"module"), never commit node_modules, keep secrets out of client bundles.
