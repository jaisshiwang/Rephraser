import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPrompt, server } from '../server.mjs';

const question={stem:'What is 2 + 2?',options:[{text:'4',correct:true},{text:'5',correct:false}]};
const settings={style:'concise',readingLevel:'course appropriate',correctPolicy:'keep',rephraseDistractors:true};

test('prompt includes correctness safeguards and selected settings',()=>{const prompt=buildPrompt(question,settings);assert.match(prompt,/exactly one correct answer/);assert.match(prompt,/Correct answer policy: keep/);assert.match(prompt,/Rephrase or replace wrong options/);assert.match(prompt,/4/)});

test('rephrase API validates questions and returns a safe demo result',async(t)=>{await new Promise(resolve=>server.listen(0,resolve));t.after(()=>server.close());const base=`http://127.0.0.1:${server.address().port}`;const invalid=await fetch(`${base}/api/rephrase`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:{stem:'No answer',options:[]},settings})});assert.equal(invalid.status,400);const response=await fetch(`${base}/api/rephrase`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question,settings})});assert.equal(response.status,200);const result=await response.json();assert.equal(result.provider,'demo');assert.equal(result.options.filter(o=>o.correct).length,1);assert.equal(result.options.find(o=>o.correct).text,'4')});
