const fs = require("node:fs");
const vm = require("node:vm");

// T1000-E adds decoder execution time to frames without device timestamps.
class ReferenceDate extends Date {
  constructor() {
    super(1700000000000);
  }
}

const lines = fs.readFileSync(0, "utf8").trim().split("\n");
for (const line of lines) {
  const item = JSON.parse(line);
  const context = vm.createContext({ Date: ReferenceDate });
  vm.runInContext(fs.readFileSync(item.source, "utf8"), context);
  context.input = {
    bytes: Array.from(Buffer.from(item.payload, "hex")),
    fPort: 5,
  };
  try {
    item.expected = vm.runInContext("decodeUplink(input)", context, {
      timeout: 1000,
    });
  } catch (error) {
    item.error = error.toString();
  }
  delete item.source;
  process.stdout.write(JSON.stringify(item) + "\n");
}
