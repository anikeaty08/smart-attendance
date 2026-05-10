import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const mustExist = [
  "app/admin/page.tsx",
  "app/admin/students/page.tsx",
  "app/admin/faculty/page.tsx",
  "app/admin/reports/page.tsx",
  "app/admin/sessions/page.tsx",
  "app/hod/page.tsx",
  "app/hod/students/page.tsx",
  "app/hod/faculty/page.tsx",
  "app/hod/reports/page.tsx",
  "app/teacher/page.tsx",
  "app/teacher/reports/page.tsx",
];

const missing = mustExist.filter((rel) => !fs.existsSync(path.join(root, rel)));

if (missing.length > 0) {
  console.error("Missing required role pages:\n" + missing.map((m) => ` - ${m}`).join("\n"));
  process.exit(1);
}

console.log("Role route smoke check passed.");
