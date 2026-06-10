import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('./public', import.meta.url));
const port = Number(process.env.PORT || 3000);

const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml' };

export function buildPrompt(question, settings) {
  const correct = question.options.find((option) => option.correct);
  return `You are an expert assessment editor. Rephrase this multiple-choice question while preserving its meaning, difficulty, learning objective, and exactly one correct answer.\n\nRules:\n- Return JSON only with keys: stem, options, rationale.\n- Each option must have text and correct keys.\n- Do not add clues, ambiguity, or change factual accuracy.\n- Style: ${settings.style}. Reading level: ${settings.readingLevel}.\n- Correct answer policy: ${settings.correctPolicy}.\n- ${settings.rephraseDistractors ? 'Rephrase or replace wrong options with plausible distractors.' : 'Keep every wrong option unchanged.'}\n- The correct answer remains semantically equivalent to: ${correct?.text ?? 'unknown'}\n\nQuestion:\n${JSON.stringify(question)}`;
}

function demoRephrase(question, settings) {
  const intros = { concise: 'Which statement best describes', conversational: 'Which of these best explains', academic: 'Which statement most accurately characterizes' };
  const subject = question.stem.replace(/^(what is|which of the following (best )?|which statement (best )?)/i, '').replace(/[?.]$/, '').trim();
  const stem = `${intros[settings.style] || intros.concise} ${subject.charAt(0).toLowerCase()}${subject.slice(1)}?`;
  const options = question.options.map((option, index) => {
    if (option.correct && settings.correctPolicy === 'keep') return option;
    if (!option.correct && !settings.rephraseDistractors) return option;
    const clean = option.text.replace(/[.]$/, '');
    return { ...option, text: index % 2 ? `${clean}, specifically` : `In practice, ${clean.charAt(0).toLowerCase()}${clean.slice(1)}` };
  });
  return { stem, options, rationale: 'Demo mode preserves the designated answer and applies deterministic wording changes. Connect an LLM for production-quality output.', provider: 'demo' };
}

async function callLLM(question, settings) {
  if (!process.env.OPENAI_API_KEY) return demoRephrase(question, settings);
  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.OPENAI_API_KEY}` },
    body: JSON.stringify({ model: process.env.OPENAI_MODEL || 'gpt-4.1-mini', input: buildPrompt(question, settings), text: { format: { type: 'json_object' } } })
  });
  if (!response.ok) throw new Error(`LLM request failed (${response.status})`);
  const data = await response.json();
  const result = JSON.parse(data.output_text);
  return { ...result, provider: 'openai' };
}

function sendJson(res, status, value) {
  res.writeHead(status, { 'Content-Type': types['.json'] });
  res.end(JSON.stringify(value));
}

export const server = createServer(async (req, res) => {
  try {
    if (req.method === 'POST' && req.url === '/api/rephrase') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const { question, settings } = JSON.parse(body);
      if (!question?.stem || !Array.isArray(question.options) || question.options.filter((item) => item.correct).length !== 1) {
        return sendJson(res, 400, { error: 'A stem and options with exactly one correct answer are required.' });
      }
      return sendJson(res, 200, await callLLM(question, settings));
    }
    if (req.method !== 'GET') return sendJson(res, 405, { error: 'Method not allowed' });
    const requested = req.url === '/' ? '/index.html' : req.url.split('?')[0];
    const path = normalize(join(root, requested));
    if (!path.startsWith(root)) return sendJson(res, 403, { error: 'Forbidden' });
    const content = await readFile(path);
    res.writeHead(200, { 'Content-Type': types[extname(path)] || 'application/octet-stream' });
    res.end(content);
  } catch (error) {
    if (error.code === 'ENOENT') return sendJson(res, 404, { error: 'Not found' });
    sendJson(res, 500, { error: error.message });
  }
});

if (process.argv[1] === fileURLToPath(import.meta.url)) server.listen(port, () => console.log(`CourseCraft running at http://localhost:${port}`));
