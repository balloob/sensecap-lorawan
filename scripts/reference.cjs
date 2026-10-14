const fs=require('fs'),vm=require('vm');
const lines=fs.readFileSync(0,'utf8').trim().split('\n');
for(const line of lines){
 const item=JSON.parse(line), ctx=vm.createContext({});
 vm.runInContext(fs.readFileSync(item.source,'utf8'),ctx);
 ctx.input={bytes:Array.from(Buffer.from(item.payload,'hex')),fPort:5};
 try {item.expected=vm.runInContext('decodeUplink(input)',ctx,{timeout:1000});}
 catch(e){item.error=e.toString();}
 delete item.source;
 process.stdout.write(JSON.stringify(item)+'\n');
}
