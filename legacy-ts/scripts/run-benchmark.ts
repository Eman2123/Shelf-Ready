/**
 * Runs the 10-task benchmark for BEFORE and AFTER mode (owner: P3).
 * STUB: lists the tasks. Results must be stored in the database and recorded for replay;
 * never print numbers that did not come from a real run.
 * Run: npm run bench:run
 */
import { benchmarkTasks } from "../src/lib/benchmark/tasks";

console.log(`bench:run (stub): ${benchmarkTasks.length} tasks loaded`);
for (const t of benchmarkTasks) console.log(`- ${t.id}: ${t.title} -> expects ${t.expected}`);
