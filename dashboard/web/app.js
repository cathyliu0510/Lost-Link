'use strict';

const icons = {
 link:'<rect x="2" y="8" width="13" height="8" rx="4" transform="rotate(-35 8 12)"/><rect x="9" y="8" width="13" height="8" rx="4" transform="rotate(-35 16 12)"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 shield:'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 list:'<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
 arrow:'<path d="M4 12h15m-5-5 5 5-5 5"/>',
 refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/>',
 bot:'<rect x="4" y="7" width="16" height="13" rx="4"/><path d="M12 3v4M1 12v4m22-4v4M8 12h.01M16 12h.01M8 16h8"/>',
 human:'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
 unlock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8-1M12 14v3"/>',
 check:'<path d="m4 12 5 5L20 6"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 box:'<path d="m3 7 9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10M8 5l9 4"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
 close:'<path d="m6 6 12 12M6 18 18 6"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
 bottle:'<path d="M9 3h6v4l3 4v15a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V11l3-4z"/><path d="M9 7h6M6 14h12M10 20v4m4-6v4"/>',
 keys:'<circle cx="8" cy="10" r="5"/><path d="m12 14 9 9m-5-5 3-3m-6 0 3-3"/>',
 phone:'<rect x="6" y="2" width="13" height="27" rx="3"/><path d="M10 6h5m-4 19h3"/>',
 wallet:'<rect x="2" y="7" width="22" height="17" rx="3"/><path d="m4 7 16-4v4M17 13h7v7h-7zM20 16h.01"/>'
};
const svg = (name) => `<svg viewBox="${['bottle','phone','wallet'].includes(name)?'0 0 28 32':'0 0 24 24'}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.box}</svg>`;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today = () => new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'});
const defaultInput = () => ({category:'flask',color:'navy',location:'library',date:today(),description:'navy flask'});
const stateNames = {submitted:'Awaiting human review',needs_clarification:'More detail needed',approved_for_pickup:'Ready for pickup',returned:'Returned to owner',rejected:'Claim rejected'};
const categoryNames = {flask:'water bottle',bottle:'water bottle','water bottle':'water bottle',thermos:'water bottle',keys:'keys',phone:'phone',wallet:'wallet',watch:'watch'};
const colorNames = {blue:'Blue',navy:'Navy',black:'Black',silver:'Silver',brown:'Brown'};
const locationNames = {library:'Library',gym:'Gym','Hayden Library':'Hayden Library','Z Center':'Z Center','Student Center':'Student Center'};
const seeds = () => [
 {report_id:'F-DEMO-01',category:'water bottle',color:'blue',location:'Hayden Library',date:today(),description:'blue water bottle'},
 {report_id:'F-DEMO-02',category:'bottle',color:'blue',location:'Z Center',date:today(),description:'blue water bottle'},
 {report_id:'F-DEMO-03',category:'thermos',color:'black',location:'Hayden Library',date:today(),description:'black thermos'},
 {report_id:'F-DEMO-04',category:'phone',color:'black',location:'Student Center',date:today(),description:'black iphone'},
 {report_id:'F-DEMO-05',category:'keys',color:'silver',location:'library',date:today(),description:'silver keys'},
 {report_id:'F-DEMO-06',category:'wallet',color:'brown',location:'Student Center',date:today(),description:'brown leather wallet'}
];

class InteractiveProvider {
 constructor(){this.reset();}
 reset(){this.s={mode:'interactive',found_count:6,lost:null,candidates:[],case:null,events:[],input:defaultInput()};this.event('finder','Found items registered','The finder agent registered 6 campus samples. Verification clues are stored separately.','Registered');}
 event(actor,title,body,tag='Completed',detail=null){this.s.events.push({id:this.s.events.length+1,actor,title,body,tag,at:new Date().toISOString(),detail,simulated:true});}
 async action(action,p={}){
  await new Promise(r=>setTimeout(r,240));
  let review=null;
  if(action==='reset'){this.reset();return this.snapshot();}
  if(action==='search'){
   if(this.s.case)throw Error('Reset the demo before starting another recovery.');
   this.s.input={...p};this.s.lost={...p,report_id:'L-DEMO-01'};
   const cat=c=>['flask','bottle','water bottle','thermos'].includes(c)?'bottle':c;
   const col=c=>c==='navy'?'blue':c;
   const loc=c=>c.toLowerCase().includes('library')?'library':c==='Z Center'?'gym':c;
   const eligible=['bottle','keys','phone','wallet'].includes(cat(p.category));
   this.s.candidates=eligible?seeds().filter(f=>cat(f.category)===cat(p.category)).map(f=>{
    let score=.5;const reasons=['category matches after normalization ('+cat(p.category)+')','dates within 0 day(s)'];const conflicts=[];
    if(col(f.color)===col(p.color)){score+=.2;reasons.push('color matches after normalization ('+col(p.color)+')');}else conflicts.push('color');
    if(loc(f.location)===loc(p.location)){score+=.2;reasons.push('location matches after normalization ('+loc(p.location)+')');}else conflicts.push('location');
    score+=cat(p.category)==='bottle'?(col(f.color)===col(p.color)?.067:.033):.05;
    return {report_id:f.report_id,score:Math.round(score*1000)/1000,reasons,unknown:[],conflicts,found_report:f};
   }).sort((a,b)=>b.score-a.score).slice(0,3):[];
   this.event('owner','Lost report registered and candidates found',this.s.candidates.length?'Normalize the wording, then compare item type, color, location and date to find leads.':'There is not enough same-category evidence. Keep the report and withhold unrelated suggestions.',this.s.candidates.length?this.s.candidates.length+' candidates':'No match yet');
  }else if(action==='claim'){
   if(!this.s.lost||!this.s.candidates.some(c=>c.report_id===p.found_id))throw Error('Choose an item from the search results first.');
   if(this.s.case)throw Error('There is already a claim for this session.');
   if(!p.message?.trim())throw Error('Enter a verification clue.');
   this.s.case={case_id:'C-DEMO-01',status:'submitted',found_report_id:p.found_id,clarification_request:null,human_decisions:[]};
   this.claim=p.message;this.followup=[];
   this.event('owner','Private claim submitted','The holder can now review the clue. Pickup details stay locked until a human decides.','Human review pending');
  }else if(action==='review'){
   if(!this.s.case)throw Error('Submit a claim before opening holder review.');
   const f=seeds().find(f=>f.report_id===this.s.case.found_report_id);
   review={your_private_detail:f.category==='water bottle'?'A green cactus sticker near the cap':'A private clue reserved by the demo holder',claim_message:this.claim,follow_up_info:this.followup||[],found_description:f.description};
  }else if(action==='clarify'){
   this.expect(['submitted']);this.s.case.status='needs_clarification';this.s.case.clarification_request=p.note||'What color is the sticker?';
   this.event('human','Holder requested clarification',this.s.case.clarification_request,'More detail needed');
  }else if(action==='info'){
   this.expect(['needs_clarification']);if(!p.text?.trim())throw Error('Enter an additional detail.');
   this.followup.push(p.text);this.s.case.status='submitted';this.event('owner','Additional detail submitted','The new detail is with the holder for another review.','Human review pending');
  }else if(action==='approve'){
   this.expect(['submitted','needs_clarification']);if(!p.pickup?.trim())throw Error('Enter pickup instructions.');
   this.s.case.status='approved_for_pickup';this.s.case.pickup_instructions=p.pickup;this.s.case.human_decisions.push({action:'approve'});
   this.event('human','Holder approved pickup','Human review is complete. Pickup instructions are now visible to the claimant.','Human-approved');
  }else if(action==='reject'){
   this.expect(['submitted','needs_clarification']);this.s.case.status='rejected';this.event('human','Holder rejected claim','This claim did not pass verification. Pickup details remain locked.','Rejected');
  }else if(action==='returned'){
   this.expect(['approved_for_pickup']);this.s.case.status='returned';this.s.found_count=5;this.event('human','Item returned — case closed','The holder confirmed the handoff. Both linked reports are closed.','Closed');
  }else if(action==='misuse'){
   if(!this.s.case)throw Error('Submit a claim before testing approval permissions.');
   this.event('owner','Agent self-approval was blocked','This interactive example shows the expected refusal. Local API mode checks a real HTTP 403 response.','Permission enforced',{expected_http_status:403});
  }else if(action==='repeat'){
   if(!this.s.lost)throw Error('Run a search first.');
   this.event('owner','Retry reused the existing record','This example illustrates idempotency. No additional lost report or claim was created.','Retry recognized');
  }else if(action==='refresh'){
   this.event('owner','Case status checked',this.s.case?stateNames[this.s.case.status]:'No claim has been submitted yet.','Status synchronized');
  }else throw Error('Unsupported action.');
  return this.snapshot(review);
 }
 expect(statuses){if(!this.s.case||!statuses.includes(this.s.case.status))throw Error('This action is not available in the current case state.');}
 snapshot(review=null){return {...structuredClone(this.s),review};}
}

class LiveProvider {
 async action(action,p={}){const r=await fetch('/demo/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...p})});const d=await r.json();if(!r.ok)throw Error(d.detail||'The service could not complete this action.');return d;}
}

let provider, data, busy=false, role='owner', review=null;
let toastTimer;
function toast(text,error=false){const el=document.querySelector('#toast');el.textContent=text;el.className='visible'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.className='',3800);}
const button=(text,action,cls='secondary',icon='',extra='')=>`<button class="btn ${cls}" data-action="${action}" ${busy?'disabled':''} ${extra}>${icon?svg(icon):''}${text}</button>`;
const actorNames={finder:'Finder agent',owner:'Owner agent',human:'Human holder'};
const avatar=(actor)=>`<span class="avatar ${actor==='finder'?'finder':actor==='human'?'human':''}">${svg(actor==='human'?'human':'bot')}</span>`;
function titleFor(f){return [colorNames[f.color]||f.color,categoryNames[f.category]||f.category||'item'].filter(Boolean).join(' ');}
function reasonTags(c){let a=[];if(c.reasons?.some(r=>r.startsWith('category')))a.push('Same type');if(c.reasons?.some(r=>r.startsWith('color')))a.push('Color matches');if(c.reasons?.some(r=>r.startsWith('location')))a.push('Location matches');if(c.conflicts?.length)a.push('Detail to check');return a.slice(0,3).map(t=>`<span class="tag ${t.includes('check')?'amber':'neutral'}">${esc(t)}</span>`).join('');}
function stageIndex(){const c=data.case;if(!c)return data.lost?1:0;if(c.status==='returned')return 4;if(c.status==='approved_for_pickup')return 3;return 2;}

function render(){
 const c=data.case, ix=stageIndex(), pending=c&&['submitted','needs_clarification'].includes(c.status), input=data.input||defaultInput();
 const steps=['Registered','Matched','Private claim','Human approval','Returned'];
 const activeState=c?stateNames[c.status]:data.lost?'Ready to claim':'Ready to start';
 const foundOpen=c?.status==='returned'?data.found_count:data.found_count;
 document.querySelector('#app').innerHTML=`<div class="shell">
 <aside class="sidebar"><a class="brand" href="./" aria-label="Lost Link workspace home"><img src="./favicon.svg" alt=""><div><strong>Lost Link</strong><small>AGENT WORKSPACE</small></div></a>
 <p class="workspace-tag">YOUR WORKSPACE</p><nav class="nav" aria-label="Workspace navigation">
 <button class="${role==='owner'?'active':''}" data-action="owner" aria-label="Agent workspace">${svg('grid')}<span>Agent workspace</span></button>
 <button class="${role==='human'?'active':''}" data-action="human" aria-label="Human review">${svg('human')}<span>Human review</span>${pending?'<b>1</b>':''}</button>
 <button data-action="logs" aria-label="Activity log">${svg('list')}<span>Activity log</span></button></nav>
 <div class="side-separator"></div><p class="side-caption">EXPLORE A SCENARIO</p>
 <button class="scenario" data-action="example"><span></span>Find a navy flask</button>
 <button class="scenario" data-action="absent"><span></span>No matching item</button>
 <button class="scenario" data-action="repeat"><span></span>Retry the same request</button>
 <button class="scenario" data-action="misuse"><span></span>Test an approval boundary</button>
 <div class="side-bottom"><div class="privacy-note">${svg('shield')}<strong>A match is just a lead</strong>Verification clues stay with the holder.<br>A human approves every pickup.</div><div class="profile"><span>K / Y</span><div><strong>Lost Link Team</strong><small>Campus prototype · v0.1</small></div></div></div></aside>
 <main class="main"><header class="topbar"><div class="breadcrumb">Workspace <span>/</span> <strong>Campus lost & found</strong></div><div class="top-actions"><span class="badge ${data.mode==='interactive'?'interactive':''}"><span class="dot"></span>${data.mode==='live'?'Local API connected':'Interactive demo · synthetic data'}</span><button class="icon-btn" data-action="reset" title="Start a fresh synthetic-data session" aria-label="Reset demo" ${busy?'disabled':''}>${svg('refresh')}</button></div></header>
 <div class="content"><section class="intro"><div><div class="eyebrow">LOST & FOUND, WORKING TOGETHER.</div><h1>A little lost. A little closer.</h1><p>Your agents find the possibilities. A human makes the handoff.</p></div><span class="small-code">CAMPUS DEMO / ${esc(today().replaceAll('-','.'))}</span></section>
 <section class="metrics" aria-label="Current session overview"><div class="metric">${svg('box')}<span>Open found items</span><strong>${foundOpen}<small>sample items</small></strong><p>Registered by finder agents</p></div><div class="metric">${svg('search')}<span>Matching candidates</span><strong class="mint">${data.candidates.length}<small>leads to check</small></strong><p>Ranked by type, color and location</p></div><div class="metric">${svg('clock')}<span>Recovery status</span><strong class="status-value">${activeState}</strong><p>${c?esc(c.case_id):'No claim created yet'}</p></div><div class="metric">${svg('shield')}<span>Final pickup authority</span><strong class="status-value mint">Human holder</strong><p>Agents cannot approve a pickup</p></div></section>
 <section class="workflow" aria-label="Recovery workflow">${steps.map((s,i)=>`<div class="step ${i<ix||c?.status==='returned'?'done':i===ix?'current':''}"><span class="step-index">${i<ix||c?.status==='returned'?svg('check'):i+1}</span><span>${s}</span></div>`).join('')}</section>
 <div class="workspace"><div class="column">
 ${c?.status==='needs_clarification'&&role==='owner'?`<div class="notice"><strong>One more detail would help</strong><p>${esc(c.clarification_request)}</p><input class="inline-input" id="followup" aria-label="Additional claim information" placeholder="For example: the sticker is green"><div>${button('Send additional detail','info','primary','arrow')}</div></div>`:''}
 <section class="panel"><div class="panel-heading"><h2>${svg('bot')} Your user’s request</h2><span class="tag neutral">Owner agent</span></div><div class="request-body"><div class="agent-label">${avatar('owner')}<span>Helping your user find a lost item</span><span class="tiny">01 / REQUEST</span></div>
 <form id="search-form"><div class="field search-desc"><label for="description">Public item description</label><input id="description" name="description" value="${esc(input.description)}" maxlength="300" required ${c?'disabled':''}></div><div class="form-grid">
 <div class="field"><label for="category">Item type</label><select id="category" name="category" ${c?'disabled':''}>${[['flask','Water bottle / flask'],['keys','Keys'],['phone','Phone'],['wallet','Wallet'],['watch','Watch']].map(([v,l])=>`<option value="${v}" ${input.category===v?'selected':''}>${l}</option>`).join('')}</select></div>
 <div class="field"><label for="color">Color</label><select id="color" name="color" ${c?'disabled':''}>${[['navy','Navy blue'],['black','Black'],['silver','Silver'],['brown','Brown']].map(([v,l])=>`<option value="${v}" ${input.color===v?'selected':''}>${l}</option>`).join('')}</select></div>
 <div class="field"><label for="location">Lost near</label><select id="location" name="location" ${c?'disabled':''}>${[['library','Library'],['gym','Gym'],['Student Center','Student Center']].map(([v,l])=>`<option value="${v}" ${input.location===v?'selected':''}>${l}</option>`).join('')}</select></div></div>
 <div class="request-footer"><span>Different words. The same possible item.</span><button class="btn primary" type="submit" ${busy||c?'disabled':''}>${svg('search')}${busy?'Working…':'Find matches'}</button></div></form></div></section>
 <section class="panel"><div class="panel-heading"><h2>${svg('list')} Agent activity</h2><span class="subtle">${data.mode==='live'?'REAL SERVICE RESPONSES':'INTERACTIVE WALKTHROUGH'}</span></div><div class="event-feed">${data.events.map(e=>`<article class="event">${avatar(e.actor)}<div class="event-content"><div class="event-top"><strong>${actorNames[e.actor]||'Lost Link'}</strong><time>${esc(new Date(e.at).toLocaleTimeString('en-GB',{hour12:false}))}</time></div><h3>${esc(e.title)}</h3><p>${esc(e.body)}</p><div class="event-tags"><span class="tag ${e.tag?.includes('Human')||e.tag?.includes('pending')?'amber':''}">${svg(e.tag?.includes('pending')?'clock':'check')}${esc(e.tag||'Completed')}</span>${e.http?`<span class="tag neutral">HTTP ${e.http.status}</span>`:''}</div></div></article>`).join('')}</div><div class="feed-end"><span></span>${data.mode==='live'?'Events reflect actual local service responses':'Synthetic-data walkthrough · no model calls'}</div></section></div>
 <div class="column right"><section class="panel"><div class="panel-heading"><h2>${svg('link')} Current claim</h2><button class="text-btn" data-action="refresh" ${busy?'disabled':''}>${svg('refresh')}Refresh status</button></div><div class="case-inner">${caseHTML(c)}</div></section>
 ${role==='human'?reviewHTML(c):candidatesHTML(c)}
 </div></div><footer class="footer"><span>${svg('shield')}Campus prototype · synthetic data · human-approved pickup</span><span>LOST LINK / FIND THE CONNECTION.</span></footer></div></main></div>`;
 bind();
}

function caseHTML(c){
 if(!c)return `<div class="case-top"><span class="case-number">WAITING FOR A CLAIM</span><span class="tag neutral">Not submitted</span></div><div class="case-state"><span>${svg('search')}</span><div><strong>Check the lead. Then make a claim.</strong><small>Choose a candidate and send a private clue to its holder.</small></div></div><div class="gate">${svg('lock')}<div><strong>Pickup details are locked</strong>The claimant sees where and when to collect only after the holder approves.</div></div>`;
 const open=['approved_for_pickup','returned'].includes(c.status);
 return `<div class="case-top"><span class="case-number">${esc(c.case_id)}</span><span class="tag ${open?'':'amber'}">${c.status==='returned'?'Closed':open?'Approved':'In progress'}</span></div><div class="case-state ${open?'complete':''}"><span>${svg(open?'check':'clock')}</span><div><strong>${stateNames[c.status]}</strong><small>${c.status==='returned'?'The holder confirmed the handoff':'Every status change leaves a record'}</small></div></div><div class="kv"><span>Found item</span><strong>${esc(c.found_report_id)}</strong></div><div class="kv"><span>Reviewed by</span><strong>Item holder</strong></div><div class="gate ${open?'open':''}">${svg(open?'unlock':'lock')}<div><strong>${open?'Pickup details unlocked':'Pickup details remain locked'}</strong>${open?esc(c.pickup_instructions):'A claim is a request, not approval. The holder verifies ownership.'}</div></div><div class="case-actions">${role==='owner'&&['submitted','needs_clarification'].includes(c.status)?button('Open human review','human','secondary','human'):''}${role==='owner'&&open?button('View activity log','logs','ghost','list'):''}</div>`;
}

function candidatesHTML(c){
 const empty=!data.candidates.length;
 return `<section class="panel"><div class="panel-heading"><h2>${svg('search')} Found-item candidates</h2><span class="subtle">${data.candidates.length} results · ranked by match score</span></div>${empty?`<div class="empty-icon">${svg('search')}</div><div class="empty-center">${data.lost?'No item with enough same-category evidence yet.<br>Unrelated items are not suggested to fill the list.':'Describe the item to start finding candidates.'}</div>`:data.candidates.map((m,i)=>{const f=m.found_report;return `<article class="candidate"><div class="item-icon">${svg(['keys','phone','wallet'].includes(f.category)?f.category:'bottle')}</div><div><div class="candidate-top"><h3>${esc(titleFor(f))}</h3><span class="score">${Math.round(m.score*100)} <small>/ 100</small></span></div><p>${esc(locationNames[f.location]||f.location)} · ${esc(f.date)}</p><div class="candidate-tags">${reasonTags(m)}</div><div class="candidate-bottom"><span>${i===0?'Best lead · ':' '}A score is not proof of ownership</span>${!c?`<button class="text-btn" data-claim="${esc(m.report_id)}" ${busy?'disabled':''}>Review & claim ${svg('arrow')}</button>`:`<span class="tag neutral">${c.found_report_id===m.report_id?'Claimed item':'Other candidate'}</span>`}</div></div></article>`;}).join('')}<div class="explain">${svg('info')}Results show reasons and conflicts. The holder’s private verification clue is never included in search.</div></section>`;
}

function reviewHTML(c){
 if(!c)return `<section class="panel review-panel"><div class="panel-heading"><h2>${svg('human')} Holder review</h2><span class="tag purple">Human review</span></div><div class="empty-icon">${svg('human')}</div><div class="empty-center">There are no claims to review yet.<br>Return to the workspace, choose a candidate and submit a claim.<br><br>${button('Back to workspace','owner','secondary','arrow')}</div></section>`;
 const actionable=['submitted','needs_clarification'].includes(c.status);
 return `<section class="panel review-panel"><div class="panel-heading"><h2>${svg('human')} Holder review</h2><span class="tag purple">Human review</span></div><div class="review-body"><div class="review-notice">${svg('human')}You are reviewing this demo claim as the human holder.</div>${review?`<div class="review-block private"><label>Your verification clue · holder review only</label><p>${esc(review.your_private_detail)}</p></div><div class="review-block"><label>The claimant’s private description</label><p>${esc(review.claim_message)}</p></div>${review.follow_up_info?.length?`<div class="review-block"><label>Additional detail from the claimant</label><p>${review.follow_up_info.map(esc).join('<br>')}</p></div>`:''}`:'<p class="empty">Reading the holder’s inbox…</p>'}
 ${actionable?`<div class="review-block"><label for="pickup">Pickup instructions to release after approval</label><input class="inline-input" id="pickup" value="Hayden Library front desk · weekdays, 9 am–5 pm" maxlength="300"></div><div class="review-buttons">${button('Verified — approve pickup','approve','primary','check')}${button('Ask for more detail','clarify','secondary','info')}${button('Reject claim','reject','ghost','close')}</div>`:c.status==='approved_for_pickup'?button('Confirm item handed over','returned','primary full','check'):`<div class="gate ${c.status==='returned'?'open':''}">${svg(c.status==='returned'?'check':'lock')}<div>${c.status==='returned'?'This case is closed. Both linked reports have been closed.':'This claim was rejected. Pickup details remain locked.'}</div></div>`}<p class="role-hint">This demo lets you switch roles manually. The service uses separate agent and human credentials.</p>${button('Back to the owner’s view','owner','ghost full','arrow')}</div></section>`;
}

async function act(action,p={}){
 if(busy)return;
 busy=true;render();
 try{const next=await provider.action(action,p);data=next;review=next.review||review;if(action==='reset'){role='owner';review=null;}if(action==='search')review=null;if(action==='info')review=null;busy=false;render();return true;}
 catch(e){busy=false;render();toast(e.message||'The action did not complete. Please try again.',true);return false;}
}

function bind(){
 document.querySelector('#search-form').addEventListener('submit',async e=>{e.preventDefault();const f=Object.fromEntries(new FormData(e.target));await act('search',{...f,date:today()});});
 document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>handle(b.dataset.action)));
 document.querySelectorAll('[data-claim]').forEach(b=>b.addEventListener('click',()=>openClaim(b.dataset.claim)));
}

async function handle(action){
 if(busy)return;
 if(action==='owner'){role='owner';review=null;render();return;}
 if(action==='human'){role='human';render();if(data.case)await act('review');return;}
 if(action==='logs'){openLogs();return;}
 if(action==='example'||action==='absent'){
  if(!await act('reset'))return;
  const input=defaultInput();if(action==='absent'){input.category='watch';input.description='black wristwatch';input.color='black';}
  await act('search',input);return;
 }
 if(action==='info'){const text=document.querySelector('#followup')?.value;if(!text?.trim()){toast('Enter an additional detail first.',true);return;}await act('info',{text});return;}
 if(action==='approve'){const pickup=document.querySelector('#pickup')?.value;await act('approve',{pickup});return;}
 if(action==='clarify'){if(await act('clarify',{note:'What color is the sticker near the cap?'}))toast('Question sent. Switch to the owner’s view to answer.');return;}
 if(['reject','returned'].includes(action)){await act(action);return;}
 if(action==='reset'){if(await act('reset')){await act('search',defaultInput());toast('A fresh synthetic-data session is ready.');}return;}
 if(['repeat','misuse','refresh'].includes(action)){if(await act(action))toast(action==='misuse'?'The agent’s self-approval request was blocked.':action==='repeat'?'The retry reused the existing record.':'Status refreshed.');}
}

function openClaim(id){
 const candidate=data.candidates.find(c=>c.report_id===id);if(!candidate)return;
 const d=document.querySelector('#claim-dialog');
 d.innerHTML=`<div class="dialog-head"><h2 id="claim-title">Submit a private claim</h2><button class="icon-btn" aria-label="Close claim dialog" data-close>${svg('close')}</button></div><form id="claim-form"><div class="dialog-body"><p>${esc(titleFor(candidate.found_report))} · ${esc(locationNames[candidate.found_report.location]||candidate.found_report.location)}</p><label for="claim-message">Describe a detail the holder can verify</label><textarea id="claim-message" name="message" required maxlength="1000">${['flask','bottle','water bottle','thermos'].includes(candidate.found_report.category)?'There is a cactus sticker near the cap.':''}</textarea><div class="dialog-hint">${svg('lock')}This clue is for claim review. It will not be added to the public listing.</div></div><div class="dialog-footer"><button class="btn ghost" type="button" data-close>Keep checking</button><button class="btn primary" type="submit">Send private claim ${svg('arrow')}</button></div></form>`;
 d.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>d.close()));
 d.querySelector('#claim-form').addEventListener('submit',async e=>{e.preventDefault();const message=new FormData(e.target).get('message');d.close();if(await act('claim',{found_id:id,message}))toast('Claim sent. Waiting for the human holder.');});d.showModal();
}

function openLogs(){
 const d=document.querySelector('#log-dialog');
 d.innerHTML=`<div class="dialog-head"><h2 id="log-title">${data.mode==='live'?'Local service activity log':'Interactive demo activity log'}</h2><button class="icon-btn" data-close aria-label="Close activity log">${svg('close')}</button></div><div class="dialog-body"><p>${data.mode==='live'?'These status codes and results come from the real Lost Link service. Credentials and private verification clues are excluded.':'This online preview simulates the workflow; it is not a service execution record. The local version shows actual HTTP responses.'}</p>${data.events.map(e=>`<div class="log-entry"><strong>${esc(actorNames[e.actor]||'System')} · ${esc(e.title)}</strong>${e.http?`<p><code>${esc(e.http.method)} ${esc(e.http.path)} → ${e.http.status}</code></p>`:''}${e.detail?`<pre>${esc(JSON.stringify(e.detail,null,2))}</pre>`:''}</div>`).join('')}</div><div class="dialog-footer"><button class="btn secondary" id="download-log">${svg('download')}Export this session</button><button class="btn primary" data-close>Done</button></div>`;
 d.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>d.close()));d.querySelector('#download-log').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({mode:data.mode,exported_at:new Date().toISOString(),case:data.case,events:data.events},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='lost-link-'+data.mode+'-record.json';a.click();URL.revokeObjectURL(url);});d.showModal();
}

async function init(){
 try{const r=await fetch('/demo/state',{signal:AbortSignal.timeout(1800)});if(!r.ok)throw Error();const d=await r.json();if(d.mode!=='live')throw Error();provider=new LiveProvider();data=d;}
 catch{provider=new InteractiveProvider();data=provider.snapshot();}
 render();if(!data.lost)await act('search',defaultInput());
}
init();
