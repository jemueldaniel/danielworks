import {build} from 'esbuild';
import {createRequire} from 'node:module';
import {mkdir,copyFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
await mkdir(path.join(project,'dist/web'),{recursive:true});
await build({absWorkingDir:project,entryPoints:['src/server.ts','src/api-client.ts','src/mcp-client.ts'],outdir:'dist',bundle:true,packages:'external',platform:'node',target:'node22',format:'esm',sourcemap:false});
// Resolve packages from this isolated npm workspace, not an unrelated ancestor
// Yarn Plug'n'Play manifest. No parent files or package-manager settings are changed.
const localPackages={name:'workspace-packages',setup(builder){
  builder.onResolve({filter:/^[^./]/},args=>{
    if(args.kind==='entry-point')return;
    return {path:createRequire(args.importer||path.join(project,'package.json')).resolve(args.path)};
  });
}};
await build({plugins:[localPackages],absWorkingDir:project,entryPoints:['web/main.tsx'],outfile:'dist/web/app.js',bundle:true,platform:'browser',target:'chrome120',format:'esm',sourcemap:false,minify:true,define:{'process.env.NODE_ENV':'"production"'}});
for(const name of ['index.html','style.css'])await copyFile(path.join(project,'web',name),path.join(project,'dist/web',name));
console.log('Built gateway, typed clients and React interface; no services started.');
