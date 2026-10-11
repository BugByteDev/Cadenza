import fs from 'node:fs';import {build} from 'esbuild';
await build({entryPoints:['node_modules/spessasynth_core/dist/index.js'],bundle:true,format:'esm',outfile:'dist/vendor/synth.mjs'});
await build({entryPoints:['node_modules/fflate/esm/browser.js'],bundle:true,format:'esm',outfile:'dist/vendor/zip.mjs'});
fs.cpSync('sounds','dist/sounds',{recursive:true});
