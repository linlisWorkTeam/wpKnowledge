#!/usr/bin/env node
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startKnowledgeServer } from '../../../endlessWpKnowledgeRunner/src/server.ts';

export {
  createKnowledgeServer,
  resolveServerBinding,
  startKnowledgeServer,
} from '../../../endlessWpKnowledgeRunner/src/server.ts';

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  startKnowledgeServer();
}
