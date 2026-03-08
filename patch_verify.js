const fs = require('fs');
let content = fs.readFileSync('app/tests/verify.spec.ts', 'utf8');
content = content.replace("const serverProcess = require('child_process').spawn('python3',", "const serverProcess = require('node:child_process').spawn('python3',");
fs.writeFileSync('app/tests/verify.spec.ts', content);
