/** Read-only deterministic diagnosis of the actual project renderer, not live mouse QA. */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import * as animation from '../standalone-app/animation.mjs';
import { createPaintAckGate } from '../standalone-app/paint-ack.mjs';

function probe(deltas) {
  const listeners = {}, moves = [], interactions = [];
  const element = { style: {}, classList: {add(){},remove(){}},
    addEventListener(name, handler) { listeners[name] = handler; },
    setPointerCapture(){}, removeAttribute(){}, getBoundingClientRect(){return {left:0,top:0,width:192,height:208};} };
  const context = vm.createContext({...animation, createPaintAckGate,
    document: {getElementById(){return element;}},
    window: {addEventListener(){}, liangPet: {onPreloadImages(){},onState(){},rendered(){},requestState(){},
      interaction(...event){interactions.push(event);},moveBy(...delta){moves.push(delta);}}},
    performance:{now(){return 0;}}, requestAnimationFrame(){}, console,
    Image:class {decode(){return Promise.resolve();}}});
  const src=fs.readFileSync(new URL('../standalone-app/renderer.mjs',import.meta.url),'utf8');
  vm.runInContext(src.replace(/^import[^\n]+\n/gm,''),context);
  let x=100;
  listeners.pointerdown({button:0,screenX:x,screenY:100,pointerId:1});
  for(const delta of deltas){x+=delta;listeners.pointermove({screenX:x,screenY:100,pointerId:1});}
  const during=interactions.map(event=>[...event]);
  listeners.pointerup();
  return {deltas,moves,during,afterRelease:interactions.map(event=>[...event])};
}
const fastRight=probe([5]); const fastLeft=probe([-5]);
const slowRight=probe(Array(12).fill(1));const slowLeft=probe(Array(12).fill(-1));
assert.deepEqual(fastRight.during,[['drag','running-right']]);
assert.deepEqual(fastLeft.during,[['drag','running-left']]);
assert.equal(slowRight.moves.length,12);assert.equal(slowRight.during.length,0);
assert.equal(slowLeft.moves.length,12);assert.equal(slowLeft.during.length,0);
const report={evidence:'DETERMINISTIC_ACTUAL_RENDERER_HARNESS_NOT_LIVE_MOUSE',
  verdict:'SLOW_DRAG_DIRECTION_TRIGGER_GAP_REPRODUCED',fastRight,fastLeft,slowRight,slowLeft};
if(process.argv.includes('--record')) {
  const folder=new URL('../docs/drag-rework/v0.1.0/evidence/',import.meta.url);
  fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(new URL('interaction-probe.json',folder),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify(report,null,2));
