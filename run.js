const { exec } = require('child_process');
const child = exec('.\\venv\\Scripts\\python.exe app.py', (err, stdout, stderr) => {
    const fs = require('fs');
    fs.writeFileSync('node_out.txt', stdout + '\nSTDERR:\n' + stderr);
});
setTimeout(() => {
    child.kill();
}, 2000);
