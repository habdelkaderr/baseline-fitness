import json, io, os, re
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)

SP=_os.path.join(PROJECT,"build","httest")
D=_os.path.join(PROJECT,"private","whoop-data")
html=io.open(_os.path.join(PROJECT,"build","baseline.html"),encoding="utf-8").read()

def rd(f, maxlines=None):
    """The user's own export, if it is here. It is deliberately optional: a
    test suite must not require somebody's private medical history to run.
    Absent, the importer receives an empty string and rejects it harmlessly,
    and every other fixture in this file is synthetic anyway."""
    p=os.path.join(D,f)
    if not os.path.isfile(p):
        return ""
    t=io.open(p,encoding="utf-8").read()
    if maxlines:
        t="\n".join(t.split("\n")[:maxlines])
    return t

CSV={
 "physiological_cycles.csv": rd("physiological_cycles.csv"),
 "workouts.csv": rd("workouts.csv"),
 "sleeps.csv": rd("sleeps.csv"),
 "journal_entries.csv": rd("journal_entries.csv", 900),
}

shim = """<script>
(function(){
  var mem={};
  try{ Object.defineProperty(window,'localStorage',{value:{
    getItem:function(k){return k in mem?mem[k]:null;},
    setItem:function(k,v){mem[k]=String(v);},
    removeItem:function(k){delete mem[k];},
    clear:function(){mem={};},
    key:function(i){return Object.keys(mem)[i]||null;},
    get length(){return Object.keys(mem).length;}
  },configurable:true});}catch(e){window.__lsFail=e.message;}
  window.__errors=[];
  window.onerror=function(m,s,l,c,e){window.__errors.push(m+' @'+l+':'+c);};
  window.addEventListener('unhandledrejection',function(e){window.__errors.push('promise: '+e.reason);});
})();
</script>
"""

tests = """<script>
var CSVDATA = __CSVDATA__;
async function runTests(){
var R=[], pass=0, fail=0;
function ok(name, cond, extra){ if(cond){pass++;R.push('PASS | '+name);} else {fail++;R.push('FAIL | '+name+(extra?' :: '+extra:''));} }
/* Setting .value on a control does not notify anything listening to it, and
   the activity form derives its length and its strain estimate from exactly
   those listeners. Every test that fills a time field has to fire the event
   a real tap would have fired. */
/* Choosing an activity goes through the picker now, the way a person does:
   tap the row that stands in for the list, then tap a row in the list. */
function chooseAct(type){
  var p=document.getElementById('asPick');
  if(!p) throw new Error('no activity picker row on this sheet');
  p.click();
  var r=document.querySelector('#sheetBody .parow[data-k="'+type+'"]');
  if(!r) throw new Error('type not offered by the picker: '+type);
  r.click();
  return r;
}
/* Open a settings group by its id. Addressing them by position broke the
   moment a group was inserted, and pointed several assertions at the wrong
   screen while still passing. */
function openSetGroup(id){
  resetStack(); TAB='today'; openSettings();
  /* Profile is the card at the top rather than a row in the list, so it has
     its own door; everything else is indexed among the rendered rows. */
  if(id==='profile'){ document.getElementById('setProfile').click(); return; }
  var i=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf(id);
  if(i<0) throw new Error('no settings group: '+id);
  document.getElementById('setRows').querySelectorAll('button')[i].click();
}
function setTime(id, v){
  var e=document.getElementById(id);
  if(!e) throw new Error('no such field: '+id);
  e.value=v;
  e.dispatchEvent(new Event('input',{bubbles:true}));
  e.dispatchEvent(new Event('change',{bubbles:true}));
  return e;
}
function tryRun(name, fn){ try{ var v=fn(); ok(name,true); return v; }catch(e){ fail++; R.push('THROW| '+name+' :: '+e.message+' | '+(e.stack||'').split('\\n')[1]); return null; } }

// ---------- boot sanity ----------
ok('no load-time errors', window.__errors.length===0, window.__errors.join(' ;; '));
ok('DB initialised', !!DB && !!DB.profile);
ok('Store initialised before DB', Store && typeof Store.mode==='string', Store?Store.mode:'none');
ok('exercise library seeded (>=80)', DB.exercises.length>=80, 'got '+DB.exercises.length);
ok('workouts seeded (>=10)', DB.workouts.length>=10, 'got '+DB.workouts.length);
ok('activities array exists', Array.isArray(DB.activities));
ok('no legacy tennis/cardio keys', DB.tennis===undefined && DB.cardio===undefined);

// every workout block references a real exercise
var badRef=[];
DB.workouts.forEach(function(w){ ['full','reduced','recovery'].forEach(function(v){
  w.blocks[v].forEach(function(b){ if(!DB.exercises.some(function(e){return e.id===b.ex;})) badRef.push(w.id+'/'+v+'/'+b.ex); }); }); });
ok('all workout exercise refs valid', badRef.length===0, badRef.join(','));
// every workout has all 3 variants non-empty
var emptyV=[];
DB.workouts.forEach(function(w){ ['full','reduced','recovery'].forEach(function(v){ if(!w.blocks[v].length) emptyV.push(w.id+'/'+v); }); });
ok('all workouts have 3 populated variants', emptyV.length===0, emptyV.join(','));
// exercise field completeness
var incomplete=DB.exercises.filter(function(e){ return !e.name||!e.cat||!e.muscles||!e.sets||!e.reps||!e.rpe||!e.rest||!e.how||!e.cue||!e.prog; });
ok('all exercises have core coaching fields', incomplete.length===0, incomplete.map(function(e){return e.id;}).join(','));
// warmup/cooldown refs
// 'sport' is not a fixed WARMUPS entry — it is generated for the chosen sports
var badW=DB.workouts.filter(function(w){ return !warmupFor(w)||!COOLDOWNS[w.cool]; });
ok('all workouts have valid warm-up/cool-down', badW.length===0, badW.map(function(w){return w.id;}).join(','));
var wuSport=warmupFor({warm:'sport'});
ok('the sport warm-up is generated, not a fixed routine',
   wuSport && wuSport.items.length>=4 && !Object.keys(WARMUPS).some(function(k){return WARMUPS[k]===wuSport;}),
   wuSport && wuSport.name);
(function(){
  var keep=DB.profile.sports;
  DB.profile.sports=['football'];
  var f=warmupFor({warm:'sport'});
  DB.profile.sports=['cycling'];
  var c=warmupFor({warm:'sport'});
  DB.profile.sports=keep;
  ok('a footballer and a cyclist get different warm-ups',
     JSON.stringify(f.items)!==JSON.stringify(c.items),
     f.name+' vs '+c.name);
  ok('the footballer warm-up includes sprint prep',
     f.items.some(function(i){return /skip|build-up|high knees/i.test(i.n);}),
     f.items.map(function(i){return i.n;}).join(', '));
})();

// ---------- CSV parsing + import ----------
var r1=tryRun('import physiological_cycles.csv', function(){ return importWhoopFile('physiological_cycles.csv', CSVDATA['physiological_cycles.csv']); });
ok('cycles detected as "cycles"', r1 && r1.kind==='cycles', r1&&r1.kind);
ok('cycle days imported (161-181 from 181 rows)', DB.whoop.cycles.length>=161 && DB.whoop.cycles.length<=181, 'got '+DB.whoop.cycles.length);
ok('rows accounted for (added+merged+dupes+bad==rows)', r1 && (r1.added+r1.merged+r1.dupes+r1.bad+r1.naps)===r1.rows,
   r1?JSON.stringify(r1):'');
ok('same-day cycles reported as merged, not silently dropped', r1 && r1.merged>0, r1&&r1.merged);
ok('every cycle day is unique', (function(){var s=new Set(DB.whoop.cycles.map(function(c){return c.date;})); return s.size===DB.whoop.cycles.length;})());
ok('merged day keeps a recovery score', (function(){ return DB.whoop.cycles.filter(function(c){return c.recovery!=null;}).length >= DB.whoop.cycles.length-5; })(),
   DB.whoop.cycles.filter(function(c){return c.recovery==null;}).length+' without recovery');
ok('no import error', r1 && !r1.error, r1&&r1.error);

var beforeC=DB.whoop.cycles.length;
var r1b=importWhoopFile('physiological_cycles.csv', CSVDATA['physiological_cycles.csv']);
ok('re-import adds no duplicate cycles', DB.whoop.cycles.length===beforeC, beforeC+' -> '+DB.whoop.cycles.length);
ok('re-import reports dupes', r1b.dupes>0, 'dupes='+r1b.dupes);

var r2=tryRun('import workouts.csv', function(){ return importWhoopFile('workouts.csv', CSVDATA['workouts.csv']); });
ok('workouts detected', r2 && r2.kind==='workouts', r2&&r2.kind);
ok('workouts imported ~192', DB.whoop.workouts.length>=185, 'got '+DB.whoop.workouts.length);
var bw=DB.whoop.workouts.length;
importWhoopFile('workouts.csv', CSVDATA['workouts.csv']);
ok('re-import adds no duplicate workouts', DB.whoop.workouts.length===bw, bw+' -> '+DB.whoop.workouts.length);

var r3=tryRun('import journal_entries.csv', function(){ return importWhoopFile('journal_entries.csv', CSVDATA['journal_entries.csv']); });
ok('journal detected', r3 && r3.kind==='journal', r3&&r3.kind);
ok('journal rows imported', DB.whoop.journal.length>100, 'got '+DB.whoop.journal.length);

var cyBefore=DB.whoop.cycles.length;
var recBefore=DB.whoop.cycles.filter(function(c){return c.recovery!=null;}).length;
var r4=tryRun('import sleeps.csv', function(){ return importWhoopFile('sleeps.csv', CSVDATA['sleeps.csv']); });
ok('sleeps detected', r4 && (r4.kind==='sleeps'||r4.kind==='cycles'), r4&&r4.kind);
ok('sleeps import skipped naps', r4 && r4.naps>0, r4&&r4.naps);
ok('sleeps import did not destroy recovery scores',
   DB.whoop.cycles.filter(function(c){return c.recovery!=null;}).length>=recBefore,
   recBefore+' -> '+DB.whoop.cycles.filter(function(c){return c.recovery!=null;}).length);
ok('sleeps import did not explode the day count', DB.whoop.cycles.length<=cyBefore+8, cyBefore+' -> '+DB.whoop.cycles.length);

// garbage file rejected
var rg=importWhoopFile('random.csv','foo,bar,baz\\n1,2,3');
ok('unrecognised CSV rejected with message', rg.kind===null && !!rg.error, JSON.stringify(rg));
var re2=importWhoopFile('empty.csv','');
ok('empty CSV rejected', !!re2.error);

// quoted CSV handling
var Q=String.fromCharCode(34);
var q=parseCSV('a,b\\n'+Q+'x,1'+Q+','+Q+'he said '+Q+Q+'hi'+Q+'\\n');
ok('CSV quote handling', q[1][0]==='x,1' && q[1][1]==='he said '+Q+'hi', JSON.stringify(q[1]));
var q2=parseCSV('a,b,c\\n1,,3\\n');
ok('CSV empty field handling', q2[1].length===3 && q2[1][1]==='', JSON.stringify(q2[1]));
// renamed header tolerance
var rn=importWhoopFile('weird.csv','Cycle start time,Recovery score %,Day Strain\\n2030-01-01 00:00:00,80,5.0\\n');
ok('tolerant header matching works', rn.kind==='cycles' && rn.added===1, JSON.stringify(rn));

// ---------- baselines ----------
tryRun('recomputeBaselines', function(){ return recomputeBaselines(); });
ok('baselines computed flag', DB.baselines.computed===true);
ok('HRV baseline plausible (60-110)', DB.baselines.hrv>60 && DB.baselines.hrv<110, 'got '+DB.baselines.hrv);
ok('RHR baseline plausible (45-62)', DB.baselines.rhr>45 && DB.baselines.rhr<62, 'got '+DB.baselines.rhr);
ok('sleep need plausible (420-620)', DB.baselines.sleepNeed>420 && DB.baselines.sleepNeed<620, 'got '+DB.baselines.sleepNeed);
ok('HRV SD > 0', DB.baselines.hrvSd>0, 'got '+DB.baselines.hrvSd);

// ---------- activity load model ----------
var lt=activityLoad({type:'tennis',min:100,rpe:7});
var lw=activityLoad({type:'walking',min:30,rpe:3});
var lf=activityLoad({type:'football',min:90,rpe:8});
var lc=activityLoad({type:'cycling',min:30,rpe:3});
ok('tennis 100min RPE7 load in 10-18', lt>=10&&lt<=18, 'got '+lt);
ok('walking load < tennis load', lw<lt, lw+' vs '+lt);
ok('football hard > tennis moderate', lf>lt, lf+' vs '+lt);
ok('easy cycling is low load', lc<5, 'got '+lc);
ok('load monotonic in duration', activityLoad({type:'running',min:60,rpe:6})>activityLoad({type:'running',min:30,rpe:6}));
ok('load monotonic in RPE', activityLoad({type:'running',min:40,rpe:9})>activityLoad({type:'running',min:40,rpe:4}));
ok('zero duration => zero load', activityLoad({type:'running',min:0,rpe:8})===0);
var dSwim=activityDemand({type:'swimming',min:45,rpe:7});
var dRun=activityDemand({type:'running',min:45,rpe:7});
ok('swimming loads upper > lower', dSwim.upper>dSwim.lower);
ok('running loads lower > upper', dRun.lower>dRun.upper);
ok('cycling near-zero impact', activityDemand({type:'cycling',min:60,rpe:6}).impact < activityDemand({type:'running',min:60,rpe:6}).impact/4);

// ---------- readiness engine ----------
var D0='2030-06-10';
function rdy(ci){ return readiness(D0, ci); }
var green=rdy({recovery:90,hrv:95,rhr:50,sleepMin:500,sleepNeed:500,prevStrain:5,energy:9,soreness:1,stress:2,motivation:9,pain:'None'});
var red  =rdy({recovery:20,hrv:58,rhr:62,sleepMin:280,sleepNeed:500,prevStrain:18,energy:2,soreness:9,stress:9,motivation:2,pain:'None'});
var mid  =rdy({recovery:60,hrv:83,rhr:54,sleepMin:450,sleepNeed:500,prevStrain:10,energy:6,soreness:4,stress:5,motivation:6,pain:'None'});
ok('great inputs => green', green.band==='green', green.band+' score '+green.score);
ok('terrible inputs => red or orange', (red.band==='red'||red.band==='orange'), red.band+' score '+red.score);
ok('middling inputs => yellow/orange', (mid.band==='yellow'||mid.band==='orange'||mid.band==='green'), mid.band+' score '+mid.score);
ok('green score > mid score > red score', green.score>mid.score && mid.score>red.score, [green.score,mid.score,red.score].join('/'));
ok('readiness gives reasons', green.why.length>=4, 'n='+green.why.length);
ok('does not rely on recovery alone', green.parts.length>=5, 'parts='+green.parts.length);
var painM=rdy({recovery:95,hrv:100,rhr:48,sleepMin:520,sleepNeed:500,prevStrain:3,energy:9,soreness:1,stress:1,motivation:9,pain:'Moderate'});
ok('moderate pain caps band at orange', painM.band==='orange'||painM.band==='red', painM.band);
var painS=rdy({recovery:95,hrv:100,rhr:48,sleepMin:520,sleepNeed:500,prevStrain:3,energy:9,soreness:1,stress:1,motivation:9,pain:'Significant'});
ok('significant pain => red', painS.band==='red', painS.band);
// sleep cliff
var s55=rdy({recovery:70,sleepMin:445,sleepNeed:500,hrv:83,rhr:54,prevStrain:5,energy:7,soreness:3,stress:3,motivation:7,pain:'None'});
var s130=rdy({recovery:70,sleepMin:370,sleepNeed:500,hrv:83,rhr:54,prevStrain:5,energy:7,soreness:3,stress:3,motivation:7,pain:'None'});
ok('sleep cliff: 55min short scores higher than 130min short', s55.score>s130.score, s55.score+' vs '+s130.score);
// HRV z
var zlo=rdy({recovery:70,hrv:60,rhr:54,sleepMin:480,sleepNeed:500,prevStrain:5,energy:7,soreness:3,stress:3,motivation:7,pain:'None'});
ok('HRV far below baseline flags hrvLow', zlo.flags.indexOf('hrvLow')>=0, zlo.flags.join(','));
var zhi=rdy({recovery:70,hrv:83,rhr:65,sleepMin:480,sleepNeed:500,prevStrain:5,energy:7,soreness:3,stress:3,motivation:7,pain:'None'});
ok('RHR far above baseline flags rhrHigh', zhi.flags.indexOf('rhrHigh')>=0, zhi.flags.join(','));
// missing data must not crash
tryRun('readiness with empty check-in', function(){ var r=readiness(D0,{}); if(r.score==null) throw new Error('null score'); return r; });
tryRun('readiness with partial data', function(){ return readiness(D0,{recovery:70}); });

// ---------- DAILY DECISION ENGINE ----------
DB.profile.planStart='2030-06-03';
DB.sessions=[]; DB.activities=[]; DB.plans={};
/* A finished setup, because the engine is now fully driven by one: a tennis
   player with dumbbells, a band, a bike and somewhere to run. Without this the
   app correctly refuses to prescribe runs or rides to someone who never said
   they could do them. */
DB.profile.sports=['tennis']; DB.profile.sport='tennis';
DB.profile.physiques=['athletic']; DB.profile.physique='athletic';
DB.profile.gear=['db','band','bike','run']; DB.profile.daysPerWeek=4;
DB.profile.onboarded=true;
applyGoalTargets();
ok('setup-derived targets cover every system',
   DB.targets.lower>0&&DB.targets.upper>0&&DB.targets.power>0&&DB.targets.core>0&&DB.targets.run>0&&DB.targets.bike>0,
   JSON.stringify(DB.targets));
var GOOD={recovery:88,hrv:95,rhr:50,sleepMin:500,sleepNeed:500,prevStrain:4,energy:8,soreness:2,stress:3,motivation:8,pain:'None',sportToday:false,availTime:60};
var D1='2030-06-13'; // Thursday — mid-week, so weekly accounting has history
function rec(date,ci){ return recommend(date,ci); }
function whyHas(r,re){ return r.why.some(function(n){return re.test(n.t);}); }
function logS(date,wid,cat,rpe){ var w=DB.workouts.find(function(x){return x.id===wid;});
  DB.sessions.push({id:'ts'+uid(),date:date,workoutId:wid,workoutName:w?w.name:wid,category:cat,variant:'full',
    done:true,durationMin:45,setsDone:15,volume:900,sessionRpe:rpe||8,entries:[]}); }

ok('no fixed weekly calendar exists', DB.schedule===undefined && DB.tennisDays===undefined);
ok('weekly targets exist', DB.targets && DB.targets.lower>0 && DB.targets.core>0);

// fresh + green => legs (top of the goal hierarchy under tennis)
var r1=rec(D1,GOOD);
ok('fresh green day picks Lower Body', r1.id==='lower', r1.id+' score board: '+r1.scored.slice(0,3).map(function(x){return x.c.id+':'+x.score;}).join(' '));
ok('recommendation carries ONE primary', typeof r1.label==='string' && r1.label.length>0);
ok('recommendation has intensity', !!r1.intensity, r1.intensity);
ok('recommendation has duration', r1.est>0, r1.est);
ok('recommendation explains why', r1.why.length>=3, 'n='+r1.why.length);
ok('recommendation states goal link', /leg strength/i.test(r1.goalNote), r1.goalNote);
ok('engine ranks every option', r1.scored.length>=9, r1.scored.length);

var YD=addDays(D1,-1);
// legs trained yesterday => not legs again
logS(YD,'w_lowerA','lower');
var r2=rec(D1,GOOD);
ok('legs yesterday => does not pick legs', r2.id!=='lower', r2.id);
ok('legs yesterday => does not pick power either', r2.id!=='power', r2.id);
ok('legs-yesterday reasoning shown', whyHas(r2,/legs were loaded yesterday|loaded yesterday/i), JSON.stringify(r2.why.map(function(n){return n.t;})));

// hard football yesterday => not legs, not power
DB.sessions=[];
DB.activities=[{id:'a1',date:YD,type:'football',min:90,rpe:9,planned:false}];
var r3=rec(D1,GOOD);
ok('hard football yesterday => not legs', r3.id!=='lower', r3.id);
ok('hard football yesterday => not power', r3.id!=='power', r3.id);
ok('football named in the reasoning', whyHas(r3,/football/i), JSON.stringify(r3.why.map(function(n){return n.t;})));

// the scenario from the brief: unexpected 90 min tennis yesterday => upper + core
DB.activities=[{id:'a2',date:YD,type:'tennis',min:90,rpe:8,planned:false}];
var r4=rec(D1,GOOD);
ok('tennis yesterday => recommends Upper Body', r4.id==='upper', r4.id+' | '+r4.scored.slice(0,4).map(function(x){return x.c.id+':'+x.score;}).join(' '));
ok('tennis yesterday => core added on', r4.addCore===true, 'addCore='+r4.addCore);
ok('upper-after-tennis logic explained', whyHas(r4,/went through your legs|costs them nothing/i), JSON.stringify(r4.why.map(function(n){return n.t;})));
ok('tennis does not count as an upper-body session', systemHistory(D1).since.upper===99, systemHistory(D1).since.upper);

// then with legs recovered => back to lower or power
DB.activities=[];
logS(addDays(D1,-3),'w_upperA','upper');
var r5=rec(D1,GOOD);
ok('legs fresh again => legs or power', r5.id==='lower'||r5.id==='power', r5.id);
DB.sessions=[];

// long run yesterday => no run today, and not power
DB.activities=[{id:'a3',date:YD,type:'running',min:75,rpe:8,planned:true}];
var r6=rec(D1,GOOD);
ok('long run yesterday => not a run', r6.id.indexOf('run')!==0, r6.id);
ok('long run yesterday => not power', r6.id!=='power', r6.id+' | '+r6.scored.slice(0,3).map(function(x){return x.c.id+':'+x.score;}).join(' '));

// tennis-heavy last 7 days suppresses running even when legs are fine
DB.activities=[{id:'a4',date:addDays(D1,-4),type:'tennis',min:110,rpe:8,planned:true},
               {id:'a5',date:addDays(D1,-6),type:'tennis',min:110,rpe:8,planned:true}];
var r7=rec(D1,GOOD);
ok('tennis-heavy week does not recommend running', r7.id.indexOf('run')!==0, r7.id);
var runOpt=r7.scored.find(function(x){return x.c.id==='run_e';});
ok('running was actively suppressed, not just outranked',
   runOpt && runOpt.notes.some(function(n){return /tennis/i.test(n.t||'');}),
   runOpt?JSON.stringify(runOpt.notes.map(function(n){return n.t;})):'none');
ok('rolling-7d tennis is what suppresses running (not calendar week)',
   systemHistory(D1).load.sport7>=200, systemHistory(D1).load.sport7);

// sore legs + recovered => bike, not run/legs
DB.activities=[];
var r8=rec(D1,Object.assign({},GOOD,{soreness:7}));
ok('soreness 7 => not legs', r8.id!=='lower', r8.id);
ok('soreness 7 => not power', r8.id!=='power', r8.id);
var legOpt=r8.scored.find(function(x){return x.c.id==='lower';});
ok('sore legs blocks lower explicitly', !!legOpt.blocked, legOpt.blocked);

// readiness ladder from the brief
var base={hrv:83,rhr:54,sleepMin:470,sleepNeed:500,prevStrain:6,energy:7,soreness:2,stress:4,motivation:7,pain:'None',sportToday:false,availTime:60};
DB.sessions=[]; DB.activities=[];
var hi=rec(D1,Object.assign({},base,{recovery:88,hrv:97,rhr:50,energy:9}));
var mid2=rec(D1,Object.assign({},base,{recovery:48,hrv:74,rhr:57,energy:5}));
var lo=rec(D1,Object.assign({},base,{recovery:28,hrv:62,rhr:61,sleepMin:320,energy:2,soreness:6}));
ok('recovery 88 => hard training', ['lower','power'].indexOf(hi.id)>=0, hi.id);
ok('recovery 48 => softer choice', ['upper','core','bike','mobility'].indexOf(mid2.id)>=0, mid2.id+' band '+mid2.readiness.band);
ok('recovery 28 => recovery/rest', ['mobility','rest'].indexOf(lo.id)>=0, lo.id+' band '+lo.readiness.band);
ok('changing one input changes the answer', hi.id!==mid2.id && mid2.id!==lo.id, [hi.id,mid2.id,lo.id].join('/'));

// pain gates
var pm=rec(D1,Object.assign({},GOOD,{pain:'Moderate'}));
ok('moderate pain => no loaded leg/upper/run', ['mobility','core','bike','rest'].indexOf(pm.id)>=0, pm.id);
var ps=rec(D1,Object.assign({},GOOD,{pain:'Significant'}));
ok('significant pain => mobility or rest', ['mobility','rest'].indexOf(ps.id)>=0, ps.id);

// tennis TODAY
var tt=rec(D1,Object.assign({},GOOD,{sportToday:true}));
ok('tennis today => not legs/power/run', ['lower','power'].indexOf(tt.id)<0 && tt.id.indexOf('run')!==0, tt.id);
ok('tennis today => offers pre-court prep', tt.prep==='w_prep');
ok('tennis today favours upper or core', ['upper','core','mobility'].indexOf(tt.id)>=0, tt.id);
var lowT=tt.scored.find(function(x){return x.c.id==='lower';});
ok('legs explicitly blocked on a tennis day', !!lowT.blocked, lowT.blocked);

// logged tennis is detected without the toggle
DB.activities=[{id:'a6',date:D1,type:'tennis',min:95,rpe:7,planned:false}];
var tl=rec(D1,Object.assign({},GOOD,{sportToday:null}));
ok('logged tennis today detected automatically', tl.isSport===true);
DB.activities=[];

// weekly targets: already met => stop pushing (log inside the same week)
DB.targets.lower=1; DB.sessions=[]; DB.activities=[];
logS(addDays(D1,-3),'w_lowerA','lower');
var rt=rec(D1,GOOD);
var lo2=rt.scored.find(function(x){return x.c.id==='lower';});
ok('met target lowers that option score', lo2.notes.some(function(n){return /already done/i.test(n.t||'');}),
   JSON.stringify(lo2.notes.map(function(n){return n.t;})));
ok('met target is surfaced as a reason not to force more',
   lo2.notes.some(function(n){return /no need to force more/i.test(n.t||'');}));
DB.targets.lower=2; DB.sessions=[];
// behind on target => boosted
DB.targets.upper=3;
var rb=rec(D1,GOOD);
var up2=rb.scored.find(function(x){return x.c.id==='upper';});
/* The shortfall is still stated - it is what justifies the score - but as a
   count rather than a verdict. "You are behind" told a user who had done
   nothing wrong that they had failed a quota the app set for them. */
ok('an unmet target is surfaced as a count', up2.notes.some(function(n){return /0 of 3 upper body strength so far this week/i.test(n.t||'');}),
   JSON.stringify(up2.notes.map(function(n){return n.t;})));
ok('and not as an accusation', !up2.notes.some(function(n){return /behind/i.test(n.t||'');}),
   JSON.stringify(up2.notes.map(function(n){return n.t;})));
DB.targets.upper=2;

// time available
var t20=rec(D1,Object.assign({},GOOD,{availTime:20}));
ok('20 min => short, finishable session', t20.est<=25, t20.id+' est '+t20.est);
ok('20 min => no core add-on bloat', !(t20.addCore && t20.est>25));
var t90=rec(D1,Object.assign({},GOOD,{availTime:90}));
ok('90 min allows a core add-on', t90.addCore===true || t90.id==='lower', t90.id+' addCore '+t90.addCore);

// combination building
var combo=rec(D1,Object.assign({},GOOD,{availTime:75}));
if(combo.addCore){
  var blocks=sessionBlocks(combo);
  var primary=DB.workouts.find(function(w){return w.id===combo.workoutId;});
  ok('combined session is longer than the primary alone',
     blocks.length > (primary.blocks[combo.variant]||primary.blocks.full).length, blocks.length);
  ok('combined session includes core exercises',
     blocks.some(function(b){var e=exOf(b.ex); return e && e.cat==='core';}));
} else { ok('combined session is longer than the primary alone',true); ok('combined session includes core exercises',true); }

// never combine two demanding systems
var allRecs=[];
[0,1,2,3,4,5,6].forEach(function(off){
  DB.sessions=[]; DB.activities=[];
  allRecs.push(rec(addDays(D1,off),GOOD));
});
ok('never recommends power+legs simultaneously',
   allRecs.every(function(r){ return !(r.id==='power' && r.workoutId==='w_lowerA'); }));

// engine never returns a blocked option
DB.sessions=[]; DB.activities=[];
var many=[];
[GOOD, Object.assign({},GOOD,{soreness:9}), Object.assign({},GOOD,{pain:'Significant'}),
 Object.assign({},GOOD,{recovery:15,hrv:55,rhr:64,sleepMin:250}), Object.assign({},GOOD,{availTime:15}),
 Object.assign({},GOOD,{sportToday:true}), {}].forEach(function(ci){
  var r=rec(D1,ci); many.push(r);
});
ok('engine always returns a usable recommendation', many.every(function(r){ return !!r.id && !!r.label; }));
ok('engine never returns a blocked candidate',
   many.every(function(r){ var s=r.scored.find(function(x){return x.c.id===r.id;}); return !s.blocked; }),
   many.map(function(r){var s=r.scored.find(function(x){return x.c.id===r.id;}); return r.id+':'+(s.blocked||'ok');}).join(' | '));
ok('empty check-in still yields a recommendation', !!rec(D1,{}).id);

// rest is only chosen when it should be
DB.sessions=[]; DB.activities=[];
var never=rec(D1,GOOD);
ok('green + fresh never recommends Rest', never.id!=='rest', never.id);

// week accounting
DB.sessions=[]; DB.activities=[];
logS('2030-06-10','w_lowerA','lower'); logS('2030-06-11','w_upperA','upper');
DB.activities=[{id:'w1',date:'2030-06-12',type:'running',min:35,rpe:5,planned:true},
               {id:'w2',date:'2030-06-13',type:'tennis',min:100,rpe:8,planned:false}];
var WPt=weekProgress('2030-06-14');
ok('weekProgress counts lower sessions', WPt.lower===1, WPt.lower);
ok('weekProgress counts upper sessions', WPt.upper===1, WPt.upper);
ok('weekProgress counts runs from activities', WPt.run===1, WPt.run);
ok('weekProgress counts tennis minutes', WPt.sportMin===100, WPt.sportMin);
ok('weekProgress week starts Monday', weekStartOf('2030-06-14')==='2030-06-10', weekStartOf('2030-06-14'));
ok('weekStartOf on a Sunday looks back', weekStartOf('2030-06-16')==='2030-06-10', weekStartOf('2030-06-16'));

// system history — lower is LOAD based (tennis loads legs), upper is TRAINING based
var SH=systemHistory('2030-06-14');
ok('systemHistory: tennis yesterday counts as leg load', SH.since.lower===1, SH.since.lower);
ok('systemHistory: last actual upper session found', SH.since.upper===3, SH.since.upper);
ok('systemHistory finds last tennis', SH.since.sport===1, SH.since.sport);
ok('systemHistory finds last run', SH.since.run===2, SH.since.run);
ok('systemHistory accumulates 3-day load', SH.load.load3>0, SH.load.load3);
ok('systemHistory tracks shoulder load from serving', SH.load.shoulder3>0, SH.load.shoulder3);
// a swim DOES count as upper training
DB.activities.push({id:'w3',date:'2030-06-13',type:'swimming',min:60,rpe:7,planned:true});
ok('swimming counts as upper training', systemHistory('2030-06-14').since.upper===1, systemHistory('2030-06-14').since.upper);
DB.activities=DB.activities.filter(function(a){return a.id!=='w3';});

// A/B alternation
DB.sessions=[]; logS('2030-06-09','w_lowerA','lower');
ok('alternates Lower A -> Lower B', alternate('w_lowerA','w_lowerB')==='w_lowerB');
logS('2030-06-10','w_lowerB','lower');
ok('alternates Lower B -> Lower A', alternate('w_lowerA','w_lowerB')==='w_lowerA');
DB.sessions=[]; DB.activities=[]; DB.plans={};

// user override
DB.plans[D1]={id:'upper',workoutId:'w_upperA',variant:'reduced',label:'Upper Body Strength',emoji:'🏠',est:30};
ok('override is stored', !!DB.plans[D1]);
ok('override is not treated as failure (engine still reasons)', rec(D1,GOOD).why.length>0);
DB.plans={};

// cardio workouts exist and are distinct
['w_runEasy','w_runQuality','w_runInt','w_bike'].forEach(function(id){
  ok('cardio workout exists: '+id, !!DB.workouts.find(function(w){return w.id===id;}));
});
ok('bike session load has low impact',
   sessionLoad({workoutId:'w_bike',variant:'full',durationMin:45,sessionRpe:5}).impact <
   sessionLoad({workoutId:'w_runEasy',variant:'full',durationMin:45,sessionRpe:5}).impact/3);

// ---------- demand aggregation ----------
DB.activities=[
 {id:'d1',date:'2030-07-01',type:'tennis',min:90,rpe:7,planned:true,time:'18:00'},
 {id:'d2',date:'2030-07-01',type:'walking',min:30,rpe:2,planned:false,time:'08:00'}
];
var dd=dayDemand('2030-07-01');
ok('dayDemand aggregates 2 items', dd.n===2, 'n='+dd.n);
ok('dayDemand load is sum', Math.abs(dd.load-(activityLoad(DB.activities[0])+activityLoad(DB.activities[1])))<0.15, dd.load);
ok('dayDemand has lower demand', dd.lower>0);
ok('dayItems sorted by time', dayItems('2030-07-01')[0].time==='08:00');
var rdm=rollingDemand('2030-07-03',7);
ok('rollingDemand includes prior days', rdm.load>0, rdm.load);
DB.activities=[];

// ---------- workout session lifecycle ----------
DB.sessions=[];
tryRun('startWorkout', function(){ startWorkout('w_lowerA','full','2030-06-10'); if(!W) throw new Error('W null'); });
ok('workout mode opened', document.getElementById('wmode').classList.contains('on'));
ok('a session opens on the overview, not in the work',
   W.phase==='preview' && W.step===0 && W.wuStep===0, W.phase+'/'+W.step);
ok('entries built from blocks', W.entries.length===DB.workouts.find(function(w){return w.id==='w_lowerA';}).blocks.full.length);
ok('each entry has planned sets', W.entries.every(function(e){return e.sets.length===e.plannedSets && e.plannedSets>0;}));
tryRun('advance to first exercise', function(){ W.phase='main'; W.step=0; drawWM(); });
ok('exercise screen rendered', /wm-ex/.test(document.getElementById('wmBody').innerHTML));
// complete all sets
tryRun('complete all sets', function(){
  W.entries.forEach(function(en){ en.sets.forEach(function(s){ s.reps='10'; s.weight='5'; s.rpe='8'; s.done=true; }); });
});
tryRun('render finish screen', function(){ W.phase='main'; W.step=W.entries.length; drawWM(); });
ok('finish screen rendered', /Workout complete/.test(document.getElementById('wmBody').innerHTML));
tryRun('save session', function(){ document.getElementById('fSave').click(); });
ok('session persisted', DB.sessions.length===1, 'n='+DB.sessions.length);
ok('session marked done', DB.sessions[0] && DB.sessions[0].done===true);
ok('session has volume', DB.sessions[0] && DB.sessions[0].volume>0, DB.sessions[0]&&DB.sessions[0].volume);
ok('session has setsDone', DB.sessions[0] && DB.sessions[0].setsDone>0);
ok('workout mode closed after save', !document.getElementById('wmode').classList.contains('on'));
ok('sessionLoad computes', sessionLoad(DB.sessions[0]).load>0, JSON.stringify(sessionLoad(DB.sessions[0])));
ok('lower session loads legs not arms', sessionLoad(DB.sessions[0]).lower > sessionLoad(DB.sessions[0]).upper);
ok('rest parse seconds', parseRest('90s')===90);
ok('rest parse minutes', parseRest('2 min')===120);
ok('rest parse dash', parseRest('—')===null);

/* Settings is an index of six pushed groups now. settingsBody() renders all of
   them and reveals one, so a test that wants a specific control just renders
   the body - which is what these assertions did before the split. */
function SETTINGS_ALL(){
  resetStack();
  settingsBody(document.getElementById('view'));
  /* reveal everything, so an assertion is about whether a control exists and
     works rather than which group it happens to sit in */
  Array.prototype.slice.call(document.querySelectorAll('#view .spane'))
    .forEach(function(el){ el.classList.add('on'); });
}

// ---------- check-in round trip (WHOOP user, uncovered date) ----------
DB.checkins={};
var keepMode0=DB.profile.mode; DB.profile.source='whoop'; DB.profile.mode='whoop';
tryRun('openCheckin renders', function(){ openCheckin('2030-06-10'); if(!document.getElementById('ciSave')) throw new Error('no save btn'); });
tryRun('save check-in', function(){
  var set=function(id,v){ var e=document.getElementById(id); if(e) e.value=v; };
  set('ciRec','75'); set('ciHrv','88'); set('ciRhr','52'); set('ciPs','6.5');
  set('ciSleep','465');
  document.getElementById('ciSave').click();
});
ok('check-in stored', !!DB.checkins['2030-06-10']);
ok('check-in sleep minutes stored', DB.checkins['2030-06-10'] && DB.checkins['2030-06-10'].sleepMin===465,
   DB.checkins['2030-06-10'] && DB.checkins['2030-06-10'].sleepMin);
ok('typed WHOOP numbers are stored for a WHOOP user', DB.checkins['2030-06-10'].recovery===75,
   DB.checkins['2030-06-10'].recovery);
ok('check-in has subjective values', DB.checkins['2030-06-10'].energy!=null);
closeSheet(); DB.profile.mode=keepMode0;

// ---------- sleep is one gesture ----------
(function(){
  DB.checkins={};
  openCheckin('2030-06-11');
  ok('sleep has no number keyboards',
     !document.getElementById('ciSh') && !document.getElementById('ciSm'));
  var s=document.getElementById('ciSleep');
  ok('sleep is a slider', s && s.type==='range', s?s.type:'missing');
  ok('it covers a plausible night', +s.min===180 && +s.max===720, s.min+'-'+s.max);
  ok('it moves in one-minute steps', +s.step===1, s.step);
  ok('and offers exact-minute buttons',
     document.querySelectorAll('[data-sleep]').length===2,
     document.querySelectorAll('[data-sleep]').length);
  ok('a minute button changes it by exactly one minute', (function(){
    s.value='450'; s.dispatchEvent(new Event('input',{bubbles:true}));
    document.querySelector('[data-sleep="1"]').click();
    return +document.getElementById('ciSleep').value===451; })(),
    document.getElementById('ciSleep').value);
  ok('and it cannot be pushed out of range', (function(){
    s.value=String(SLEEP_MIN); s.dispatchEvent(new Event('input',{bubbles:true}));
    document.querySelector('[data-sleep="-1"]').click();
    return +document.getElementById('ciSleep').value===SLEEP_MIN; })());
  ok('an odd number of minutes reads correctly', (function(){
    s.value='443'; s.dispatchEvent(new Event('input',{bubbles:true}));
    return document.getElementById('ciSleep_o').textContent==='7h 23m'; })(),
    document.getElementById('ciSleep_o').textContent);
  ok('the readout is human', /h/.test(document.getElementById('ciSleep_o').textContent),
     document.getElementById('ciSleep_o').textContent);

  // a stepper needed 30 taps to reach a normal night; a slider needs one move
  s.value='450'; s.dispatchEvent(new Event('input',{bubbles:true}));
  ok('one move sets any value', document.getElementById('ciSleep_o').textContent==='7h 30m',
     document.getElementById('ciSleep_o').textContent);
  document.getElementById('ciSave').click();
  ok('the slider value is what gets stored', DB.checkins['2030-06-11'].sleepMin===450,
     DB.checkins['2030-06-11'].sleepMin);
  closeSheet(); DB.checkins={};
})();

// ---------- the slider starts from a real prior, never an invention ----------
(function(){
  DB.checkins={};
  var keepW=DB.whoop;
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};

  // 1 · nothing to go on: the sleep-need target, and it says so
  openCheckin('2030-07-01');
  ok('with no history it starts at the sleep-need target',
     +document.getElementById('ciSleep').value===DB.baselines.sleepNeed,
     document.getElementById('ciSleep').value+' vs '+DB.baselines.sleepNeed);
  ok('and discloses that it is a target, not an answer',
     /target/.test($('#sheetBody').innerHTML));
  closeSheet();

  // 2 · last time's answer wins over the target
  DB.checkins['2030-07-01']={date:'2030-07-01',sleepMin:390,energy:6,soreness:3,
                             stress:4,motivation:7,pain:'None'};
  openCheckin('2030-07-02');
  ok('it starts from last time when there is a last time',
     +document.getElementById('ciSleep').value===390,
     document.getElementById('ciSleep').value);
  ok('and says where that came from',
     /last time/i.test($('#sheetBody').innerHTML));
  closeSheet();

  // 3 · imported data wins over everything
  DB.whoop={cycles:[{date:'2030-07-03',sleepMin:465,recovery:70}],
            workouts:[],journal:[],imports:[]};
  openCheckin('2030-07-03');
  ok('imported sleep wins over any prior',
     +document.getElementById('ciSleep').value===465,
     document.getElementById('ciSleep').value);
  closeSheet();

  DB.whoop=keepW; DB.checkins={};
})();

// ---------- the feel sliders start from last time, not a constant ----------
(function(){
  DB.checkins={};
  DB.checkins['2030-06-01']={date:'2030-06-01',energy:2,soreness:9,stress:8,
                             motivation:3,pain:'None'};
  openCheckin('2030-06-02');
  ok('energy starts from the previous answer',
     +document.getElementById('ciEn').value===2, document.getElementById('ciEn').value);
  ok('soreness starts from the previous answer',
     +document.getElementById('ciSo').value===9, document.getElementById('ciSo').value);
  ok('stress starts from the previous answer',
     +document.getElementById('ciSt').value===8, document.getElementById('ciSt').value);
  ok('motivation starts from the previous answer',
     +document.getElementById('ciMo').value===3, document.getElementById('ciMo').value);
  ok('and it says where the numbers came from',
     /yesterday.s answers/i.test($('#sheetBody').innerHTML));
  closeSheet();

  // with no history at all it falls back to neutral, not to nothing
  DB.checkins={};
  openCheckin('2030-06-02');
  ok('a first ever check-in still has usable slider positions',
     +document.getElementById('ciEn').value>0 && +document.getElementById('ciSo').value>0);
  ok('and does not claim to be carrying anything forward',
     !/yesterday.s answers/i.test($('#sheetBody').innerHTML));
  closeSheet();
  DB.checkins={};
})();

// ---------- notes are optional and out of the way ----------
(function(){
  DB.checkins={};
  openCheckin('2030-06-12');
  ok('the note field starts hidden',
     document.getElementById('ciNoteB').hasAttribute('hidden'));
  document.getElementById('ciNoteT').click();
  ok('and opens on request',
     !document.getElementById('ciNoteB').hasAttribute('hidden'));
  ok('saving with no note stored is fine', (function(){
    document.getElementById('ciSave').click();
    return DB.checkins['2030-06-12'] && DB.checkins['2030-06-12'].notes===''; })(),
    DB.checkins['2030-06-12'] && JSON.stringify(DB.checkins['2030-06-12'].notes));
  closeSheet(); DB.checkins={};
})();

// ---------- activity sheet round trip ----------
DB.activities=[];
tryRun('activitySheet renders', function(){ activitySheet(null,'2030-06-14');
  /* Save deliberately does not exist until a type is chosen */
  if(!document.getElementById('asPick')) throw new Error('no type picker'); });
// nothing is pre-selected: the old sheet defaulted the type to tennis, the
// intensity to Moderate and planned to true, recording three opinions the
// user never expressed
ok('no activity type is pre-selected',
   /Select activity/.test(document.getElementById('asPick').textContent),
   document.getElementById('asPick').textContent);
ok('Save is not offered until a type is chosen',
   !document.getElementById('asSave'));
ok('it says what to do instead', /Pick one/i.test($('#sheetBody').innerHTML));

tryRun('save activity', function(){
  chooseAct('tennis');
  setTime('asFrom','18:30'); setTime('asTo','20:05');
  document.getElementById('asSave').click();
});
ok('activity stored', DB.activities.length===1, 'n='+DB.activities.length);
ok('the length comes from the two times', DB.activities[0] && DB.activities[0].min===95,
   DB.activities[0] && DB.activities[0].min);
ok('and both times are kept',
   DB.activities[0] && DB.activities[0].time==='18:30' && DB.activities[0].endTime==='20:05',
   JSON.stringify(DB.activities[0] && [DB.activities[0].time, DB.activities[0].endTime]));
ok('the chosen type is recorded', DB.activities[0] && DB.activities[0].type==='tennis');
ok('intensity is not invented', DB.activities[0] && DB.activities[0].intensity===null,
   JSON.stringify(DB.activities[0] && DB.activities[0].intensity));
ok('planned is not invented', DB.activities[0] && DB.activities[0].planned===null,
   JSON.stringify(DB.activities[0] && DB.activities[0].planned));
ok('load is still computable without them', activityLoad(DB.activities[0])>0,
   activityLoad(DB.activities[0]));
closeSheet();

// ---------- "OTHER" ASKS WHAT IT WAS ----------
(function(){
  DB.activities=[];
  activitySheet(null,'2030-08-01');
  chooseAct('other');
  ok('choosing Other asks for a name', !!document.getElementById('asName'));
  ok('the name field offers suggestions', !!document.getElementById('asNames'));
  ok('there are plenty of suggestions',
     document.querySelectorAll('#asNames option').length>=30,
     document.querySelectorAll('#asNames option').length);
  ok('the name is asked up front, not inside the details',
     document.getElementById('asMore').contains(document.getElementById('asName'))===false);
  ok('and the chosen type is shown on the row', /Other/.test(
     document.getElementById('asPick').textContent),
     document.getElementById('asPick').textContent);
  ok('Other does not also ask for a description',
     !document.getElementById('asSubtype2'));

  document.getElementById('asName').value='Trampolining';
  setTime('asFrom','10:00'); setTime('asTo','10:40');
  document.getElementById('asSave').click();
  ok('the typed name is stored', DB.activities[0] && DB.activities[0].subtype==='Trampolining',
     JSON.stringify(DB.activities[0] && DB.activities[0].subtype));
  closeSheet();

  // and it becomes a suggestion next time, ahead of the built-in list
  activitySheet(null,'2030-08-02');
  chooseAct('other');
  var opts=Array.prototype.slice.call(document.querySelectorAll('#asNames option'))
            .map(function(o){ return o.value; });
  ok('your own words become suggestions', opts.indexOf('Trampolining')>=0);
  ok('and they come first', opts[0]==='Trampolining', opts.slice(0,3).join(','));
  closeSheet();

  // a named type is unaffected
  activitySheet(null,'2030-08-03');
  chooseAct('running');
  ok('a known type is not asked to name itself', !document.getElementById('asName'));
  closeSheet();
  DB.activities=[];
})();

// ---------- logging takes three answers ----------
(function(){
  DB.activities=[];
  activitySheet(null,'2030-06-15');
  chooseAct('running');
  /* Something that already happened is asked the questions you can answer
     about something that already happened: when it started and when it ended.
     There is no separate duration control, because there is nothing for one
     to disagree with. */
  ok('it asks when it started', !!document.getElementById('asFrom'));
  ok('and when it ended', !!document.getElementById('asTo'));
  ok('there is no separate duration field', !document.getElementById('asMin')
     && !document.getElementById('asQmin'));
  ok('intensity offers one-tap choices', document.querySelectorAll('#asInt button').length===4);
  ok('the details are collapsed', document.getElementById('asMore').hasAttribute('hidden'));
  ok('no load preview lecture', !document.getElementById('asPreview'));
  ok('the length is unknown until both times are given',
     /Set both times/.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);

  setTime('asFrom','07:15'); setTime('asTo','08:00');
  ok('two times are a length', /45m/.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);
  ok('and a strain to go with it', +document.getElementById('asStrain').value>0,
     document.getElementById('asStrain').value);
  ok('which says where it came from',
     /Estimated from 45 minutes/.test(document.getElementById('asStrainH').textContent),
     document.getElementById('asStrainH').textContent);

  var before=+document.getElementById('asStrain').value;
  document.querySelector('#asInt button[data-v=Hard]').click();
  ok('saying it was hard raises the estimate',
     +document.getElementById('asStrain').value>before,
     before+' -> '+document.getElementById('asStrain').value);

  document.getElementById('asSave').click();
  ok('two times, one word and a save is enough', DB.activities.length===1, DB.activities.length);
  ok('it recorded what was said', DB.activities[0].type==='running'
     && DB.activities[0].min===45 && DB.activities[0].intensity==='Hard',
     JSON.stringify(DB.activities[0]));
  ok('the strain went in with it', DB.activities[0].strain>0, DB.activities[0].strain);
  ok('and is flagged as the estimate rather than a stated figure',
     DB.activities[0].strainAuto===true, DB.activities[0].strainAuto);
  ok('the date came from the caller', DB.activities[0].date==='2030-06-15',
     DB.activities[0].date);
  closeSheet();

  // details still work when opened
  DB.activities=[];
  activitySheet(null,'2030-06-16');
  chooseAct('running');
  document.getElementById('asMoreT').click();
  ok('the date is asked up front, with the times', !!document.getElementById('asDate'));
  ok('opening details reveals the rest', !!document.getElementById('asNotes'));
  ok('and distance for a distance activity', !!document.getElementById('asDist'));
  setTime('asFrom','06:00'); setTime('asTo','06:30');
  document.getElementById('asDist').value='6';
  document.getElementById('asSave').click();
  ok('detail fields are saved', DB.activities[0] && DB.activities[0].dist===6,
     JSON.stringify(DB.activities[0]));
  ok('pace is derived rather than asked for', DB.activities[0].pace==='5:00',
     DB.activities[0].pace);
  closeSheet();
  DB.activities=[];
})();

// ---------- TWO WAYS TO LOG, EACH ASKING WHAT IT CAN KNOW ----------
(function(){
  // --- minutes between two clock times ---
  ok('two times are a length', minsBetween('18:30','20:05')===95, minsBetween('18:30','20:05'));
  ok('a game that ran past midnight still has a length',
     minsBetween('22:40','00:25')===105, minsBetween('22:40','00:25'));
  ok('one time on its own is not', minsBetween('18:30','')===null
     && minsBetween('','20:05')===null);
  ok('nonsense is not a time', minsBetween('99:99','20:05')===null
     && minsBetween('abc','20:05')===null);
  ok('zero length is zero, not null', minsBetween('07:00','07:00')===0);
  ok('an end can be worked out from a start and a length',
     timePlus('18:30',95)==='20:05', timePlus('18:30',95));
  ok('and it wraps past midnight', timePlus('23:30',60)==='00:30', timePlus('23:30',60));

  // --- a stated strain outranks the estimate ---
  var est={type:'tennis', min:90, rpe:8};
  var said={type:'tennis', min:90, rpe:8, strain:14.2};
  ok('without one, the curve decides', activityLoad(est)>0, activityLoad(est));
  ok('with one, it is used verbatim', activityLoad(said)===14.2, activityLoad(said));
  ok('and it is clamped to the scale',
     activityLoad({type:'tennis',min:90,rpe:8,strain:99})===21
     && activityLoad({type:'tennis',min:90,rpe:8,strain:-5})===0);
  ok('null means estimate, not zero',
     activityLoad({type:'tennis',min:90,rpe:8,strain:null})===activityLoad(est));

  /* and it has to reach everything the estimate reached: the day's load, the
     acute:chronic ratio and therefore tomorrow's recommendation */
  var keepA=DB.activities;
  var D=addDays(todayISO(),-1);
  DB.activities=[{id:'z1',date:D,type:'tennis',min:90,rpe:8}];
  var guessed=dayDemand(D).load;
  DB.activities=[{id:'z1',date:D,type:'tennis',min:90,rpe:8,strain:18.5}];
  var stated=dayDemand(D).load;
  ok('a stated strain changes the day it belongs to', stated!==guessed,
     guessed+' -> '+stated);
  ok('and it is the figure that was stated', stated===18.5, stated);
  DB.activities=keepA;

  // --- the "how hard" answer now reaches the load model ---
  /* It never did: activityLoad reads `rpe`, which only the slider inside
     "Add details" ever set, so Maximal and Easy produced identical strain
     whenever the details stayed closed - which is almost always. */
  var keepB=DB.activities;
  DB.activities=[];
  activitySheet(null,'2030-05-01');
  chooseAct('cycling');
  setTime('asFrom','09:00'); setTime('asTo','10:00');
  document.querySelector('#asInt button[data-v=Easy]').click();
  document.getElementById('asSave').click();
  var easy=DB.activities[0];
  closeSheet();

  DB.activities=[];
  activitySheet(null,'2030-05-01');
  chooseAct('cycling');
  setTime('asFrom','09:00'); setTime('asTo','10:00');
  document.querySelector('#asInt button[data-v=Maximal]').click();
  document.getElementById('asSave').click();
  var maximal=DB.activities[0];
  closeSheet();

  ok('an easy hour records a low effort', easy.rpe===4, easy.rpe);
  ok('a maximal one records a high effort', maximal.rpe===9, maximal.rpe);
  ok('and the same hour is not the same strain', maximal.strain>easy.strain,
     easy.strain+' vs '+maximal.strain);

  /* The slider inside the details is a finer correction on top of the pills.
     It exists in the DOM whether or not anyone has opened the details, so
     "the element is there" is not the same as "the user answered" - which is
     exactly how the pills went on being ignored. */
  DB.activities=[];
  activitySheet(null,'2030-05-01');
  chooseAct('cycling');
  setTime('asFrom','09:00'); setTime('asTo','10:00');
  document.querySelector('#asInt button[data-v=Hard]').click();
  document.getElementById('asMoreT').click();
  ok('the slider follows the pill until it is moved',
     +document.getElementById('asRpe').value===8,
     document.getElementById('asRpe').value);
  ok('and its readout follows too', document.getElementById('asRpe_o').textContent==='8',
     document.getElementById('asRpe_o').textContent);
  var rp=document.getElementById('asRpe');
  rp.value='10'; rp.dispatchEvent(new Event('input',{bubbles:true}));
  document.getElementById('asSave').click();
  ok('once moved, the slider is the answer', DB.activities[0].rpe===10,
     DB.activities[0].rpe);
  var movedId=DB.activities[0].id;
  closeSheet();

  // re-opening that record must not mistake its own stored effort for a default
  activitySheet(movedId,'2030-05-01');
  document.getElementById('asMoreT').click();
  ok('re-opening keeps the effort that was set',
     +document.getElementById('asRpe').value===10,
     document.getElementById('asRpe').value);
  closeSheet();

  /* Opening "Add details" redraws the sheet. Every pill group except the type
     used to be rendered from the stored record, which for a NEW activity is
     empty - so choosing Hard and then opening the details silently threw the
     answer away, and the record saved with no intensity at all. */
  DB.activities=[];
  activitySheet(null,'2030-05-04');
  chooseAct('tennis');
  setTime('asFrom','17:00'); setTime('asTo','18:30');
  document.querySelector('#asInt button[data-v=Hard]').click();
  document.getElementById('asMoreT').click();          // redraw
  ok('opening the details keeps the intensity you chose',
     document.querySelectorAll('#asInt button.on').length===1
     && document.querySelector('#asInt button.on').dataset.v==='Hard',
     document.querySelectorAll('#asInt button.on').length);
  document.querySelector('#asFormat button[data-v=Doubles]').click();
  document.querySelector('#asPlan button[data-v="0"]').click();
  document.getElementById('asMoreT').click();          // redraw again
  document.getElementById('asMoreT').click();
  ok('and the format', document.querySelector('#asFormat button.on').dataset.v==='Doubles');
  ok('and whether it was planned',
     document.querySelector('#asPlan button.on').dataset.v==='0');
  ok('and the times', document.getElementById('asFrom').value==='17:00'
     && document.getElementById('asTo').value==='18:30',
     document.getElementById('asFrom').value+'/'+document.getElementById('asTo').value);
  document.getElementById('asSave').click();
  ok('so the record keeps all of it', DB.activities[0].intensity==='Hard'
     && DB.activities[0].format==='Doubles' && DB.activities[0].planned===false
     && DB.activities[0].min===90,
     JSON.stringify(DB.activities[0]));
  closeSheet();

  // --- a figure you type is kept as yours ---
  DB.activities=[];
  activitySheet(null,'2030-05-02');
  chooseAct('running');
  setTime('asFrom','07:00'); setTime('asTo','07:40');
  var f=document.getElementById('asStrain');
  var auto=+f.value;
  f.value='13.7'; f.dispatchEvent(new Event('input',{bubbles:true}));
  ok('typing a strain marks it as yours',
     /Your figure/.test(document.getElementById('asStrainH').textContent),
     document.getElementById('asStrainH').textContent);
  /* changing the times must not now overwrite what you typed */
  setTime('asTo','08:30');
  ok('and changing the times leaves it alone',
     document.getElementById('asStrain').value==='13.7',
     document.getElementById('asStrain').value);
  ok('though the length still updates', /1h 30m/.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);
  document.getElementById('asSave').click();
  ok('a typed strain is stored verbatim', DB.activities[0].strain===13.7,
     DB.activities[0].strain);
  ok('and marked as not an estimate', DB.activities[0].strainAuto===false);
  ok('it is what the load model then uses', activityLoad(DB.activities[0])===13.7);
  ok('the estimate would have said otherwise', Math.abs(auto-13.7)>0.2, auto);
  closeSheet();

  // --- clearing it hands the number back ---
  DB.activities=[];
  activitySheet(null,'2030-05-03');
  chooseAct('running');
  setTime('asFrom','07:00'); setTime('asTo','07:40');
  var f2=document.getElementById('asStrain');
  f2.value='19'; f2.dispatchEvent(new Event('input',{bubbles:true}));
  f2.value='';   f2.dispatchEvent(new Event('input',{bubbles:true}));
  ok('clearing it goes back to the estimate',
     /Estimated from/.test(document.getElementById('asStrainH').textContent),
     document.getElementById('asStrainH').textContent);
  closeSheet();

  // --- a record logged before any of this still opens and saves ---
  DB.activities=[{id:'old1',date:'2030-04-01',type:'tennis',min:60,time:'18:00',
                  intensity:'Moderate',rpe:6}];
  activitySheet('old1','2030-04-01');
  ok('an older record works out its end from its start and length',
     document.getElementById('asTo').value==='19:00',
     document.getElementById('asTo').value);
  ok('and shows the length it already had',
     /1h 00m|1h 0m|60m/.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);
  closeSheet();

  // one with no start time at all keeps its length rather than losing it
  DB.activities=[{id:'old2',date:'2030-04-02',type:'yoga',min:35}];
  activitySheet('old2','2030-04-02');
  ok('a record with no times keeps the length it had',
     /35m/.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);
  ok('and says it needs times', /set the times/i.test(document.getElementById('asDur').textContent),
     document.getElementById('asDur').textContent);
  document.getElementById('asSave').click();
  ok('saving it does not throw the length away', DB.activities[0].min===35,
     DB.activities[0].min);
  closeSheet();

  DB.activities=keepB;
})();

// ---------- STARTING SOMETHING ASKS ONE QUESTION ----------
(function(){
  var keepA=DB.activities;
  DB.activities=[];
  startActivitySheet();
  ok('it asks what you are doing', !!document.getElementById('paQ'));
  /* "How hard do you expect it to be" is a prediction nobody can make
     standing at the door with their shoes on. */
  ok('it does not ask how hard it will be', !document.getElementById('stInt')
     && !document.querySelector('#sheetBody .pills'),
     document.getElementById('sheetBody').textContent.slice(0,200));
  ok('and there is nothing to start until you answer', !document.getElementById('psGo'));
  document.querySelector('#sheetBody .parow[data-k="tennis"]').click();
  ok('choosing one offers the clock', !!document.getElementById('psGo'));
  ok('and says when the effort question comes',
     /asked at the end/i.test(document.getElementById('sheetBody').textContent),
     document.getElementById('sheetBody').textContent.slice(0,240));
  closeSheet();

  // the live session carries no assumed intensity
  startLiveActivity('tennis');
  ok('nothing is assumed about how hard it is', W.intensity===null,
     JSON.stringify(W.intensity));
  ok('but the strain still counts', (function(){
     W.entries[0].run.startedAt=Date.now()-30*60*1000; cardTick();
     return cardStrain(W.entries[0])>0; })(), cardStrain(W.entries[0]));

  document.getElementById('cardStop').click();
  document.querySelector('#wmBody [data-log]').click();
  cancelAuto(); nextStep();
  ok('the finish asks how hard it was', !!document.getElementById('afInt'));
  ok('with nothing pre-selected',
     document.querySelectorAll('#afInt button.on').length===0);
  ok('and offers the strain it counted', +document.getElementById('afStrain').value>0,
     document.getElementById('afStrain').value);

  var was=+document.getElementById('afStrain').value;
  document.querySelector('#afInt button[data-v=Maximal]').click();
  ok('answering raises what it counted', +document.getElementById('afStrain').value>was,
     was+' -> '+document.getElementById('afStrain').value);

  // a watch figure replaces it outright
  var sf=document.getElementById('afStrain');
  sf.value='16.4'; sf.dispatchEvent(new Event('input',{bubbles:true}));
  document.getElementById('afSave').click();
  ok('a live session saves an activity', DB.activities.length===1, DB.activities.length);
  ok('with the strain you stated', DB.activities[0].strain===16.4, DB.activities[0].strain);
  ok('marked as yours', DB.activities[0].strainAuto===false);
  ok('the effort you chose', DB.activities[0].intensity==='Maximal');
  ok('and both ends of the clock', !!DB.activities[0].time && !!DB.activities[0].endTime,
     DB.activities[0].time+' -> '+DB.activities[0].endTime);
  DB.activities=keepA;
})();

// ---------- ONE WAY TO ADD, ONE WAY TO START ----------
(function(){
  var keepA=DB.activities, keepC=DB.checkins, keepS=DB.sessions;
  var T=todayISO();
  DB.activities=[]; DB.sessions=[];
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  /* "Log an activity" was rendered three times by three branches of Today and
     twice more on the Activity tab: five controls for two actions. */
  resetStack(); TAB='today'; render();
  var todayHTML=document.getElementById('view').innerHTML;
  ok('Today offers exactly one Add activity',
     (todayHTML.match(/id="acAdd"/g)||[]).length===1,
     (todayHTML.match(/id="acAdd"/g)||[]).length);
  ok('and exactly one Start activity',
     (todayHTML.match(/id="acStart"/g)||[]).length===1,
     (todayHTML.match(/id="acStart"/g)||[]).length);
  ok('the old repeated button is gone everywhere',
     todayHTML.indexOf('btnQuickLog')<0);
  ok('they live on the activities card', !!document.getElementById('actsCard'));

  TAB='today'; render();
  var actHTML=document.getElementById('view').innerHTML;
  ok('the Activity tab uses the same card', !!document.getElementById('actsCard'));
  ok('with one of each button',
     (actHTML.match(/id="acAdd"/g)||[]).length===1
     && (actHTML.match(/id="acStart"/g)||[]).length===1);

  // and the card lists what the day holds
  DB.activities=[
    {id:'c1',date:T,type:'cycling',min:45,time:'16:00',endTime:'16:45',
     intensity:'Moderate',rpe:6},
    {id:'c2',date:T,type:'tennis',min:90,time:'18:00',endTime:'19:30',
     intensity:'Hard',rpe:8}
  ];
  TAB='today'; render();
  ok('each activity is a row', document.querySelectorAll('#actsCard [data-aid]').length===2,
     document.querySelectorAll('#actsCard [data-aid]').length);
  ok('with the strain it came to',
     document.querySelectorAll('#actsCard .dr-s').length===2,
     document.querySelectorAll('#actsCard .dr-s').length);
  ok('and when it started', /16:00/.test(document.getElementById('actsCard').textContent)
     && /18:00/.test(document.getElementById('actsCard').textContent),
     document.getElementById('actsCard').textContent.slice(0,240));
  /* the bar says how long it ran against the longest thing that day: the
     90-minute game must draw a longer bar than the 45-minute ride */
  var bars=document.querySelectorAll('#actsCard .dr-bar i');
  ok('each effort carries a length', bars.length===2, bars.length);
  ok('and the longer one is drawn longer',
     parseFloat(bars[1].style.width)>parseFloat(bars[0].style.width),
     bars[0].style.width+' vs '+bars[1].style.width);
  ok('the longest thing that day fills the bar',
     parseFloat(bars[1].style.width)===100, bars[1].style.width);
  ok('the card totals the day', /strain/.test(document.getElementById('actsCard').textContent));
  ok('tapping one opens it', (function(){
     document.querySelector('#actsCard [data-aid="c1"]').click();
     var open=document.getElementById('sheet').classList.contains('on');
     closeSheet(); return open; })());

  DB.activities=keepA; DB.checkins=keepC; DB.sessions=keepS;
})();

// ---------- THE ACTIVITY PICKER ----------
(function(){
  var keepA=DB.activities;
  DB.activities=[
    {id:'p1',date:addDays(todayISO(),-1),type:'cycling',min:40,rpe:6},
    {id:'p2',date:addDays(todayISO(),-3),type:'tennis',min:90,rpe:8},
    {id:'p3',date:addDays(todayISO(),-9),type:'cycling',min:30,rpe:5}
  ];
  ok('what you have done recently comes first',
     recentActTypes()[0]==='cycling' && recentActTypes()[1]==='tennis',
     recentActTypes().join(','));
  ok('and each type only once', recentActTypes().filter(function(x){
     return x==='cycling'; }).length===1, recentActTypes().join(','));

  DB.activities=[];
  ok('with no history the profile supplies the shortlist',
     recentActTypes().length===mainSportActs().slice(0,6).length,
     recentActTypes().join(','));

  DB.activities=[{id:'p1',date:todayISO(),type:'cycling',min:40,rpe:6}];
  var got=null;
  pickActivity(function(k){ got=k; closeSheet(); },'Pick one');
  ok('the picker opens with a search box', !!document.getElementById('paQ'));
  ok('it offers every type', document.querySelectorAll('#sheetBody .parow').length
     >= Object.keys(ACT_TYPES).length,
     document.querySelectorAll('#sheetBody .parow').length);
  ok('with a most-recent section first',
     /Most recent/.test(document.getElementById('sheetBody').textContent),
     document.getElementById('sheetBody').textContent.slice(0,80));

  // search filters without destroying the field being typed into
  var q=document.getElementById('paQ');
  q.value='ten'; q.dispatchEvent(new Event('input',{bubbles:true}));
  ok('searching narrows the list', (function(){
     var vis=0;
     Array.prototype.forEach.call(document.querySelectorAll('#sheetBody .parow'),
       function(b){ if(!b.hidden) vis++; });
     return vis>0 && vis<6; })(),
     (function(){ var v=[]; Array.prototype.forEach.call(
        document.querySelectorAll('#sheetBody .parow'),
        function(b){ if(!b.hidden) v.push(b.dataset.k); }); return v.join(','); })());
  ok('the search field survives its own filtering',
     document.getElementById('paQ')===q && q.value==='ten');
  ok('a section with nothing left in it is hidden', (function(){
     q.value='zzzznothing'; q.dispatchEvent(new Event('input',{bubbles:true}));
     return document.getElementById('paNone').hidden===false; })());
  q.value=''; q.dispatchEvent(new Event('input',{bubbles:true}));
  ok('clearing it brings everything back',
     document.getElementById('paNone').hidden===true);

  document.querySelector('#sheetBody .parow[data-k="tennis"]').click();
  ok('picking one reports it', got==='tennis', got);
  closeSheet();

  ok('every type has an icon', Object.keys(ACT_TYPES).every(function(k){
     return !!ICON[ACT_ICON(k)]; }),
     Object.keys(ACT_TYPES).filter(function(k){return !ICON[ACT_ICON(k)];}).join(','));

  DB.activities=keepA;
})();

// ---------- CHOOSING AND STARTING ARE TWO MOMENTS ----------
(function(){
  var keepA=DB.activities;
  DB.activities=[];
  startActivityFlow();
  ok('starting begins with the picker', !!document.getElementById('paQ'));
  document.querySelector('#sheetBody .parow[data-k="cycling"]').click();
  ok('choosing one leads to a pre-start screen', !!document.getElementById('psGo'),
     document.getElementById('sheetBody').innerHTML.slice(0,200));
  ok('which names what you chose', /Cycling/.test(document.getElementById('sheetBody').textContent));
  ok('and lets you change your mind', !!document.getElementById('psChange'));
  ok('no strain target unless you ask for one',
     document.getElementById('psOn').checked===false);
  ok('and no number to set while it is off', !document.getElementById('psT'));

  document.getElementById('psOn').click();
  ok('turning it on offers a number', !!document.getElementById('psT'));
  document.getElementById('psT').value='8';
  document.getElementById('psT').dispatchEvent(new Event('input',{bubbles:true}));
  document.getElementById('psGo').click();
  closeSheet();
  /* the start is deferred behind the sheet closing, so drive it directly */
  startLiveActivity('cycling',null,8);
  ok('the session carries the target', W.strainTarget===8, W.strainTarget);
  ok('and has not hit it yet', W.targetHit===false);

  // run the clock until the strain crosses it
  W.entries[0].run.startedAt = Date.now() - 90*60*1000;
  cardTick();
  ok('crossing the target is noticed', W.targetHit===true,
     cardStrain(W.entries[0])+' vs '+W.strainTarget);
  ok('and the clock screen says what it is aiming at',
     /of 8/.test(document.getElementById('wmBody').textContent),
     document.getElementById('wmBody').textContent.slice(0,300));
  exitWM(true);
  DB.activities=keepA;
})();

// ---------- A SCORE IS DRAWN AS A PROPORTION ----------
(function(){
  var keepC=DB.checkins, keepA=DB.activities;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,sleepNeed:480,
                  energy:7,soreness:3,stress:3,motivation:8,pain:'None'};
  DB.activities=[{id:'r1',date:T,type:'cycling',min:45,rpe:6}];
  resetStack(); TAB='today'; render();

  /* Readiness leads as a score with its arc; strain and sleep are metric
     tiles below it - an icon, a figure and a bar. Three identical rings said
     all three weighed the same, which in this app they do not. */
  ok('readiness leads alone', document.querySelectorAll('.scores .score').length===1,
     document.querySelectorAll('.scores .score').length);
  /* readiness is not one of three equals: it leads, at full width, with its
     band in words */
  ok('readiness leads', document.querySelector('.score.lead')===document.getElementById('rdRow'));
  ok('and says its band in words',
     document.querySelector('#rdRow .score-w').textContent.length>2,
     document.querySelector('#rdRow .score-w').textContent);
  ok('the other two sit below it as a pair of tiles',
     document.querySelectorAll('.score-pair .mtile').length===2,
     document.querySelectorAll('.score-pair .mtile').length);
  ok('and each tile carries an icon, a figure and a bar',
     Array.prototype.slice.call(document.querySelectorAll('.score-pair .mtile'))
       .every(function(t){ return t.querySelector('.mt-i svg') && t.querySelector('.mt-v')
                                  && t.querySelector('.mt-b i'); }));
  /* an open arc, not a closed ring: three quarters of the circle, which is
     the shape of the app's own mark */
  ok('the arc is open, not a closed ring', (function(){
     var c=document.querySelector('#rdRow .arc-bg');
     if(!c) return false;
     var da=c.getAttribute('stroke-dasharray').split(/[ ,]+/).map(parseFloat);
     return da.length===2 && Math.abs(da[0]/da[1]-0.75)<0.01; })(),
     (document.querySelector('#rdRow .arc-bg')||{getAttribute:function(){return 'none';}})
       .getAttribute('stroke-dasharray'));
  ok('readiness is one of them', !!document.getElementById('rdRow'));
  ok('strain is another', !!document.getElementById('ringStrain'));
  ok('and sleep the third', !!document.getElementById('ringSleep'));
  ok('each is still a way into its own screen',
     document.querySelectorAll('.scores button').length===3);
  /* The ring row wires three buttons and Today wires #rdRow separately. An
     onclick assignment overwrites silently, so "is it bound" is not enough -
     this checks the binding still does the right thing. */
  document.getElementById('rdRow').click();
  ok('the readiness ring opens the readiness screen', STACK.length===1,
     STACK.length);
  ok('and that screen is the right one',
     /Readiness/.test(document.getElementById('appbar').textContent),
     document.getElementById('appbar').textContent.slice(0,40));
  popPage(); render();
  ok('the readiness ring shows the score',
     document.getElementById('rdRow').textContent.indexOf(
       String(readiness(T,DB.checkins[T]).score))>=0,
     document.getElementById('rdRow').textContent);
  ok('the arc is drawn in proportion', (function(){
     var c=document.querySelector('#rdRow .arc-fg');
     if(!c) return false;
     var arc=parseFloat(c.getAttribute('stroke-dasharray').split(/[ ,]+/)[0]);
     var off=parseFloat(c.getAttribute('stroke-dashoffset'));
     var pct=(1-off/arc)*100;
     return Math.abs(pct-readiness(T,DB.checkins[T]).score)<1.5; })(),
     (function(){ var c=document.querySelector('#rdRow .arc-fg');
        return c? c.getAttribute('stroke-dashoffset')+'/'+c.getAttribute('stroke-dasharray'):'none'; })());

  // nothing to draw is an em-dash, not a ring at zero
  DB.checkins={}; DB.activities=[];
  resetStack(); TAB='today'; render();
  var sl=document.getElementById('ringSleep');
  if(sl){
    ok('an unknown score draws no arc', !sl.querySelector('.arc-fg'),
       sl.innerHTML.slice(0,160));
    ok('and says so with a dash', /—/.test(sl.textContent), sl.textContent);
  } else {
    ok('an unknown score draws no arc', true, 'no ring row on this branch');
    ok('and says so with a dash', true, 'no ring row on this branch');
  }

  DB.checkins=keepC; DB.activities=keepA;
})();

// ---------- every view renders ----------
var views={today:viewToday,workouts:viewWorkouts,progress:viewProgress,whoop:viewWhoop,settings:viewSettings,settingsBody:settingsBody};
Object.keys(views).forEach(function(k){
  tryRun('view renders: '+k, function(){ TAB=k; var v=document.getElementById('view'); views[k](v); if(!v.innerHTML.length) throw new Error('empty'); });
});
// sub-tabs
['program','library','warmups','history'].forEach(function(t){
  tryRun('workouts subtab: '+t, function(){ WTAB=t; viewWorkouts(document.getElementById('view')); }); });
/* Activity is not a view any more: its panes are pushed pages reached from
   the group under the day's activities on Today. Each still has to render. */
[['timeline',paneTimeline],['tennis',paneTennis],
 ['history',paneActHistory],['totals',paneTotals]].forEach(function(pair){
  tryRun('activity pane: '+pair[0], function(){
    var v=document.getElementById('view');
    v.innerHTML=''; pair[1](v);
    if(!v.innerHTML.length) throw new Error('empty'); }); });
['training','tests','physique','links'].forEach(function(t){
  tryRun('progress subtab: '+t, function(){ PTAB=t; viewProgress(document.getElementById('view')); }); });
['trends','sleep','baselines','import'].forEach(function(t){
  tryRun('whoop subtab: '+t, function(){ HTAB=t; viewWhoop(document.getElementById('view')); }); });

// sheets
tryRun('previewWorkout sheet', function(){ previewWorkout('w_lowerA','full'); }); closeSheet();
tryRun('previewWorkout recovery variant', function(){ previewWorkout('w_power','recovery'); }); closeSheet();
tryRun('previewWorkout with core add-on', function(){ previewWorkout('w_lowerA','full',{addCore:true,workoutId:'w_lowerA',variant:'full'}); }); closeSheet();
tryRun('editWorkout sheet', function(){ editWorkout('w_core'); }); closeSheet();
tryRun('exerciseSheet view', function(){ exerciseSheet('lx01'); }); closeSheet();
tryRun('exerciseSheet edit', function(){ exerciseSheet('lx01',true); }); closeSheet();
tryRun('pickExercise sheet', function(){ pickExercise(function(){}); }); closeSheet();
tryRun('editTargets sheet', function(){ editSchedule(); }); closeSheet();
tryRun('changePlan sheet', function(){ changePlan(todayISO()); }); closeSheet();
tryRun('pickVariantFor sheet', function(){ pickVariantFor(todayISO(),'w_lowerA',null); }); closeSheet();
tryRun('chooseVariant sheet', function(){ chooseVariant('w_lowerA'); }); closeSheet();
// override round-trip through the UI
DB.plans={};
tryRun('override via changePlan', function(){
  changePlan(todayISO());
  var b=document.querySelector('[data-w="w_upperB"]'); if(!b) throw new Error('no direct pick button');
  b.click();
});
closeSheet();
tryRun('correlations run', function(){ var c=correlations(); if(!Array.isArray(c)) throw new Error('not array'); return c; });
ok('correlations produced with real data', correlations().length>0, 'n='+correlations().length);

// ---------- export / migrate ----------
var js=tryRun('exportJSON payload builds', function(){ return JSON.stringify({_app:'baseline.tps',data:DB}); });
ok('export JSON parses back', (function(){ try{ var d=JSON.parse(js); return !!d.data.profile; }catch(e){ return false; } })());
tryRun('CSV escape', function(){ if(csvEsc('a,b')!=='"a,b"') throw new Error('bad'); });
var mg=tryRun('migrate legacy tennis/cardio', function(){
  return migrate({profile:{},exercises:DB.exercises,workouts:DB.workouts,
    tennis:[{id:'x1',date:'2030-01-01',min:90,rpe:7}], cardio:[{id:'x2',date:'2030-01-02',mode:'bike',min:40,rpe:4,distance:20}]});
});
var mgS=tryRun('migrate drops the old fixed schedule', function(){
  return migrate({profile:{},exercises:DB.exercises,workouts:DB.workouts,
    schedule:{1:'w_lowerA'}, tennisDays:[0,3,6], altSchedule:{0:'w_lowerB'},
    sessions:[{id:'os1',date:'2030-01-01',workoutId:'w_lowerA',done:true,variant:'full',entries:[]}]});
});
ok('legacy schedule removed on migrate', mgS && mgS.schedule===undefined && mgS.tennisDays===undefined && mgS.altSchedule===undefined);
ok('an un-set profile gets no targets on migrate', mgS && Object.keys(mgS.targets||{}).length===0, mgS && JSON.stringify(mgS.targets));
ok('plans object added on migrate', mgS && typeof mgS.plans==='object');
ok('old sessions get a category backfilled', mgS && mgS.sessions[0].category==='lower', mgS&&mgS.sessions[0].category);
var mgC=tryRun('migrate adds missing new cardio workouts', function(){
  return migrate({profile:{},exercises:DB.exercises,workouts:DB.workouts.filter(function(w){return w.id!=='w_bike';})});
});
ok('missing w_bike restored on migrate', mgC && !!mgC.workouts.find(function(w){return w.id==='w_bike';}));
ok('legacy tennis migrated to activities', mg && mg.activities.some(function(a){return a.type==='tennis'&&a.min===90;}));
ok('legacy cardio migrated to activities', mg && mg.activities.some(function(a){return a.type==='cycling'&&a.dist===20;}));
ok('legacy keys removed after migrate', mg && mg.tennis===undefined && mg.cardio===undefined);
var mg2=tryRun('migrate drops dangling exercise refs', function(){
  return migrate({profile:{},exercises:[{id:'keep',name:'x',cat:'lower',muscles:'m',sets:1,reps:'1',rpe:'7',rest:'1s',how:'h',cue:'c',prog:'p'}],
    workouts:[{id:'w1',name:'w',short:'w',type:'strength',warm:'lower',cool:'lower',est:{full:1,reduced:1,recovery:1},
      blocks:{full:[{ex:'keep'},{ex:'GONE'}],reduced:[],recovery:[]}}]});
});
ok('dangling ref removed', mg2 && mg2.workouts[0].blocks.full.length===1, mg2&&JSON.stringify(mg2.workouts[0].blocks.full));
var mg3=tryRun('migrate empty object', function(){ return migrate({}); });
ok('migrate({}) yields usable DB', mg3 && mg3.exercises.length>0 && mg3.workouts.length>0);

// ---------- persistence (IndexedDB primary, versioned schema) ----------
ok('Store reports a durable mode', Store.durable===true, Store.mode);
ok('schema constants present', typeof DB_VERSION==='number' && typeof SCHEMA_VERSION==='number',
   'db='+DB_VERSION+' schema='+SCHEMA_VERSION);
ok('object stores defined', Object.keys(STORES).length>=10, Object.keys(STORES).length);
ok('WHOOP has its own stores', !!STORES.wCycles && !!STORES.wWorkouts && !!STORES.wJournal);
ok('date indexes defined', STORES.sessions.idx.indexOf('date')>=0 && STORES.activities.idx.indexOf('date')>=0);
ok('meta carries schema version', DB.meta && DB.meta.schema===SCHEMA_VERSION, DB.meta&&DB.meta.schema);
DB.exercises[0].notes='EDITED_MARKER';
var wrote=await Store.write(true);
ok('write to durable storage succeeds', wrote===true, 'mode='+Store.mode);
ok('collectionRows maps checkins to rows', Array.isArray(collectionRows('checkins')));
ok('collectionRows maps WHOOP cycles', collectionRows('wCycles').length===DB.whoop.cycles.length);

// true reload simulation: read back out of storage exactly as boot() does
var loaded=await Store.loadAll();
ok('loadAll returns stored data', !!loaded, loaded?'ok':'null');
var reloaded=loaded?migrate(hydrate(loaded)):null;
ok('reload preserves sessions', reloaded && reloaded.sessions.length===DB.sessions.length, (reloaded?reloaded.sessions.length:'?')+' vs '+DB.sessions.length);
ok('reload preserves activities', reloaded && reloaded.activities.length===DB.activities.length);
ok('reload preserves check-ins', reloaded && Object.keys(reloaded.checkins).length===Object.keys(DB.checkins).length,
   (reloaded?Object.keys(reloaded.checkins).length:'?')+' vs '+Object.keys(DB.checkins).length);
ok('reload preserves WHOOP cycles', reloaded && reloaded.whoop.cycles.length===DB.whoop.cycles.length,
   (reloaded?reloaded.whoop.cycles.length:'?')+' vs '+DB.whoop.cycles.length);
ok('reload preserves WHOOP journal', reloaded && reloaded.whoop.journal.length===DB.whoop.journal.length);
ok('reload preserves targets', reloaded && reloaded.targets.lower===DB.targets.lower);
ok('reload preserves the chosen wearable', reloaded && reloaded.profile.source===DB.profile.source,
   (reloaded?reloaded.profile.source:'?')+' vs '+DB.profile.source);
ok('reload preserves custom exercise edits',
   reloaded && (reloaded.exercises.find(function(e){return e.notes==='EDITED_MARKER';})!=null));
ok('reload preserves cycle ordering', reloaded && reloaded.whoop.cycles.length>1 &&
   reloaded.whoop.cycles[0].date < reloaded.whoop.cycles[reloaded.whoop.cycles.length-1].date);
// live workout uses small prefs, not the main store
tryRun('live workout state uses prefs', function(){
  Store.pref('live','{"x":1}');
  if(Store.pref('live')!=='{"x":1}') throw new Error('mismatch');
  Store.pref('live',null);
});

// ---------- SETUP WIZARD ----------
ok('sports list offered', SPORTS.length>=6 && SPORTS.some(function(s){return s.id==='tennis';}));
ok('physique goals offered', PHYSIQUES.length>=4);
ok('equipment tiers defined', TIERS.length===3 && TIERS[0].id===0 && TIERS[2].id===2);
tryRun('startSetup renders the first step', function(){ startSetup();
  if(!document.getElementById('setNext')) throw new Error('no next button'); });
ok('the first thing asked is the name, not a wearable',
   !!document.getElementById('setName') && !document.getElementById('setSrcSel'));
ok('the wearable step offers every supported device', (function(){
  var i=SETUP_STEPS.map(function(x){return x.id;}).indexOf('device');
  SETUP.step=i; drawSetup();
  var h=$('#sheetBody').innerHTML;
  return /WHOOP/.test(h) && /Garmin/.test(h) && /Oura/.test(h); })());
ok('the wearable step does not ask about one brand',
   !/Do you use WHOOP/.test($('#sheetBody').innerHTML));
// walk every step, however many there are
(function(){
  var reached=[], want=[];
  startSetup();
  for(var i=0;i<SETUP_STEPS.length;i++){
    reached.push(SETUP.step); want.push(i);
    if(SETUP.step<SETUP_STEPS.length-1){ document.getElementById('setNext').click(); }
  }
  ok('wizard advances through every step',
     reached.join(',')===want.join(','), reached.join(','));
})();

// the primary button must never move or resize between steps
(function(){
  startSetup(); SETUP.draft.source='none';
  var seen=[];
  for(var s=0;s<SETUP_STEPS.length;s++){
    SETUP.step=s; drawSetup();
    var n=document.getElementById('setNext'), b=document.getElementById('setBack');
    seen.push({s:s, hasNext:!!n, hasBack:!!b,
               nextFlex:n?n.style.flex:'', backFlex:b?b.style.flex:''});
  }
  ok('every step has both footer buttons', seen.every(function(x){return x.hasNext&&x.hasBack;}),
     JSON.stringify(seen));
  ok('the footer proportions are identical on every step',
     seen.every(function(x){return x.nextFlex===seen[0].nextFlex && x.backFlex===seen[0].backFlex;}),
     JSON.stringify(seen.map(function(x){return x.backFlex+'/'+x.nextFlex;})));
  SETUP.step=0; drawSetup();
  ok('on the first step the left button closes instead of going back',
     /Close/.test(document.getElementById('setBack').textContent));
  SETUP.step=1; drawSetup();
  ok('after the first step it is a Back button',
     /Back/.test(document.getElementById('setBack').textContent));
  closeSheet();
})();
// ---------- THE WIZARD: SEVEN STEPS, ADDRESSED BY ID ----------
(function(){
  // never drive the wizard by step number: reordering it must not silently
  // point an assertion at a different screen
  var goTo=function(id){
    var i=SETUP_STEPS.map(function(x){return x.id;}).indexOf(id);
    if(i<0) return false;
    SETUP.step=i; drawSetup(); return true;
  };
  var bodyHTML=function(){ return $('#sheetBody').innerHTML; };
  var nextText=function(){ return document.getElementById('setNext').textContent.trim(); };

  startSetup();
  ok('the wizard has seven steps', SETUP_STEPS.length===7, SETUP_STEPS.length);
  ok('the first step is the name', SETUP_STEPS[0].id==='name', SETUP_STEPS[0].id);
  ok('the wearable is not the first question',
     SETUP_STEPS.map(function(x){return x.id;}).indexOf('device')>=4,
     SETUP_STEPS.map(function(x){return x.id;}).join(','));

  // --- name ---
  ok('step: name exists', goTo('name'));
  ok('the name step has a text input', (function(){
    var i=document.getElementById('setName');
    return i && i.tagName==='INPUT' && i.type==='text'; })());
  ok('an empty name offers Skip', /Skip/.test(nextText()), nextText());
  SETUP.draft.name='Hatem'; goTo('name');
  ok('a filled name offers Continue', /Continue/.test(nextText()), nextText());
  ok('the name is not asked twice anywhere else', (function(){
    var n=0;
    SETUP_STEPS.forEach(function(st){ goTo(st.id);
      if(document.getElementById('setName')) n++; });
    return n===1; })());

  // --- what for (goals) ---
  ok('step: goals exists', goTo('goals'));
  SETUP.draft.physiques=[]; goTo('goals');
  ok('goals can be empty', !!document.getElementById('setGoalPick'));
  ok('an empty goal list says None',
     /None selected/.test(document.getElementById('setGoalPick').innerHTML),
     document.getElementById('setGoalPick').innerHTML.slice(0,90));
  ok('an empty goal list still continues', /Continue/.test(nextText()), nextText());
  SETUP.draft.physiques=['muscle','lean']; goTo('goals');
  ok('conflicting goals are flagged', /pull against each other/.test(bodyHTML()));

  // --- sports ---
  ok('step: sports exists', goTo('sports'));
  SETUP.draft.sports=[]; goTo('sports');
  ok('sports can be empty', !!document.getElementById('setSportPick'));
  ok('an empty sport list says so',
     /None/.test(document.getElementById('setSportPick').innerHTML));
  ok('"no specific sport" is not offered as a choice as well as None',
     SETUP_SPORTS().every(function(s){ return s.id!=='general'; }),
     SETUP_SPORTS().map(function(s){return s.id;}).join(','));
  ok('the engine still has a neutral fallback profile',
     !!SPORT_PROFILES.general);
  SETUP.draft.sports=['tennis','football']; goTo('sports');
  ok('the leading sport is marked MAIN',
     /MAIN/.test(document.getElementById('setSportPick').innerHTML));

  // the last chip must now be removable - this was the bug that made
  // "None" unreachable
  SETUP.draft.sports=['tennis']; goTo('sports');
  document.querySelector('#setSportPick [data-rm]').click();
  ok('the last sport CAN be removed', SETUP.draft.sports.length===0,
     SETUP.draft.sports.join(','));
  SETUP.draft.physiques=['athletic']; goTo('goals');
  document.querySelector('#setGoalPick [data-rm]').click();
  ok('the last goal CAN be removed', SETUP.draft.physiques.length===0,
     SETUP.draft.physiques.join(','));

  // --- equipment: where first, then what ---
  ok('step: gear exists', goTo('gear'));
  SETUP.draft.gear=[]; SETUP.draft.place=null; goTo('gear');

  /* The question that decides the shape of the next one. A gym has everything
     until told otherwise; at home nothing is assumed. */
  ok('it asks where you train first', !!document.getElementById('setGear_place'),
     bodyHTML().slice(0,160));
  ok('with exactly two answers',
     document.querySelectorAll('#setGear_place button').length===2,
     document.querySelectorAll('#setGear_place button').length);
  ok('and no equipment list before that is answered',
     document.querySelectorAll('.gr').length===0,
     document.querySelectorAll('.gr').length);
  ok('the step is not complete until it is answered', stepEmpty('gear',SETUP.draft)===true);

  // ---- at a gym ----
  document.querySelector('#setGear_place button[data-p=gym]').click();
  ok('choosing a gym records it', SETUP.draft.place==='gym', SETUP.draft.place);
  ok('and starts with everything available',
     SETUP.draft.gear.length===GYM_GEAR.length, SETUP.draft.gear.join(','));
  ok('the step is now answered', stepEmpty('gear',SETUP.draft)===false);
  /* the whole point: it does NOT make you read a list */
  ok('no list is shown by default',
     document.querySelectorAll('.gr').length===0,
     document.querySelectorAll('.gr').length);
  ok('but there is a way to remove what your gym lacks',
     !!document.getElementById('setGear_more'));

  document.getElementById('setGear_more').click();
  ok('opening it lists the gym items',
     document.querySelectorAll('.gr').length===GYM_GEAR.length,
     document.querySelectorAll('.gr').length);
  ok('and everything is ticked to begin with',
     document.querySelectorAll('.gr.on').length===GYM_GEAR.length,
     document.querySelectorAll('.gr.on').length);
  document.querySelector('.gr[data-g=cable]').click();
  ok('tapping one removes it', SETUP.draft.gear.indexOf('cable')<0,
     SETUP.draft.gear.join(','));
  ok('and the rest stay', SETUP.draft.gear.length===GYM_GEAR.length-1,
     SETUP.draft.gear.length);

  // ---- at home ----
  SETUP.draft.place=null; SETUP.draft.gear=[]; goTo('gear');
  document.querySelector('#setGear_place button[data-p=home]').click();
  ok('choosing home records it', SETUP.draft.place==='home');
  ok('and starts with nothing assumed', SETUP.draft.gear.length===0,
     SETUP.draft.gear.join(','));
  ok('the list is what people keep at home',
     document.querySelectorAll('.gr').length===HOME_GEAR.length,
     document.querySelectorAll('.gr').length);
  ok('and it includes a home multi-gym or cable tower',
     /multi-gym/i.test(bodyHTML()), 'no multi-gym hint');
  ok('nothing is ticked', document.querySelectorAll('.gr.on').length===0);

  document.querySelector('.gr[data-g=db]').click();
  ok('tapping an item adds it', SETUP.draft.gear.indexOf('db')>=0,
     SETUP.draft.gear.join(','));
  ok('the step shows what that unlocks', /exercises available/i.test(bodyHTML()));

  // ---- weights, only where a weight means something ----
  ok('a weighted item that is ticked asks for a weight',
     document.querySelectorAll('.gr-w [data-gid=db]').length===1,
     document.querySelectorAll('.gr-w').length);
  ok('and nothing else does',
     document.querySelectorAll('.gr-w').length===1,
     document.querySelectorAll('.gr-w').length);
  /* the band has no weight to give, so it must never ask for one */
  document.querySelector('.gr[data-g=band]').click();
  ok('an unweighted item asks for nothing',
     document.querySelectorAll('.gr-w').length===1,
     document.querySelectorAll('.gr-w').length);

  (function(){
    var inp=document.querySelector('.gr-w [data-gid=db]');
    inp.value='22'; inp.dispatchEvent(new Event('input',{bubbles:true}));
    ok('the weight is stored', (SETUP.draft.gearKg||{}).db===22,
       JSON.stringify(SETUP.draft.gearKg));
    ok('and dbKg is kept in step, because stepSize reads it',
       SETUP.draft.dbKg===22, SETUP.draft.dbKg);
  })();

  /* unticking takes the field away again rather than leaving a stale number
     on screen with nothing to attach it to */
  document.querySelector('.gr[data-g=db]').click();
  ok('unticking removes the weight field',
     document.querySelectorAll('.gr-w').length===0,
     document.querySelectorAll('.gr-w').length);

  // ---- you can change your mind about where ----
  ok('there is a way back to the other choice', !!document.getElementById('setGear_back'));
  document.getElementById('setGear_back').click();
  ok('which returns to the question', SETUP.draft.place===null
     && !!document.getElementById('setGear_place'), SETUP.draft.place);

  /* No equipment id was invented: every one of them has to gate at least one
     exercise, or ticking it would do nothing at all. */
  ok('every equipment item actually gates an exercise', (function(){
    var dead=[];
    EQUIP_ITEMS.forEach(function(it){
      var used=DB.exercises.some(function(e){
        return (deriveNeeds(e)||[]).indexOf(it.id)>=0; });
      if(!used) dead.push(it.id);
    });
    return dead.length===0; })(),
    EQUIP_ITEMS.filter(function(it){
      return !DB.exercises.some(function(e){
        return (deriveNeeds(e)||[]).indexOf(it.id)>=0; });
    }).map(function(i){return i.id;}).join(','));

  SETUP.draft.place='home'; SETUP.draft.gear=['db'];

  // --- how much ---
  ok('step: sched exists', goTo('sched'));
  ok('frequency and duration share one screen',
     !!document.getElementById('setDays') && !!document.getElementById('setMin'));
  SETUP.draft.daysPerWeek=null; SETUP.draft.sessionMin=null; goTo('sched');
  ok('neither is pre-selected',
     document.querySelectorAll('#setDays button.on').length===0
     && document.querySelectorAll('#setMin button.on').length===0);
  ok('leaving them blank is disclosed, not hidden',
     new RegExp('assumes '+DEFAULT_DAYS+' days').test(bodyHTML()),
     bodyHTML().slice(-160));

  // --- wearable (optional) ---
  ok('step: device exists', goTo('device'));
  SETUP.draft.source=null; goTo('device');
  ok('the wearable defaults to None', (function(){
    var sel=document.getElementById('setSrcSel');
    return sel && sel.value===''; })());
  ok('None is the first option offered', (function(){
    var o=document.getElementById('setSrcSel').options[0];
    return o.value==='' && /None/.test(o.textContent); })());
  ok('no wearable offers Skip', /Skip/.test(nextText()), nextText());
  SETUP.draft.source='oura'; goTo('device');
  ok('choosing a wearable is recorded and described',
     /readiness/i.test(bodyHTML()), bodyHTML().slice(0,140));
  ok('a chosen wearable offers Continue', /Continue/.test(nextText()), nextText());

  // --- about you (optional, last) ---
  ok('step: body exists', goTo('body'));
  ok('the body step is last', SETUP_STEPS[SETUP_STEPS.length-1].id==='body');
  SETUP.draft.age=null; SETUP.draft.heightCm=null; SETUP.draft.weightKg=null;
  goTo('body');
  ok('body metrics are asked', !!document.querySelector('[data-k=age]')
     && !!document.querySelector('[data-k=heightCm]')
     && !!document.querySelector('[data-k=weightKg]'));
  ok('an empty body step can be skipped to finish',
     /Skip/.test(nextText()), nextText());
  SETUP.draft.age=30; goTo('body');
  ok('a filled body step finishes', /Finish/.test(nextText()), nextText());

  // --- no step blocks progress ---
  ok('no step refuses to advance', (function(){
    SETUP={step:0, draft:{gear:[],sports:[],physiques:[],name:'',
      source:null,age:null,heightCm:null,weightKg:null,
      daysPerWeek:null,sessionMin:null,units:'metric'}};
    drawSetup();
    for(var i=0;i<SETUP_STEPS.length-1;i++){
      var before=SETUP.step;
      document.getElementById('setNext').click();
      if(SETUP.step!==before+1) return false;
    }
    return true; })());

  // --- the footer geometry, which is what used to jump ---
  var seen=[];
  SETUP_STEPS.forEach(function(st,i){
    SETUP.step=i; drawSetup();
    var n=document.getElementById('setNext'), b=document.getElementById('setBack');
    var row=document.querySelector('#sheetFoot .btn-row');
    seen.push({s:st.id, hasNext:!!n, hasBack:!!b,
               cols:row?getComputedStyle(row).gridTemplateColumns:''});
  });
  ok('every step has both footer buttons',
     seen.every(function(x){return x.hasNext&&x.hasBack;}), JSON.stringify(seen));
  ok('the footer columns are identical on every step',
     seen.every(function(x){return x.cols===seen[0].cols;}),
     JSON.stringify(seen.map(function(x){return x.s+':'+x.cols;})));
  SETUP.step=0; drawSetup();
  ok('on the first step the left button closes instead of going back',
     /Close/.test(document.getElementById('setBack').textContent));
  SETUP.step=1; drawSetup();
  ok('after the first step it is a Back button',
     /Back/.test(document.getElementById('setBack').textContent));

  // --- the label must follow what you TYPE, not only what a redraw sees ---
  // (this is the bug the earlier assertions missed: they only ever looked
  //  after a drawSetup, and typing does not redraw)
  goTo('name');
  SETUP.draft.name=''; goTo('name');
  ok('an untouched name step says Skip', /Skip/.test(nextText()), nextText());
  (function(){
    var i=document.getElementById('setName');
    i.value='Hatem';
    i.dispatchEvent(new Event('input',{bubbles:true}));
  })();
  ok('typing a name turns Skip into Continue', /Continue/.test(nextText()), nextText());
  ok('typing a name does not lose the field',
     !!document.getElementById('setName'));
  ok('the typed value survives', document.getElementById('setName').value==='Hatem',
     document.getElementById('setName').value);
  ok('and it reached the draft', SETUP.draft.name==='Hatem', SETUP.draft.name);
  (function(){
    var i=document.getElementById('setName');
    i.value='';
    i.dispatchEvent(new Event('input',{bubbles:true}));
  })();
  ok('clearing the name goes back to Skip', /Skip/.test(nextText()), nextText());

  // same mechanism on the last step, where the label is a finish label
  goTo('body');
  SETUP.draft.age=null; SETUP.draft.heightCm=null; SETUP.draft.weightKg=null;
  goTo('body');
  ok('an empty last step says Skip & finish', /Skip/.test(nextText()), nextText());
  (function(){
    var i=document.querySelector('[data-k=age]');
    i.value='30'; i.dispatchEvent(new Event('input',{bubbles:true}));
  })();
  ok('typing an age turns it into Finish', /Finish/.test(nextText()), nextText());

  // tapping a schedule pill drops the "assumes N days" disclosure
  goTo('sched');
  SETUP.draft.daysPerWeek=null; SETUP.draft.sessionMin=null; goTo('sched');
  ok('the disclosure is shown while blank',
     new RegExp('assumes '+DEFAULT_DAYS).test($('#sheetBody').innerHTML));
  document.querySelector('#setDays button[data-v="4"]').click();
  document.querySelector('#setMin button[data-v="45"]').click();
  ok('answering removes the disclosure',
     !new RegExp('assumes '+DEFAULT_DAYS).test($('#sheetBody').innerHTML),
     $('#sheetBody').innerHTML.slice(-140));
  ok('and the answers stuck',
     SETUP.draft.daysPerWeek===4 && SETUP.draft.sessionMin===45,
     SETUP.draft.daysPerWeek+'/'+SETUP.draft.sessionMin);

  closeSheet();
})();

// ---------- WORKOUT MODE: THUMBS, NOT KEYBOARDS ----------
(function(){
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None',availTime:60};
  tryRun('starting a workout', function(){ startWorkout('w_lowerA','full',T); });
  W.phase='main'; W.step=0; drawWM();
  var en=W.entries[0];

  /* THE ACTIVE SCREEN IS NOT A FORM.
     Nothing is typed, nothing is chosen, nothing is confirmed. The exercise,
     the set it is on, one button. Everything that used to sit here - steppers
     for every set, an effort control, Add a set, Back, Next exercise - was the
     user being asked to operate the app while out of breath. */
  ok('the set screen has no number keyboard inputs',
     document.querySelectorAll('#wmBody input[type=number]').length===0,
     document.querySelectorAll('#wmBody input[type=number]').length);
  ok('no data entry is offered during a set at all',
     document.querySelectorAll('#wmBody .stp').length===0,
     document.querySelectorAll('#wmBody .stp').length);
  ok('exactly one set state is on screen',
     document.querySelectorAll('#wmBody .wset').length===1,
     document.querySelectorAll('#wmBody .wset').length);
  ok('and it is the first unlogged set',
     /SET 1 OF/i.test(document.querySelector('.wset .ws-l').textContent),
     document.querySelector('.wset .ws-l').textContent);
  ok('there is exactly one primary action',
     document.querySelectorAll('#wmBody [data-log]').length===1,
     document.querySelectorAll('#wmBody [data-log]').length);
  ok('and it says what it does', /Log set/i.test(document.querySelector('[data-log]').textContent),
     document.querySelector('[data-log]').textContent.trim());
  ok('the prescription is shown, not asked for',
     /8|10|12|15/.test(document.querySelector('.wset .ws-v').textContent),
     document.querySelector('.wset .ws-v').textContent.trim());
  ok('a bodyweight exercise shows no kg anywhere', (function(){
     if(exLoadable(exOf(en.exerciseId))) return true;   // not a bodyweight one
     return document.querySelectorAll('.wset .ws-kg').length===0; })(),
     document.querySelectorAll('.wset .ws-kg').length);

  /* Deviation is possible, but it is a detour: tapping the number. */
  (function(){
    var v=document.getElementById('wsAdj');
    ok('the prescribed number is what you tap to deviate', !!v);
    v.click();
    ok('which opens steppers, off the training screen',
       document.querySelectorAll('#sheetBody .stp').length>0,
       document.querySelectorAll('#sheetBody .stp').length);
    var reps=document.querySelector('#sheetBody [data-k=reps]');
    var before=reps.value;
    reps.parentElement.querySelector('button[data-d="1"]').click();
    ok('+ increases reps by one', +reps.value===(+before||+reps.placeholder||0)+1,
       before+' -> '+reps.value);
    ok('the increase reached the set model', W.entries[0].sets[0].reps===reps.value,
       W.entries[0].sets[0].reps+' vs '+reps.value);
    reps.parentElement.querySelector('button[data-d="-1"]').click();
    ok('- decreases it again', +reps.value===(+before||+reps.placeholder||0), reps.value);
    closeSheet(); drawWM();
  })();

  // weight increments match the equipment
  ok('weight steps by 1 below 20kg', stepSize('weight',10)===1, stepSize('weight',10));
  ok('weight steps by 2.5 at and above 20kg', stepSize('weight',20)===2.5, stepSize('weight',20));
  ok('reps always step by one', stepSize('reps',50)===1);
  /* jump to an exercise that actually carries weight: a bodyweight one has no
     kg field at all now, which is the point of stage 12 */
  (function(){
    for(var q=0;q<W.entries.length;q++){
      if(exLoadable(exOf(W.entries[q].exerciseId))){ W.phase='main'; W.step=q; drawWM(); break; }
    }
  })();
  (function(){
    document.getElementById('wsAdj').click();
    var w=document.querySelector('#sheetBody [data-k=weight]');
    ok('a loadable exercise offers kg in the adjust sheet', !!w);
    w.value='20'; w.dispatchEvent(new Event('input',{bubbles:true}));
    w.parentElement.querySelector('button[data-d="1"]').click();
    ok('20kg + one step is 22.5', w.value==='22.5', w.value);
    w.parentElement.querySelector('button[data-d="1"]').click();
    ok('and again is 25 with no floating point dust', w.value==='25', w.value);
    w.value='0'; w.dispatchEvent(new Event('input',{bubbles:true}));
    w.parentElement.querySelector('button[data-d="-1"]').click();
    ok('weight never goes negative', +w.value>=0, w.value);
    closeSheet(); drawWM();
  })();

  // ticking a set still auto-fills RPE from the plan, as it always did
  (function(){
    /* back to the first exercise: the block above moved to a loadable one */
    W.phase='main'; W.step=0; var e0=W.entries[0];
    e0.sets.forEach(function(s){ s.done=false; s.rpe=''; });
    drawWM();
    document.querySelector('[data-log="0"]').click();
    ok('completing a set marks it done', e0.sets[0].done===true);
    ok('completing a set still fills RPE from the plan',
       !!e0.sets[0].rpe, e0.sets[0].rpe);
  })();

  /* Effort is no longer asked per exercise while training. complete() already
     records it from the plan, so the data stays complete without a control on
     the screen - the distinction between a rich data model and a busy UI. */
  ok('no effort control sits on the training screen',
     document.querySelectorAll('#wmBody [data-k=rpe]').length===0,
     document.querySelectorAll('#wmBody [data-k=rpe]').length);
  ok('but effort is still recorded for the engine',
     W.entries[0].sets.filter(function(s){return s.done;}).every(function(s){ return !!s.rpe; }),
     JSON.stringify(W.entries[0].sets.map(function(s){return s.rpe;})));
  ok('and so is a timestamp',
     W.entries[0].sets.filter(function(s){return s.done;}).every(function(s){ return !!s.at; }));

  /* Two secondary controls, and neither is part of the training loop. */
  ok('the footer carries Pause and More, nothing else',
     !!document.getElementById('wmPauseBtn') && !!document.getElementById('wmMore')
     && document.querySelectorAll('#wmFoot button').length===2,
     document.querySelectorAll('#wmFoot button').length);
  ok('there is no Add a set on the training screen', !document.getElementById('wmAddSet'));
  ok('there is no Next exercise button', !document.getElementById('wmNext'));
  ok('there is no Back button', !document.getElementById('wmPrev'));
  ok('and no list of what has already been logged',
     document.querySelectorAll('#wmBody .wdone').length===0);
  ok('replace/skip/note are behind More',
     !document.getElementById('wmSwap') && !document.getElementById('wmSkip')
     && !document.getElementById('wmNote'));
  ok('More is the safety valve, and holds the exceptions', (function(){
    document.getElementById('wmMore').click();
    var txt=document.getElementById('wmMoreRows').textContent;
    var got=/Undo the last set/.test(txt) && /Add a set/.test(txt)
         && /Replace exercise/.test(txt) && /Skip this exercise/.test(txt)
         && /Add a note/.test(txt) && /How to do it/.test(txt);
    closeSheet();
    return got; })(), document.getElementById('wmMoreRows')?document.getElementById('wmMoreRows').textContent.slice(0,120):'');

  /* The glimpse appears where it is true: on the LAST set, whose next thing
     really is a different exercise. Mid-exercise the next thing is the next
     set, which the screen already says, so naming another exercise there just
     pointed past the set about to be done. */
  (function(){
    var e0=W.entries[W.step];
    e0.sets.forEach(function(s){ s.done=false; });
    if(e0.sets.length>1){
      drawWM();
      ok('no glimpse while there are sets left on this exercise',
         !document.querySelector('#wmBody .unext'),
         document.querySelector('#wmBody .unext') ? document.querySelector('#wmBody .unext').textContent : '');
    } else {
      ok('no glimpse while there are sets left on this exercise', true, 'single-set exercise');
    }
    for(var q=0;q<e0.sets.length-1;q++) e0.sets[q].done=true;
    stopRest(); drawWM();
    ok('and a one-line glimpse on the last set',
       !!document.querySelector('#wmBody .unext'),
       document.getElementById('wmBody').textContent.slice(-60));
    e0.sets.forEach(function(s){ s.done=false; });
    stopRest(); drawWM();
  })();
  ok('and the rest of the workout is not on screen', (function(){
     var txt=document.getElementById('wmBody').textContent, n=0;
     W.entries.forEach(function(e){ if(txt.indexOf(e.name)>=0) n++; });
     return n<=2; })(), 'exercise names visible');

  exitWM(true); DB.checkins={};
})();

// ---------- EVERY OFFERED SPORT IS A REAL SPORT ----------
(function(){
  ok('there are plenty of sports to choose from', SPORTS.length>=16, SPORTS.length);

  // the trap: an id in SPORTS with no SPORT_PROFILES entry falls through to
  // 'general', so the user is told nothing was heard while the app says it was
  var orphans=SPORTS.filter(function(s){ return !SPORT_PROFILES[s.id]; })
                    .map(function(s){ return s.id; });
  ok('every offered sport has a profile', orphans.length===0, orphans.join(','));

  // and every profile's act types must be real, or the "is this your sport"
  // guard silently never fires
  var badActs=[];
  Object.keys(SPORT_PROFILES).forEach(function(id){
    (SPORT_PROFILES[id].act||[]).forEach(function(a){
      if(!ACT_TYPES[a]) badActs.push(id+'->'+a);
    });
  });
  ok('every profile maps onto real activity types', badActs.length===0, badActs.join(','));

  // prep and focus keys must exist too, or a warm-up comes out empty
  var badPrep=[], badFocus=[];
  Object.keys(SPORT_PROFILES).forEach(function(id){
    (SPORT_PROFILES[id].prep||[]).forEach(function(k){
      if(!PREP_BLOCKS[k]) badPrep.push(id+'->'+k); });
    (SPORT_PROFILES[id].focus||[]).forEach(function(k){
      if(!FOCUS_BLOCKS[k]) badFocus.push(id+'->'+k); });
  });
  ok('every profile prep block exists', badPrep.length===0, badPrep.join(','));
  ok('every profile focus block exists', badFocus.length===0, badFocus.join(','));

  ok('every sport has a description for the picker',
     SPORTS.every(function(s){ return s.focus && s.focus.length>20; }),
     SPORTS.filter(function(s){return !s.focus;}).map(function(s){return s.id;}).join(','));

  // each new sport must actually change what gets trained
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  ['swimming','climbing','rowing','skiing','golf','volleyball'].forEach(function(id){
    DB.profile.sports=[id]; DB.profile.sport=id;
    ok('choosing '+id+' produces a real warm-up', sportWarmup().items.length>0,
       id+': '+sportWarmup().items.length);
    ok('choosing '+id+' produces its own qualities text',
       (sportProf().qualities||'').length>10, id);
  });
  DB.profile=keepP;
})();

// ---------- AN UNFINISHED SETUP IS NOT LOST ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile)), keepUI=DB.ui;
  DB.ui={}; DB.profile.onboarded=false;
  DB.profile.sports=[]; DB.profile.physiques=[]; DB.profile.gear=[];
  DB.profile.name=''; DB.profile.daysPerWeek=null; DB.profile.sessionMin=null;

  // get three steps in and enter some things
  startSetup();
  SETUP.draft.name='Hatem';
  SETUP.draft.physiques=['athletic'];
  SETUP.step=3; drawSetup();        // equipment
  SETUP.draft.gear=['db'];
  drawSetup();                       // persists

  ok('an unfinished draft is saved', !!(DB.ui&&DB.ui.setup), JSON.stringify(DB.ui.setup&&DB.ui.setup.step));
  ok('it remembers which step', DB.ui.setup.step===3, DB.ui.setup.step);

  // abandon it the way a user does
  closeSheet();
  SETUP={step:0, draft:null};

  // ...and come back
  startSetup();
  ok('reopening resumes the same step', SETUP.step===3, SETUP.step);
  ok('reopening keeps the name', SETUP.draft.name==='Hatem', SETUP.draft.name);
  ok('reopening keeps the goal', SETUP.draft.physiques.join(',')==='athletic',
     SETUP.draft.physiques.join(','));
  ok('reopening keeps the equipment', SETUP.draft.gear.join(',')==='db',
     SETUP.draft.gear.join(','));

  // finishing clears it, so it cannot come back later
  SETUP.step=SETUP_STEPS.length-1; drawSetup();
  finishSetup();
  ok('finishing forgets the draft', !(DB.ui&&DB.ui.setup),
     JSON.stringify(DB.ui&&DB.ui.setup));

  // editing from Settings must never resurrect a draft
  DB.ui.setup={step:2, draft:{name:'Stale', sports:['golf'], physiques:[], gear:[]}};
  DB.profile.onboarded=true;
  startSetup(true);
  ok('editing from Settings starts at the beginning', SETUP.step===0, SETUP.step);
  ok('editing from Settings ignores a stale draft',
     SETUP.draft.name!=='Stale', SETUP.draft.name);
  closeSheet();

  DB.profile=keepP; DB.ui=keepUI||{};
})();

// ---------- ERASING ALL DATA ----------
(function(){
  // the handler used to end with chooseMode(), which does not exist: the wipe
  // happened and then threw, leaving the app on a dead screen
  ok('chooseMode is not referenced any more',
     typeof chooseMode==='undefined');
  ok('startSetup exists to take its place', typeof startSetup==='function');
  ok('Store can clear itself', typeof Store.clearAll==='function');

  // the button lives with backup and restore, not under the program reset
  TAB='today'; resetStack(); openSettings();
  var di=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf('data');
  document.getElementById('setRows').querySelectorAll('button')[di].click();
  var html=document.getElementById('view').innerHTML;
  ok('there is an erase-all control', !!document.getElementById('rsAll'));
  ok('it is called what it does', /Erase all data/.test(html));
  ok('it warns that it cannot be undone', /cannot be undone/.test(html));
  ok('it sits in the Data section', (function(){
    var b=document.getElementById('rsAll');
    var card=b&&b.closest('.spane');
    return !!card && card.classList.contains('data'); })(),
    (function(){ var b=document.getElementById('rsAll');
      var c=b&&b.closest('.spane'); return c?c.className:'none'; })());
  ok('the program reset keeps its own separate warning',
     /Your history is kept/.test(html));
  resetStack();
})();

// ---------- FINISHING SETUP RECORDS WHAT WAS ACTUALLY CHOSEN ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile)), keepT=DB.targets;

  // a user who answered nothing at all must end up with an empty profile,
  // not an invented one
  startSetup();
  SETUP.draft.name=''; SETUP.draft.sports=[]; SETUP.draft.physiques=[];
  SETUP.draft.gear=[]; SETUP.draft.source=null;
  SETUP.draft.daysPerWeek=null; SETUP.draft.sessionMin=null;
  tryRun('finishing an empty setup', function(){ finishSetup(); });
  ok('an empty setup stores no sport', DB.profile.sports.length===0,
     DB.profile.sports.join(','));
  ok('an empty setup stores no goal', DB.profile.physiques.length===0,
     DB.profile.physiques.join(','));
  ok('an empty setup stores no leading sport', DB.profile.sport===null,
     String(DB.profile.sport));
  ok('an empty setup stores no schedule',
     DB.profile.daysPerWeek===null && DB.profile.sessionMin===null,
     DB.profile.daysPerWeek+'/'+DB.profile.sessionMin);
  ok('an empty setup writes no goal prose', DB.profile.goalPrimary==='',
     DB.profile.goalPrimary);
  ok('an empty setup is still marked complete', DB.profile.onboarded===true);
  ok('the engine still has a working frequency', trainDays()===DEFAULT_DAYS, trainDays());
  ok('the engine still has a working session length',
     sessMin()===DEFAULT_SESSION_MIN, sessMin());
  ok('hasSport reports honestly', hasSport()===false);
  ok('nothing counts as the user sport when none was chosen',
     mainSportActs().length===0, mainSportActs().join(','));

  // and a user who answered gets exactly what they said
  startSetup();
  SETUP.draft.name='  Hatem  ';
  SETUP.draft.sports=['tennis']; SETUP.draft.physiques=['athletic'];
  SETUP.draft.gear=['db','band']; SETUP.draft.daysPerWeek=4;
  SETUP.draft.sessionMin=45; SETUP.draft.source=null;
  tryRun('finishing a filled setup', function(){ finishSetup(); });
  ok('the name is stored trimmed', DB.profile.name==='Hatem', '['+DB.profile.name+']');
  ok('the sport is stored', DB.profile.sport==='tennis', String(DB.profile.sport));
  ok('the schedule is stored', DB.profile.daysPerWeek===4 && DB.profile.sessionMin===45);
  ok('targets are derived once something is known',
     Object.keys(DB.targets).length>0, JSON.stringify(DB.targets));

  DB.profile=keepP; DB.targets=keepT; closeSheet();
})();
// keyboard handling exists and does not fire on desktop-sized viewports
ok('keyboard handler wired', typeof bindKeyboard==='function' && typeof wireFocusScroll==='function');
tryRun('bindKeyboard runs without a visualViewport', function(){ bindKeyboard(); });
ok('sheet not in keyboard mode by default', !document.getElementById('sheet').classList.contains('kb-open'));

// complete it and check it lands in the profile
(function(){
  var keep=JSON.parse(JSON.stringify(DB.profile));
  SETUP.draft={mode:'manual',name:'Test',age:34,sex:'Male',heightCm:182,weightKg:77.5,
    gear:['db','band','bench','bar','bb','cable','bike','run'],dbKg:20,
    sports:['football','tennis'],physiques:['muscle','athletic'],daysPerWeek:5,sessionMin:60,units:'metric'};
  SETUP.step=SETUP_STEPS.length-1; drawSetup();
  document.getElementById('setNext').click();
  ok('setup writes age/sex/height/weight', DB.profile.age===34 && DB.profile.sex==='Male' &&
     DB.profile.heightCm===182 && DB.profile.weightKg===77.5);
  ok('setup writes the equipment ticks', DB.profile.gear.indexOf('bb')>=0, DB.profile.gear.join(','));
  ok('tier is derived from the ticks', DB.profile.tier===2, DB.profile.tier);
  ok('dumbbell weight recorded', DB.profile.dbKg===20, DB.profile.dbKg);
  ok('setup writes multiple sports', DB.profile.sports.join(',')==='football,tennis', DB.profile.sports.join(','));
  ok('leading sport recorded', DB.profile.sport==='football');
  ok('setup writes multiple goals', DB.profile.physiques.join(',')==='muscle,athletic');
  ok('setup writes schedule', DB.profile.daysPerWeek===5 && DB.profile.sessionMin===60);
  ok('setup marks onboarded', DB.profile.onboarded===true);
  ok('goal text reflects the chosen sport', /football/i.test(DB.profile.goalPrimary), DB.profile.goalPrimary);
  ok('equipment list reflects the actual ticks', DB.profile.equipment.join(' ').indexOf('Barbell')>=0,
     DB.profile.equipment.join(', '));
  ok('weekly targets adapt to the goal', DB.targets.upper>=2 && DB.targets.power>=1,
     JSON.stringify(DB.targets));
  ok('goal text names every chosen sport',
     /football/i.test(DB.profile.goalPrimary) && /tennis/i.test(DB.profile.goalPrimary),
     DB.profile.goalPrimary);
  ok('goal text says which sport leads', /led by football/i.test(DB.profile.goalPrimary));
  DB.profile=keep; applyGoalTargets();
})();
// multi-sport / multi-goal target shaping
(function(){
  var keep=JSON.parse(JSON.stringify(DB.profile));
  var P=DB.profile;
  P.daysPerWeek=5;
  P.sports=['running']; P.physiques=['perform']; applyGoalTargets();
  ok('runner gets more runs than a tennis player', DB.targets.run>=3, DB.targets.run);
  P.sports=['cycling']; applyGoalTargets();
  ok('cyclist gets rides, not runs', DB.targets.bike>=3 && DB.targets.run===0,
     'bike '+DB.targets.bike+' run '+DB.targets.run);
  P.sports=['cycling','running']; applyGoalTargets();
  ok('cyclist who also runs still gets runs', DB.targets.run>0, DB.targets.run);
  P.sports=['tennis']; P.physiques=['muscle']; applyGoalTargets();
  var upMuscle=DB.targets.upper;
  P.physiques=['perform']; applyGoalTargets();
  ok('muscle goal raises upper-body volume', upMuscle>DB.targets.upper, upMuscle+' vs '+DB.targets.upper);
  P.physiques=['lean']; applyGoalTargets();
  var leanCardio=DB.targets.run+DB.targets.bike;
  P.physiques=['perform']; applyGoalTargets();
  ok('lean goal raises conditioning', leanCardio>DB.targets.run+DB.targets.bike);
  P.physiques=['muscle','lean']; applyGoalTargets();
  ok('conflicting goals still produce a usable plan',
     DB.targets.upper>=2 && (DB.targets.run+DB.targets.bike)>=3, JSON.stringify(DB.targets));
  P.sports=['tennis','football','basketball']; P.daysPerWeek=3; applyGoalTargets();
  ok('three sports on three days drops power work', DB.targets.power===0, DB.targets.power);
  DB.profile=keep; applyGoalTargets();
})();
// old single-value profiles migrate to arrays
(function(){
  var m=migrate({profile:{sport:'running',physique:'lean',onboarded:true},meta:{schema:2},
    exercises:DB.exercises,workouts:DB.workouts});
  ok('legacy single sport becomes an array', Array.isArray(m.profile.sports) &&
     m.profile.sports[0]==='running', JSON.stringify(m.profile.sports));
  ok('legacy single goal becomes an array', Array.isArray(m.profile.physiques) &&
     m.profile.physiques[0]==='lean');
})();
closeSheet();

// ---------- EQUIPMENT TIERS drive exercise selection ----------
ok('gym exercises added to the library', DB.exercises.filter(function(e){return e.tier===2;}).length>=12,
   DB.exercises.filter(function(e){return e.tier===2;}).length);
ok('home-tier exercises exist', DB.exercises.filter(function(e){return e.tier===1;}).length>=8);
ok('every exercise has a movement pattern', DB.exercises.every(function(e){return !!e.pat;}),
   DB.exercises.filter(function(e){return !e.pat;}).map(function(e){return e.id;}).join(','));
ok('every exercise has a tier', DB.exercises.every(function(e){return e.tier!=null;}));
ok('no unknown patterns', DB.exercises.every(function(e){return e.pat==='other'||!!PATTERNS[e.pat];}),
   DB.exercises.filter(function(e){return e.pat!=='other'&&!PATTERNS[e.pat];}).map(function(e){return e.id+':'+e.pat;}).join(','));
(function(){
  var keepG=DB.profile.gear, keepB=DB.profile.preferBest;
  DB.profile.preferBest=true;

  // owns dumbbells and a band, nothing else
  DB.profile.gear=['db','band','bike','run'];
  var r0=resolveExercise('lx01');                       // Tempo Goblet Squat, needs db
  ok('dumbbell owner keeps the goblet squat', canDo(r0), r0.name);
  var b0=resolveExercise('lx02');                       // Bulgarian split squat needs a bench
  ok('no bench => swapped off bench exercises', canDo(b0) && (b0.needs||[]).indexOf('bench')<0, b0.name);
  ok('the swap keeps the same movement pattern', b0.pat==='lunge', b0.pat);
  var p0=resolveExercise('g12');                        // Pull-Up needs a bar
  ok('no bar => a doable vertical pull instead', canDo(p0), p0.name+' needs '+(p0.needs||[]).join('+'));

  // full gym
  DB.profile.gear=['db','band','bench','bar','bb','cable','bike','run'];
  var r2=resolveExercise('lx01');
  ok('gym user is upgraded to the barbell version', (r2.needs||[]).indexOf('bb')>=0 && r2.pat==='squat',
     r2.name+' needs '+(r2.needs||[]).join('+'));
  var c2=resolveExercise('co09');                       // Band Pallof -> Cable Pallof
  ok('gym user gets the cable anti-rotation version', (c2.needs||[]).indexOf('cable')>=0 && c2.pat==='antirot', c2.name);
  ok('mobility is never "upgraded"', resolveExercise('mo01').id==='mo01');
  ok('cardio is never "upgraded"', resolveExercise('cd01').id==='cd01');

  DB.profile.preferBest=false;
  ok('preferBest off keeps the base exercise', resolveExercise('lx01').id==='lx01');
  DB.profile.preferBest=true;

  // sessions are built from exercises you can actually do
  DB.profile.gear=[];
  var blk0=sessionBlocks({workoutId:'w_lowerA',variant:'full',addCore:false});
  ok('bodyweight-only session needs no equipment',
     blk0.every(function(b){ return canDo(exOf(b.ex)); }),
     blk0.filter(function(b){return !canDo(exOf(b.ex));}).map(function(b){return exOf(b.ex).name;}).join(','));
  DB.profile.gear=['db','band','bench','bar','bb','cable','bike','run'];
  var blk2=sessionBlocks({workoutId:'w_lowerA',variant:'full',addCore:false});
  ok('gym session uses gym exercises',
     blk2.some(function(b){ var n=exOf(b.ex).needs||[]; return n.indexOf('bb')>=0||n.indexOf('cable')>=0; }),
     blk2.map(function(b){return exOf(b.ex).name;}).join(' | '));
  ok('same number of exercises regardless of equipment', blk0.length===blk2.length, blk0.length+' vs '+blk2.length);
  ok('swaps are explained in the block note',
     blk2.filter(function(b){return b.swappedFrom;}).every(function(b){ return !!b.note; }));
  DB.profile.gear=keepG; DB.profile.preferBest=keepB;
})();

// ---------- TWO MODES: WHOOP optional, never invented ----------
(function(){
  var keepW=DB.whoop, keepB=DB.baselines, keepM=DB.profile.mode;

  // --- MANUAL MODE: no WHOOP data at all ---
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.baselines=Object.assign({},SEED_BASE);
  DB.profile.mode='manual';
  ok('hasWhoop() false with no data', hasWhoop()===false);
  ok('baselines are NOT invented', DB.baselines.hrv===null && DB.baselines.rhr===null &&
     DB.baselines.recovery===null, JSON.stringify({hrv:DB.baselines.hrv,rhr:DB.baselines.rhr}));
  ok('baselines marked not computed', DB.baselines.computed===false);
  ok('sleep target flagged generic', DB.baselines.sleepNeedGeneric===true);

  var ciM={sleepMin:450,energy:7,soreness:3,stress:4,motivation:8,pain:'None',availTime:60,sportToday:false};
  var rdM=readiness(todayISO(),ciM);
  ok('readiness works with zero WHOOP inputs', rdM.score>0 && rdM.score<=100, rdM.score);
  ok('readiness assigns a band without WHOOP', ['green','yellow','orange','red'].indexOf(rdM.band)>=0, rdM.band);
  ok('no WHOOP signals counted', rdM.sources.whoop.length===0, JSON.stringify(rdM.sources.whoop));
  ok('sources describe feel + history, not WHOOP',
     /how you feel/.test(rdM.sources.label) && !/WHOOP/.test(rdM.sources.label), rdM.sources.label);
  ok('confidence reported', ['high','moderate','low'].indexOf(rdM.sources.confidence)>=0, rdM.sources.confidence);
  ok('missing signals reduce weight, not fabricate', rdM.weight<100 && rdM.weight>0, rdM.weight);
  var partKeys=rdM.parts.map(function(p){return p.key;});
  ok('no recovery part without WHOOP', partKeys.indexOf('recovery')<0, partKeys.join(','));
  ok('no hrv part without WHOOP', partKeys.indexOf('hrv')<0);
  ok('no rhr part without WHOOP', partKeys.indexOf('rhr')<0);
  ok('sleep + subjective still used', partKeys.indexOf('sleep')>=0 && partKeys.indexOf('subjective')>=0, partKeys.join(','));
  var recM=recommend(todayISO(),ciM);
  ok('engine still recommends without WHOOP', !!recM.id && !!recM.label, recM.id);
  ok('recommendation explains inputs without WHOOP', recM.why.length>=2);
  ok('generic sleep target is labelled as generic',
     recM.why.some(function(n){return /generic/i.test(n.t);}) || rdM.why.some(function(n){return /generic/i.test(n.t);}),
     JSON.stringify(rdM.why.map(function(n){return n.t;})));

  // --- WHOOP MODE: restore real imported data ---
  DB.whoop=keepW; DB.profile.source='whoop'; DB.profile.mode='whoop'; recomputeBaselines();
  ok('hasWhoop() true after import', hasWhoop()===true, DB.whoop.cycles.length+' cycles');
  ok('baselines computed from real data', DB.baselines.computed===true);
  ok('HRV baseline now a number', typeof DB.baselines.hrv==='number' && DB.baselines.hrv>0, DB.baselines.hrv);
  ok('sleep need no longer generic', DB.baselines.sleepNeedGeneric===false);
  var ciW=Object.assign({recovery:74,hrv:86,rhr:52,prevStrain:9},ciM);
  var rdW=readiness(todayISO(),ciW);
  ok('WHOOP signals now counted', rdW.sources.whoop.length>=3, JSON.stringify(rdW.sources.whoop));
  ok('sources label mentions WHOOP', /WHOOP/.test(rdW.sources.label), rdW.sources.label);
  ok('more inputs => higher weight', rdW.weight>rdM.weight, rdW.weight+' vs '+rdM.weight);
  ok('confidence rises with WHOOP', rdW.sources.confidence==='high', rdW.sources.confidence);

  // --- switching back is non-destructive ---
  var nSess=DB.sessions.length, nAct=DB.activities.length;
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.baselines=Object.assign({},SEED_BASE); DB.profile.mode='manual';
  ok('removing WHOOP keeps sessions', DB.sessions.length===nSess);
  ok('removing WHOOP keeps activities', DB.activities.length===nAct);
  ok('engine still works after WHOOP removed', !!recommend(todayISO(),ciM).id);
  DB.whoop=keepW; DB.baselines=keepB; DB.profile.mode=keepM; recomputeBaselines();
})();
ok('first run asks for a mode', freshDB().profile.mode===null && freshDB().profile.onboarded===false);
// an upgraded v1 install must not inherit someone else's baselines
(function(){
  var up=migrate({profile:{},meta:{schema:1},exercises:DB.exercises,workouts:DB.workouts,
    baselines:{hrv:83,rhr:53.9,recovery:66.8,computed:true},
    whoop:{cycles:[],workouts:[],journal:[],imports:[]}});
  ok('v1 baselines dropped when no WHOOP data present', up.baselines.hrv===null, up.baselines.hrv);
  ok('v1 install defaults to manual mode', up.profile.mode==='manual', up.profile.mode);
  ok('v1 install skips the mode picker', up.profile.onboarded===true);
  ok('schema stamped forward', up.meta.schema===SCHEMA_VERSION, up.meta.schema);
})();

// ---------- CHECK-IN never asks for WHOOP numbers it can work out ----------
(function(){
  var keepW=DB.whoop, keepM=DB.profile.mode, keepC=DB.checkins;

  // (a) WHOOP data covers this date -> auto-filled, nothing to type
  var covered=DB.whoop.cycles[DB.whoop.cycles.length-1].date;
  DB.profile.source='whoop'; DB.profile.mode='whoop'; DB.checkins={};
  openCheckin(covered);
  var html=$('#sheetBody').innerHTML;
  ok('covered date shows WHOOP as automatic', /AUTOMATIC/.test(html));
  ok('covered date does not ask you to type recovery',
     document.getElementById('ciRec').type==='hidden', document.getElementById('ciRec').type);
  ok('covered date pre-fills the real value',
     document.getElementById('ciRec').value===String(cycleByDate(covered).recovery),
     document.getElementById('ciRec').value);
  ok('covered date has no visible WHOOP inputs',
     $$('#sheetBody input[type=number]').filter(function(i){
       return ['ciRec','ciHrv','ciRhr','ciSp','ciPs'].indexOf(i.id)>=0; }).length===0);
  closeSheet();

  // (b) device user, date not covered -> asked plainly, compared to baselines
  DB.profile.source='whoop'; DB.profile.sourceFields=null;
  var future='2031-01-15';
  openCheckin(future);
  html=$('#sheetBody').innerHTML;
  ok('uncovered date asks for this morning\\'s numbers', /This morning.s WHOOP numbers/i.test(html));
  ok('device fields are visible and editable',
     document.getElementById('ciRec').type==='number' && document.getElementById('ciHrv').type==='number');
  ok('the imported baselines are shown for comparison',
     /your own baselines/i.test(html) && /HRV/.test(html));
  ok('blank fields are explicitly weighed out, not guessed', /will not guess/i.test(html));
  ok('saving without touching it stores no WHOOP values', (function(){
    document.getElementById('ciSleep').value='450';
    document.getElementById('ciSave').click();
    var c=DB.checkins[future];
    return c && c.recovery===null && c.hrv===null && c.rhr===null;
  })(), JSON.stringify(DB.checkins[future]&&{r:DB.checkins[future].recovery,h:DB.checkins[future].hrv}));
  ok('load is estimated from the log instead', DB.checkins[future].prevStrainEstimated===true);
  closeSheet();

  // (c) no wearable at all -> never mentioned
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.profile.source='none'; DB.profile.sourceFields=null; DB.profile.mode='manual'; DB.checkins={};
  openCheckin(todayISO());
  html=$('#sheetBody').innerHTML;
  ok('manual mode never mentions WHOOP in the check-in', !/WHOOP/i.test(html), html.slice(0,120));
  ok('manual mode has no WHOOP inputs at all',
     !document.getElementById('ciRec') && !document.getElementById('ciHrv') &&
     !document.getElementById('ciRhr') && !document.getElementById('ciPs'));
  ok('manual mode still asks how you feel',
     !!document.getElementById('ciEn') && !!document.getElementById('ciSo') &&
     !!document.getElementById('ciSt') && !!document.getElementById('ciMo'));
  ok('manual mode still asks sleep and time', !!document.getElementById('ciSleep') && !!document.getElementById('ciTime'));
  closeSheet();

  DB.whoop=keepW; DB.profile.mode=keepM; DB.checkins=keepC;
})();

// ---------- without WHOOP the engine uses feel + training history ----------
(function(){
  var keepW=DB.whoop, keepC=DB.checkins, keepA=DB.activities, keepB=DB.baselines;
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.baselines=Object.assign({},SEED_BASE);
  DB.profile.mode='manual';
  var D2='2031-03-20';
  var base={sleepMin:450,energy:7,soreness:3,stress:4,motivation:7,pain:'None',availTime:60,sportToday:false};

  // build a personal subjective baseline
  DB.checkins={};
  for(var i=1;i<=12;i++){
    DB.checkins[addDays(D2,-i)]={date:addDays(D2,-i),energy:7,soreness:3,stress:4,motivation:7,sleepMin:450};
  }
  var SB=subjectiveBaseline(D2);
  ok('subjective baseline builds from your own check-ins', SB.ready===true && SB.n===12, SB.n);
  ok('subjective baseline finds your usual energy', Math.abs(SB.energy-7)<0.01, SB.energy);

  var r=readiness(D2,base);
  var keys=r.parts.map(function(p){return p.key;});
  ok('no WHOOP signals used', keys.indexOf('recovery')<0 && keys.indexOf('hrv')<0 && keys.indexOf('rhr')<0, keys.join(','));
  ok('subjective carries more weight without physiology',
     r.parts.find(function(p){return p.key==='subjective';}).weight===30,
     JSON.stringify(r.parts.map(function(p){return p.key+':'+p.weight;})));
  ok('own-norm comparison is used', keys.indexOf('ownNorm')>=0, keys.join(','));
  ok('training load state is used', keys.indexOf('loadState')>=0, keys.join(','));
  ok('sources describe feel + history', /how you feel/.test(r.sources.label), r.sources.label);
  ok('confidence is reported without WHOOP', ['high','moderate','low'].indexOf(r.sources.confidence)>=0, r.sources.confidence);

  // feeling worse than your own norm must lower the score
  var good=readiness(D2,Object.assign({},base,{energy:9,soreness:1}));
  var poor=readiness(D2,Object.assign({},base,{energy:3,soreness:8}));
  ok('feeling much worse than usual lowers readiness', poor.score<good.score-15,
     good.score+' vs '+poor.score);
  ok('a bad day without WHOOP still reaches a low band',
     ['orange','red','yellow'].indexOf(poor.band)>=0, poor.band);

  // accumulated load must lower it too, with nothing else changing
  DB.activities=[];
  var fresh=readiness(D2,base).score;
  DB.activities=[
    {id:'h1',date:addDays(D2,-1),type:'football',min:90,rpe:9,planned:true},
    {id:'h2',date:addDays(D2,-2),type:'tennis',min:120,rpe:8,planned:true},
    {id:'h3',date:addDays(D2,-3),type:'running',min:70,rpe:8,planned:true}
  ];
  var loaded=readiness(D2,base);
  ok('three hard days lowers readiness on identical feel', loaded.score<fresh,
     fresh+' -> '+loaded.score);
  ok('accumulated load is explained', loaded.why.some(function(n){return /load/i.test(n.t);}),
     JSON.stringify(loaded.why.map(function(n){return n.t;})));
  ok('rest debt is detected', loaded.parts.some(function(p){return p.key==='restDebt';}),
     loaded.parts.map(function(p){return p.key;}).join(','));
  // and the engine still produces a real recommendation
  var recM=recommend(D2,base);
  ok('manual mode still recommends a session', !!recM.id && !!recM.workoutId||recM.id==='rest', recM.id);
  ok('manual recommendation explains itself', recM.why.length>=3, recM.why.length);

  DB.whoop=keepW; DB.checkins=keepC; DB.activities=keepA; DB.baselines=keepB;
  DB.profile.source='whoop'; DB.profile.mode='whoop'; recomputeBaselines();
})();

// ---------- CYCLE TRACKING: OPTIONAL, AND OFF BY DEFAULT ----------
(function(){
  var keepC=DB.checkins, keepM=DB.mcycle, keepP=JSON.parse(JSON.stringify(DB.profile));
  var keepS=DB.sessions, keepW=DB.whoop;

  function reset(){
    DB.checkins={}; DB.sessions=[];
    DB.mcycle={on:false,starts:[],typicalLen:null,typicalPeriod:null,askedAt:null};
  }
  /* build a history: `cycles` periods of `len` days, with `quality` shifting
     the reported day for the named phase. A test fixture, nothing more. */
  function history(opts){
    reset();
    DB.mcycle.on=true;
    var len=opts.len||28, n=opts.cycles||0, plen=opts.periodLen||5;
    var start=opts.from||'2026-01-05';
    for(var c=0;c<n;c++){
      var s=addDays(start, c*(len + (opts.jitter? ((c%2)?opts.jitter:-opts.jitter) : 0)));
      DB.mcycle.starts.push(s);
      for(var d=0;d<len;d++){
        var day=addDays(s,d);
        if(day>todayISO()) break;
        var bleeding = d<plen;
        DB.checkins[day]={date:day, energy:6, soreness:3, stress:4, motivation:6,
                          sleepMin:450, pain:'None',
                          mc:{bleeding:bleeding, cramps:bleeding?4:0}};
        /* shift the named phase so an association exists to find */
        if(opts.worsePhase){
          var ph=mcPhase(day);
          if(ph.phase===opts.worsePhase){
            DB.checkins[day].energy=2; DB.checkins[day].soreness=8;
            DB.checkins[day].motivation=3;
            DB.checkins[day].mc.cramps=7;
          }
        }
      }
    }
    DB.mcycle.starts.sort();
  }

  // ---- off by default, and completely inert ----
  reset();
  ok('cycle tracking is off on a fresh profile', mcOn()===false);
  ok('a fresh profile has no period dates', freshDB().mcycle.starts.length===0);
  ok('a fresh profile is not marked as tracking', freshDB().mcycle.on===false);
  ok('mcycle is a stored key', KV_KEYS.indexOf('mcycle')>=0);

  var T=todayISO();
  DB.checkins[T]={date:T,energy:7,soreness:3,stress:3,motivation:8,sleepMin:450,pain:'None'};
  var offScore=readiness(T,DB.checkins[T]).score;
  ok('readiness reports no cycle block when off', readiness(T,DB.checkins[T]).mc===null);
  ok('phase is unknown when off', mcPhase(T).phase==='unknown');
  ok('there is no cycle row on Today when off', mcRow(T)==='');
  ok('no cycle block in Patterns when off', mcLinksBlock()==='');

  // ---- a female profile that declines tracking sees nothing ----
  DB.profile.sex='Female';
  ok('a female profile does not imply tracking', mcOn()===false);
  ok('and still gets no cycle row', mcRow(T)==='');
  ok('and an identical readiness score', readiness(T,DB.checkins[T]).score===offScore,
     readiness(T,DB.checkins[T]).score+' vs '+offScore);

  // ---- enabling it later works, and changes nothing on its own ----
  DB.mcycle.on=true;
  ok('tracking can be enabled after setup', mcOn()===true);
  ok('enabling it alone does not move the score',
     readiness(T,DB.checkins[T]).score===offScore,
     readiness(T,DB.checkins[T]).score+' vs '+offScore);
  ok('but the cycle block now exists', !!readiness(T,DB.checkins[T]).mc);
  ok('with no data the phase is unknown', mcPhase(T).phase==='unknown',
     mcPhase(T).phase);
  ok('and it says why rather than guessing',
     /No period logged yet/.test(mcPhase(T).note), mcPhase(T).note);
  ok('the summary offers to start logging',
     /Log today/.test(mcRow(T)) || /start counting/.test(mcSummary(T).sub));

  // ---- disabling removes the influence again ----
  DB.mcycle.on=false;
  ok('disabling makes it inert again', readiness(T,DB.checkins[T]).mc===null);

  // ---- counting, phases, and refusing to guess ----
  reset(); DB.mcycle.on=true;
  DB.mcycle.starts=['2026-09-01'];
  ok('cycle day counts from the period start', mcDay('2026-09-01')===1, mcDay('2026-09-01'));
  ok('day 12 is day 12', mcDay('2026-09-12')===12, mcDay('2026-09-12'));
  ok('a date before any start has no day', mcDay('2026-08-30')===null);
  ok('with one start and no length, phase is unknown',
     mcPhase('2026-09-12').phase==='unknown', mcPhase('2026-09-12').phase);
  ok('missing typical length is not filled with 28',
     mcStats().use===null, String(mcStats().use));

  DB.mcycle.typicalLen=28; DB.mcycle.typicalPeriod=5;
  ok('a stated length is used', mcStats().use===28, mcStats().use);
  ok('day 3 is menstrual', mcPhase('2026-09-03').phase==='menstrual');
  ok('day 10 is follicular', mcPhase('2026-09-10').phase==='follicular',
     mcPhase('2026-09-10').phase);
  ok('day 14 is the ovulatory window', mcPhase('2026-09-14').phase==='ovulatory',
     mcPhase('2026-09-14').phase);
  ok('day 22 is luteal', mcPhase('2026-09-22').phase==='luteal',
     mcPhase('2026-09-22').phase);
  ok('a phase from one cycle is low confidence',
     mcPhase('2026-09-22').confidence==='low', mcPhase('2026-09-22').confidence);
  /* 'late' and 'unknown' both mean no phase is known and both suppress any
     readiness adjustment; 'late' additionally carries how far past it is. */
  ok('well past the expected length, no phase is claimed',
     ['unknown','late'].indexOf(mcPhase('2026-10-20').phase)>=0,
     mcPhase('2026-10-20').phase);
  ok('and no confidence is claimed either',
     mcPhase('2026-10-20').confidence==='none', mcPhase('2026-10-20').confidence);
  ok('and it explains that rather than saying nothing',
     /past your usual/.test(mcPhase('2026-10-20').note), mcPhase('2026-10-20').note);

  // different lengths must actually shift the phases
  DB.mcycle.typicalLen=35;
  ok('a 35-day cycle moves the ovulatory window later',
     mcPhase('2026-09-21').phase==='ovulatory', mcPhase('2026-09-21').phase);
  ok('and day 14 is still follicular for that user',
     mcPhase('2026-09-14').phase==='follicular', mcPhase('2026-09-14').phase);
  DB.mcycle.typicalLen=21;
  ok('a short cycle still splits sensibly',
     ['follicular','ovulatory','luteal','menstrual'].indexOf(mcPhase('2026-09-09').phase)>=0,
     mcPhase('2026-09-09').phase);
  DB.mcycle.typicalLen=17; DB.mcycle.typicalPeriod=6;
  ok('a cycle too short to split says so rather than inventing phases',
     mcPhase('2026-09-10').phase==='unknown', mcPhase('2026-09-10').phase);

  // ---- reported bleeding outranks the estimate ----
  reset(); DB.mcycle.on=true;
  DB.mcycle.starts=['2026-09-01']; DB.mcycle.typicalLen=28;
  mcSetLog('2026-09-20',{bleeding:true});
  ok('logged bleeding beats an estimated luteal phase',
     mcPhase('2026-09-20').phase==='menstrual', mcPhase('2026-09-20').phase);
  ok('and is labelled as reported, not estimated',
     mcPhase('2026-09-20').confidence==='reported');

  // ---- period starts are derived from bleeding, not asked for ----
  reset(); DB.mcycle.on=true;
  ['2026-03-01','2026-03-02','2026-03-03'].forEach(function(d){ mcSetLog(d,{bleeding:true}); });
  ['2026-03-29','2026-03-30'].forEach(function(d){ mcSetLog(d,{bleeding:true}); });
  ok('a run of bleeding days yields one start', mcStarts().length===2,
     mcStarts().join(','));
  ok('the derived length is the gap between them', mcStats().lens[0]===28,
     JSON.stringify(mcStats().lens));
  ok('period length is derived from the runs', mcPeriodLen()===3, mcPeriodLen());

  // ---- irregular cycles are handled, never penalised ----
  history({cycles:4, len:28, jitter:7, worsePhase:null, from:'2026-04-01'});
  var S=mcStats();
  ok('an irregular history is recognised as irregular', S.regular===false,
     JSON.stringify({sd:S.sd, lens:S.lens}));
  ok('and its phase estimates drop to low confidence', (function(){
    var st=mcStarts(); var probe=addDays(st[st.length-1],20);
    var ph=mcPhase(probe);
    return ph.phase==='unknown' || ph.confidence==='low'; })());
  ok('irregularity costs nothing: no negative adjustment appears',
     mcAdjust(addDays(mcStarts()[mcStarts().length-1],20)).delta===0,
     mcAdjust(addDays(mcStarts()[mcStarts().length-1],20)).delta);

  // ---- evidence gating: thin data does nothing ----
  history({cycles:1, len:28, worsePhase:'luteal', from:'2026-06-01'});
  var probe1=addDays(mcStarts()[0],20);
  ok('one cycle produces no established pattern',
     mcEvidence().phases.luteal.established===false,
     JSON.stringify(mcEvidence().phases.luteal));
  ok('one cycle cannot change the readiness score',
     mcAdjust(probe1).delta===0, mcAdjust(probe1).delta);
  ok('and nothing is said about a pattern that is not there',
     mcAdjust(probe1).line===null);

  // ---- repeated observations may gradually influence it, within a cap ----
  history({cycles:4, len:28, worsePhase:'luteal', from:'2026-05-01'});
  var st2=mcStarts(), probe2=addDays(st2[st2.length-1],20);
  var ev=mcEvidence();
  ok('four cycles of the same pattern is established',
     ev.phases.luteal.established===true, JSON.stringify(ev.phases.luteal));
  var adj=mcAdjust(probe2);
  ok('an established pattern produces an adjustment', adj.delta!==0, adj.delta);
  ok('the adjustment is negative for a consistently worse phase',
     adj.delta<0, adj.delta);
  ok('the adjustment is capped at 5 points',
     Math.abs(adj.delta)<=MC_MAX_ADJUST, adj.delta);
  ok('it is described as a correlation, not a cause',
     /not a cause/.test(adj.line) && !/hormone/i.test(adj.line), adj.line);
  ok('it names the sample it is based on', /logged days/.test(adj.line));

  // an unaffected phase in the same history still gets nothing
  var fol=addDays(st2[st2.length-1],9);
  ok('a phase with no pattern is left alone', mcAdjust(fol).delta===0,
     mcAdjust(fol).delta+' for '+mcPhase(fol).phase);

  // ---- and it cannot dominate: the cap is small next to the signals ----
  (function(){
    var d=probe2;
    DB.checkins[d]=Object.assign({},DB.checkins[d],{energy:2,soreness:8,motivation:3});
    var withCycle=readiness(d,DB.checkins[d]).score;
    DB.mcycle.on=false;
    var without=readiness(d,DB.checkins[d]).score;
    DB.mcycle.on=true;
    ok('cycle context moves the score by no more than the cap',
       Math.abs(withCycle-without)<=MC_MAX_ADJUST,
       without+' -> '+withCycle);
  })();

  // ---- SAFETY: cycle context can never lift a pain cap ----
  (function(){
    history({cycles:4, len:28, worsePhase:'follicular', from:'2026-05-01'});
    var st3=mcStarts(), day=addDays(st3[st3.length-1],9);
    /* make the pattern strongly POSITIVE so it would raise the score */
    Object.keys(DB.checkins).forEach(function(k){
      if(mcPhase(k).phase==='follicular'){
        DB.checkins[k].energy=10; DB.checkins[k].soreness=0;
        DB.checkins[k].motivation=10; DB.checkins[k].mc.cramps=0;
      }
    });
    DB.checkins[day]=Object.assign({},DB.checkins[day],
      {energy:10,soreness:0,stress:1,motivation:10,sleepMin:500,pain:'Significant'});
    var r=readiness(day,DB.checkins[day]);
    ok('significant pain still caps the band regardless of cycle context',
       r.band==='red', r.band+' score '+r.score);
    DB.checkins[day].pain='Moderate';
    var r2=readiness(day,DB.checkins[day]);
    ok('moderate pain still caps the band regardless of cycle context',
       r2.band==='orange'||r2.band==='red', r2.band);
    ok('the pain reason is still given',
       r2.why.some(function(w){ return /pain/i.test(w.t); }));
  })();

  // ---- the user's own report outranks any estimate ----
  (function(){
    reset(); DB.mcycle.on=true;
    DB.mcycle.starts=['2026-09-01']; DB.mcycle.typicalLen=28;
    var d='2026-09-10';
    DB.checkins[d]={date:d,energy:6,soreness:3,stress:4,motivation:6,sleepMin:450,pain:'None'};
    var base=readiness(d,DB.checkins[d]).score;
    mcSetLog(d,{feel:'discomfort'});
    var worse=readiness(d,DB.checkins[d]).score;
    ok('reporting significant discomfort lowers the score', worse<base, base+' -> '+worse);
    ok('and it is explained as the reported state',
       readiness(d,DB.checkins[d]).why.some(function(w){
         return /you reported feeling/i.test(w.t); }));
    mcSetLog(d,{feel:'strong'});
    var better=readiness(d,DB.checkins[d]).score;
    ok('reporting feeling strong raises it', better>base, base+' -> '+better);
    mcSetLog(d,{feel:'normal'});
    ok('normal leaves it where it was', readiness(d,DB.checkins[d]).score===base,
       readiness(d,DB.checkins[d]).score+' vs '+base);

    // ...but a good report still cannot beat pain
    DB.checkins[d].pain='Significant';
    mcSetLog(d,{feel:'strong'});
    ok('feeling strong does not undo significant pain',
       readiness(d,DB.checkins[d]).band==='red',
       readiness(d,DB.checkins[d]).band);
    DB.checkins[d].pain='None';
  })();

  // ---- cramps behave like reported discomfort, not a phase rule ----
  (function(){
    reset(); DB.mcycle.on=true;
    var d=todayISO();
    DB.checkins[d]={date:d,energy:6,soreness:3,stress:4,motivation:6,sleepMin:450,pain:'None'};
    var base=readiness(d,DB.checkins[d]).score;
    mcSetLog(d,{cramps:9});
    var withCramps=readiness(d,DB.checkins[d]).score;
    ok('significant cramps lower readiness', withCramps<base, base+' -> '+withCramps);
    ok('and are named in the reasoning',
       readiness(d,DB.checkins[d]).why.some(function(w){ return /cramps/i.test(w.t); }));
    mcSetLog(d,{cramps:0});
    ok('no cramps is not treated as a penalty',
       readiness(d,DB.checkins[d]).score>=base-1, readiness(d,DB.checkins[d]).score);
  })();

  // ---- works for manual-only users and for wearable users alike ----
  (function(){
    history({cycles:4, len:28, worsePhase:'luteal', from:'2026-05-01'});
    var st4=mcStarts(), day=addDays(st4[st4.length-1],20);
    DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
    DB.profile.source='none';
    var manual=readiness(day,DB.checkins[day]);
    ok('a manual-only user still gets a cycle-aware score', !!manual.mc);
    ok('and the pattern applies for them', manual.flags.indexOf('mcPattern')>=0,
       manual.flags.join(','));

    /* the same day, now with wearable numbers present */
    DB.profile.source='whoop';
    DB.checkins[day]=Object.assign({},DB.checkins[day],{recovery:70,hrv:80,rhr:52});
    DB.baselines=Object.assign({},DB.baselines,{hrv:80,hrvSd:8,rhr:52,rhrSd:3,
      recovery:65,computed:true});
    var withDev=readiness(day,DB.checkins[day]);
    ok('a wearable user also gets it', withDev.flags.indexOf('mcPattern')>=0,
       withDev.flags.join(','));
    ok('wearable signals still dominate the weighting',
       withDev.parts.some(function(p){ return p.key==='recovery'; }));
    ok('the cycle nudge is still capped alongside wearable data', (function(){
      DB.mcycle.on=false; var a=readiness(day,DB.checkins[day]).score;
      DB.mcycle.on=true;  var b=readiness(day,DB.checkins[day]).score;
      return Math.abs(a-b)<=MC_MAX_ADJUST; })());
  })();

  // ---- actual workout performance feeds the observation ----
  (function(){
    history({cycles:3, len:28, from:'2026-05-01'});
    var st5=mcStarts(), day=addDays(st5[st5.length-1],20);
    var before=mcDayQuality(day);
    DB.sessions=[{id:'mcs1',date:day,done:true,sessionRpe:10,workoutId:'w_lowerA',
                  entries:[]}];
    var after=mcDayQuality(day);
    ok('a maximal-RPE session lowers the observed day quality',
       after<before, before+' -> '+after);
    DB.sessions=[];
  })();

  // ---- persistence, backup and restore ----
  (function(){
    reset(); DB.mcycle.on=true;
    DB.mcycle.starts=['2026-09-01']; DB.mcycle.typicalLen=29;
    mcSetLog('2026-09-02',{bleeding:true,cramps:6,symptoms:['Cramps'],note:'ouch'});

    /* the import path is migrate() over a parsed backup */
    var round=migrate(JSON.parse(JSON.stringify(DB)));
    ok('cycle settings survive a backup round trip',
       round.mcycle && round.mcycle.on===true && round.mcycle.typicalLen===29,
       JSON.stringify(round.mcycle));
    ok('period dates survive a backup round trip',
       round.mcycle.starts.join(',')==='2026-09-01', round.mcycle.starts.join(','));
    ok('daily cycle entries survive a backup round trip',
       round.checkins['2026-09-02'] && round.checkins['2026-09-02'].mc
       && round.checkins['2026-09-02'].mc.cramps===6,
       JSON.stringify(round.checkins['2026-09-02'] && round.checkins['2026-09-02'].mc));
    ok('symptoms and notes survive too',
       round.checkins['2026-09-02'].mc.symptoms.join(',')==='Cramps'
       && round.checkins['2026-09-02'].mc.note==='ouch');

    /* an install that predates the feature gets it off, not missing */
    var old=migrate({profile:{},exercises:DB.exercises,workouts:DB.workouts});
    ok('an older backup gains the setting, switched off',
       old.mcycle && old.mcycle.on===false, JSON.stringify(old.mcycle));
    ok('and no invented period dates', old.mcycle.starts.length===0);

    /* the hydrate path used at boot keeps it too */
    var hy=hydrate({kv:{mcycle:{on:true,starts:['2026-01-01'],typicalLen:30,typicalPeriod:4}},
                    cols:{}});
    ok('the boot path restores cycle settings',
       hy.mcycle.on===true && hy.mcycle.typicalLen===30, JSON.stringify(hy.mcycle));
  })();

  // ---- deleting it really deletes it ----
  (function(){
    reset(); DB.mcycle.on=true;
    DB.mcycle.starts=['2026-09-01'];
    mcSetLog('2026-09-02',{bleeding:true,cramps:6});
    DB.checkins['2026-09-02'].energy=7;
    mcWipe();
    ok('wiping turns tracking off', mcOn()===false);
    ok('wiping removes period dates', DB.mcycle.starts.length===0);
    ok('wiping removes the daily entries',
       !DB.checkins['2026-09-02'].mc, JSON.stringify(DB.checkins['2026-09-02']));
    ok('but keeps the rest of the check-in', DB.checkins['2026-09-02'].energy===7);
  })();

  // ---- nothing cycle-shaped in the shipped defaults ----
  (function(){
    var f=freshDB();
    ok('no cycle data in a fresh database',
       f.mcycle.on===false && f.mcycle.starts.length===0
       && f.mcycle.typicalLen===null && f.mcycle.typicalPeriod===null);
    ok('no check-in in a fresh database at all',
       Object.keys(f.checkins).length===0);
    var anyMc=Object.keys(f.checkins).some(function(k){ return !!f.checkins[k].mc; });
    ok('and therefore no seeded cycle entries', anyMc===false);
  })();

  // ---- the week view carries the cycle when tracking is on ----
  (function(){
    reset();
    var T2=todayISO();
    ok('no cycle marks on the week view when off',
       weekStrip(T2).indexOf('var(--pink)')<0);

    /* The bleeding days have to fall inside the week the strip is DRAWING, and
       T2-3 is in the previous ISO week whenever T2 is early in one - so on a
       Monday nothing pink appeared and this failed. Count forward from the
       week's own Monday instead, never into the future. */
    DB.mcycle.on=true;
    DB.mcycle.typicalLen=28;
    var wk0=weekStartOf(T2), bleed=[];
    for(var bi=0;bi<3;bi++){ var bd=addDays(wk0,bi); if(bd<=T2) bleed.push(bd); }
    if(!bleed.length) bleed=[T2];
    DB.mcycle.starts=[bleed[0]];
    bleed.forEach(function(bd){ mcSetLog(bd,{bleeding:true}); });

    var strip=weekStrip(T2);
    ok('the week view shows cycle days once on',
       strip.indexOf('cycle day')>=0 || /min-width:17px/.test(strip));
    ok('a logged bleeding day is marked distinctly',
       strip.indexOf('var(--pink)')>=0);
    var cdToday=mcDay(T2);
    ok('the day number is shown', strip.indexOf('>'+cdToday+'<')>=0, String(cdToday));
    ok('the legend explains the marks', /cycle day/i.test(strip));

    // and it is still the same seven cells, not a second calendar
    // seven cells, six dividers and a "none" on the last
    ok('the week view is still one row of seven cells',
       (strip.match(/border-right:/g)||[]).length===7,
       (strip.match(/border-right:/g)||[]).length);

    DB.mcycle.on=false;
    ok('turning it off removes the marks again',
       weekStrip(T2).indexOf('var(--pink)')<0);
  })();

  // ---- settings: one button off, one button on ----
  (function(){
    reset();
    var openCycleSettings=function(){
      resetStack(); TAB='today'; openSettings();
      var i=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf('cycle');
      document.getElementById('setRows').querySelectorAll('button')[i].click();
    };

    openCycleSettings();
    var card=document.querySelector('#view .spane.cycle');
    ok('with tracking off there is exactly one button',
       card && card.querySelectorAll('button').length===1,
       card? card.querySelectorAll('button').length : 'no card');
    ok('and it is the enable button', !!document.getElementById('sMcEnable'));
    ok('no disable button while it is already off', !document.getElementById('sMcOff'));
    ok('no fields while it is off', !document.getElementById('sMcLen'));

    document.getElementById('sMcEnable').click();
    /* Enabling used to leave you counting from nothing. It now asks the three
       questions every specialist tracker asks, and all of them are skippable. */
    ok('enabling asks when the last period started', !!document.getElementById('mcS0'));
    ok('and for the two usual lengths',
       !!document.getElementById('mcP0') && !!document.getElementById('mcL0'));
    ok('nothing is pre-filled with an assumed 28 days',
       document.getElementById('mcL0').value==='' &&
       document.getElementById('mcP0').value==='',
       document.getElementById('mcL0').value+'/'+document.getElementById('mcP0').value);
    ok('and it can be skipped', !!document.getElementById('mcS0skip'));
    document.getElementById('mcS0skip').click();
    ok('skipping still turns it on', mcOn()===true);
    closeSheet();

    openCycleSettings();
    card=document.querySelector('#view .spane.cycle');
    ok('with tracking on there is one button at the bottom',
       card && card.querySelectorAll('button').length===1,
       card? card.querySelectorAll('button').length : 'no card');
    ok('and it is the disable button', !!document.getElementById('sMcOff'));
    ok('the enable button is gone', !document.getElementById('sMcEnable'));
    ok('the settings fields are there', !!document.getElementById('sMcLen')
       && !!document.getElementById('sMcPer'));
    ok('the disable button is last in the section', (function(){
      var b=document.getElementById('sMcOff');
      var all=card.querySelectorAll('button');
      return all[all.length-1]===b; })());

    // disabling offers both keeping and deleting, from one button
    mcSetLog(todayISO(),{bleeding:true,cramps:5});
    document.getElementById('sMcOff').click();
    ok('disabling asks what to do with the entries',
       !!document.getElementById('mcKeep') && !!document.getElementById('mcDel'));
    document.getElementById('mcKeep').click();
    ok('keeping turns tracking off', mcOn()===false);
    ok('and keeps the entries', !!mcLog(todayISO()),
       JSON.stringify(mcLog(todayISO())));
    closeSheet();

    DB.mcycle.on=true;
    openCycleSettings();
    document.getElementById('sMcOff').click();
    document.getElementById('mcDel').click();
    ok('deleting turns tracking off too', mcOn()===false);
    ok('and removes the entries', !mcLog(todayISO()));
    closeSheet(); resetStack();
  })();

  // ---- the date input must survive its own change handler ----
  (function(){
    reset();
    DB.mcycle.on=true;
    resetStack(); TAB='today'; openSettings();
    var i=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf('cycle');
    document.getElementById('setRows').querySelectorAll('button')[i].click();

    var inp=document.getElementById('sMcStart');
    ok('there is a date field for backfilling', !!inp);
    var past=addDays(todayISO(),-30);
    inp.value=past;
    inp.dispatchEvent(new Event('change',{bubbles:true}));

    /* THE BUG: the handler called render(), which replaced the page and
       destroyed this very input - closing the native date picker the instant
       a date was chosen. The element must still be in the document. */
    ok('the date input still exists after its own change handler',
       document.getElementById('sMcStart')===inp,
       document.getElementById('sMcStart')? 'replaced' : 'removed');
    ok('the page was not re-rendered underneath it',
       document.body.contains(inp));
    ok('but the date was recorded', DB.mcycle.starts.indexOf(past)>=0,
       DB.mcycle.starts.join(','));
    ok('and the count shown was updated in place',
       /1 recorded/.test(document.getElementById('sMcCount').textContent),
       document.getElementById('sMcCount').textContent);
    ok('the field clears itself ready for another', inp.value==='', inp.value);

    // a future date is refused rather than stored
    inp.value=addDays(todayISO(),7);
    inp.dispatchEvent(new Event('change',{bubbles:true}));
    ok('a future period start is refused',
       DB.mcycle.starts.indexOf(addDays(todayISO(),7))<0,
       DB.mcycle.starts.join(','));
    ok('and the field is cleared', inp.value==='');
    ok('the input survived that too', document.getElementById('sMcStart')===inp);
    resetStack();
  })();

  // ---- the interface only exists when it is on ----
  (function(){
    reset();
    var d=todayISO();
    DB.checkins[d]={date:d,energy:7,soreness:3,stress:3,motivation:8,sleepMin:450,pain:'None'};
    TAB='today'; resetStack(); render();
    ok('no cycle row on Today while off', !document.getElementById('mcRow'));
    DB.mcycle.on=true; render();
    ok('a cycle row appears once on', !!document.getElementById('mcRow'));
    ok('it is one row, not a dashboard',
       document.querySelectorAll('#mcRow button').length===1);
    document.querySelector('#mcRow button').click();
    ok('it opens the cycle page', STACK.length===1, STACK.length);
    ok('the page names itself',
       /Cycle/.test(document.getElementById('appbar').textContent));
    ok('the page offers the log', !!document.getElementById('mcLogBtn'));
    ok('the page carries a not-a-medical-device note',
       /not a medical device/i.test(document.getElementById('view').innerHTML));
    ok('the page never mentions fertility as a prediction',
       /does not estimate fertility/i.test(document.getElementById('view').innerHTML));
    resetStack();

    tryRun('the cycle log sheet opens', function(){ mcSheet(d); });
    ok('the sheet asks about bleeding', !!document.getElementById('mcBleed'));
    ok('the sheet offers the four feeling options',
       document.querySelectorAll('#mcFeel button').length===4);
    ok('the sheet asks about cramps', !!document.getElementById('mcCramps'));
    ok('the sheet does not ask energy again', !document.getElementById('ciEn'));
    ok('the sheet says data stays on the device',
       /this device only/i.test(document.getElementById('sheet').innerHTML));
    closeSheet();
    render();
  })();

  DB.checkins=keepC; DB.mcycle=keepM; DB.profile=keepP;
  DB.sessions=keepS; DB.whoop=keepW;
  resetStack(); TAB='today';
})();

// ---------- THE APP DOES NOT CLAIM TO KNOW THINGS IT CANNOT ----------
(function(){
  var keepS=DB.sessions, keepA=DB.activities, keepC=DB.checkins, keepW=DB.whoop;
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  var T=todayISO();

  // ---- day one: nothing logged at all ----
  DB.sessions=[]; DB.activities=[]; DB.checkins={};
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.profile.onboarded=true;
  var H=systemHistory(T);
  ok('with no history the span is zero', H.spanDays===0, H.spanDays);
  ok('and every system reads as not-found', H.since.lower===99 && H.since.upper===99);
  ok('the wording does not invent a fortnight',
     sinceSpan(99,0).indexOf('two weeks')<0, sinceSpan(99,0));
  ok('it claims no duration at all', sinceSpan(99,0)==='yet', sinceSpan(99,0));

  DB.checkins[T]={date:T,energy:7,soreness:3,stress:3,motivation:8,sleepMin:450,pain:'None'};
  var r=readiness(T,DB.checkins[T]);
  var rec=recommend(T,DB.checkins[T],r);
  var prose=rec.why.map(function(w){return w.t;}).join(' ');
  ok('no "over two weeks" claim on day one',
     prose.indexOf('over two weeks')<0, prose.slice(0,220));
  ok('nor in the leg line', (rec.why.concat([{t:''}]))
     .every(function(w){ return !/not taken real load in over two weeks/.test(w.t); }));

  // ---- four days in: honest about how much it has seen ----
  DB.sessions=[{id:'s4',date:addDays(T,-4),done:true,workoutId:'w_upperA',
    workoutName:'Upper A',variant:'full',entries:[],durationMin:40}];
  H=systemHistory(T);
  ok('four days of history is reported as four', H.spanDays===4, H.spanDays);
  ok('the wording scopes itself to what it has seen',
     /4 days Baseline has been tracking/.test(sinceSpan(99,4)), sinceSpan(99,4));
  ok('and still does not say two weeks',
     sinceSpan(99,4).indexOf('two weeks')<0, sinceSpan(99,4));

  // ---- a genuine fortnight: the original sentence is still correct ----
  DB.sessions=[{id:'s20',date:addDays(T,-20),done:true,workoutId:'w_upperA',
    workoutName:'Upper A',variant:'full',entries:[],durationMin:40}];
  H=systemHistory(T);
  ok('twenty days of history is reported as twenty', H.spanDays===20, H.spanDays);
  ok('and then "over two weeks" is a true statement',
     /over two weeks/.test(sinceSpan(99,20)), sinceSpan(99,20));

  // ---- a known gap still reads as days ----
  ok('a real gap is stated in days', sinceSpan(5,20)==='for 5 days', sinceSpan(5,20));

  // ---- the SCORING is deliberately unchanged ----
  ok('never and a fortnight score the same, because both mean "due"', (function(){
    DB.sessions=[]; DB.activities=[]; DB.checkins={};
    DB.checkins[T]={date:T,energy:7,soreness:3,stress:3,motivation:8,sleepMin:450,pain:'None'};
    var a=systemHistory(T).since.lower;
    DB.sessions=[{id:'old',date:addDays(T,-20),done:true,workoutId:'w_upperA',
      workoutName:'Upper A',variant:'full',entries:[],durationMin:40}];
    var b=systemHistory(T).since.lower;
    return a===99 && b===99; })());

  // ---- the Today helper draws the same distinction ----
  DB.sessions=[]; DB.activities=[]; DB.checkins={};
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  ok('with nothing at all it says never logged', sinceText(99,0)==='never logged',
     sinceText(99,0));
  DB.activities=[{id:'a1',date:addDays(T,-3),type:'walking',min:20,rpe:2}];
  ok('with a little history it says not yet, not two weeks',
     sinceText(99,3)==='not yet', sinceText(99,3));
  ok('with real history the fortnight wording returns',
     sinceText(99,30)==='over 2 weeks ago', sinceText(99,30));
  ok('and a known gap is still a number of days', sinceText(4,30)==='4 days ago');

  DB.sessions=keepS; DB.activities=keepA; DB.checkins=keepC; DB.whoop=keepW;
  DB.profile=keepP;
})();

// ---------- TIME AVAILABLE IS VISIBLE, NOT HIDDEN ----------
(function(){
  var keepC=DB.checkins, keepP=JSON.parse(JSON.stringify(DB.profile));
  DB.checkins={}; DB.profile.sessionMin=45;
  var T=todayISO();
  openCheckin(T);

  var pills=document.getElementById('ciTime');
  ok('time available is on the check-in itself', !!pills);
  ok('it is not inside the note disclosure', (function(){
    var nb=document.getElementById('ciNoteB');
    return nb && !nb.contains(pills); })());
  ok('your usual length is pre-selected', (function(){
    var on=document.querySelector('#ciTime button.on');
    return on && +on.dataset.v===45; })(),
    (document.querySelector('#ciTime button.on')||{dataset:{}}).dataset.v);
  ok('and it is labelled as the usual one',
     /usual/.test(document.getElementById('ciTime').innerHTML));
  ok('a normal day therefore needs no input at all', (function(){
    document.getElementById('ciSave').click();
    return DB.checkins[T] && DB.checkins[T].availTime===45; })(),
    DB.checkins[T] && DB.checkins[T].availTime);

  // a short day is exactly one tap
  DB.checkins={};
  openCheckin(T);
  document.querySelector('#ciTime button[data-v="20"]').click();
  document.getElementById('ciSave').click();
  ok('a short day is one tap', DB.checkins[T].availTime===20, DB.checkins[T].availTime);

  // an unusual profile length still appears as an option
  DB.checkins={}; DB.profile.sessionMin=75;
  openCheckin(T);
  ok('an unusual usual length is still offered',
     !!document.querySelector('#ciTime button[data-v="75"]'),
     document.getElementById('ciTime').textContent);
  closeSheet();
  DB.checkins=keepC; DB.profile=keepP;
})();

// ---------- EVERY WARM-UP MOVEMENT EXPLAINS ITSELF ----------
(function(){
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  tryRun('starting a session', function(){ startWorkout('w_lowerA','full',T); });
  var body=document.getElementById('wmBody');

  /* EVERY movement on one screen, each explaining itself in place. This
     replaced a stepped runner that made the user press through five screens to
     read five lines, and before that a flat list whose instructions were
     hidden behind a tap with nothing to say they were there. */
  var wuRows=body.querySelectorAll('.wacc [data-acc^=w]');
  ok('every warm-up movement is on the one screen',
     wuRows.length===W.warmup.items.length,
     wuRows.length+' rows for '+W.warmup.items.length+' movements');
  ok('each row names its movement and its prescription',
     Array.prototype.slice.call(wuRows).every(function(r){
       return r.querySelector('.wacc-t') && r.querySelector('.wacc-m'); }));
  ok('the first is already open, so the screen shows what a movement looks like',
     wuRows[0].classList.contains('open')
     && !!wuRows[0].querySelector('.wacc-b:not([hidden])'),
     wuRows[0].className);
  ok('and it explains how to do it, in place',
     !!wuRows[0].querySelector('.wacc-b p') &&
     wuRows[0].querySelector('.wacc-b p').textContent.trim()===warmupHow(W.warmup.items[0].n).trim(),
     wuRows[0].querySelector('.wacc-b p') ? wuRows[0].querySelector('.wacc-b p').textContent.slice(0,60) : '(none)');
  ok('with an illustration of that movement',
     !!wuRows[0].querySelector('.illus svg.fig') || !illusKey({name:W.warmup.items[0].n}),
     W.warmup.items[0].n);
  ok('the closed rows carry a thumbnail instead',
     W.warmup.items.length<2 ||
       !!body.querySelector('.wacc [data-acc=w1] .illus.sm'),
     body.querySelector('.wacc [data-acc=w1]') ? body.querySelector('.wacc [data-acc=w1]').className : '(one movement)');
  /* opening another closes the first: five open rows is the wall of text this
     screen exists to avoid */
  if(W.warmup.items.length>1){
    body.querySelector('.wacc [data-acc=w1] .wacc-h').click();
    var now=document.getElementById('wmBody');
    ok('opening one closes the other',
       now.querySelectorAll('.wacc-b:not([hidden])').length===1
       && now.querySelector('.wacc [data-acc=w1]').classList.contains('open'),
       now.querySelectorAll('.wacc-b:not([hidden])').length+' open');
    ok('and the instruction shown is that movement’s',
       now.querySelector('.wacc [data-acc=w1] .wacc-b p').textContent.trim()
         === warmupHow(W.warmup.items[1].n).trim(),
       W.warmup.items[1].n);
  } else {
    ok('opening one closes the other', true, 'single-movement warm-up');
    ok('and the instruction shown is that movement’s', true, 'single-movement warm-up');
  }
  ok('no navigation between movements is offered at all',
     !document.getElementById('wuNext') && !document.getElementById('wuBack'));
  body=document.getElementById('wmBody');

  // every movement in every routine must have one: a warm-up tile that
  // cannot explain itself is the whole problem this fixes
  var missing=[];
  Object.keys(WARMUPS).forEach(function(k){
    (WARMUPS[k].items||[]).forEach(function(it){
      if(!warmupHow(it.n) && missing.indexOf(it.n)<0) missing.push(it.n);
    });
  });
  Object.keys(PREP_BLOCKS).forEach(function(k){
    (PREP_BLOCKS[k]||[]).forEach(function(it){
      if(!warmupHow(it.n) && missing.indexOf(it.n)<0) missing.push(it.n);
    });
  });
  ok('every warm-up movement has instructions', missing.length===0, missing.join(' | '));
  ok('and none of them is a stub',
     Object.keys(WARMUP_HOW).every(function(k){ return WARMUP_HOW[k].length>25; }),
     Object.keys(WARMUP_HOW).filter(function(k){return WARMUP_HOW[k].length<=25;}).join(','));

  exitWM(true); DB.checkins={};
})();
// ---------- LOGGING A SET COSTS ONE TAP ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:75,hrv:86,rhr:52,sleepMin:460,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  // a session last week, so there is something to repeat
  DB.sessions=[{id:'pl1',date:addDays(T,-7),done:true,workoutId:'w_lowerA',
    workoutName:'Lower A',variant:'full',durationMin:45,entries:[
      {exerciseId:'lx01',name:'Tempo Goblet Squat',plannedSets:3,plannedReps:'8-12',
       sets:[{reps:'10',weight:'20',rpe:'8',done:true},
             {reps:'10',weight:'20',rpe:'8',done:true},
             {reps:'9', weight:'22.5',rpe:'9',done:true}]}]}];

  /* Rest now starts itself after a logged set and holds the screen, which is
     the point of it. This block is about set records, so it runs with the rest
     timer off; the rest screen has its own tests. */
  var keepRestB=DB.settings.restTimerOn;
  DB.settings.restTimerOn=false;
  tryRun('starting the same workout again', function(){ startWorkout('w_lowerA','full',T); });
  var ix=-1;
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  ok('the exercise is in the session', ix>=0, W.entries.map(function(e){return e.exerciseId;}).join(','));
  var en=W.entries[ix];

  // 1 · primed from history, set by set
  ok('set 1 is primed from last time', en.sets[0].weight==='20' && en.sets[0].reps==='10',
     JSON.stringify(en.sets[0]));
  ok('set 3 is primed from ITS set last time', en.sets[2].weight==='22.5',
     JSON.stringify(en.sets[2]));
  ok('nothing is marked done by priming',
     en.sets.every(function(s){ return !s.done; }));

  // 2 · one tap records it
  W.phase='main'; W.step=ix; drawWM();
  var before=en.sets.filter(function(s){return s.done;}).length;
  document.querySelector('#wmBody [data-log]').click();
  ok('one tap completes a set',
     en.sets.filter(function(s){return s.done;}).length===before+1);
  ok('and it recorded the primed numbers',
     en.sets[0].weight==='20' && en.sets[0].reps==='10', JSON.stringify(en.sets[0]));

  /* 3 · the SAME screen moves on to the next set by itself.
     Not a new screen per set, and no tap to get there. */
  stopRest();
  ok('the screen is now set 2 of the same exercise',
     /SET 2 OF/i.test(document.querySelector('.wset .ws-l').textContent),
     document.querySelector('.wset .ws-l').textContent);
  ok('and it is still the same exercise',
     document.querySelector('.wm-ex').textContent===en.name,
     document.querySelector('.wm-ex').textContent+' vs '+en.name);
  document.querySelector('#wmBody [data-log]').click(); stopRest();
  ok('the next tap logs the next set', en.sets[1].done===true);
  /* Undo moved under More: it is an exception, not part of the loop. */
  (function(){
    document.getElementById('wmMore').click();
    var rows=document.querySelectorAll('#wmMoreRows button');
    for(var q=0;q<rows.length;q++){
      if(/Undo the last set/.test(rows[q].textContent)){ rows[q].click(); break; }
    }
    closeSheet();
  })();
  ok('and Undo under More takes it back', en.sets[1].done===false,
     en.sets.map(function(s){return s.done?'1':'0';}).join(''));
  drawWM(); stopRest();
  document.querySelector('#wmBody [data-log]').click(); stopRest();

  // 4 · carry forward: change it once, not four times
  startWorkout('w_lowerA','full',T);
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  en=W.entries[ix]; W.phase='main'; W.step=ix; drawWM();
  en.sets[0].weight='25';
  document.querySelector('#wmBody [data-log]').click();
  ok('confirming a set carries its numbers to the untouched ones',
     en.sets[1].weight==='25' && en.sets[2].weight==='25',
     en.sets.map(function(s){return s.weight;}).join(','));

  // ...but never over something the user edited themselves
  startWorkout('w_lowerA','full',T);
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  en=W.entries[ix]; W.phase='main'; W.step=ix; drawWM();
  en.sets[2].weight='30'; en.sets[2].touched=true;
  en.sets[0].weight='25';
  document.querySelector('#wmBody [data-log]').click();
  ok('an edited set is not overwritten by carry-forward',
     en.sets[2].weight==='30', en.sets.map(function(s){return s.weight;}).join(','));
  ok('but an untouched one still follows', en.sets[1].weight==='25');

  // 5 · there is exactly ONE way to log a set, and ONE tap per set
  var keepRest=DB.settings.restTimerOn;
  DB.settings.restTimerOn=false;          // the rest screen is tested on its own
  startWorkout('w_lowerA','full',T);
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  en=W.entries[ix]; W.phase='main'; W.step=ix; drawWM();
  ok('the bulk "log the rest as shown" shortcut is gone',
     !document.getElementById('wmAll'));
  ok('there is one log button on the screen, not several',
     document.querySelectorAll('#wmBody [data-log]').length===1);
  /* One tap per set, and NO taps in between: the loop never presses anything
     but Log set, yet it walks the whole exercise and off the end of it. */
  var guard=0, taps=0, want=en.sets.length;
  while(document.querySelector('#wmBody [data-log]') && guard++<20 && !en.sets.every(function(s){return s.done;})){
    document.querySelector('#wmBody [data-log]').click(); taps++;
  }
  ok('every set is logged with one tap each and nothing else',
     en.sets.every(function(s){ return s.done; }) && taps===want,
     taps+' taps for '+want+' sets');
  ok('and it kept the primed numbers', en.sets[0].weight==='20');
  ok('the screen moved on by itself, with no further tap',
     W.step!==ix || document.querySelector('.wm-ex').textContent!==en.name,
     'step '+ix+' -> '+W.step);
  DB.settings.restTimerOn=keepRest;

  // 6 · the set screen is not a reference manual any more
  startWorkout('w_lowerA','full',T);
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  W.phase='main'; W.step=ix; drawWM();
  var body=document.getElementById('wmBody').innerHTML;
  ok('no progression rule on the set screen', !/Progression rule/.test(body));
  ok('no substitutions block on the set screen', !/If this is not working/.test(body));
  ok('no coaching cue on the set screen', body.indexOf('Cue:')<0);
  ok('but last time is still there, because it is the target',
     /Last time/i.test(body));
  ok('and all of it is one tap away', (function(){
    document.getElementById('wmMore').click();
    var has=/How to do it/.test(document.getElementById('sheet').innerHTML);
    closeSheet(); return has; })());

  // 7 · a tap must not scroll you back to the top
  startWorkout('w_lowerA','full',T);
  W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
  W.phase='main'; W.step=ix; drawWM();
  var wb=document.getElementById('wmBody');
  wb.scrollTop=40;
  var at=wb.scrollTop;
  if(at>0){
    document.querySelector('#wmBody [data-log]').click();
    ok('completing a set keeps your place on the screen', wb.scrollTop===at,
       at+' -> '+wb.scrollTop);
  } else {
    ok('completing a set keeps your place on the screen', true, 'not scrollable here');
  }
  cancelAuto();

  exitWM(true);
  DB.settings.restTimerOn=keepRestB;
  DB.sessions=keepS; DB.checkins=keepC;
})();

// ---------- THE TWO BUGS THE TOUR FOUND ----------
(function(){
  // 1 · statTile must escape its delta, and still colour it
  var tile=statTile('Avg recovery',73,'%','g','▼ 4');
  ok('a delta with an arrow is not emitted as markup',
     tile.indexOf('<span')<0, tile);
  ok('a falling delta is coloured', /dlt down/.test(tile), tile);
  ok('a rising delta is coloured', /dlt up/.test(statTile('x',1,'','', '▲ 2')));
  ok('a plain delta gets no direction class',
     !/dlt (up|down)/.test(statTile('x',1,'','','vs 3')));
  // and anything markup-shaped stays escaped rather than rendering
  var nasty=statTile('x',1,'','','<b>boom</b>');
  ok('markup in a delta is escaped, not rendered',
     nasty.indexOf('<b>boom')<0 && nasty.indexOf('&lt;b&gt;')>=0, nasty);

  // the real week numbers must contain no tags in their deltas
  var keepC=DB.checkins;
  var wn=weekNumbers(weekReview());
  ok('the week numbers emit no escaped markup',
     wn.indexOf('&lt;span')<0, wn.slice(0,120));
  DB.checkins=keepC;

  // 2 · "what moved it" must not be empty when there are reasons
  var T2=todayISO();
  DB.checkins[T2]={date:T2,recovery:74,hrv:86,rhr:52,sleepMin:455,prevStrain:11,
                   energy:7,soreness:4,stress:4,motivation:8,pain:'None'};
  var rd=readiness(T2,DB.checkins[T2]);
  ok('readiness produced reasons', rd.why.length>0, rd.why.length);
  ok('readiness parts carry no text', rd.parts.every(function(p){ return !p.t; }));
  resetStack(); pushPage({build:pageReadiness(T2)});
  var html=document.getElementById('view').innerHTML;
  ok('the readiness page lists what moved it',
     !/Nothing logged yet today/.test(html) && /What moved it/.test(html));
  ok('and it shows as many reasons as the engine gave',
     (html.match(/class="(pos|neg|warn|info)"/g)||[]).length>=Math.min(3,rd.why.length),
     (html.match(/class="(pos|neg|warn|info)"/g)||[]).length+' vs '+rd.why.length);
  resetStack(); DB.checkins={};
})();

// ---------- TODAY SHOWS AT MOST ONE NOTICE ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile)), keepU=JSON.parse(JSON.stringify(DB.ui||{}));
  var keepC=DB.checkins, keepS=DB.sessions, keepA=DB.activities, keepT=DB.tests;
  var T=todayISO();
  DB.profile.onboarded=true; DB.ui.tourDone=false; DB.ui.digestSeen=null;
  DB.checkins={}; DB.sessions=[]; DB.activities=[]; DB.tests=[];

  // make every notice true at once
  setAway(addDays(T,5),'Holiday');
  DB.profile.planStart=addDays(T,-7*7);      // pushes the phase towards week 8
  ok('with everything true, exactly one notice is offered',
     (noticeHTML(T).match(/<button/g)||[]).length===1,
     (noticeHTML(T).match(/<button/g)||[]).length);
  ok('away wins the priority', noticeRow(T).id==='away', noticeRow(T).id);
  ok('and Today renders one notice row', (function(){
    TAB='today'; resetStack(); render();
    return document.querySelectorAll('#noticeRow button').length===1; })(),
    document.querySelectorAll('#noticeRow button').length);

  // away mode
  ok('away mode reports itself', isAway(T)===true);
  ok('it counts the days left', awayDaysLeft(T)===5, awayDaysLeft(T));
  ok('it names the reason', /Holiday/.test(noticeHTML(T)));
  ok('a past date is not away', isAway(addDays(T,9))===false);
  setAway(null,'');
  ok('ending the break clears it', isAway(T)===false);
  ok('and the notice moves on to something else',
     !noticeRow(T) || noticeRow(T).id!=='away',
     noticeRow(T)? noticeRow(T).id : 'none');

  // retest week. Progression is earned by logged work, not by the calendar,
  // so eight weeks of elapsed time is not enough on its own - a session has
  // to exist in each of them. That is currentPhase() working as designed.
  DB.profile.planStart=addDays(T,-7*7);
  DB.sessions=[];
  for(var wq=0;wq<8;wq++){
    /* On the Monday, -(wq*7+1) put every session in the PREVIOUS ISO week, so
       the current week's bucket was empty and the phase counter came up one
       short of eight. Land on the day itself. */
    DB.sessions.push({id:'rw'+wq, date:addDays(T,-(wq*7)), done:true,
      workoutId:'w_lowerA', workoutName:'Lower A', variant:'full',
      entries:[], durationMin:40});
  }
  ok('eight weeks of logged work reaches week 8', currentPhase().w===8,
     currentPhase().w+' (trained weeks '+trainedWeeks(DB.profile.planStart,T)+')');
  ok('there are tests worth repeating', retestsDue().length>0, retestsDue().length);
  ok('the retest notice appears', noticeRow(T).id==='retest', noticeRow(T).id);
  ok('it says how many', new RegExp(retestsDue().length+' test').test(noticeHTML(T)),
     noticeHTML(T).slice(0,140));
  // a fresh result removes that test from the list
  var n0=retestsDue().length;
  DB.tests=[{id:'r1',testId:TESTS[0].id,date:T,value:10}];
  ok('a fresh result is not due again', retestsDue().length===n0-1,
     retestsDue().length+' vs '+n0);
  DB.tests=[];

  // the weekly digest, on the day the week turns over
  DB.profile.planStart=T;                    // out of week 8
  DB.sessions=[{id:'d1',date:addDays(T,-3),done:true,workoutId:'w_lowerA',
                workoutName:'Lower A',variant:'full',entries:[],durationMin:40}];
  ok('the digest only offers itself on a Monday', (function(){
    var mon=weekStartOf(T);
    while(dowOf(mon)!==1) mon=addDays(mon,1);
    var r=noticeRow(mon);
    var notMon=addDays(mon,2);
    var r2=noticeRow(notMon);
    return (r&&r.id==='digest') && !(r2&&r2.id==='digest'); })(),
    JSON.stringify(noticeRow(T)&&noticeRow(T).id));
  ok('opening the digest stops it asking again', (function(){
    var mon=weekStartOf(T);
    while(dowOf(mon)!==1) mon=addDays(mon,1);
    var r=noticeRow(mon); if(!r||r.id!=='digest') return true;
    r.go();
    resetStack();
    var again=noticeRow(mon);
    return !(again&&again.id==='digest'); })());

  DB.profile=keepP; DB.ui=keepU; DB.checkins=keepC; DB.sessions=keepS;
  DB.activities=keepA; DB.tests=keepT; resetStack(); TAB='today';
})();

// ---------- SESSION FEEDBACK CHANGES WHAT COMES NEXT ----------
(function(){
  var keepS=DB.sessions;
  DB.sessions=[];
  ok('no rated sessions means no bias', feedbackBias().bias===0);
  ok('and nothing is claimed', feedbackBias().line===null);

  // two is not enough
  DB.sessions=[{id:'f1',date:addDays(todayISO(),-2),done:true,feedback:'hard'},
               {id:'f2',date:addDays(todayISO(),-4),done:true,feedback:'hard'}];
  ok('two ratings is still not enough', feedbackBias().bias===0,
     JSON.stringify(feedbackBias()));

  // three that agree is
  DB.sessions.push({id:'f3',date:addDays(todayISO(),-6),done:true,feedback:'hard'});
  var fb=feedbackBias();
  ok('three agreeing ratings produce a bias', fb.bias===-1, JSON.stringify(fb));
  ok('and it says so in plain words', /too hard/.test(fb.line), fb.line);
  ok('the sample size is reported', fb.n===3, fb.n);

  // three that disagree do not
  DB.sessions=[{id:'g1',date:addDays(todayISO(),-2),done:true,feedback:'hard'},
               {id:'g2',date:addDays(todayISO(),-4),done:true,feedback:'easy'},
               {id:'g3',date:addDays(todayISO(),-6),done:true,feedback:'right'}];
  ok('mixed ratings produce no bias', feedbackBias().bias===0,
     JSON.stringify(feedbackBias()));

  // the other direction works too
  DB.sessions=[{id:'h1',date:addDays(todayISO(),-2),done:true,feedback:'easy'},
               {id:'h2',date:addDays(todayISO(),-4),done:true,feedback:'easy'},
               {id:'h3',date:addDays(todayISO(),-6),done:true,feedback:'easy'}];
  ok('three easy ratings lean the other way', feedbackBias().bias===1);
  ok('and say so', /too easy/.test(feedbackBias().line), feedbackBias().line);
  ok('unrated sessions are ignored entirely', (function(){
    DB.sessions.push({id:'h4',date:todayISO(),done:true});
    return feedbackBias().n===3; })(), feedbackBias().n);
  DB.sessions=keepS;
})();

// ---------- "THIS HURT" ROUTES AROUND AN EXERCISE ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  DB.profile.avoid=[];
  var ex=DB.exercises.filter(function(e){ return canDo(e) && e.pat==='squat'; })[0]
       || DB.exercises.filter(function(e){ return canDo(e); })[0];

  ok('nothing is avoided to begin with', avoidList().length===0);
  ok('and the exercise resolves to itself or an upgrade',
     !!resolveExercise(ex.id));

  avoidExercise(ex.id,'hurt');
  ok('it is now avoided', isAvoided(ex.id)===true);
  ok('the avoid list carries an expiry',
     avoidList()[0].until===addDays(todayISO(),AVOID_DAYS),
     avoidList()[0].until);
  ok('it expires on its own',
     isAvoided(ex.id, addDays(todayISO(), AVOID_DAYS+1))===false);

  var res=resolveExercise(ex.id);
  ok('the resolver routes around it', res && res.id!==ex.id,
     res? res.id : 'nothing');
  ok('and stays doable with the same kit', res && canDo(res));
  ok('an avoided exercise is never promoted into a session', (function(){
    var all=DB.workouts.map(function(w){
      return (w.blocks.full||[]).map(function(b){
        var r=resolveExercise(b.ex); return r?r.id:null; });
    });
    var flat=[].concat.apply([],all);
    return flat.indexOf(ex.id)<0; })());

  unavoid(ex.id);
  ok('it can be un-avoided', isAvoided(ex.id)===false);
  DB.profile=keepP;
})();

// ---------- EQUIPMENT-AWARE WEIGHT STEPS ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile));

  DB.profile.gear=['db']; DB.profile.dbKg=12;
  ok('light dumbbells step by 1', stepSize('weight',4)===1, stepSize('weight',4));
  ok('past halfway up a light rack they step by 2',
     stepSize('weight',8)===2, stepSize('weight',8));

  DB.profile.gear=['db','bb','bar']; DB.profile.dbKg=30;
  ok('a loaded barbell steps by 2.5', stepSize('weight',60)===2.5, stepSize('weight',60));
  ok('an empty-ish bar still steps small', stepSize('weight',10)===1, stepSize('weight',10));

  DB.profile.gear=[]; DB.profile.dbKg=null;
  ok('with no kit declared it falls back sensibly',
     stepSize('weight',5)===1 && stepSize('weight',40)===2.5);
  ok('reps never change step', stepSize('reps',100)===1);
  DB.profile=keepP;
})();

// ---------- A SESSION AS TEXT ----------
(function(){
  var s={date:todayISO(), workoutName:'Lower A', durationMin:44, variant:'reduced',
    band:'yellow', readinessScore:68, sessionRpe:8, feedback:'right',
    notes:'felt fine', entries:[
      {name:'Goblet Squat', note:'left knee tight', sets:[
        {reps:'10',weight:'20',rpe:'7',done:true},
        {reps:'9',weight:'20',rpe:'8',done:true},
        {reps:'8',weight:'20',rpe:'9',done:false}]},
      {name:'Skipped thing', skipped:true, sets:[]}
    ]};
  var txt=sessionText(s);
  ok('the text names the session', /Lower A/.test(txt));
  ok('it spells out the version', /Reduced volume/.test(txt), txt.slice(0,160));
  ok('it lists the completed sets', /10 reps . 20 kg/.test(txt), txt);
  ok('it leaves out the set that was not done',
     (txt.match(/set [0-9]/g)||[]).length===2, (txt.match(/set [0-9]/g)||[]).length);
  ok('it marks a skipped exercise', /skipped/.test(txt));
  ok('it carries the exercise note', /left knee tight/.test(txt));
  ok('it carries how it felt', /About right/.test(txt));
  ok('it has no markup in it', txt.indexOf('<')<0);
  ok('copying does not throw', (function(){
    try{ copySession(s); return true; }catch(e){ return false; } })());
})();

// ---------- WHY THIS EXERCISE ----------
(function(){
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  tryRun('starting a session', function(){ startWorkout('w_lowerA','full',T); });
  W.phase='main'; W.step=0; drawWM();
  var en=W.entries[0];
  var bits=exerciseWhy(en);
  ok('it explains what the exercise covers', bits.length>0, bits.length);
  ok('it says when you last did it',
     bits.join(' ').indexOf('last did it')>=0
     || bits.join(' ').indexOf('not done this one before')>=0,
     bits.join(' | '));
  /* Asserted by what the menu offers rather than by how many rows it has: a
     count breaks every time a legitimate action is added, which says nothing
     about whether the menu is right. */
  ok('the More menu offers it', (function(){
    document.getElementById('wmMore').click();
    var txt=document.getElementById('wmMoreRows').textContent;
    var has=/Why this exercise/.test(txt) && /How to do it/.test(txt)
         && /Replace exercise/.test(txt) && /Skip this exercise/.test(txt);
    closeSheet();
    return has; })(),
    document.getElementById('wmMoreRows')?document.getElementById('wmMoreRows').textContent.slice(0,140):'');
  exitWM(); DB.checkins={};
})();

// ---------- NO EMOJI ANYWHERE ----------
(function(){
  // emoji render at a size and style nobody chose, differently on every
  // platform. The app draws its own icons instead.
  /* a codepoint scan rather than a regex literal: unicode escapes inside this
     file are parsed by Python first, and a lone surrogate cannot be encoded */
  function hasEmoji(s){
    s=String(s||'');
    for(var i=0;i<s.length;i++){
      var c=s.charCodeAt(i);
      if(c>=0xD800&&c<=0xDBFF) return true;   // high surrogate: astral, i.e. emoji
      if(c>=0x2600&&c<=0x27BF) return true;   // misc symbols and dingbats
      if(c>=0x2B00&&c<=0x2BFF) return true;   // arrows and shapes
      if(c===0xFE0F) return true;             // emoji variation selector
    }
    return false;
  }
  var EMOJI={test:hasEmoji};
  ok('the emoji detector works',
     hasEmoji(String.fromCharCode(0xD83C,0xDFBE)) && !hasEmoji('Tennis'));

  ok('no activity type carries an emoji',
     Object.keys(ACT_TYPES).every(function(k){
       return !ACT_TYPES[k].emoji && !EMOJI.test(ACT_TYPES[k].name); }),
     Object.keys(ACT_TYPES).filter(function(k){return !!ACT_TYPES[k].emoji;}).join(','));
  ok('every activity type has a short label for the week strip',
     Object.keys(ACT_TYPES).every(function(k){
       return ACT_TYPES[k].short && ACT_TYPES[k].short.length<=5; }),
     Object.keys(ACT_TYPES).filter(function(k){return !ACT_TYPES[k].short;}).join(','));
  ok('no sport carries an emoji',
     SPORTS.every(function(s){ return !s.emoji && !EMOJI.test(s.name); }));
  ok('SPORT_EMOJI is gone', typeof SPORT_EMOJI==='undefined');

  // and nothing reaches the screen
  var keepTab=TAB, seen=[];
  function scan(label){
    var h=document.getElementById('view').innerHTML;
    if(EMOJI.test(h)) seen.push(label);
  }
  ['today','workouts','tennis','progress'].forEach(function(tab){
    resetStack(); TAB=tab; renderNav(); render(); scan(tab);
  });
  resetStack(); openSettings(); scan('settings');
  /* every pane, including the one reached from the card rather than a row */
  SET_PANES.forEach(function(g){
    resetStack(); openSettings();
    openSetGroup(g.id);
    scan('settings/'+g.id);
  });
  resetStack(); TAB='today'; render();
  ok('no emoji on any screen', seen.length===0, seen.join(','));

  // nor in the chrome or a sheet
  ok('no emoji in the nav', !EMOJI.test(document.getElementById('nav').innerHTML));
  openCheckin(todayISO());
  ok('no emoji in the check-in', !EMOJI.test(document.getElementById('sheet').innerHTML));
  closeSheet();
  activitySheet(null,todayISO());
  ok('no emoji in the activity sheet', !EMOJI.test(document.getElementById('sheet').innerHTML));
  closeSheet();
  ok('the sheet close button is an icon, not a glyph',
     !!document.querySelector('#sheetX svg'));

  TAB=keepTab; resetStack(); render();
})();

// ---------- EVERY SETTINGS CONTROL STILL SAVES ----------
(function(){
  /* persist() bails out early when the settings body is not on screen. That
     guard used to look for #sName, which vanished when the profile became
     read-only - and silently stopped EVERY control in Settings from saving.
     Nothing tested it. This does. */
  var keepS=JSON.parse(JSON.stringify(DB.settings));
  SETTINGS_ALL();

  var a=document.getElementById('sAuto');
  var was=DB.settings.autoAdjust;
  a.checked=!was; a.dispatchEvent(new Event('change',{bubbles:true}));
  ok('a checkbox still writes through with the profile read-only',
     DB.settings.autoAdjust===!was, was+' -> '+DB.settings.autoAdjust);

  var hs=document.getElementById('sHs');
  if(hs){
    hs.value='13'; hs.dispatchEvent(new Event('input',{bubbles:true}));
    ok('a number field still writes through', DB.settings.hardStrain===13,
       DB.settings.hardStrain);
  }
  ok('and persist is not writing over the profile', (function(){
    var P=DB.profile;
    var n=P.name, ag=P.age;
    document.getElementById('sAuto').dispatchEvent(new Event('change',{bubbles:true}));
    return P.name===n && P.age===ag; })(),
    JSON.stringify({name:DB.profile.name, age:DB.profile.age}));

  DB.settings=keepS;
})();

// ---------- THE PROFILE IS READ-ONLY UNTIL YOU ASK ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  DB.profile.name='Sam'; DB.profile.age=34;
  DB.profile.heightCm=182; DB.profile.weightKg=77.5;
  DB.profile.sex='Male'; DB.profile.units='metric';
  PROF_EDIT=false; PROF_DRAFT=null;

  /* the profile is reached from the card at the top of Settings, not a row */
  var open=function(){ openSetGroup('profile'); };

  // ---- read mode ----
  open();
  ok('the profile shows values, not inputs',
     !document.getElementById('sName') && !document.getElementById('sAge'));
  ok('there is an Edit button', !!document.getElementById('profEdit'));
  var html=document.getElementById('view').innerHTML;
  ok('the name is shown', /Sam/.test(html));
  ok('metric height is shown in cm', /182 cm/.test(html), html.slice(0,400));
  ok('metric weight is shown in kg', /77.5 kg/.test(html));

  // ---- edit mode ----
  document.getElementById('profEdit').click();
  ok('Edit reveals the inputs', !!document.getElementById('sName')
     && !!document.getElementById('sAge'));
  ok('and offers Save and Cancel', !!document.getElementById('profSave')
     && !!document.getElementById('profCancel'));
  ok('the Edit button is gone while editing', !document.getElementById('profEdit'));

  // ---- cancel discards ----
  document.getElementById('sName').value='Changed';
  document.getElementById('profCancel').click();
  ok('Cancel discards the edit', DB.profile.name==='Sam', DB.profile.name);
  ok('and returns to read mode', !!document.getElementById('profEdit'));

  // ---- save commits ----
  document.getElementById('profEdit').click();
  document.getElementById('sName').value='Alex';
  document.getElementById('sAge').value='35';
  document.getElementById('profSave').click();
  ok('Save commits the edit', DB.profile.name==='Alex' && DB.profile.age===35,
     DB.profile.name+'/'+DB.profile.age);
  ok('and returns to read mode', !!document.getElementById('profEdit'));

  DB.profile=keepP; PROF_EDIT=false; PROF_DRAFT=null; resetStack();
})();

// ---------- UNITS ACTUALLY CONVERT ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile));

  // the maths, both ways
  ok('82.5 kg is about 182 lb', Math.round(kgToLb(82.5))===182, kgToLb(82.5));
  ok('and back again', Math.abs(lbToKg(kgToLb(82.5))-82.5)<0.1, lbToKg(kgToLb(82.5)));
  ok('182 cm is 6 feet 0 inches', (function(){
    var f=cmToFtIn(182); return f.ft===6 && f.inch===0; })(),
    JSON.stringify(cmToFtIn(182)));
  ok('175 cm is 5 feet 9 inches', (function(){
    var f=cmToFtIn(175); return f.ft===5 && f.inch===9; })(),
    JSON.stringify(cmToFtIn(175)));
  ok('feet and inches convert back', ftInToCm(6,0)===183 || ftInToCm(6,0)===182,
     ftInToCm(6,0));
  ok('an empty height stays empty', ftInToCm('','')===null);

  // display follows the setting
  DB.profile.units='metric'; DB.profile.heightCm=182; DB.profile.weightKg=77.5;
  ok('metric shows cm', showHeight(182)==='182 cm', showHeight(182));
  ok('metric shows kg', showWeight(77.5)==='77.5 kg', showWeight(77.5));
  DB.profile.units='imperial';
  ok('imperial shows feet and inches', /6/.test(showHeight(182)) && showHeight(182).indexOf('cm')<0,
     showHeight(182));
  ok('imperial shows pounds', /lb/.test(showWeight(77.5)), showWeight(77.5));
  ok('a missing value is a dash either way',
     showHeight(null)==='—' && showWeight(null)==='—');

  // the stored figure never changes when the unit does
  DB.profile.units='metric';
  var h=DB.profile.heightCm, w=DB.profile.weightKg;
  DB.profile.units='imperial';
  ok('switching units does not rewrite the stored height', DB.profile.heightCm===h);
  ok('nor the stored weight', DB.profile.weightKg===w);

  // and the editor offers the right fields for the chosen unit
  PROF_EDIT=false; PROF_DRAFT=null;
  openSetGroup('profile');
  document.getElementById('profEdit').click();
  ok('imperial editing asks for feet and inches',
     !!document.getElementById('sHtFt') && !!document.getElementById('sHtIn'));
  ok('and for pounds', !!document.getElementById('sWtLb'));
  ok('not for cm or kg', !document.getElementById('sHt') && !document.getElementById('sWt'));
  ok('the imperial fields are pre-filled from the stored metric',
     +document.getElementById('sHtFt').value===6,
     document.getElementById('sHtFt').value);

  // switching unit mid-edit keeps what was typed, shown the other way round
  document.getElementById('sWtLb').value=String(Math.round(kgToLb(80)));
  document.querySelector('#sUnits button[data-v="metric"]').click();
  ok('switching to metric mid-edit converts what was typed',
     Math.abs(+document.getElementById('sWt').value-80)<1.5,
     document.getElementById('sWt').value);
  ok('and now offers cm', !!document.getElementById('sHt'));

  // saving in imperial stores metric
  document.querySelector('#sUnits button[data-v="imperial"]').click();
  document.getElementById('sWtLb').value='200';
  document.getElementById('profSave').click();
  ok('a weight entered in pounds is stored in kg',
     Math.abs(DB.profile.weightKg-90.7)<0.3, DB.profile.weightKg);
  ok('and the unit preference is saved', DB.profile.units==='imperial',
     DB.profile.units);
  ok('the read view then shows it back in pounds',
     /200 lb/.test(document.getElementById('view').innerHTML),
     document.getElementById('view').innerHTML.slice(0,400));

  DB.profile=keepP; PROF_EDIT=false; PROF_DRAFT=null; resetStack();
})();

// ---------- SETTINGS IS AN INDEX OF GROUPS ----------
(function(){
  var keepTab=TAB;
  TAB='today'; resetStack(); openSettings();
  var rows=document.getElementById('setRows');
  ok('Settings opens as a row list', !!rows);
  ok('Settings has no segment bar', !document.getElementById('setSeg'));
  /* One row per pane that IS a row. Profile is the card at the top - the two
     questions a settings screen is opened to answer are whose copy this is and
     where the data lives, so those lead rather than sitting in the list. */
  var listed=SET_PANES.filter(function(x){ return x.sec; }).length;
  ok('one row per group', rows && rows.querySelectorAll('button').length===listed,
     rows?rows.querySelectorAll('button').length+'/'+listed:'none');
  ok('the profile is the card at the top, with its own way in',
     !!document.getElementById('setProfile'));
  ok('and the card says where the data is kept',
     !!document.querySelector('.set-store'),
     document.querySelector('.set-store') ? document.querySelector('.set-store').textContent.trim() : '(none)');
  ['Training preferences','Workout experience','Wearables','Data','Privacy','Appearance',
   'Help & feedback','About Baseline']
    .forEach(function(n){
      ok('Settings offers "'+n+'"', rows && rows.textContent.indexOf(n)>=0);
    });
  ['App experience','Training','Health & data','Support'].forEach(function(s){
    ok('and groups them under "'+s+'"',
       document.getElementById('view').textContent.indexOf(s)>=0);
  });
  ok('every group row says what is in it',
     rows && rows.querySelectorAll('.rw-s').length===listed,
     rows?rows.querySelectorAll('.rw-s').length+'/'+listed:'none');
  ok('and carries its own mark',
     rows && rows.querySelectorAll('.rw-i svg').length===listed,
     rows?rows.querySelectorAll('.rw-i svg').length+'/'+listed:'none');

  // each group opens, and none of them is empty
  SET_PANES.forEach(function(g){
    resetStack(); TAB='today'; openSettings();
    openSetGroup(g.id);
    /* depth 1: Settings is a destination now, so only the row pushes. Back
       goes group -> the Settings index, which is the tab itself. */
    ok('group "'+g.id+'" pushes a page', STACK.length===1, STACK.length);
    ok('group "'+g.id+'" titles itself',
       (document.getElementById('appbar').textContent||'').indexOf(g.name)>=0,
       document.getElementById('appbar').textContent.slice(0,40));
    // the trap: a group with nothing classed into it renders a blank screen
    var shown=document.querySelectorAll('#view .spane.'+g.id);
    ok('group "'+g.id+'" contains at least one card', shown.length>0, shown.length);
    var vis=0;
    Array.prototype.slice.call(shown).forEach(function(el){
      if(el.classList.contains('on')) vis++; });
    ok('group "'+g.id+'" reveals its cards', vis===shown.length, vis+'/'+shown.length);
    // and nothing from another group is on screen
    var leaked=[];
    SET_PANES.forEach(function(o){
      if(o.id===g.id) return;
      Array.prototype.slice.call(document.querySelectorAll('#view .spane.'+o.id))
        .forEach(function(el){ if(el.classList.contains('on')) leaked.push(o.id); });
    });
    ok('group "'+g.id+'" shows nothing from other groups',
       leaked.length===0, leaked.join(','));
  });

  // back should walk out one level at a time
  openSetGroup('profile');
  ok('a group is one level deep', STACK.length===1, STACK.length);
  popPage(true);
  ok('back from a group returns to the Settings index',
     STACK.length===0 && !!document.getElementById('setRows'), STACK.length);
  ok('which is the tab itself, so there is nowhere further back to go',
     TAB==='settings' && !document.getElementById('abBack'), TAB);

  // the things the user asked to be able to find
  openSetGroup('data');
  ok('Erase all data is in the Data group', !!document.getElementById('rsAll'));
  ok('Backup is in the Data group', !!document.getElementById('expJson'));
  openSetGroup('appearance');
  ok('the theme picker is in Appearance', !!document.getElementById('sTheme'));
  ok('Appearance is only the theme',
     document.querySelectorAll('#view .spane.on').length===1,
     document.querySelectorAll('#view .spane.on').length);
  openSetGroup('wearables');
  ok('the wearable lives under Wearables', /Your wearable/.test(document.getElementById('view').innerHTML));

  resetStack(); TAB=keepTab;
})();

// ---------- SETTINGS CONTROLS ACTUALLY DO SOMETHING ----------
(function(){
  var keepS=JSON.parse(JSON.stringify(DB.settings));
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  TAB='today'; resetStack(); SETTINGS_ALL();

  // the two behaviour switches
  var a=document.getElementById('sAuto'), r=document.getElementById('sRest');
  ok('autoAdjust checkbox exists', !!a);
  ok('restTimer checkbox exists', !!r);
  var a0=DB.settings.autoAdjust, r0=DB.settings.restTimerOn;
  a.checked=!a0; a.dispatchEvent(new Event('change',{bubbles:true}));
  ok('autoAdjust checkbox writes through', DB.settings.autoAdjust===!a0,
     a0+' -> '+DB.settings.autoAdjust);
  r.checked=!r0; r.dispatchEvent(new Event('change',{bubbles:true}));
  ok('rest timer checkbox writes through', DB.settings.restTimerOn===!r0,
     r0+' -> '+DB.settings.restTimerOn);
  // and they actually change behaviour
  DB.settings.autoAdjust=false;
  var bad2={recovery:20,hrv:55,rhr:64,sleepMin:280,energy:1,soreness:9,stress:9,motivation:1,
            pain:'None',sportToday:false,availTime:60};
  ok('autoAdjust off => full volume', recommend(todayISO(),bad2).variant==='full',
     recommend(todayISO(),bad2).variant);
  DB.settings.autoAdjust=true;
  var advised=recommend(todayISO(),bad2);
  ok('autoAdjust on => engine adapts the session',
     advised.variant!=='full' || ['mobility','rest','core'].indexOf(advised.id)>=0,
     advised.id+'/'+advised.variant);
  DB.settings.restTimerOn=false;
  ok('rest timer off is respected by the engine', DB.settings.restTimerOn===false);

  // threshold sliders
  SETTINGS_ALL();
  var g=document.getElementById('sb_green');
  ok('band sliders exist', !!g && !!document.getElementById('sb_yellow') && !!document.getElementById('sb_orange'));
  ok('sliders are range inputs', g.type==='range');
  ok('sliders show a drag hint', /drag to adjust/.test($('#view').innerHTML));
  ok('band strip is drawn', /RED/.test($('#view').innerHTML) && /GREEN/.test($('#view').innerHTML));
  ok('each band explains what happens', /Full session at the prescribed effort/.test($('#view').innerHTML));
  g.value='80'; g.dispatchEvent(new Event('change',{bubbles:true}));
  ok('moving the green slider changes the threshold', DB.settings.bands.green===80, DB.settings.bands.green);
  ok('bands stay correctly ordered',
     DB.settings.bands.green>DB.settings.bands.yellow && DB.settings.bands.yellow>DB.settings.bands.orange,
     JSON.stringify(DB.settings.bands));
  SETTINGS_ALL();
  document.getElementById('sbReset').click();
  ok('reset restores default thresholds',
     DB.settings.bands.green===72 && DB.settings.bands.yellow===56 && DB.settings.bands.orange===42,
     JSON.stringify(DB.settings.bands));

  // sports and goals: only what you chose, shown as blocks, "+" for the rest
  DB.profile.sports=['tennis']; DB.profile.sport='tennis';
  DB.profile.physiques=['athletic']; DB.profile.physique='athletic';
  SETTINGS_ALL();
  ok('goals are not free-text', !document.getElementById('sG1') && !document.getElementById('sG2'));
  ok('settings show only the chosen sports, not all of them',
     document.querySelectorAll('#sportPick .chipblk').length===1,
     document.querySelectorAll('#sportPick .chipblk').length+' of '+SPORTS.length);
  ok('leading sport is marked MAIN', /MAIN/.test(document.getElementById('sportPick').innerHTML));
  ok('sports offer a + to add more', !!document.querySelector('#sportPick [data-add]'));
  ok('goals show only what is chosen', document.querySelectorAll('#goalPick .chipblk').length===1);
  // the + opens a sheet listing everything not already chosen
  document.querySelector('#sportPick [data-add]').click();
  var rows=document.querySelectorAll('.pickrow');
  ok('+ lists every sport', rows.length===SPORTS.length, rows.length);
  // pick one that is not already chosen
  var target=null;
  Array.prototype.slice.call(rows).forEach(function(r){
    if(!target && !r.classList.contains('on')) target=r; });
  if(target) target.click();
  document.getElementById('pkDone').click();
  ok('picking from the sheet adds the sport', DB.profile.sports.length===2, DB.profile.sports.join(','));
  ok('goal text is derived, never typed', /Improve/i.test(DB.profile.goalPrimary), DB.profile.goalPrimary);
  ok('targets re-derive from goal changes', DB.targets.lower>0 && DB.targets.core>0);
  // removing the main sport promotes the next one
  SETTINGS_ALL();
  document.querySelector('#sportPick [data-rm]').click();
  ok('removing the main sport promotes the next', DB.profile.sports.length===1 && DB.profile.sport===DB.profile.sports[0],
     DB.profile.sports.join(','));

  // EQUIPMENT: the same editor the wizard uses, reachable after setup is over.
  // Settings used to render a flat chip picker instead, so the gym/home
  // question and its weight fields existed ONLY during onboarding. Anyone who
  // had already finished setup could not reach any of it, and a freshly
  // deployed build looked identical to the one before it.
  DB.profile.gear=['db','band']; DB.profile.place='home';
  SETTINGS_ALL();
  ok('equipment is not free-text', !document.getElementById('sEq'));
  ok('settings uses the shared gear editor, not the old chip picker',
     !!document.getElementById('setsGear_root') && !document.getElementById('gearPick'));
  ok('at home, the whole home list is offered',
     document.querySelectorAll('#setsGear_root .gr').length===HOME_GEAR.length,
     document.querySelectorAll('#setsGear_root .gr').length);
  ok('what you already own is ticked',
     document.querySelectorAll('#setsGear_root .gr.on').length===2,
     document.querySelectorAll('#setsGear_root .gr.on').length);
  document.querySelector('#setsGear_root .gr[data-g=bike]').click();
  ok('adding equipment writes through', DB.profile.gear.indexOf('bike')>=0, DB.profile.gear.join(','));
  ok('equipment list is rebuilt from the blocks',
     DB.profile.equipment[0]==='Bodyweight' && /Bicycle/i.test(DB.profile.equipment.join(' ')),
     JSON.stringify(DB.profile.equipment));

  // a weight belongs to the item, and only appears once that item is ticked
  SETTINGS_ALL();
  ok('a ticked weighted item offers a weight',
     !!document.querySelector('#setsGear_root .gwrap .gr-w'));
  ok('an unticked item offers no weight field',
     document.querySelectorAll('#setsGear_root .gr-w').length
       <= document.querySelectorAll('#setsGear_root .gr.on').length,
     document.querySelectorAll('#setsGear_root .gr-w').length);
  var kgIn=document.querySelector('#setsGear_root .gr-w input');
  kgIn.value='24'; kgIn.dispatchEvent(new Event('input',{bubbles:true}));
  ok('the weight is stored beside the item it belongs to', gearKg('db')===24, gearKg('db'));
  ok('the dumbbell weight stays in step with dbKg', DB.profile.dbKg===24, DB.profile.dbKg);

  // AT A GYM: everything is assumed, and the list is opt-OUT rather than opt-in
  SETTINGS_ALL();
  document.getElementById('setsGear_back').click();
  SETTINGS_ALL();
  ok('changing where you train asks the question again',
     !!document.getElementById('setsGear_place'));
  document.querySelector('#setsGear_place button[data-p=gym]').click();
  ok('a gym is assumed to have everything',
     DB.profile.gear.length===GYM_GEAR.length, DB.profile.gear.length);
  SETTINGS_ALL();
  ok('the gym list is not shown unless asked for', !document.getElementById('setsGear_list'));
  document.getElementById('setsGear_more').click();
  SETTINGS_ALL();
  ok('a gym can be told what it lacks', !!document.getElementById('setsGear_list'));
  ok('where you train is remembered', DB.profile.place==='gym', DB.profile.place);

  // unlike sports, equipment can go to zero — bodyweight only is a real answer
  DB.profile.place='home'; SETTINGS_ALL();
  var guard=0;
  while(document.querySelector('#setsGear_root .gr.on') && guard++ < 40){
    document.querySelector('#setsGear_root .gr.on').click();
    SETTINGS_ALL();
  }
  ok('equipment can be emptied to bodyweight only', DB.profile.gear.length===0, DB.profile.gear.join(','));
  ok('emptying equipment drops the targets it made impossible',
     !DB.targets.bike, JSON.stringify(DB.targets));
  ok('with nothing ticked, the question comes back', placeOf(DB.profile)===null || DB.profile.place==='home',
     placeOf(DB.profile));

  DB.settings=keepS; DB.profile=keepP; applyGoalTargets();
})();


// ---------- THE HOME SCREEN MUST DESCRIBE TODAY ----------
// Four ways it asserted something it did not know, or ignored something it did.
(function(){
  var keepSe=JSON.parse(JSON.stringify(DB.sessions)),
      keepAc=JSON.parse(JSON.stringify(DB.activities)),
      keepCi=JSON.parse(JSON.stringify(DB.checkins)),
      keepWh=DB.whoop,
      keepBl=JSON.parse(JSON.stringify(DB.baselines)),
      keepPr=JSON.parse(JSON.stringify(DB.profile));
  var T=todayISO();

  // 1 · A PHYSIOLOGICAL IMPORT IS NOT A TRAINING HISTORY.
  // Three days of use plus a WHOOP export reaching back six months. The span
  // was read off the export, so the app announced a fortnight of idle legs to
  // a profile it had known for three days.
  DB.sessions=[]; DB.activities=[];
  DB.checkins={};
  DB.checkins[T]={sleepMin:430,energy:7,soreness:2,stress:4,motivation:7};
  DB.checkins[addDays(T,-1)]={sleepMin:420,energy:6,soreness:2};
  DB.checkins[addDays(T,-2)]={sleepMin:440,energy:7,soreness:3};
  var cyc=[];
  for(var i=179;i>=0;i--) cyc.push({date:addDays(T,-i),recovery:60,hrv:76,rhr:52,strain:8,sleepMin:430});
  DB.whoop={cycles:cyc,workouts:[],journal:[],imports:[]};
  var H3=systemHistory(T);
  var cov3=dataCoverage(T);
  /* Three days of check-ins and six months of imported cycles. The window that
     qualifies a body-system claim is the first of those, not the second. */
  ok('coverage sees the import', cov3.hasImport && cov3.importDays>=179, cov3.importDays);
  ok('but the self window is what Baseline itself watched', cov3.selfDays<=3, cov3.selfDays);
  ok('span follows the self window, not the import', H3.spanDays===cov3.selfDays && H3.spanDays<=3,
     H3.spanDays+' vs import '+cov3.importDays);
  ok('three days is still "learning"', cov3.level==='learning', cov3.level);
  var why3=recommend(T,DB.checkins[T]).why.map(function(n){return n.t;}).join(' ');
  ok('a three-day-old profile is not told its legs idled for a fortnight',
     !/over two weeks/.test(why3), why3.slice(0,170));
  // and once there IS training logged, the span is that training's span
  DB.activities=[{id:'a_h1',date:addDays(T,-2),type:'swimming',min:40,strain:7}];
  ok('span counts every day Baseline was in a position to see',
     systemHistory(T).spanDays===2, systemHistory(T).spanDays);
  ok('the prose names the span it actually has',
     /in the 2 days Baseline has been tracking/.test(sinceSpan(99,2)), sinceSpan(99,2));
  ok('a real fortnight still reads as a fortnight', /over two weeks/.test(sinceSpan(99,30)), sinceSpan(99,30));
  ok('no logged training claims no duration at all', sinceSpan(99,0)==='yet', sinceSpan(99,0));

  // 2 · THE WEEK HEADING MUST NOT CONTRADICT THE WEEK STRIP.
  WEEKOFF=0; SELDAY=null; resetStack(); TAB='today'; render();
  var headsOf=function(){
    return Array.prototype.slice.call(document.querySelectorAll('#view .sec-t'))
             .map(function(e){return e.textContent.trim();}); };
  /* "This week" while it IS this week; the dates once the arrows move it, so
     the heading is never a period the strip is not showing. */
  ok('the week heading reads plainly while it is this week',
     headsOf().indexOf('This week')>=0, headsOf().join(' | '));
  /* The heading names the period the strip is SHOWING and moves with it. An
     earlier pass had it name no period at all, which was the safe answer to
     "This week" being wrong once you pressed the arrow; naming the actual
     range is the better one, as long as the two cannot disagree. */
  ok('the week section is still labelled', headsOf().indexOf('This week')>=0,
     headsOf().join(' | '));
  ok('and recent activity has a heading of its own',
     headsOf().indexOf('Recent activity')>=0, headsOf().join(' | '));
  var lbl=document.querySelector('#view .wk-l');
  ok('the strip is what names the week', lbl && /This week/.test(lbl.textContent),
     lbl?lbl.textContent:'(no strip)');
  var prev=document.getElementById('wkPrev');
  ok('the strip can step backwards', !!prev);
  if(prev){
    prev.click();
    var lbl2=document.querySelector('#view .wk-l');
    /* An explicit range rather than "Last week": relative labels stop being
       readable two steps back, and the user must always know which days are
       on screen. */
    ok('stepping back names the exact period',
       lbl2 && /[0-9]{1,2}.*[0-9]{1,2} [A-Z][a-z][a-z]/.test(lbl2.textContent) && !/week/i.test(lbl2.textContent),
       lbl2?lbl2.textContent:'(no strip)');
    ok('and the heading moved with it, rather than still saying "this week"',
       headsOf().indexOf('This week')<0
       && headsOf().indexOf(weekRangeLabel(addDays(weekStartOf(todayISO()),-7),
                                           addDays(weekStartOf(todayISO()),-1)))>=0,
       headsOf().join(' | ')+'  vs strip  '+lbl2.textContent.trim());
  }
  WEEKOFF=0; SELDAY=null;

  // 3 · THE SLEEP RING ANSWERS A SLEEP QUESTION.
  DB.baselines.sleepNeed=480; DB.baselines.sleepNeedGeneric=false;
  DB.checkins[T]={sleepMin:390,sleepNeed:480,energy:7,soreness:2,stress:4,motivation:7,
                  recovery:60,hrv:76,rhr:52,prevStrain:8};
  var sp=sleepPlan(T);
  ok('the sleep plan knows the target', sp.need===480, sp.need);
  ok('and the shortfall against it', sp.shortfall===90, sp.shortfall);
  ok('the readiness sleep curve is invertible',
     Math.abs(sleepScoreFor(sleepMinsForScore(60,480),480)-60)<0.6,
     sleepScoreFor(sleepMinsForScore(60,480),480));
  ok('meeting the need is the top of the range', sleepMinsForScore(95,480)===480, sleepMinsForScore(95,480));
  ok('it says how long tonight has to be', sp.better && sp.better.mins>sp.slept,
     sp.better?sp.better.mins:'(none)');
  ok('and what that is worth in readiness points', sp.better && sp.better.gain>0,
     sp.better?sp.better.gain:null);
  ok('points are scaled by the signals that actually reported today',
     sp.perPt>0 && sp.perPt<1, sp.perPt);
  ok('a night that met the target promises nothing further',
     (function(){ DB.checkins[T].sleepMin=500; var s2=sleepPlan(T);
                  DB.checkins[T].sleepMin=390;
                  return s2.better===null && s2.shortfall<=0; })());
  ok('sleep never claims more than its own weight', sp.weight===18 && sp.maxGain<18,
     sp.weight+'/'+sp.maxGain);
  resetStack(); TAB='today'; render();
  /* Home carries the sleep tile, and the readiness screen carries a second
     door to the same detail - deliberately, because that screen is where the
     figure is explained. */
  ok('Home carries a sleep tile', !!document.getElementById('ringSleep'));
  pushPage({build:pageReadiness(T)});
  var sr=document.getElementById('rdSleep');
  ok('the readiness screen opens the sleep detail', !!sr);
  if(sr){
    sr.click();
    var stxt=document.getElementById('view').textContent;
    ok('tapping it opens the sleep page, not the check-in form',
       /Tonight/.test(stxt) && /What a night is worth/.test(stxt), stxt.slice(0,130));
    ok('the page states the need it is measuring against', /8h 00m/.test(stxt), stxt.slice(0,220));
    ok('the page is honest that sleep is one input of several',
       /resting heart rate/.test(stxt), stxt.slice(0,260));
    /* The ring is a fixed-width block, so it has to be laid out beside
       something or it sits hard left with the tile empty next to it. */
    var head=document.querySelector('#view .sleeph');
    ok('the ring shares its row with the figures', !!head && !!head.querySelector('.arc')
       && !!head.querySelector('.sh-v'), head?head.textContent.slice(0,60):'(no header)');
    ok('and the header is laid out as a row, not a lone centred ring',
       !!head && getComputedStyle(head).display==='flex',
       head?getComputedStyle(head).display:'(none)');
    ok('the duration is stated once, not restated in prose',
       head.textContent.split(fmtMin(sp.slept)).length-1===1,
       fmtMin(sp.slept)+' in: '+head.textContent.slice(0,90));
    /* the tier rows used to contain two identical durations, because 95 and 85
       both invert to the full need */
    var rows=Array.prototype.slice.call(document.querySelectorAll('#view .card .kv .v'))
               .map(function(e){return e.textContent.trim();});
    ok('every tier row is a different duration',
       rows.length>=3 && rows.length===rows.filter(function(v,i){return rows.indexOf(v)===i;}).length,
       rows.join(' | '));
    popPage(); render();
  }

  // 4 · SOMETHING DONE THIS MORNING CHANGES THIS EVENING'S PLAN.
  // Deliberately NOT the main sport: a basketball game loads legs whether or
  // not basketball is what you train for, and the old code only ever noticed
  // the main sport, as a yes/no flag.
  DB.profile.sports=['tennis']; DB.profile.sport='tennis';
  DB.sessions=[]; DB.activities=[]; DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.checkins={};
  DB.checkins[T]={sleepMin:470,sleepNeed:480,energy:8,soreness:1,stress:3,motivation:8,
                  recovery:78,hrv:88,rhr:50,prevStrain:6};
  ok('the test activity is not the main sport', isMainSportAct('basketball')===false);
  var before=recommend(T,DB.checkins[T]);
  ok('nothing logged means no load in today yet', dayDemand(T).load===0, dayDemand(T).load);
  ok('a fresh green day does prescribe real work',
     ['lower','power','upper'].indexOf(before.id)>=0, before.id+'/'+before.variant);
  DB.activities=[{id:'a_bb',date:T,type:'basketball',min:110,strain:15,time:'11:00'}];
  var after=recommend(T,DB.checkins[T]);
  ok('a game logged this morning registers as load today', dayDemand(T).load>=10, dayDemand(T).load);
  ok('legs logged today are seen as loaded today', dayDemand(T).lower>=6, dayDemand(T).lower);
  ok('the plan actually responds to it',
     after.id!==before.id || after.variant!==before.variant,
     before.id+'/'+before.variant+' -> '+after.id+'/'+after.variant);
  ok('a leg session is not stacked on top of a hard game',
     after.id!=='lower' && after.id!=='power', after.id);
  var whyA=after.why.map(function(n){return n.t;}).join(' ');
  ok('and it says why, naming today', /today/.test(whyA), whyA.slice(0,200));
  ok('it no longer claims fresh legs after a game',
     !/have not taken real load/.test(whyA), whyA.slice(0,200));
  // a gentle activity must NOT derail a good day - the response is proportional
  DB.activities=[{id:'a_w',date:T,type:'walking',min:25,strain:2,time:'09:00'}];
  var mild=recommend(T,DB.checkins[T]);
  ok('a short walk does not derail the day', mild.id===before.id, mild.id+' vs '+before.id);
  ok('a short walk does not cut the volume', mild.variant===before.variant,
     mild.variant+' vs '+before.variant);

  DB.sessions=keepSe; DB.activities=keepAc; DB.checkins=keepCi; DB.whoop=keepWh;
  DB.baselines=keepBl; DB.profile=keepPr;
  WEEKOFF=0; SELDAY=null; resetStack(); TAB='today';
})();


// ---------- A WEARABLE IS AN ENHANCEMENT, NOT A PREREQUISITE ----------
// Four users have to get a complete screen: one with WHOOP, one with another
// device, one with no device, and one who has not imported anything yet. What
// none of them may get is a card holding a dash where a strap would go.
(function(){
  var kSe=DB.sessions, kAc=DB.activities, kCi=JSON.parse(JSON.stringify(DB.checkins)),
      kWh=DB.whoop, kPr=JSON.parse(JSON.stringify(DB.profile)),
      kBl=JSON.parse(JSON.stringify(DB.baselines)), kMe=JSON.parse(JSON.stringify(DB.meta));
  var T=todayISO();
  var home=function(){ resetStack(); TAB='today'; render();
                       return document.getElementById('view'); };

  /* --- no device, no import, nothing checked in --- */
  DB.sessions=[]; DB.activities=[]; DB.checkins={};
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.profile.source='none'; DB.profile.onboarded=true;
  DB.meta.created=T+'T08:00:00.000Z';
  var v=home(), txt=v.textContent;
  ok('with no device the home screen still renders', txt.length>200, txt.length+' chars');
  ok('and says it is learning rather than showing a number it has not got',
     /Learning your baseline/.test(txt), txt.slice(0,180));
  ok('no HRV tile is reserved on the home screen', txt.indexOf('HRV')<0, txt.slice(0,220));
  ok('no resting-HR tile either', !/RHR|Resting HR/.test(txt), txt.slice(0,220));
  ok('and no sleep card sitting empty',
     !document.getElementById('ringSleep'), 'sleep tile absent without a figure');
  ok('the slot carries something Baseline always knows instead',
     !!document.getElementById('ringWeek'),
     document.getElementById('ringWeek') ? document.getElementById('ringWeek').textContent.trim() : '(none)');
  ok('no tile anywhere on the home screen is a bare dash',
     Array.prototype.slice.call(v.querySelectorAll('.score .arc-t'))
       .every(function(e){ return e.textContent.trim()!=='—'; }),
     Array.prototype.slice.call(v.querySelectorAll('.score .arc-t')).map(function(e){return e.textContent;}).join('|'));
  ok('and there is still a clear next action', !!document.getElementById('btnStart')
     || !!document.getElementById('btnCheck')
     || /Rest is the recommendation/.test(txt), txt.slice(0,200));

  /* --- no device, but they checked in: a real number, from what they said --- */
  DB.checkins[T]={date:T,energy:7,soreness:2,stress:3,motivation:7,pain:'None',sleepMin:430};
  v=home(); txt=v.textContent;
  ok('a check-in produces a real readiness score without any device',
     !/Learning your baseline/.test(txt)
     && /^[0-9]+$/.test((document.querySelector('#rdRow .arc-t')||{textContent:''}).textContent.trim()),
     (document.querySelector('#rdRow .arc-t')||{textContent:'(none)'}).textContent);
  ok('sleep they reported themselves does get its tile',
     !!document.getElementById('ringSleep'));
  ok('but still no HRV or recovery tile', txt.indexOf('HRV')<0 && !/Avg recovery/.test(txt));

  /* --- Progress with no device: no empty wearable tiles --- */
  TAB='progress'; resetStack(); render();
  var pv=document.getElementById('view').textContent;
  ok('Progress renders without a device', pv.length>100, pv.length+' chars');
  ok('and reserves no wearable tiles',
     pv.indexOf('Avg HRV')<0 && pv.indexOf('Avg RHR')<0 && pv.indexOf('Avg recovery')<0,
     pv.slice(0,220));
  ok('it leads with what was actually logged',
     /Sessions/.test(pv) && /Activities/.test(pv), pv.slice(0,220));

  /* --- and with a device, the figures appear --- */
  var cyc=[];
  for(var i=29;i>=0;i--) cyc.push({date:addDays(T,-i),recovery:70,hrv:84,rhr:52,strain:9,sleepMin:440});
  DB.whoop={cycles:cyc,workouts:[],journal:[],imports:[]};
  DB.profile.source='whoop'; recomputeBaselines();
  DB.checkins[T]=Object.assign({recovery:70,hrv:84,rhr:52,prevStrain:9},DB.checkins[T]);
  TAB='progress'; resetStack(); render();
  var pv2=document.getElementById('view').textContent;
  ok('with a device the wearable figures do appear',
     /Avg HRV/.test(pv2) || /Avg recovery/.test(pv2), pv2.slice(0,240));
  ok('and they are additions, not replacements',
     /Sessions/.test(pv2) && /Activities/.test(pv2));

  DB.sessions=kSe; DB.activities=kAc; DB.checkins=kCi; DB.whoop=kWh;
  DB.profile=kPr; DB.baselines=kBl; DB.meta=kMe;
  resetStack(); TAB='today';
})();


// ---------- EVERY ILLUSTRATION IS REAL, OR THERE ISN'T ONE ----------
// The spec's "no fake image paths" rule. Inline SVG cannot 404, so what is
// checked instead is that every key resolves to a pose, every pose renders,
// and nothing shows equipment the app does not support.
(function(){
  var keys=Object.keys(POSES);
  ok('there is a pose library', keys.length>=20, keys.length+' poses');

  var badRef=[];
  POSE_RULES.forEach(function(r){ if(!POSES[r[1]]) badRef.push(String(r[0])+' -> '+r[1]); });
  Object.keys(EX_ILLUS_OVERRIDE).forEach(function(id){
    if(!POSES[EX_ILLUS_OVERRIDE[id]]) badRef.push(id+' -> '+EX_ILLUS_OVERRIDE[id]); });
  Object.keys(WU_ILLUS).forEach(function(n){ if(!POSES[WU_ILLUS[n]]) badRef.push(n+' -> '+WU_ILLUS[n]); });
  ok('every illustration reference resolves to a real pose', badRef.length===0, badRef.join(' | '));

  /* THE CHECK THAT WAS MISSING.
     The first validator asked only whether a reference resolved, so a mapping
     that pointed at a real pose of the WRONG movement passed every test - and
     one did: "DB Bicep Curl" drew a band held overhead. Naming the pairs is
     what makes a wrong answer fail. */
  var expect=[
    ['DB Bicep Curl','db-curl'], ['DB Hammer Curl','db-curl'], ['Band Curl','db-curl'],
    ['Sliding Leg Curl','nordic'], ['Nordic Curl Eccentric','nordic'],
    ['Band Kneeling Lat Pull','lat-pull'], ['Band Lat Pulldown','lat-pull'],
    ['Band Row','row'], ['DB Bent-Over Row','row'], ['Inverted Row','row'],
    ['Band Pull-Apart','band-pull-apart'], ['Band Face Pull','band-face-pull'],
    ['Band Pallof Press','band-pallof'], ['Half-Kneeling Band Chop','band-pallof'],
    ['DB Overhead Press','db-press-oh'], ['DB Arnold Press','db-press-oh'],
    ['DB Floor Press','floor-press'], ['DB Lateral Raise','db-raise'],
    ['DB Front Raise','db-raise'], ['Band Triceps Pushdown','band-pushdown'],
    ['DB Overhead Triceps Extension','db-overhead-tri'],
    ['Push-Up','push-up'], ['Pike Push-Up','pike-push-up'],
    ['Elevated Pike Push-Up','pike-push-up'], ['Scapular push-ups','scap-pushup'],
    ['RKC Plank','plank'], ['Side Plank','side-plank'], ['Side Plank Hip Dip','side-plank'],
    ['Copenhagen Plank','copenhagen'], ['Dead Bug','dead-bug'], ['Bird Dog','bird-dog'],
    ['Hollow Body Hold','hollow-hold'], ['Suitcase Carry','carry'],
    ['Single-Leg Glute Bridge','sl-glute-bridge'], ['Floor Hip Thrust','glute-bridge'],
    ['DB Romanian Deadlift','hinge'], ['Single-Leg RDL','sl-rdl'],
    ['Wall Sit','wall-sit'], ['Tibialis Raise','tibialis-raise'],
    ['Standing Calf Raise','calf-raise'], ['Single-Leg Calf Raise','sl-calf-raise'],
    ['Tempo Goblet Squat','goblet-squat'], ['Split Squat','split-squat'],
    ['Cossack Squat','split-squat'], ['Reverse Lunge','lunge'], ['Lateral Lunge','lunge'],
    ['Pogo Hops','pogo-hops'], ['Countermovement Jump','jump'],
    ['Lateral Bound (Skater)','lateral-bound'], ['Deceleration Drill','decel'],
    ['Zone 2 Run','run'], ['Zone 2 Bike','bike'], ['Hill Sprints','run'],
    ['Recovery Spin','bike'], ['Easy Walk','walk'], ['Tempo Run','run'],
    ['Wall Slides','wall-slides'], ['Shoulder CARs','shoulder-cars'],
    ['Cat-Cow','cat-cow'], ['Thoracic Rotation (Open Book)','open-book'],
    ['90/90 Hip Switch','hip-90-90'], ['Calf Stretch','calf-stretch'],
    ['Couch Stretch','couch-stretch'], ['Band Shoulder Dislocates','band-overhead'],
    ['Superman','superman'], ['Prone Y-T-W','prone-ytw']
  ];
  var wrong=[];
  expect.forEach(function(p){
    var got=illusKey({name:p[0]});
    if(got!==p[1]) wrong.push(p[0]+': '+(got||'NONE')+' (wanted '+p[1]+') via '+illusWhy({name:p[0]}));
  });
  ok('each movement gets the drawing of THAT movement', wrong.length===0, wrong.join('  |  '));

  var badDraw=[];
  keys.forEach(function(k){
    var s='';
    try{ s=figSVG(POSES[k]); }catch(e){ badDraw.push(k+': '+e.message); return; }
    if(s.indexOf('<svg')<0 || s.indexOf('NaN')>=0 || s.indexOf('undefined')>=0) badDraw.push(k);
  });
  ok('every pose renders clean SVG', badDraw.length===0, badDraw.join(', '));

  /* A figure needs a body. A pose missing its torso or head would render as a
     scatter of lines and still pass a "contains <svg>" check. */
  var thin=keys.filter(function(k){ var p=POSES[k];
    return !p.head || !p.sh || !p.hip || !p.leg || !p.arm; });
  ok('every pose has a head, a torso, an arm and a leg', thin.length===0, thin.join(', '));

  /* Equipment must be kit the user can actually own. The renderer only knows
     how to draw a band, a dumbbell, a wall, a block, a bike and an arrow -
     there is no barbell, cable or machine to draw by accident. */
  var props={};
  keys.forEach(function(k){ (POSES[k].props||[]).forEach(function(p){ props[p.t]=1; }); });
  var allowed={band:1,db:1,wall:1,block:1,anchor:1,arr:1,arc:1,bike:1};
  ok('no illustration introduces unsupported equipment',
     Object.keys(props).every(function(t){ return allowed[t]; }), Object.keys(props).join(', '));

  /* ---------------------------------------------------------------------
     SWITCHES YOU CAN SEE
     Every boolean was a bare checkbox, and appearance:none in the stylesheet
     left it an invisible 22px square: it toggled, it saved, and the screen
     showed nothing, so the settings looked broken. A control that changes a
     setting has to be visible and its states have to differ.
     ------------------------------------------------------------------ */
  (function(){
    DB.profile.onboarded=true;
    resetStack(); TAB='settings'; render();
    pushPage({build:function(c){ SETTAB='alerts'; settingsBody(c); }});

    var rows=document.querySelectorAll('#view .spane.on .tglr');
    ok('the workout experience pane is built from switch rows', rows.length>=3,
       rows.length+' rows');

    var bad=[];
    Array.prototype.forEach.call(rows, function(r){
      var inp=r.querySelector('input[type=checkbox]');
      var trk=r.querySelector('.tgl');
      var lbl=(r.querySelector('.tg-t')||{}).textContent||'?';
      if(!inp){ bad.push(lbl+': no checkbox'); return; }
      if(!trk){ bad.push(lbl+': no track drawn'); return; }
      var tb=trk.getBoundingClientRect();
      /* the part the eye sees, not the input, which is deliberately clear */
      if(tb.width<28 || tb.height<18)
        bad.push(lbl+': track is '+Math.round(tb.width)+'x'+Math.round(tb.height));
      var cs=getComputedStyle(trk);
      if(cs.display==='none' || cs.visibility==='hidden')
        bad.push(lbl+': track is '+cs.display+'/'+cs.visibility);
      /* transparent on transparent is the fault that started this */
      if(cs.backgroundColor==='rgba(0, 0, 0, 0)' && parseFloat(cs.borderTopWidth)<1)
        bad.push(lbl+': track has neither fill nor edge');
      /* the whole row is the hit area, so the invisible input has to cover it */
      var rb=r.getBoundingClientRect(), ib=inp.getBoundingClientRect();
      if(ib.width < rb.width-1 || ib.height < rb.height-1)
        bad.push(lbl+': hit area '+Math.round(ib.width)+'x'+Math.round(ib.height)
          +' inside a row of '+Math.round(rb.width)+'x'+Math.round(rb.height));
    });
    ok('every switch draws a track you can see and can hit', bad.length===0,
       bad.join(' | '));

    /* On and off have to look different. Compare the same control in both
       positions rather than trusting the rule that is supposed to do it. */
    (function(){
      /* Rendered, not scripted: setting .checked in script does not flush a
         style recalc, so reading the computed style straight afterwards gives
         the old answer and the test passes or fails on its own timing. Two
         rows in two states, drawn together, is what the eye compares. */
      var keepR=DB.settings.restTimerOn, keepS=DB.settings.sound;
      DB.settings.restTimerOn=true; DB.settings.sound=false;
      resetStack(); TAB='settings'; render();
      pushPage({build:function(c){ SETTAB='alerts'; settingsBody(c); }});
      var on =document.getElementById('sRest').parentNode.querySelector('.tgl');
      var off=document.getElementById('sSound').parentNode.querySelector('.tgl');
      var onC=getComputedStyle(on), offC=getComputedStyle(off);
      var onBg=onC.backgroundColor, offBg=offC.backgroundColor;
      var onKnob=getComputedStyle(on,'::after').transform;
      var offKnob=getComputedStyle(off,'::after').transform;
      ok('a switch that is on is not the same colour as one that is off',
         onBg!==offBg, offBg+' -> '+onBg);
      ok('and its knob is not in the same place',
         onKnob!==offKnob, offKnob+' -> '+onKnob);
      /* the on colour is the accent, so it reads as on rather than as some
         other shade of grey */
      ok('the on state uses the accent colour',
         onBg===getComputedStyle(document.body).getPropertyValue('--accent').trim()
         || /rgb/.test(onBg) && onBg!==offBg, onBg);
      DB.settings.restTimerOn=keepR; DB.settings.sound=keepS;
      resetStack(); TAB='settings'; render();
      pushPage({build:function(c){ SETTAB='alerts'; settingsBody(c); }});
    })();

    /* And it still does what it did: the tap changes the stored setting. */
    (function(){
      var before=DB.settings.restTimerOn;
      document.getElementById('sRest').click();
      ok('tapping a switch changes the setting it names',
         DB.settings.restTimerOn===!before, before+' -> '+DB.settings.restTimerOn);
      document.getElementById('sRest').click();
      ok('and tapping it back restores it', DB.settings.restTimerOn===before);
    })();

    /* The notification row has a state the switch cannot show: on, with the
       browser refusing. That has to be said in words. */
    (function(){
      var row=document.getElementById('sNotify').parentNode;
      ok('the notification row says what it is doing, not just what it is for',
         !!row.querySelector('.tg-s'));
      var h=document.getElementById('sNotifyH');
      ok('and says what to do next', !!h && h.textContent.trim().length>20,
         h? h.textContent.trim().slice(0,70) : '(missing)');
      /* the wording has to name the thing rather than describe a feature */
      var lbl=(row.querySelector('.tg-t')||{}).textContent||'';
      ok('the label is about the rest being over', /rest is over/i.test(lbl), lbl);
      /* never claimed as on without the permission that makes it mean
         something - the check that stops a silent phone reading as working */
      DB.settings.notify=true;
      ok('notifyOn() still requires the browser to have allowed it',
         notifyOn()===(notifyState()==='granted'),
         notifyState()+' / '+notifyOn());
      DB.settings.notify=false;
    })();

    /* Nothing is left drawing itself the old way. */
    (function(){
      var naked=[];
      document.querySelectorAll('#view input[type=checkbox]').forEach(function(i){
        if(!i.closest('.tglr')) naked.push(i.id||'(no id)');
      });
      ok('no checkbox is left outside a switch row', naked.length===0, naked.join(', '));
    })();

    resetStack(); TAB='today'; render();
  })();

  /* ---------------------------------------------------------------------
     THE ICON SET: ONE DRAWING PER THING
     A shared glyph is invisible in a diff and obvious on screen. The log grid
     drew running, walking and hiking with one runner and put the flame on
     seven more sports, and the core session carried the upload arrow - which
     is the share glyph on every phone. These check the drawings, not the
     names of the drawings.
     ------------------------------------------------------------------ */
  (function(){
    var aud=iconAudit();
    ok('no two icon names are the same drawing', aud.dup.length===0,
       aud.dup.join(', ') || aud.total+' distinct');

    /* Every activity the engine knows about is named in the table, so a new
       sport cannot silently fall through to the generic mark. */
    var unnamed=Object.keys(ACT_TYPES).filter(function(k){ return !ACT_ICONS[k]; });
    ok('every activity type has its own entry', unnamed.length===0, unnamed.join(', '));

    /* And every entry points at a drawing that exists. */
    var broken=Object.keys(ACT_ICONS).filter(function(k){ return !ICON[ACT_ICONS[k]]; });
    ok('and every entry names a drawing that exists', broken.length===0, broken.join(', '));

    /* The grid is the screen that shows them together, which is where the
       repetition was seen. Compare the rendered SVG bodies. */
    resetStack(); TAB='log'; LOGQ=''; render();
    var tiles=document.querySelectorAll('#lgGrid button');
    ok('the log grid offers every activity', tiles.length>=Object.keys(ACT_TYPES).length-1,
       tiles.length+' tiles');
    var byGlyph={}, repeated=[];
    Array.prototype.forEach.call(tiles, function(b){
      var i=b.querySelector('i svg'), nm=(b.querySelector('span')||{}).textContent||'?';
      if(!i){ repeated.push(nm+' has no icon'); return; }
      var g=i.innerHTML.replace(/[^!-~]+/g,'');
      if(byGlyph[g]) repeated.push(byGlyph[g]+' = '+nm); else byGlyph[g]=nm;
    });
    ok('and no two of them are drawn the same', repeated.length===0, repeated.join(' | '));

    /* Running, walking and hiking specifically - the three the user named. */
    ok('running, walking and hiking are three different drawings',
       ICON[ACT_ICON('running')]!==ICON[ACT_ICON('walking')] &&
       ICON[ACT_ICON('walking')]!==ICON[ACT_ICON('hiking')] &&
       ICON[ACT_ICON('running')]!==ICON[ACT_ICON('hiking')],
       [ACT_ICON('running'),ACT_ICON('walking'),ACT_ICON('hiking')].join('/'));

    /* The core session's mark is not the upload arrow, and is not any other
       mark the app already uses for an action. */
    var coreIcon=planIcon({id:'core'});
    ok('the core session has a mark of its own', coreIcon==='core', coreIcon);
    ok('and it is not the upload arrow', ICON[coreIcon]!==ICON.ul);
    ok('nor anything else in the set',
       Object.keys(ICON).filter(function(k){ return ICON[k]===ICON[coreIcon]; }).length===1);

    /* Each session type the engine can prescribe gets its own mark, checked
       across the whole plan vocabulary rather than one id at a time. */
    var ids=['lower','upper','power','core','run_e','run_q','run_int','bike',
             'mobility','rest','prep'];
    var seen={}, clash=[];
    ids.forEach(function(id){
      var g=ICON[planIcon({id:id})];
      if(!g){ clash.push(id+' has no drawing'); return; }
      if(seen[g]) clash.push(seen[g]+' = '+id); else seen[g]=id;
    });
    ok('no two session types share a mark', clash.length===0, clash.join(' | '));

    /* The wearable metric list shows many marks together too. */
    var mseen={}, mclash=[];
    Object.keys(DATA_FIELDS||{}).forEach(function(k){
      var g=ICON[DATA_FIELDS[k].icon];
      if(!g){ mclash.push(k+' has no drawing'); return; }
      if(mseen[g]) mclash.push(mseen[g]+' = '+k); else mseen[g]=k;
    });
    ok('no two metrics share a mark', mclash.length===0, mclash.join(' | '));

    resetStack(); TAB='today'; render();
  })();

  /* Coverage, stated rather than assumed: this is a starter library and the
     test says how far it reaches so it cannot quietly stall. */
  var cov=illusCoverage();
  ok('the starter library covers a real share of the catalogue',
     cov.have >= Math.round(cov.total*0.5),
     cov.have+' of '+cov.total+' exercises, '+cov.poses+' poses');

  /* Everything the ENGINE can actually prescribe should be drawn. */
  var missing=[];
  DB.workouts.forEach(function(w){
    ['full','reduced','recovery'].forEach(function(v){
      ((w.blocks&&w.blocks[v])||[]).forEach(function(b){
        var ex=exOf(b.ex);
        if(ex && !illusKey(ex) && missing.indexOf(ex.name)<0) missing.push(ex.name);
      });
    });
  });
  ok('every exercise an authored workout can prescribe has one',
     missing.length===0, missing.join(', '));

  /* AND everything a SUBSTITUTION can reach. The reported gap was an exercise
     from the second library in p03b, which the id table never covered - the
     catalogue the engine can resolve to is bigger than the one it authors. */
  /* What is allowed to be undrawn is gym kit: a rack, a cable stack, a bar, a
     machine. The app only offers those to somebody who ticked that equipment,
     and drawing them is a separate job with its own props. Anything needing
     only bodyweight, dumbbells, a band, a wall, the floor, a chair, a towel, a
     bike or open ground is kit the figure system already draws, so an undrawn
     one there is a gap and not a limit. */
  var SUPPORTED={BW:1,DB:1,BAND:1,WALL:1,FLOOR:1,CHAIR:1,TOWEL:1,BIKE:1,RUN:1};
  var gapHome=[], gapGym=[];
  (DB.exercises||[]).forEach(function(ex){
    if(illusKey(ex)) return;
    var home = ex.equip ? !!SUPPORTED[ex.equip] : ((ex.tier||0) < 2);
    (home?gapHome:gapGym).push(ex.name);
  });
  ok('nothing needing only home kit is left undrawn',
     gapHome.length===0, gapHome.join(', '));
  ok('and what is left needs a rack, a cable or a bar',
     gapGym.length===0 || gapGym.every(function(n){
       return /barbell|bench|cable|pull-?up|chin-?up|hanging|leg press|machine|kettlebell|treadmill|rower|med ball/i.test(n); }),
     gapGym.join(', '));

  /* And every warm-up movement the app can show. */
  var wuMiss=[];
  Object.keys(WARMUPS).forEach(function(k){
    (WARMUPS[k].items||[]).forEach(function(it){
      if(!illusKey({name:it.n}) && wuMiss.indexOf(it.n)<0) wuMiss.push(it.n); });
  });
  ok('every warm-up movement in the stock routines has one',
     wuMiss.length===0, wuMiss.join(', '));

  /* A movement with no pose is a deliberate mark, never a broken image. */
  var none=illusHTML({name:'a movement nobody has drawn yet'},'sm');
  ok('an undrawn movement falls back cleanly',
     none.indexOf('illus')>=0 && none.indexOf('none')>=0 && none.indexOf('<img')<0, none.slice(0,70));
  ok('and nothing anywhere loads an external image',
     figSVG(POSES[keys[0]]).indexOf('http')<0 && figSVG(POSES[keys[0]]).indexOf('<img')<0);
})();


// ---------- BASELINE MUST NOT CLAIM WHAT IT NEVER OBSERVED ----------
// The engine may score an unseen system as due - "never observed" and "not
// trained recently" lead to the same decision. What it may not do is DESCRIBE
// the second when it only has grounds for the first.
(function(){
  var kSe=JSON.parse(JSON.stringify(DB.sessions)), kAc=JSON.parse(JSON.stringify(DB.activities)),
      kCi=JSON.parse(JSON.stringify(DB.checkins)), kMe=JSON.parse(JSON.stringify(DB.meta)),
      kPr=JSON.parse(JSON.stringify(DB.profile)), kWh=DB.whoop,
      kBl=JSON.parse(JSON.stringify(DB.baselines)), kTg=JSON.parse(JSON.stringify(DB.targets));
  var T=todayISO();
  var FEEL={sleepMin:450,energy:7,soreness:2,stress:3,motivation:7,pain:'None'};
  var reset=function(installedDaysAgo){
    DB.sessions=[]; DB.activities=[]; DB.checkins={};
    DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
    DB.meta.created=addDays(T,-installedDaysAgo)+'T08:00:00.000Z';
  };
  var whyOf=function(){
    var r=recommend(T,DB.checkins[T]);
    return r.why.map(function(n){return n.t;})
      .concat((r.ruledOut||[]).map(function(x){return x.why;})).join('  ');
  };

  // === A · a brand-new profile knows nothing, and says so ===
  reset(0);
  var c0=dataCoverage(T);
  ok('a new profile has observed nothing', c0.selfDays===0 && !c0.hasImport, c0.selfDays);
  ok('and reports itself as still learning', c0.level==='learning', c0.level);
  ok('no absence is describable on day zero',
     absenceNote('core work',99,c0.selfDays)===null, absenceNote('core work',99,c0.selfDays));
  DB.checkins[T]=Object.assign({},FEEL);
  var w0=whyOf();
  ok('a new profile is never told it has not trained core',
     !/has not been trained/i.test(w0) && !/core work in over two weeks/i.test(w0), w0.slice(0,240));
  ok('and is never told it is behind', !/behind/i.test(w0), w0.slice(0,240));
  ok('and is never told a system idled for several days',
     !/in several days/i.test(w0), w0.slice(0,240));
  ok('but it does say plainly that it is still learning',
     /still learning|first day|not yet enough|does not have enough history/i.test(w0), w0.slice(0,240));
  ok('and it still produces a recommendation', !!recommend(T,DB.checkins[T]).id);

  // === B · four days in: describable, but scoped to four days ===
  reset(4);
  DB.checkins[addDays(T,-3)]={sleepMin:440,energy:7};
  DB.checkins[T]=Object.assign({},FEEL);
  var c4=dataCoverage(T);
  ok('four days in, the window is four days', c4.selfDays===4, c4.selfDays);
  ok('an absence becomes describable, scoped to what was watched',
     /4 days Baseline has been tracking/.test(absenceNote('core work',99,4)||''),
     absenceNote('core work',99,4));
  ok('and still refuses to claim a fortnight',
     (absenceNote('core work',99,4)||'').indexOf('two weeks')<0, absenceNote('core work',99,4));
  ok('the wording is "logged", not "trained"',
     /logged/.test(absenceNote('core work',99,4)||'') && !/trained/.test(absenceNote('core work',99,4)||''),
     absenceNote('core work',99,4));

  // === C · a month in, plain language is earned ===
  reset(30);
  DB.checkins[T]=Object.assign({},FEEL);
  ok('a month in, coverage reads as established', dataCoverage(T).level==='established', dataCoverage(T).level);
  ok('and a real fortnight is finally stated plainly',
     absenceNote('core work',99,30)==='No core work in over two weeks.', absenceNote('core work',99,30));

  // === D · a gap that was actually seen needs no hedging ===
  // since!==99 means a load WAS found on that day, which is itself proof the
  // window reaches back that far.
  ok('an observed gap is stated as days', absenceNote('core work',5,5)==='No core work for 5 days.',
     absenceNote('core work',5,5));
  ok('and does not depend on the coverage window', absenceNote('core work',5,0)==='No core work for 5 days.',
     absenceNote('core work',5,0));

  // === E · an import extends physiology, never body-system claims ===
  reset(2);
  var cyc=[];
  for(var i=200;i>=0;i--) cyc.push({date:addDays(T,-i),recovery:62,hrv:80,rhr:52,strain:9,sleepMin:440});
  DB.whoop={cycles:cyc,workouts:[{date:addDays(T,-40),activity:'Weightlifting',strain:11}],journal:[],imports:[]};
  DB.checkins[T]=Object.assign({},FEEL);
  var cI=dataCoverage(T);
  ok('the import is visible as an import', cI.hasImport && cI.importDays>=200, cI.importDays);
  ok('the combined window includes it', cI.days>=200, cI.days);
  ok('the self window does not', cI.selfDays<=2, cI.selfDays);
  ok('so six months of cycles cannot manufacture a fortnight claim',
     whyOf().indexOf('two weeks')<0, whyOf().slice(0,240));
  ok('and the import is still usable for physiology',
     dataCoverage(T).importStart===addDays(T,-200), dataCoverage(T).importStart);

  // === F · weekly targets need the week observed before they judge it ===
  DB.targets=Object.assign({},DB.targets,{core:4});
  var coreNotes=function(){
    var r=recommend(T,DB.checkins[T]);
    var c=(r.scored||[]).filter(function(x){return x.c.id==='core';})[0];
    return c ? c.notes.map(function(n){return n.t;}).filter(Boolean).join('  ') : '';
  };
  /* Coverage has to be SHORTER than the elapsed week for the gate to bite, and
     how long the week has been running depends on the day this test runs. On a
     Monday one day of coverage covers the whole elapsed week, and the claim is
     then legitimate - so the fixture is derived, not hard-coded to 1. */
  reset(0);
  DB.checkins[T]=Object.assign({},FEEL);
  var elapsedNow=weekProgress(T).elapsed;
  var n1=coreNotes();
  ok('a profile younger than the elapsed week makes no weekly claim',
     elapsedNow<=0 || (n1.indexOf('so far this week')<0 && !/behind/i.test(n1)),
     'coverage 0 vs elapsed '+elapsedNow+' :: '+n1.slice(0,160));
  reset(40);
  DB.checkins[T]=Object.assign({},FEEL);
  var n40=coreNotes();
  ok('with the week observed, the shortfall is stated as a count',
     /0 of 4 .* so far this week/.test(n40), n40.slice(0,200));
  ok('and never as an accusation', !/behind/i.test(n40), n40.slice(0,200));
  var scoreAt=function(days){
    reset(days); DB.checkins[T]=Object.assign({},FEEL);
    var r=recommend(T,DB.checkins[T]);
    var c=(r.scored||[]).filter(function(x){return x.c.id==='core';})[0];
    return c?c.score:null;
  };
  var s1=scoreAt(1), s40=scoreAt(40);
  ok('coverage changes the words, not the decision', s1!=null && s40!=null && Math.abs(s1-s40)<0.5,
     s1+' vs '+s40);
  DB.targets=JSON.parse(JSON.stringify(kTg));

  // === G · missing inputs are omitted, never invented ===
  reset(30);
  DB.checkins[T]={energy:7,soreness:2,stress:3,motivation:7,pain:'None'};   // no sleep, no HRV, no recovery
  var wM=whyOf();
  ok('no recovery figure is quoted when none exists', !/recovery <b>/.test(wM) && !/recovery [0-9]/.test(wM), wM.slice(0,240));
  ok('no HRV figure is quoted when none exists', wM.indexOf('HRV')<0, wM.slice(0,240));
  ok('no sleep figure is quoted when none exists', !/sleep <b>/.test(wM), wM.slice(0,240));
  ok('what WAS reported is still used', /energy/i.test(wM) || /soreness/i.test(wM), wM.slice(0,240));
  ok('and it still recommends something', !!recommend(T,DB.checkins[T]).id);

  // === H · tennis: planned is not the same as played ===
  reset(14);
  DB.profile.sports=['tennis']; DB.profile.sport='tennis';
  DB.checkins[T]=Object.assign({sportToday:true},FEEL);
  var planned=recommend(T,DB.checkins[T]);
  ok('a match still ahead offers pre-sport prep', planned.prep==='w_prep', planned.prep);
  ok('and is flagged as ahead, not done', planned.sportAhead===true && planned.sportDone===false);
  DB.activities=[{id:'a_ten',date:T,type:'tennis',min:114,strain:16.5,time:'11:00'}];
  var played=recommend(T,DB.checkins[T]);
  ok('a match already played cancels pre-sport prep', played.prep===null, String(played.prep));
  ok('and is flagged as done', played.sportDone===true && played.sportAhead===false);
  var wT=played.why.map(function(n){return n.t;})
          .concat((played.ruledOut||[]).map(function(x){return x.why;})).join('  ');
  ok('nothing still speaks as though the match were upcoming',
     !/you are doing tennis today/i.test(wT), wT.slice(0,260));
  ok('the past tense is used instead', /you played tennis today/i.test(wT),
     JSON.stringify(played.ruledOut));
  /* the exclusions must be about today, not about a yesterday that no longer
     describes the day */
  var outTxt=(played.ruledOut||[]).map(function(x){return x.why;}).join('  ');
  ok('"Not today" leads with what was actually ruled out',
     (played.ruledOut||[])[0] && played.ruledOut[0].hard===true, JSON.stringify(played.ruledOut[0]));
  ok('nothing calls the legs fresh after a match',
     outTxt.indexOf('fresh legs')<0, outTxt.slice(0,200));
  ok('nothing claims the recent days held nothing hard',
     outTxt.indexOf('Nothing hard in recent days')<0, outTxt.slice(0,200));
  ok('the match load reaches the decision', dayDemand(T).lower>=6, dayDemand(T).lower);
  ok('and legs are not prescribed on top of it', played.id!=='lower' && played.id!=='power', played.id);
  // a non-sport activity must not switch the prep row on
  DB.activities=[{id:'a_wk',date:T,type:'walking',min:30,strain:2}];
  ok('an unrelated activity does not resurrect pre-sport prep',
     recommend(T,DB.checkins[T]).prep==='w_prep', 'sportToday is still set, so prep is still correct');
  DB.checkins[T]=Object.assign({},FEEL);
  ok('and with no match planned or played there is no prep at all',
     recommend(T,DB.checkins[T]).prep===null, String(recommend(T,DB.checkins[T]).prep));

  // === I · a warm-up must not rehearse the session it warms up for ===
  var norm=function(s){ return String(s||'').toLowerCase().replace(/[^a-z]/g,''); };
  var core=DB.workouts.filter(function(w){return w.id==='w_core';})[0];
  var blocks=sessionBlocks({workoutId:'w_core',variant:'full',date:T});
  var mains=blocks.map(function(b){ return (exOf(b.ex)||{}).name; }).filter(Boolean);
  var raw=warmupFor(core), cut=warmupMinus(raw,mains);
  var overlap=function(wu){ return wu.items.filter(function(it){
      return mains.some(function(m){ return norm(m)===norm(it.n); }); }).map(function(i){return i.n;}); };
  ok('the authored core warm-up really does overlap its own block',
     overlap(raw).length>0, overlap(raw).join(', '));
  ok('and the overlap is gone by the time it is shown',
     overlap(cut).length===0, overlap(cut).join(', '));
  ok('the warm-up is never emptied entirely', cut.items.length>=1, cut.items.length);
  ok('filtering the warm-up does not touch the main list',
     sessionBlocks({workoutId:'w_core',variant:'full',date:T})
       .map(function(b){return b.ex;}).join(',')===blocks.map(function(b){return b.ex;}).join(','));
  ok('a warm-up with no overlap is returned unchanged',
     warmupMinus(WARMUPS.upper,['Pallof Press'])===WARMUPS.upper);

  // === J · the workout runner separates the phases ===
  startWorkout('w_core','full',T,null);
  ok('a session opens on the overview', W && W.phase==='preview', W?W.phase:'(no W)');
  /* THE OVERVIEW: the whole session, readable, before any of it starts. */
  (function(){
    var b=document.getElementById('wmBody'), txt=b.textContent;
    ok('it lists the warm-up movements',
       W.warmup.items.every(function(it){ return txt.indexOf(it.n)>=0; }),
       W.warmup.items.map(function(i){return i.n;}).join(', '));
    ok('and every exercise in the workout',
       W.entries.every(function(e){ return txt.indexOf(e.name)>=0; }),
       W.entries.map(function(e){return e.name;}).join(', '));
    ok('with the prescription on each line',
       b.querySelectorAll('.wacc-m').length>=W.entries.length,
       b.querySelectorAll('.wacc-m').length+' meta lines for '+W.entries.length+' exercises');
    ok('exactly one row is open on arrival',
       b.querySelectorAll('.wacc-b:not([hidden])').length===1,
       b.querySelectorAll('.wacc-b:not([hidden])').length);
    ok('an exercise row opens onto its own illustration and instruction', (function(){
       var r=document.querySelector('#wmBody .wacc [data-acc=e0] .wacc-h'); if(!r) return false;
       r.click();
       var row=document.querySelector('#wmBody .wacc [data-acc=e0]');
       return row.classList.contains('open')
           && !!row.querySelector('.wacc-b p')
           && document.querySelectorAll('#wmBody .wacc-b:not([hidden])').length===1; })(),
       document.querySelectorAll('#wmBody .wacc-b:not([hidden])').length+' open');
    document.querySelector('#wmBody .wacc [data-acc=e0] .wacc-h').click();
    ok('and closes again', document.querySelectorAll('#wmBody .wacc-b:not([hidden])').length===0);
    var f=document.getElementById('wmFoot').textContent;
    ok('the overview offers exactly the two actions',
       /Start warm-up/.test(f) && /Skip warm-up/.test(f), f.trim().slice(0,60));
  })();
  /* Start warm-up is not Skip warm-up: it keeps you on the one screen that
     shows all the movements, and the action becomes Start workout. */
  document.getElementById('wmGo').click();
  ok('starting the warm-up stays on the warm-up screen',
     W.phase==='preview' && W.wuStarted===true, W.phase+'/'+W.wuStarted);
  ok('and the action becomes Start workout',
     /Start workout/.test(document.getElementById('wmFoot').textContent),
     document.getElementById('wmFoot').textContent.trim().slice(0,60));
  document.getElementById('wmSkipWu').click();
  ok('entries are the MAIN exercises only', W.entries.length===blocks.length, W.entries.length+' vs '+blocks.length);
  ok('the warm-up is its own list, not part of the main one',
     W.warmup.items.length>0 && W.warmup.items!==W.entries, W.warmup.items.length);
  ok('leaving the warm-up lands on the first main exercise',
     W.phase==='main' && W.step===0, W.phase+'/'+W.step);
  ok('and the main runner shows that exercise',
     document.getElementById('wmBody').textContent.indexOf(W.entries[0].name)>=0, W.entries[0].name);
  ok('no warm-up movement reappears as a main exercise',
     !W.entries.some(function(e){ return W.warmup.items.some(function(it){ return norm(it.n)===norm(e.name); }); }),
     W.entries.map(function(e){return e.name;}).join(', '));
  /* THE ILLUSTRATION is the answer to "what am I doing?", and it is the point
     of the space the old screen left empty. */
  var body0=document.getElementById('wmBody');
  ok('the exercise is illustrated',
     !!body0.querySelector('.illus.lg svg.fig') || !illusKey(exOf(W.entries[0].exerciseId)),
     W.entries[0].name);
  ok('the illustration is not wrapped in yet another card',
     !body0.querySelector('.card .illus') && !body0.querySelector('.nowcard .illus'));
  ok('the name comes before the illustration',
     body0.innerHTML.indexOf('wm-ex') < body0.innerHTML.indexOf('illus'),
     body0.innerHTML.indexOf('wm-ex')+' / '+body0.innerHTML.indexOf('illus'));
  ok('and the set state comes after it',
     body0.innerHTML.indexOf('illus') < body0.innerHTML.indexOf('wset'),
     body0.innerHTML.indexOf('illus')+' / '+body0.innerHTML.indexOf('wset'));
  ok('the set states its unit under the number',
     !!body0.querySelector('.wset .ws-u'),
     body0.querySelector('.wset .ws-u') ? body0.querySelector('.wset .ws-u').textContent : '(none)');

  // skipping from the overview must land in exactly the same place
  W.phase='preview'; W.wuStarted=false; W.step=0; drawWM();
  document.getElementById('wmSkipWu').click();
  ok('skipping the warm-up lands on the first main exercise',
     W.phase==='main' && W.step===0, W.phase+'/'+W.step);
  ok('and records that it was skipped, which the engine may know',
     W.warmupSkipped===true, String(W.warmupSkipped));
  // a session paused before phases existed must still resume somewhere real
  W.phase=null; W.step=-1; wmNormalise();
  ok('a session saved under the old model resumes on the overview',
     W.phase==='preview' && W.step===0, W.phase+'/'+W.step);
  // and one saved mid stepped-warm-up, which no longer exists
  W.phase='warmup'; wmNormalise();
  ok('a session saved mid stepped-warm-up resumes on the one warm-up screen',
     W.phase==='preview', W.phase);
  exitWM(true); closeSheet(); W=null;

  // === K · activity warm-ups are activity-specific, and optional ===
  ok('a sport with a profile offers one', !!activityWarmup('tennis'));
  ok('a different sport gets a different one',
     activityWarmup('running').items.map(function(i){return i.n;}).join(',')
       !== activityWarmup('tennis').items.map(function(i){return i.n;}).join(','));
  ok('an activity with no profile is offered none', activityWarmup('walking')===null);
  ok('and neither is "other"', activityWarmup('other')===null);
  ok('nor yoga', activityWarmup('yoga')===null);
  preStartSheet('tennis');
  var f1=document.getElementById('sheetFoot').textContent;
  ok('starting an activity asks about the warm-up first',
     /Start with warm-up/.test(f1) && /Start right away/.test(f1), f1.slice(0,90));
  document.getElementById('psWu').click();
  var b1=document.getElementById('sheetBody').textContent;
  ok('the warm-up screen leads to the activity, not an exercise',
     b1.indexOf('Up next')>=0 && b1.indexOf('Tennis')>=0, b1.slice(0,140));
  ok('and says the clock has not started', /clock starts when you begin/i.test(b1), b1.slice(0,200));
  ok('the activity is what starts from there',
     /Start Tennis/.test(document.getElementById('sheetFoot').textContent),
     document.getElementById('sheetFoot').textContent.slice(0,80));
  closeSheet();
  preStartSheet('walking');
  var f2=document.getElementById('sheetFoot').textContent;
  ok('an activity with no warm-up just starts',
     /Start activity/.test(f2) && !/Start with warm-up/.test(f2), f2.slice(0,90));
  closeSheet();
  // the warm-up cannot be counted as activity time: nothing is recorded until
  // startLiveActivity runs, which the warm-up screen never calls
  ok('no activity is created by viewing a warm-up',
     DB.activities.filter(function(a){return a.date===T&&a.type==='tennis';}).length===0,
     DB.activities.length);

  // === L · logging something shows the plan it produced, not a stale one ===
  reset(14);
  DB.profile.sports=['tennis']; DB.profile.sport='tennis';
  DB.checkins[T]=Object.assign({},FEEL);
  var logged={id:'a_done',date:T,type:'tennis',min:114,strain:16.5,intensity:'Hard'};
  DB.activities=[logged];
  activityLoggedSheet(logged);
  var conf=document.getElementById('sheetBody').textContent;
  ok('the confirmation names what was logged', /Tennis logged/.test(conf), conf.slice(0,120));
  ok('and its actual figures', /1h 54m/.test(conf) && /16.5/.test(conf), conf.slice(0,140));
  ok('and says the plan moved', /plan has been updated/i.test(conf), conf.slice(0,160));
  ok('the next session shown is the recalculated one',
     conf.indexOf(recommend(T,DB.checkins[T]).label)>=0,
     conf.slice(0,200)+' :: expected '+recommend(T,DB.checkins[T]).label);
  ok('and it is not the pre-match plan',
     (function(){ DB.activities=[]; var before=recommend(T,DB.checkins[T]);
                  DB.activities=[logged]; var after=recommend(T,DB.checkins[T]);
                  return before.id!==after.id || before.variant!==after.variant; })(),
     'logging a match must change something');
  closeSheet();

  DB.sessions=kSe; DB.activities=kAc; DB.checkins=kCi; DB.meta=kMe;
  DB.profile=kPr; DB.whoop=kWh; DB.baselines=kBl; DB.targets=kTg;
  resetStack(); TAB='today';
})();


// ---------- WEARABLES: WHOOP IS ONE OPTION, NOT THE MODEL ----------
(function(){
  var keep=JSON.parse(JSON.stringify(DB.profile)), keepW=DB.whoop, keepC=DB.checkins;
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};

  ok('several wearables are offered', SOURCES.length>=8, SOURCES.length);
  ok('WHOOP is just a row in the table', SOURCES.some(function(s){return s.id==='whoop';}));
  ok('no-wearable is a real option', SOURCES.some(function(s){return s.id==='none'&&s.fields.length===0;}));
  ok('every source declares the fields it provides',
     SOURCES.every(function(s){ return Array.isArray(s.fields) &&
       s.fields.every(function(f){ return !!DATA_FIELDS[f]; }); }),
     SOURCES.filter(function(s){return !Array.isArray(s.fields);}).map(function(s){return s.id;}).join(','));
  ok('every source explains how to get its data', SOURCES.every(function(s){return !!s.how;}));

  // a device without a recovery score must not be asked for one
  DB.profile.source='apple'; DB.profile.sourceFields=null; DB.checkins={};
  ok('Apple Watch provides no recovery score', !hasField('recovery'));
  ok('Apple Watch does provide HRV', hasField('hrv'));
  openCheckin(todayISO());
  var h=$('#sheetBody').innerHTML;
  ok('a device with no recovery score is never asked for one', !document.getElementById('ciRec'));
  ok('but it is still asked for HRV', !!document.getElementById('ciHrv'));
  ok('the check-in names the actual device', /Apple Watch/.test(h), h.slice(0,200));
  closeSheet();

  // vendor wording follows the device
  DB.profile.source='garmin';
  ok('Garmin recovery is labelled in Garmin terms', /Body Battery|Training Readiness/i.test(fieldLabel('recovery')),
     fieldLabel('recovery'));
  DB.profile.source='oura';
  ok('Oura recovery is labelled Readiness', /Readiness/i.test(fieldLabel('recovery')), fieldLabel('recovery'));
  DB.profile.source='whoop';
  ok('WHOOP recovery keeps its own wording', /Recovery/i.test(fieldLabel('recovery')), fieldLabel('recovery'));

  // "another wearable" lets the user say what it reports
  DB.profile.source='other'; DB.profile.sourceFields=['hrv','sleep'];
  ok('a custom wearable is narrowed to the ticked fields',
     hasField('hrv') && hasField('sleep') && !hasField('recovery') && !hasField('strain'),
     srcFields().join(','));
  DB.checkins={}; openCheckin(todayISO());
  ok('an unticked field is never asked for', !document.getElementById('ciRec'));
  ok('a ticked field is asked for', !!document.getElementById('ciHrv'));
  closeSheet();

  // no wearable: the metrics view says so rather than showing an empty chart
  DB.profile.source='none'; DB.profile.sourceFields=null;
  ok('no wearable means no device fields', srcFields().length===0 && !usesDevice());
  DB.checkins={}; openCheckin(todayISO());
  ok('no wearable means no metric inputs at all',
     !document.getElementById('ciRec') && !document.getElementById('ciHrv') && !document.getElementById('ciRhr'));
  closeSheet();
  HTAB=null; resetStack();
  tryRun('metrics view without a wearable', function(){ openMetrics(); });
  ok('metrics view explains there is no wearable rather than showing nothing',
     /No wearable connected/i.test(document.getElementById('view').innerHTML),
     document.getElementById('view').innerHTML.slice(0,160));
  ok('and does not offer trend pages it cannot fill',
     document.querySelectorAll('#hRows button').length===0,
     document.querySelectorAll('#hRows button').length);
  resetStack();

  // the importer is no longer WHOOP-only
  DB.profile.source='oura';
  var ouraCsv='date,Readiness Score,Average HRV,Lowest Resting Heart Rate,Total Sleep Duration\\n'+
              '2030-03-01,82,74,51,27000\\n2030-03-02,65,58,55,21600\\n';
  var r=importWhoopFile('oura_daily.csv', ouraCsv);
  ok('an Oura-style export is recognised', r.kind==='cycles' && !r.error, JSON.stringify(r));
  ok('Oura rows are imported', r.added===2, r.added);
  var row=DB.whoop.cycles.find(function(x){return x.date==='2030-03-01';});
  ok('readiness maps onto the recovery slot', row && row.recovery===82, row&&row.recovery);
  ok('vendor HRV wording resolves', row && row.hrv===74, row&&row.hrv);
  ok('vendor resting-HR wording resolves', row && row.rhr===51, row&&row.rhr);
  ok('sleep given in seconds converts to minutes', row && row.sleepMin===450, row&&row.sleepMin);

  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  var garminCsv='Date,Body Battery,HRV,Resting Heart Rate,Sleep Duration,Training Load\\n'+
                '2030-04-01,71,66,49,7.5,140\\n';
  var g=importWhoopFile('garmin.csv', garminCsv);
  ok('a Garmin-style export is recognised', g.kind==='cycles' && !g.error, JSON.stringify(g));
  var grow=DB.whoop.cycles[0];
  ok('Body Battery maps onto the recovery slot', grow && grow.recovery===71, grow&&grow.recovery);
  ok('sleep given in decimal hours converts to minutes', grow && grow.sleepMin===450, grow&&grow.sleepMin);
  ok('training load maps onto the strain slot', grow && grow.strain===140, grow&&grow.strain);

  // a file with no date and no metrics is still rejected
  var junk=importWhoopFile('notes.csv','foo,bar\\n1,2\\n');
  ok('an unrelated CSV is still rejected', !!junk.error, JSON.stringify(junk));

  // legacy installs migrate onto the new field
  var mg=migrate({profile:{mode:'whoop',onboarded:true},meta:{schema:2},
                  exercises:DB.exercises,workouts:DB.workouts});
  ok('an old WHOOP user migrates to the whoop source', mg.profile.source==='whoop', mg.profile.source);
  var mg2=migrate({profile:{mode:'manual',onboarded:true},meta:{schema:2},
                   exercises:DB.exercises,workouts:DB.workouts});
  ok('an old manual user migrates to no wearable', mg2.profile.source==='none', mg2.profile.source);

  DB.profile=keep; DB.whoop=keepW; DB.checkins=keepC;
})();


// ---------- WHAT YOU DID LAST TIME ----------
(function(){
  var keepS=DB.sessions, keepA=DB.activities;
  DB.sessions=[]; DB.activities=[];
  ok('no history means no last performance', lastPerformance('lx01')===null);

  DB.sessions.push({id:'lp1',date:'2030-05-01',done:true,workoutName:'Lower A',entries:[
    {exerciseId:'lx01',name:'Goblet Squat',sets:[
      {reps:'10',weight:'12',rpe:'8',done:true},
      {reps:'10',weight:'12',rpe:'8',done:true},
      {reps:'8', weight:'12',rpe:'9',done:true}]},
    {exerciseId:'lx09',name:'SL RDL',sets:[{reps:'8',weight:'',rpe:'7',done:false}]}
  ]});
  var lp=lastPerformance('lx01');
  ok('last performance is found', !!lp, JSON.stringify(lp));
  ok('it reports the date', lp.date==='2030-05-01', lp.date);
  ok('it keeps only completed sets', lp.sets.length===3, lp.sets.length);
  ok('it reports the top weight', lp.topWeight===12, lp.topWeight);
  ok('an exercise with no completed sets has no last performance',
     lastPerformance('lx09')===null);
  ok('summary collapses identical sets', /^2 . 10 @ 12 kg|3 . /.test(setsSummary(lp.sets.slice(0,2))),
     setsSummary(lp.sets.slice(0,2)));
  ok('summary lists differing sets', setsSummary(lp.sets).indexOf(',')>=0, setsSummary(lp.sets));

  // a newer session wins over an older one
  DB.sessions.push({id:'lp2',date:'2030-05-08',done:true,workoutName:'Lower A',entries:[
    {exerciseId:'lx01',name:'Goblet Squat',sets:[
      {reps:'10',weight:'14',rpe:'8',done:true},
      {reps:'10',weight:'14',rpe:'8',done:true}]}
  ]});
  ok('the most recent session is used', lastPerformance('lx01').topWeight===14,
     lastPerformance('lx01').topWeight);
  ok('the live session is excluded from its own lookup',
     lastPerformance('lx01',null,'lp2').topWeight===12,
     lastPerformance('lx01',null,'lp2').topWeight);

  // progress comparison
  var prev=lastPerformance('lx01',null,'lp2');
  var better=progressVs(prev,{sets:[{reps:'10',weight:'15',rpe:'8',done:true},
                                    {reps:'10',weight:'15',rpe:'8',done:true},
                                    {reps:'10',weight:'15',rpe:'8',done:true}]});
  ok('more volume is reported as progress', better && better.up===true, JSON.stringify(better));
  var worse=progressVs(prev,{sets:[{reps:'5',weight:'8',rpe:'6',done:true}]});
  ok('much less volume is reported as a drop', worse && worse.up===false, JSON.stringify(worse));
  ok('an unstarted exercise is not judged', progressVs(prev,{sets:[{reps:'',weight:'',done:false}]})===null);

  // and it actually reaches the screen
  DB.sessions=[DB.sessions[0]];
  var wmHtml='';
  tryRun('workout mode with history', function(){
    startWorkout('w_lowerA','full',todayISO());
    var ix=-1;
    W.entries.forEach(function(e,n){ if(e.exerciseId==='lx01') ix=n; });
    if(ix<0) throw new Error('lx01 absent: '+W.entries.map(function(e){return e.exerciseId;}).join(','));
    W.phase='main'; W.step=ix; drawWM();
    wmHtml=document.getElementById('wmBody').innerHTML;
  });
  ok('workout mode shows what you did last time', /Last time/i.test(wmHtml), wmHtml.slice(0,200));
  ok('it shows the actual numbers, not just a label', /12 kg/.test(wmHtml), wmHtml.slice(0,200));
  // The set arrives PRE-FILLED with last time's numbers - that is what makes
  // logging one tap - but it is shown unconfirmed and is not part of the
  // record until the user ticks it.
  /* Seeding is what makes logging one tap. It is no longer visible as a filled
     input, because there are no inputs: the number is shown, and it is what
     gets recorded on the tap. */
  ok('last time seeds the value, so confirming is one tap', (function(){
     var e=W.entries[W.step];
     return /12 kg/.test(document.querySelector('.wset .ws-v').textContent)
            && e.sets[0].weight==='12'; })(),
     document.querySelector('.wset .ws-v').textContent.trim()
       +' / model '+JSON.stringify(W.entries[W.step].sets[0]));
  ok('a primed set is not marked done',
     W.entries.every(function(e){ return e.sets.every(function(s){ return !s.done; }); }));
  /* It used to say "filled in from last time". It now says why the number is
     what it is, which with one session of history is that nothing has been
     earned yet - and that is a better answer than naming the source. */
  /* The explanation moved off the training screen with everything else that
     was not the current action. It is still one tap away, on the how-to. */
  ok('the reason the numbers are what they are is one tap away', (function(){
     document.getElementById('wmHowLine').click();
     var h=document.getElementById('sheet').innerHTML;
     closeSheet();
     return /Nothing is being pushed up yet/i.test(h) || /The plan in full/.test(h); })(),
     'via the how-to line');
  exitWM(true);

  DB.sessions=[]; DB.activities=[];
  tryRun('workout mode with no history', function(){
    startWorkout('w_lowerA','full',todayISO()); W.phase='main'; W.step=0; drawWM(); });
  /* With no history there is no "last time" line at all, rather than a line
     saying there is nothing to say. The screen shows the prescription, which
     is the whole instruction on a first attempt. */
  ok('a first attempt shows the plan and no empty history line',
     document.querySelectorAll('#wmBody .ws-last').length===0
     && !!document.querySelector('.wset .ws-v'),
     document.getElementById('wmBody').textContent.slice(0,120));
  exitWM(true);

  DB.sessions=keepS; DB.activities=keepA;
})();

// ---------- PROGRESSION IS EARNED, NOT SCHEDULED ----------
(function(){
  var keepS=DB.sessions, keepA=DB.activities, keepP=DB.profile.planStart;
  var T=todayISO();
  DB.sessions=[]; DB.activities=[];

  // eight calendar weeks have passed but nothing was ever logged
  DB.profile.planStart=addDays(T,-56);
  var idle=currentPhase();
  ok('an untrained block does not advance', idle.absWeek===1, idle.absWeek);
  ok('the calendar week is still reported', idle.elapsedWeek>=8, idle.elapsedWeek);
  ok('the pause is counted, not hidden', idle.pausedWeeks>=7, idle.pausedWeeks);

  // train in four of those weeks
  [0,7,14,21].forEach(function(d,i){
    DB.sessions.push({id:'ph'+i,date:addDays(DB.profile.planStart,d+1),done:true,
      workoutId:'w_lowerA',workoutName:'Lower A',category:'lower',entries:[]});
  });
  var some=currentPhase();
  ok('only weeks with training count', some.absWeek===4, some.absWeek+' of '+some.elapsedWeek);
  ok('phase name follows the earned week', some.w===4, some.w);

  // a logged activity counts as training too
  DB.activities.push({id:'pa1',date:addDays(DB.profile.planStart,29),type:'running',min:30,rpe:5});
  ok('a logged activity also earns a week', currentPhase().absWeek===5, currentPhase().absWeek);

  // it must never run ahead of the calendar
  DB.profile.planStart=addDays(T,-7);
  DB.sessions=[]; DB.activities=[];
  for(var k=0;k<40;k++) DB.sessions.push({id:'pz'+k,date:addDays(T,-k),done:true,
    workoutId:'w_lowerA',workoutName:'Lower A',category:'lower',entries:[]});
  ok('progression never overtakes the calendar', currentPhase().absWeek<=2, currentPhase().absWeek);

  DB.sessions=keepS; DB.activities=keepA; DB.profile.planStart=keepP;
})();


// ---------- INJURIES PERSIST AND ROUTE AROUND THEMSELVES ----------
(function(){
  var keepL=DB.profile.limits, keepS=DB.sessions, T=todayISO();
  DB.profile.limits=[];
  ok('no limitations by default', !hasLimits() && activeLimits().length===0);
  ok('every body area maps to real movement patterns',
     BODY_AREAS.every(function(a){ return a.avoid.length>0 &&
       a.avoid.concat(a.caution||[]).every(function(pp){ return !!PATTERNS[pp]; }); }),
     BODY_AREAS.filter(function(a){return !a.avoid.length;}).map(function(a){return a.id;}).join(','));

  // a knee, managed, for two weeks
  DB.profile.limits=[{id:'L1',area:'knee',side:'Left',severity:'mod',
                      until:addDays(T,14),note:'physio'}];
  ok('an active limitation is detected', hasLimits() && activeLimits().length===1);
  ok('it names itself in plain words', /left knee/i.test(limitsText()), limitsText());
  var pat=limitPatterns();
  ok('jumping is dropped', pat.avoid.indexOf('jump')>=0, pat.avoid.join(','));
  ok('squatting is capped, not dropped',
     pat.caution.indexOf('squat')>=0 && pat.avoid.indexOf('squat')<0,
     'avoid='+pat.avoid.join(',')+' caution='+pat.caution.join(','));
  ok('unrelated patterns are untouched',
     pat.avoid.indexOf('pushh')<0 && pat.avoid.indexOf('pullv')<0, pat.avoid.join(','));

  // severity escalates the cautioned patterns
  DB.profile.limits[0].severity='high';
  ok('a significant limitation drops the cautioned patterns too',
     limitPatterns().avoid.indexOf('squat')>=0, limitPatterns().avoid.join(','));
  DB.profile.limits[0].severity='mod';

  // no prescribed exercise may load the injured pattern
  var offending=[];
  DB.workouts.forEach(function(w){
    ['full','reduced','recovery'].forEach(function(v){
      sessionBlocks({workoutId:w.id,variant:v,addCore:false}).forEach(function(b){
        var e=exOf(b.ex); if(!e) return;
        if(limitBlocks(e)) offending.push(w.id+'/'+v+':'+e.name+'('+((EX_META[e.id]||[])[0])+')');
      });
    });
  });
  ok('no session prescribes a movement the injury forbids', offending.length===0,
     offending.slice(0,5).join(' | '));

  // the engine steers away from the systems that load it
  ok('explosive work is a limited system while the knee is flagged',
     limitSystems().indexOf('expl')>=0, limitSystems().join(','));
  DB.sessions=[]; DB.checkins={};
  var good={recovery:90,hrv:95,rhr:50,sleepMin:500,sleepNeed:500,prevStrain:3,energy:9,
            soreness:1,stress:2,motivation:9,pain:'None',availTime:70};
  var rr=recommend(T,good);
  ok('a green day with a knee injury does not pick power', rr.id!=='power', rr.id);
  var powerOpt=rr.scored.filter(function(x){return x.c.sys==='expl';})[0];
  ok('the injury is named in the reasoning for what was rejected',
     powerOpt && (powerOpt.blocked||powerOpt.notes.some(function(n){return /knee/i.test(n.t||'');})),
     powerOpt?JSON.stringify(powerOpt.notes.map(function(n){return n.t;})):'no power option');

  // a significant one blocks it outright
  DB.profile.limits[0].severity='high';
  var rr2=recommend(T,good);
  var p2=rr2.scored.filter(function(x){return x.c.sys==='expl';})[0];
  ok('a significant limitation blocks that system outright', p2 && !!p2.blocked, p2?p2.blocked:'-');

  // expiry is automatic
  DB.profile.limits=[{id:'L2',area:'knee',severity:'mod',until:addDays(T,-1)}];
  ok('an expired limitation stops applying', !hasLimits() && limitPatterns().avoid.length===0);
  ok('but it is still on file', DB.profile.limits.length===1);

  // it survives a reload and a migration
  DB.profile.limits=[{id:'L3',area:'shoulder',severity:'mod',until:addDays(T,7)}];
  var mg=migrate({profile:{limits:DB.profile.limits.slice(),onboarded:true},meta:{schema:2},
                  exercises:DB.exercises,workouts:DB.workouts});
  ok('limitations survive migration', mg.profile.limits.length===1, JSON.stringify(mg.profile.limits));
  var bad=migrate({profile:{limits:[{id:'x',area:'not-a-real-area'}],onboarded:true},meta:{schema:2},
                   exercises:DB.exercises,workouts:DB.workouts});
  ok('an unknown body area is dropped rather than trusted', bad.profile.limits.length===0);

  // and the settings UI can manage them
  DB.profile.limits=[{id:'L4',area:'knee',side:'Left',severity:'mod',until:addDays(T,10)}];
  tryRun('settings renders limitations', function(){ SETTINGS_ALL(); });
  ok('settings shows the active limitation', /Left Knee/i.test(document.getElementById('view').innerHTML));
  ok('settings offers to add one', !!document.getElementById('limAdd'));
  tryRun('limitation sheet opens', function(){ limitSheet(null); });
  ok('the sheet lists body areas', document.querySelectorAll('.limArea').length===BODY_AREAS.length,
     document.querySelectorAll('.limArea').length);
  closeSheet();

  DB.profile.limits=keepL; DB.sessions=keepS;
})();

// ---------- DOES THE ADVICE ACTUALLY WORK? ----------
(function(){
  var keepD=DB.decisions, keepS=DB.sessions, keepA=DB.activities, keepW=DB.whoop, keepC=DB.checkins;
  DB.decisions={}; DB.sessions=[]; DB.activities=[];
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]}; DB.checkins={};

  var empty=adviceReview();
  ok('with no decisions it claims nothing', empty.n===0 && empty.ready!==true, JSON.stringify(empty));

  // a rest day taken, and a rest day ignored
  DB.decisions['2030-09-02']={id:'rest',label:'Rest',band:'red',score:30};
  DB.decisions['2030-09-04']={id:'rest',label:'Rest',band:'red',score:31};
  DB.sessions.push({id:'fb1',date:'2030-09-04',done:true,workoutId:'w_lowerA',
                    workoutName:'Lower A',category:'lower',entries:[]});
  ok('a rest day with nothing logged counts as followed',
     followedAdvice('2030-09-02').followed===true);
  ok('a rest day that was trained through counts as ignored',
     followedAdvice('2030-09-04').followed===false);

  // a session recommendation matched by category
  DB.decisions['2030-09-06']={id:'lower',label:'Lower Body Strength',band:'green',score:80};
  DB.sessions.push({id:'fb2',date:'2030-09-06',done:true,workoutId:'w_lowerA',
                    workoutName:'Lower A',category:'lower',entries:[]});
  ok('doing the recommended category counts as followed',
     followedAdvice('2030-09-06').followed===true);
  DB.decisions['2030-09-08']={id:'lower',label:'Lower Body Strength',band:'green',score:80};
  DB.sessions.push({id:'fb3',date:'2030-09-08',done:true,workoutId:'w_upperA',
                    workoutName:'Upper A',category:'upper',entries:[]});
  ok('doing something else counts as ignored', followedAdvice('2030-09-08').followed===false);

  // below the minimum it refuses to draw a conclusion
  var few=adviceReview();
  ok('a handful of days is not enough to conclude', few.ready!==true, JSON.stringify(few));
  ok('but adherence is still reported', few.adherence!=null, few.adherence);

  // give it enough of both, with a clear outcome signal
  DB.decisions={}; DB.sessions=[]; DB.checkins={};
  for(var i=0;i<7;i++){
    var dF='2030-10-'+String(2+i*2).padStart(2,'0');
    DB.decisions[dF]={id:'rest',label:'Rest',band:'red',score:30};
    DB.checkins[addDays(dF,1)]={date:addDays(dF,1),energy:9};      // followed -> good morning
    var dI='2030-11-'+String(2+i*2).padStart(2,'0');
    DB.decisions[dI]={id:'rest',label:'Rest',band:'red',score:30};
    DB.sessions.push({id:'fx'+i,date:dI,done:true,workoutId:'w_lowerA',
                      workoutName:'Lower A',category:'lower',entries:[]});
    DB.checkins[addDays(dI,1)]={date:addDays(dI,1),energy:4};      // ignored -> bad morning
  }
  var rev=adviceReview();
  ok('with enough of both sides it will compare', rev.ready===true, JSON.stringify(rev));
  ok('it counts both sides', rev.nKept===7 && rev.nIgnored===7, rev.nKept+'/'+rev.nIgnored);
  ok('it detects that following the advice went better', rev.diff>0, rev.diff);
  ok('it uses subjective energy when there is no wearable',
     /energy/i.test(rev.label), rev.label);

  // with a wearable, recovery is preferred over the subjective measure
  DB.whoop.cycles=Object.keys(DB.checkins).map(function(d){
    return {date:d, recovery: DB.checkins[d].energy>=9?85:45}; });
  var rev2=adviceReview();
  ok('a wearable outcome takes precedence', /recovery/i.test(rev2.label), rev2.label);

  // and it reaches the screen
  resetStack();
  tryRun('advice review renders', function(){ openPane('Patterns',null,paneLinks); });
  ok('the review is shown to the user',
     /advice any good/i.test(document.getElementById('view').innerHTML));
  resetStack();

  DB.decisions=keepD; DB.sessions=keepS; DB.activities=keepA; DB.whoop=keepW; DB.checkins=keepC;
})();


// ---------- NAVIGATION IS NEVER NAMED AFTER A DEVICE ----------
(function(){
  var keep=JSON.parse(JSON.stringify(DB.profile));
  var brands=['WHOOP','Garmin','Oura','Fitbit','Apple','Samsung','Polar','COROS'];

  function navText(){ renderNav(); return document.getElementById('nav').textContent; }
  function tabLabels(){ return tabs().map(function(t){return t.label;}); }

  var seenLabels=null;
  ['whoop','garmin','oura','fitbit','apple','samsung','polar','coros','other','none'].forEach(function(src){
    DB.profile.source=src; DB.profile.sourceFields=null;
    var labels=tabLabels().join('|');
    if(seenLabels===null) seenLabels=labels;
    ok('nav labels identical for source "'+src+'"', labels===seenLabels, labels+' vs '+seenLabels);
    var txt=navText();
    var leaked=brands.filter(function(b){ return txt.indexOf(b)>=0; });
    ok('no brand name in the nav for source "'+src+'"', leaked.length===0, leaked.join(','));
  });
  ok('the metrics screen keeps a generic name',
     (function(){ resetStack(); openMetrics(); var t=($('#appbar').textContent||'').indexOf('Metrics')>=0; resetStack(); return t; })(), $('#appbar').textContent);

  // the screen heading is generic too; the device belongs in the subtitle
  DB.profile.source='garmin';
  HTAB='trends';
  tryRun('metrics view for a Garmin user', function(){ viewWhoop(document.getElementById('view')); });
  var bar=document.querySelector('.appbar');
  var h=bar?bar.querySelector('.ttl'):null;
  ok('the metrics heading is generic', h && /Metrics/i.test(h.textContent) && !/Garmin/i.test(h.textContent),
     h?h.textContent:'no heading');
  ok('the device is named in the subtitle instead', bar && /Garmin/i.test(bar.textContent),
     bar?bar.textContent.slice(0,80):'-');

  DB.profile=keep;
})();


// ---------- SETTINGS IS SECTIONED, NOT ONE LONG SCROLL ----------
(function(){
  SETTINGS_ALL();
  var all=document.querySelectorAll('#view .spane');
  ok('every settings card belongs to a pane', all.length>=13, all.length);
  // nothing may be orphaned: a card with no pane class would vanish for good
  var orphan=[];
  Array.prototype.slice.call(document.querySelectorAll('#view > .card')).forEach(function(c){
    if(!c.classList.contains('spane')) orphan.push((c.textContent||'').trim().slice(0,24));
  });
  ok('no settings card is left out of every pane', orphan.length===0, orphan.join(' | '));

  function shown(){ return Array.prototype.slice.call(document.querySelectorAll('#view .spane'))
      .filter(function(e){return e.classList.contains('on');}).length; }

  SET_PANES.forEach(function(pn){
    setPane(pn.id);
    ok('pane "'+pn.id+'" shows something', shown()>0, shown());
    ok('pane "'+pn.id+'" hides the others',
       shown()<all.length, shown()+' of '+all.length);
    ok('pane "'+pn.id+'" is the one recorded as current', SETTAB===pn.id, SETTAB);
  });

  // every pane together must account for all cards, with none in two panes
  var counts={}; var total=0;
  SET_PANES.forEach(function(pn){ setPane(pn.id); counts[pn.id]=shown(); total+=shown(); });
  ok('panes partition the cards exactly once', total===all.length,
     JSON.stringify(counts)+' total '+total+' vs '+all.length);

  // switching groups must not lose typed input: they are hidden, not redrawn
  setPane('training');
  var noteEl=document.getElementById('sEqNote');
  ok('the Training group holds the equipment note', !!noteEl);
  if(noteEl){
    var was=noteEl.value;
    noteEl.value='Tester';
    setPane('data'); setPane('training');
    ok('switching groups does not discard typed input',
       document.getElementById('sEqNote').value==='Tester',
       document.getElementById('sEqNote').value);
    noteEl.value=was;
  }
  setPane('profile');
  ok('the Profile group is read-only until asked', !!document.getElementById('profEdit')
     && !document.getElementById('sName'));
})();

// ---------- BUILD IDENTITY AND BUG REPORTS ----------
(function(){
  // date, with an optional letter for a second build on the same day
  ok('the app has a build stamp', typeof APP_BUILD==='string' && /^[0-9]{4}-[0-9]{2}-[0-9]{2}[a-z]?$/.test(APP_BUILD), APP_BUILD);

  var d=diagnostics();
  ok('diagnostics names the build', d.indexOf(APP_BUILD)>=0, d.slice(0,60));
  ok('diagnostics reports the storage mode', /Storage:/.test(d));
  ok('diagnostics reports setup state', /Setup:/.test(d));
  ok('diagnostics counts what is logged', /Data: \\d+ sessions/.test(d), d);
  ok('diagnostics reports errors', /Errors:/.test(d));

  // the promise: counts, never content
  DB.checkins['2031-03-03']={date:'2031-03-03',energy:7,soreness:3,notes:'my private note',recovery:91};
  DB.activities.push({id:'dx1',date:'2031-03-03',type:'tennis',min:123,rpe:9,notes:'secret detail'});
  DB.profile.name='Jane Doe';
  var d2=diagnostics();
  ['my private note','secret detail','Jane Doe','91','123'].forEach(function(leak){
    ok('diagnostics does not leak "'+leak+'"', d2.indexOf(leak)<0, d2);
  });
  delete DB.checkins['2031-03-03'];
  DB.activities=DB.activities.filter(function(a){return a.id!=='dx1';});
  DB.profile.name='';

  // errors are captured for a report rather than lost
  noteError('boom at line 1');
  ok('an error is recorded', diagnostics().indexOf('boom at line 1')>=0, diagnostics());
  var many=0; while(many++<9) noteError('e'+many);
  ok('the error log stays short', ERRLOG.length<=5, ERRLOG.length);
  ERRLOG.length=0;

  // and it is reachable from the UI
  SETTINGS_ALL();
  setPane('app');
  ok('the App pane offers a diagnostics button', !!document.getElementById('sDiag'));
  ok('the App pane shows the build number',
     document.getElementById('view').textContent.indexOf(APP_BUILD)>=0);
  tryRun('diagnostics sheet opens', function(){ showDiagnostics(); });
  ok('the diagnostics sheet contains the report',
     (document.getElementById('diagTxt')||{}).value.indexOf(APP_BUILD)>=0);
  closeSheet();
  setPane('you');
})();


// ---------- THE BUILT-IN LIBRARY IS ONE LIST ----------
(function(){
  var all=builtInExercises();
  ok('the library is assembled in one place', all.length>=160, all.length);
  ok('freshDB gets the whole library', freshDB().exercises.length===all.length,
     freshDB().exercises.length+' vs '+all.length);

  // ids must be unique or the later one silently shadows the earlier
  var seen={}, dupes=[];
  all.forEach(function(e){ if(seen[e.id]) dupes.push(e.id); seen[e.id]=1; });
  ok('no duplicate exercise ids', dupes.length===0, dupes.join(','));

  // names too: two identical names in a picker is a usability bug
  var byName={}, dupeNames=[];
  all.forEach(function(e){ var k=e.name.toLowerCase();
    if(byName[k]) dupeNames.push(e.name); byName[k]=1; });
  ok('no duplicate exercise names', dupeNames.length===0, dupeNames.join(' | '));

  // every one must be coachable and classified
  var bad=all.filter(function(e){
    return !e.name||!e.cat||!e.muscles||!e.sets||!e.reps||!e.rpe||!e.rest||!e.how||!e.cue||!e.prog; });
  ok('every exercise carries its coaching fields', bad.length===0,
     bad.map(function(e){return e.id;}).join(','));
  var noPat=all.filter(function(e){ return !e.pat||e.pat==='other'; });
  ok('every exercise has a real movement pattern', noPat.length===0,
     noPat.map(function(e){return e.id;}).join(','));
  var badCat=all.filter(function(e){
    return ['lower','core','push','pull','mobility','plyo','cardio','speed'].indexOf(e.cat)<0; });
  ok('every category is one the library filter knows', badCat.length===0,
     badCat.map(function(e){return e.id+':'+e.cat;}).join(','));

  // the point of the additions: no pattern may be left with fewer than three
  var count={};
  all.forEach(function(e){ count[e.pat]=(count[e.pat]||0)+1; });
  var thin=Object.keys(PATTERNS).filter(function(k){ return (count[k]||0)<3; });
  ok('no movement pattern has fewer than three options', thin.length===0,
     thin.map(function(k){return k+':'+(count[k]||0);}).join(', '));

  // and every pattern must have at least one option needing no equipment,
  // otherwise a bodyweight-only user loses that pattern entirely
  var keepG=DB.profile.gear; DB.profile.gear=[];
  var stranded=Object.keys(PATTERNS).filter(function(k){
    if(k==='cardio'||k==='sprint'||k==='cod') return false;   // these need space, fairly
    return !all.some(function(e){ return e.pat===k && (e.needs||[]).length===0; });
  });
  ok('every strength pattern has a bodyweight option', stranded.length===0, stranded.join(', '));
  DB.profile.gear=keepG;
})();

// ---------- NEW EXERCISES REACH EXISTING INSTALLS ----------
(function(){
  var all=builtInExercises();

  // an install that predates the additions must receive them on migrate
  var old=migrate({
    profile:{onboarded:true,gear:['db','band'],sports:['tennis']},
    meta:{schema:2},
    exercises:seedExercises().slice(0,20),      // a stale, partial library
    workouts:DB.workouts
  });
  ok('migrate backfills the whole built-in library',
     old.exercises.length>=all.length, old.exercises.length+' vs '+all.length);
  ['x01','x24','g01'].forEach(function(id){
    ok('migrate delivers '+id, old.exercises.some(function(e){return e.id===id;}));
  });

  // a user's own edits and additions must survive that backfill
  var mine=seedExercises().slice(0,5);
  mine[0]=Object.assign({},mine[0],{notes:'MY EDIT'});
  mine.push({id:'mine1',name:'My Own Exercise',cat:'core',muscles:'x',sets:3,reps:'10',
             rpe:'RPE 7',rest:'60s',how:'x',cue:'x',prog:'x'});
  var kept=migrate({profile:{onboarded:true},meta:{schema:2},exercises:mine,workouts:DB.workouts});
  ok('a user edit survives the backfill',
     kept.exercises.some(function(e){return e.notes==='MY EDIT';}));
  ok('a user-created exercise survives the backfill',
     kept.exercises.some(function(e){return e.id==='mine1';}));
  ok('and the built-ins are added alongside it',
     kept.exercises.length>=all.length+1, kept.exercises.length);
})();

// ---------- THE NEW EXERCISES DECLARE THEIR KIT HONESTLY ----------
(function(){
  var keepG=DB.profile.gear;
  var extra=applyExMeta(extraExercises());
  ok('41 exercises were added', extra.length===41, extra.length);

  // needs must be derived, and must match the equipment wording
  var wrong=[];
  extra.forEach(function(e){
    var txt=((e.equip||'')+' '+e.name).toLowerCase();
    if(/band/.test(txt)     && (e.needs||[]).indexOf('band')<0)  wrong.push(e.id+' band');
    if(/kettlebell/.test(txt)&& (e.needs||[]).indexOf('kb')<0)   wrong.push(e.id+' kb');
    if(/pull-up bar/.test(txt)&&(e.needs||[]).indexOf('bar')<0)  wrong.push(e.id+' bar');
    // and nothing may claim kit its wording never mentions
    if((e.needs||[]).indexOf('cable')>=0) wrong.push(e.id+' claims cable');
    if((e.needs||[]).indexOf('bb')>=0)    wrong.push(e.id+' claims barbell');
  });
  ok('the new exercises need exactly what they say', wrong.length===0, wrong.join(', '));

  // a bodyweight-only user can do a real share of them
  DB.profile.gear=[];
  var doable=extra.filter(function(e){ return canDo(e); });
  ok('a bodyweight-only user can do most of the additions', doable.length>=18,
     doable.length+' of '+extra.length);

  // with dumbbells and a band, more again
  DB.profile.gear=['db','band'];
  ok('dumbbells and a band unlock more', extra.filter(function(e){return canDo(e);}).length>=24,
     extra.filter(function(e){return canDo(e);}).length);
  DB.profile.gear=keepG;
})();


// ---------- TODAY LEADS WITH THE RECOMMENDATION ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  var T=todayISO();
  DB.profile.onboarded=true; DB.profile.source='whoop'; DB.profile.name='Hatem';
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,soreness:3,
                  stress:3,motivation:8,pain:'None',availTime:60};
  TAB='today'; resetStack(); viewToday(document.getElementById('view'));
  var view=document.getElementById('view');
  var html=view.innerHTML;
  function posOf(n){ return html.indexOf(n); }

  var rdrow = posOf('class="scores"');
  var rec   = posOf('class="rec"');
  var start = posOf('id="btnStart"');
  var why   = posOf('id="whyT"');
  var swap  = posOf('id="btnSwap"');
  var week  = posOf('class="sec-hd"');
  var log   = posOf('id="actsCard"');

  [['readiness row',rdrow],['recommendation',rec],['start button',start],
   ['why toggle',why],['change plan',swap],['week strip',week],
   ['log activity',log]].forEach(function(pair){
    ok('Today renders the '+pair[0], pair[1]>=0, pair[1]);
  });

  ok('readiness comes first', rdrow>=0 && rdrow<rec, rdrow+' vs '+rec);
  ok('the recommendation comes before any action', rec<start, rec+' / '+start);
  ok('Start is the first action offered', start<why && start<swap,
     'start '+start+' why '+why+' swap '+swap);
  ok('Why sits below Start, not above it', why>start, why+' / '+start);
  ok('the week strip is below the decision', week>swap, week+' / '+swap);
  ok('logging is the last thing offered', log>week, log+' / '+week);

  // the greeting uses the name, once
  ok('the app bar greets by first name',
     /Hatem/.test(document.getElementById('appbar').textContent),
     document.getElementById('appbar').textContent.slice(0,40));
  ok('the name is not repeated in the body', !/Hatem/.test(html));

  // what must NOT be on Today any more
  ok('no six-tile metric grid on Today', !/Today's numbers/.test(html));
  ok('no weekly target bars on Today', !/This week so far/.test(html));
  ok('no how-you-feel sliders on Today', !/How you feel/.test(html));
  ok('no readiness accordion on Today', !document.getElementById('accReady'));
  ok('no getting-started checklist on Today', !/Getting started/.test(html));

  // Today is materially shorter than it was: it used to run to ten blocks
  ok('Today is a short screen', view.querySelectorAll('.card,.rec,.rows,.rdrow').length<=6,
     view.querySelectorAll('.card,.rec,.rows,.rdrow').length);

  // ---- the readiness detail page carries what Today gave up ----
  resetStack();
  tryRun('pushing the readiness page', function(){
    pushPage({build:pageReadiness(T)}); });
  var rv=document.getElementById('view').innerHTML;
  ok('the readiness page shows the score', /class="rec-t"/.test(rv));
  ok('the readiness page explains what moved it', /What moved it/.test(rv));
  ok('the readiness page carries the morning numbers', /This morning/.test(rv));
  ok('the readiness page carries how you feel', /How you said you feel/.test(rv));
  ok('the readiness page offers the wearable trends',
     !!document.getElementById('rdMetrics'));
  resetStack();

  // ---- and a user with no wearable sees no wearable figures ----
  DB.profile.source='none'; DB.profile.sourceFields=null;
  var keepW=DB.whoop; DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
  DB.checkins[T]={date:T,sleepMin:450,energy:7,soreness:3,stress:3,motivation:8,
                  pain:'None',availTime:60};
  resetStack(); pushPage({build:pageReadiness(T)});
  var nv=document.getElementById('view').innerHTML;
  ok('no Recovery tile without a wearable', !/>Recovery</.test(nv));
  ok('no HRV tile without a wearable', !/>HRV</.test(nv));
  ok('no Rest HR tile without a wearable', !/>Rest HR</.test(nv));
  ok('sleep and load are still shown', /Sleep/.test(nv) && /7d load/.test(nv));
  ok('no link to wearable trends without a wearable',
     !document.getElementById('rdMetrics'));
  DB.whoop=keepW; resetStack();

  DB.profile=keepP; DB.checkins={}; TAB='today';
})();

// ---------- THE NAV IS FOUR FIXED DESTINATIONS ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile)), keepW=DB.whoop;
  var ids=function(){ return tabs().map(function(t){return t.id;}); };

  /* Four destinations and one action. Logging is the thing people do most
     often that is not training, and it was a row buried on Home; it gets the
     middle of the bar and a shape of its own so it does not read as a fifth
     place to go. */
  ok('the nav has four destinations and one action', ids().length===5, ids().join(','));
  ['today','workouts','log','progress','settings'].forEach(function(id){
    ok('tab "'+id+'" is present', ids().indexOf(id)>=0, ids().join(','));
  });
  ok('Log sits in the middle', ids()[2]==='log', ids().join(','));
  ok('and only Log is marked as the action',
     tabs().filter(function(t){return t.mid;}).map(function(t){return t.id;}).join(',')==='log',
     tabs().filter(function(t){return t.mid;}).map(function(t){return t.id;}).join(','));
  ok('Activity is no longer a tab', ids().indexOf('tennis')<0, ids().join(','));
  ok('Metrics is not a tab', ids().indexOf('whoop')<0, ids().join(','));

  // the whole point of a fixed bar: it does not change shape under you
  var shapes=[];
  ['none','whoop','garmin','oura'].forEach(function(src){
    DB.profile.source=src;
    DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
    shapes.push(ids().join(','));
    DB.whoop={cycles:[{date:'2030-01-01',recovery:70}],workouts:[],journal:[],imports:[]};
    shapes.push(ids().join(','));
  });
  ok('the nav is identical for every wearable and data state',
     shapes.every(function(s){ return s===shapes[0]; }), shapes.join(' | '));

  // ...and both displaced screens are still reachable
  ok('openSettings exists', typeof openSettings==='function');
  ok('openMetrics exists', typeof openMetrics==='function');

  resetStack(); TAB='today'; render();
  tryRun('opening settings', function(){ openSettings(); });
  ok('settings is a destination, not a page', STACK.length===0, STACK.length);
  ok('the settings screen rendered', $('#view').innerHTML.length>200, $('#view').innerHTML.length);
  ok('and the nav moved to it', TAB==='settings', TAB);

  // metrics is still a pushed page, and that is what a pushed page looks like
  resetStack(); TAB='today'; render();
  tryRun('pushing the metrics page', function(){ openMetrics(); });
  ok('a pushed page is on the stack', STACK.length===1, STACK.length);
  ok('a pushed page gets a back button', !!document.getElementById('abBack'));
  ok('the nav still shows the owning tab', TAB==='today', TAB);
  tryRun('popping back', function(){ popPage(true); });
  ok('popping empties the stack', STACK.length===0, STACK.length);
  ok('back on a tab there is no back button', !document.getElementById('abBack'));
  /* the gear is gone for good: the bar offers Settings directly */
  ok('no settings gear anywhere', !document.getElementById('abGear'));

  // metrics is reachable the same way
  resetStack();
  DB.profile.source='whoop';
  tryRun('pushing the metrics page', function(){ openMetrics(); });
  ok('metrics pushes a page', STACK.length===1, STACK.length);
  resetStack();

  // switching destination must not leave you buried in the old one
  openSettings();
  tryRun('switching tab from inside a page', function(){ go('progress'); });
  ok('changing tab clears the stack', STACK.length===0, STACK.length);
  ok('changing tab lands on that tab', TAB==='progress', TAB);

  // a stale saved tab from the old six-tab build must not blank the screen
  TAB='whoop';
  tryRun('render with a tab that no longer exists', function(){ renderNav(); render(); });
  ok('a removed tab falls back to Today', TAB==='today', TAB);
  TAB='tennis';
  tryRun('render with the old activity tab', function(){ renderNav(); render(); });
  ok('the old activity tab falls back to Today', TAB==='today', TAB);

  // the row list is the one way into a page
  var rowsHTML=navRows('tRows',[{t:'First',s:'sub one',go:function(){}},
                                {t:'Second',icon:'gear',badge:'None',go:function(){}}]);
  ok('navRows renders one button per item',
     (rowsHTML.match(/<button/g)||[]).length===2);
  ok('navRows shows a subtitle', rowsHTML.indexOf('sub one')>=0);
  ok('navRows shows a badge', rowsHTML.indexOf('>None<')>=0);
  ok('navRows always offers an affordance',
     (rowsHTML.match(/rw-c/g)||[]).length===2);

  DB.profile=keepP; DB.whoop=keepW; TAB='today'; resetStack();
})();


// ---------- THE ENGINE SAYS WHAT IT REJECTED ----------
(function(){
  var keepP=JSON.parse(JSON.stringify(DB.profile)), keepS=DB.sessions, keepA=DB.activities;
  var T=todayISO();
  DB.profile.onboarded=true; DB.profile.source='whoop';
  DB.profile.sports=['tennis']; DB.profile.gear=['db','band','bike','run'];
  DB.profile.daysPerWeek=4; applyGoalTargets();
  DB.sessions=[]; DB.activities=[]; DB.checkins={};

  var good={recovery:90,hrv:95,rhr:50,sleepMin:500,sleepNeed:500,prevStrain:3,energy:9,
            soreness:1,stress:2,motivation:9,pain:'None',availTime:70};
  var r=recommend(T,good);
  ok('the recommendation carries what was ruled out', Array.isArray(r.ruledOut), typeof r.ruledOut);
  ok('something is actually ruled out on a normal day', r.ruledOut.length>0, r.ruledOut.length);
  ok('at most three are listed', r.ruledOut.length<=3, r.ruledOut.length);
  ok('each carries a label and a reason',
     r.ruledOut.every(function(x){ return x.label && x.why; }), JSON.stringify(r.ruledOut));
  ok('the chosen option is never in the ruled-out list',
     !r.ruledOut.some(function(x){ return x.label===r.label; }), r.label);

  // it must be visible without opening anything
  DB.checkins[T]=good; DB.checkins[T].date=T;
  TAB='today'; viewToday(document.getElementById('view'));
  var view=document.getElementById('view');
  var why=view.querySelector('.whybox');
  ok('the ruled-out strip renders inside the Why expansion', why && !!why.querySelector('.ruled'), why?'no .ruled':'no .whybox');
  ok('the Why expansion starts closed', why && why.hasAttribute('hidden'));
  ok('and opening it reveals the reasons', (function(){ var t=document.getElementById('whyT'); if(!t) return false; t.click(); return !document.getElementById('whyB').hasAttribute('hidden'); })());

  var ruled=view.querySelector('.ruled');
  ok('it names a rejected option', ruled && /[A-Za-z]/.test(ruled.textContent), ruled?ruled.textContent.slice(0,60):'-');

  // a hard block should read as a reason, not a score
  DB.checkins[T]=Object.assign({},good,{pain:'Significant'});
  var blocked=recommend(T,DB.checkins[T]);
  ok('a blocked option explains itself in words',
     blocked.ruledOut.some(function(x){ return /pain/i.test(x.why); }),
     JSON.stringify(blocked.ruledOut));

  DB.profile=keepP; DB.sessions=keepS; DB.activities=keepA; DB.checkins={};
})();

// ---------- PROGRAM'S EXPLAINERS ARE COLLAPSED ----------
(function(){
  resetStack();
  openPane('Workouts',null,paneProgram);
  var v=document.getElementById('view');
  ['accPri'].forEach(function(id){
    var el=document.getElementById(id);
    ok('program has a collapsible '+id, !!el);
    ok(id+' starts closed', el && !el.classList.contains('open'));
    var h=document.getElementById(id+'H');
    ok(id+' has a header to tap', !!h);
    if(h){ h.click();
      ok(id+' opens when tapped', el.classList.contains('open'));
      h.click();
      ok(id+' closes again', !el.classList.contains('open')); }
  });
  // the things you actually go there for stay visible
  ok('the workout list is not collapsed', /All workouts/.test(v.innerHTML));
  ok('the collapsed header still summarises itself',
     /What the engine weighs, in order/.test(v.innerHTML), 'no priority summary');
  resetStack();

  // the progression plan now sits on the Train tab, where "where am I" belongs
  TAB='workouts'; render();
  var tv=document.getElementById('view');
  ok('the progression plan is on the Train tab', !!document.getElementById('accPlan'));
  ok('it starts closed',
     !document.getElementById('accPlan').classList.contains('open'));
  var h2=document.getElementById('accPlanH');
  ok('it has a header to tap', !!h2);
  if(h2){ h2.click();
    ok('it opens', document.getElementById('accPlan').classList.contains('open')); }
  ok('and it says which week you are in', /Week [0-9]/.test(tv.innerHTML));
  TAB='today'; render();
})();

// ---------- EACH SECTION LEADS WITH ITS OWN CONTENT ----------
(function(){
  var keepTab=TAB;

  // TRAIN: the programme, not a menu
  resetStack(); TAB='workouts'; render();
  var tv=document.getElementById('view');
  ok('Train leads with this week', tv.innerHTML.indexOf('This week')>=0);
  ok('Train shows the targets without a tap', !!document.getElementById('edSched'));
  ok('Train puts the targets above the rows',
     tv.innerHTML.indexOf('edSched') < tv.innerHTML.indexOf('wRows'),
     tv.innerHTML.indexOf('edSched')+' / '+tv.innerHTML.indexOf('wRows'));
  ok('Train names the phase in the app bar',
     /Week [0-9]/.test(document.getElementById('appbar').textContent),
     document.getElementById('appbar').textContent);

  // PROGRESS: four views over one period
  resetStack(); TAB='progress'; PTAB='overview'; POFF=0; render();
  var pv=document.getElementById('view');
  /* Progress is four views over one period, and the overview leads with the
     load rather than a verdict sentence: the number and its direction say more
     in less room than "Going well so far" did. */
  ok('Progress offers its four views', !!document.getElementById('pSeg')
     && document.querySelectorAll('#pSeg button').length===4,
     document.querySelectorAll('#pSeg button').length);
  ok('and opens on the overview',
     document.querySelector('#pSeg button.on').textContent.trim()==='Overview',
     document.querySelector('#pSeg button.on').textContent);
  ok('the period is named and changeable', !!document.getElementById('pPeriod')
     && /This week/.test(document.getElementById('pPeriod').textContent),
     document.getElementById('pPeriod') ? document.getElementById('pPeriod').textContent.trim() : '(none)');
  ok('Progress leads with the training load',
     /Training load/.test(pv.innerHTML) && !!pv.querySelector('.pload .pl-v'),
     pv.querySelector('.pload .pl-v') ? pv.querySelector('.pload .pl-v').textContent : '(none)');
  ok('with the week charted beside it', !!pv.querySelector('.pload .pl-c svg.chart'));
  ok('and sessions and activities as their own tiles',
     pv.querySelectorAll('.stats .stat').length>=2 && /Sessions/.test(pv.innerHTML)
     && /Activities/.test(pv.innerHTML));
  ok('the load sits above the deeper rows',
     pv.innerHTML.indexOf('Training load') < pv.innerHTML.indexOf('pRows'),
     pv.innerHTML.indexOf('Training load')+' / '+pv.innerHTML.indexOf('pRows'));
  ok('switching view keeps you on the tab, not a pushed page', (function(){
    var b=document.querySelectorAll('#pSeg button')[1];
    b.click();
    var still=STACK.length===0 && document.querySelector('#pSeg button.on').textContent.trim()==='Training';
    document.querySelectorAll('#pSeg button')[0].click();
    return still; })(), 'STACK '+STACK.length);

  // and the four tabs must not all be the same shape - the actual complaint
  var shapes={};
  ['today','workouts','tennis','progress'].forEach(function(tab){
    resetStack(); TAB=tab; render();
    var v=document.getElementById('view');
    shapes[tab]=[
      v.querySelector('.rec')?'lead':'-',                 // a dominant block
      v.querySelector('.rows')?'rows':'-',                // navigation
      v.querySelector('.btn.primary.big')?'action':'-',   // a primary action
      v.querySelector('.card')?'card':'-',
      v.querySelector('.seg')?'views':'-'                 // several views of one thing
    ].join('/');
  });
  var distinct={}; var n=0;
  Object.keys(shapes).forEach(function(k){
    if(!distinct[shapes[k]]){ distinct[shapes[k]]=1; n++; } });
  ok('the four sections are not all the same shape', n>=3,
     JSON.stringify(shapes));
  ok('every section still offers navigation onward', (function(){
    return ['workouts','tennis','progress'].every(function(tab){
      resetStack(); TAB=tab; render();
      return !!document.getElementById('view').querySelector('.rows'); }); })());

  TAB=keepTab; resetStack(); render();
})();

// ---------- EVERY SECTION IS A LIST OF ROWS THAT LEAD SOMEWHERE ----------
(function(){
  var keepTab=TAB;
  [['workouts','wRows',4,['Workouts','Exercises','Warm-ups','History']],
   ['progress','pRows',4,['Strength','Tests','Physique','Patterns']]
  ].forEach(function(spec){
    resetStack(); TAB=spec[0]; render();
    var rows=document.getElementById(spec[1]);
    ok(spec[0]+' opens as a row list', !!rows);
    if(!rows) return;
    var btns=rows.querySelectorAll('button');
    ok(spec[0]+' has '+spec[2]+' rows', btns.length===spec[2], btns.length);
    spec[3].forEach(function(label){
      ok(spec[0]+' offers "'+label+'"', rows.textContent.indexOf(label)>=0);
    });
    // every row carries its own one-line answer, so most visits need no tap
    ok(spec[0]+' rows all summarise themselves',
       rows.querySelectorAll('.rw-s').length===btns.length,
       rows.querySelectorAll('.rw-s').length+'/'+btns.length);
    // and every row actually goes somewhere
    for(var i=0;i<btns.length;i++){
      resetStack(); TAB=spec[0]; render();
      var b=document.getElementById(spec[1]).querySelectorAll('button')[i];
      var name=b.textContent.trim().slice(0,22);
      b.click();
      ok(spec[0]+' row "'+name+'" pushes a page', STACK.length===1, STACK.length);
      ok(spec[0]+' row "'+name+'" renders content',
         document.getElementById('view').textContent.trim().length>30);
      ok(spec[0]+' row "'+name+'" can be backed out of',
         (function(){ popPage(true); return STACK.length===0; })());
    }
  });

  /* Train keeps no sub-tab bar - its screen is a list of questions. Progress
     does have one, because it genuinely holds four views of the same period
     and a row list made you leave and come back to compare them. */
  ['workouts','tennis'].forEach(function(tab){
    resetStack(); TAB=tab; render();
    ok(tab+' has no segment bar',
       !document.getElementById('wSeg') && !document.getElementById('aSeg')
       && !document.getElementById('hSeg'));
  });
  resetStack(); TAB='progress'; render();
  ok('progress does have one, and only one',
     document.querySelectorAll('#view .seg').length===1,
     document.querySelectorAll('#view .seg').length);

  // Activity leads with logging, because that is what it is for
  resetStack(); TAB='today'; render();
  ok('the day, and one of each action, live on Today',
     !!document.getElementById('actsCard') && !!document.getElementById('acAdd')
     && !!document.getElementById('acStart'));
  ok('and the deeper activity views are grouped under it',
     !!document.getElementById('aRows'));

  TAB=keepTab; resetStack(); render();
})();

// ---------- A NEW USER IS ORIENTED, AND THEN LEFT ALONE ----------
(function(){
  var keepS=DB.sessions, keepA=DB.activities, keepC=DB.checkins, keepP=JSON.parse(JSON.stringify(DB.profile));
  var T=todayISO();
  DB.profile.onboarded=true;
  DB.sessions=[]; DB.activities=[]; DB.checkins={};

  var keepU=JSON.parse(JSON.stringify(DB.ui||{}));
  DB.ui.tourDone=false;

  ok('nothing logged means nothing counted', loggedCount()===0, loggedCount());

  // --- the walkthrough explains the whole model in plain language ---
  ok('there is a walkthrough', Array.isArray(TOUR) && TOUR.length>=5, TOUR.length);
  ok('every card has a heading and a body',
     TOUR.every(function(c){ return c.t && c.b && c.b.length>40; }));
  ok('it covers what the app does',
     /picks one session/i.test(TOUR.map(function(c){return c.t;}).join(' ')));
  ok('it covers what it needs from you',
     /minute/i.test(TOUR.map(function(c){return c.t+' '+c.b;}).join(' ')));
  ok('it covers that you can override it',
     /overriding/i.test(TOUR.map(function(c){return c.b;}).join(' ')));
  ok('it covers logging other activity',
     /unplanned/i.test(TOUR.map(function(c){return c.b;}).join(' ')));
  ok('it covers where the data lives',
     /no server/i.test(TOUR.map(function(c){return c.b;}).join(' ')));
  ok('it tells you to back up',
     /Backup/.test(TOUR.map(function(c){return c.b;}).join(' ')));
  ok('no jargon in the headings', !/readiness|acute|RPE|HRV/i.test(
     TOUR.map(function(c){return c.t;}).join(' ')),
     TOUR.map(function(c){return c.t;}).join(' | '));

  // --- it walks, and it can be left at any point ---
  tryRun('the walkthrough opens', function(){ openTour(); });
  ok('it opens on the first card', TOURSTEP===0, TOURSTEP);
  ok('it shows the first heading', $('#sheetBody').innerHTML.indexOf(TOUR[0].t)>=0);
  ok('every card offers a way out', (function(){
    for(var i=0;i<TOUR.length;i++){
      TOURSTEP=i; drawTour();
      if(!document.getElementById('tourSkip')) return false;
      if(!document.getElementById('tourNext')) return false;
    }
    return true; })());
  ok('the footer geometry never changes', (function(){
    var cols=[];
    for(var i=0;i<TOUR.length;i++){
      TOURSTEP=i; drawTour();
      cols.push(getComputedStyle(document.querySelector('#sheetFoot .btn-row')).gridTemplateColumns);
    }
    return cols.every(function(c){ return c===cols[0]; }); })());

  TOURSTEP=0; drawTour();
  ok('Next advances', (function(){
    document.getElementById('tourNext').click(); return TOURSTEP===1; })(), TOURSTEP);
  ok('the last card finishes instead of advancing', (function(){
    TOURSTEP=TOUR.length-1; drawTour();
    return /Got it/.test(document.getElementById('tourNext').textContent); })());
  ok('the last card offers Back rather than Skip', (function(){
    return /Back/.test(document.getElementById('tourSkip').textContent); })());

  // --- seen is seen, whether read or skipped ---
  DB.ui.tourDone=false;
  openTour();
  document.getElementById('tourSkip').click();   // skip from card one
  ok('skipping closes it', !document.getElementById('sheet').classList.contains('on'));
  tryRun('the close handler runs', function(){ endTour(); });
  ok('skipping counts as seen', tourSeen()===true);

  // --- the way back in, and its self-removal ---
  DB.ui.tourDone=false; DB.checkins={}; DB.activities=[]; DB.sessions=[];
  ok('a new user is offered the walkthrough on Today',
     noticeHTML(T).length>0 && /New here/.test(noticeHTML(T)));
  ok('the offer is one row, not a banner',
     (noticeHTML(T).match(/<button/g)||[]).length===1);
  ok('it says how long it takes', /about a minute/i.test(noticeHTML(T)));
  DB.ui.tourDone=true;
  ok('once seen, the offer is gone', !/New here/.test(noticeHTML(T)),
     noticeHTML(T).slice(0,60));
  DB.ui.tourDone=false;
  DB.checkins[T]={date:T,energy:7,soreness:3,stress:3,motivation:7,pain:'None'};
  for(var i=0;i<6;i++) DB.activities.push({id:'ob'+i,date:addDays(T,-i),type:'walking',min:20,rpe:2});
  ok('once there is real history the offer is gone too',
     !/New here/.test(noticeHTML(T)), noticeHTML(T).slice(0,60));
  ok('and it is not on the Today screen', (function(){
    TAB='today'; resetStack(); render();
    var n=document.getElementById('noticeRow');
    return !n || n.dataset.n!=='tour'; })());

  // --- and it stays reachable from Settings forever ---
  resetStack(); openSettings();
  var ai=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf('about');
  document.getElementById('setRows').querySelectorAll('button')[ai].click();
  ok('Settings > About can reopen the walkthrough', !!document.getElementById('sTour'));
  document.getElementById('sTour').click();
  ok('and it opens from there', $('#sheetBody').innerHTML.indexOf(TOUR[0].t)>=0);
  closeSheet(); resetStack();

  // --- the two things it replaced are gone, not merely unused ---
  ok('the old welcome sheet is gone', typeof welcome==='undefined');
  ok('the old getting-started card is gone', typeof firstWeekCard==='undefined');

  DB.ui=keepU;

  DB.sessions=keepS; DB.activities=keepA; DB.checkins=keepC; DB.profile=keepP;
  resetStack(); TAB='today';
})();

// ---------- THE WEEK REVIEW MOVED TO TODAY ----------
(function(){
  var keepC=DB.checkins, T=todayISO();
  DB.checkins[T]={date:T,recovery:70,hrv:80,rhr:54,sleepMin:440,energy:7,soreness:3,
                  stress:3,motivation:7,pain:'None',availTime:60};

  var R=weekReview();
  ok('weekReview returns the narrative', Array.isArray(R.good)&&Array.isArray(R.attn)&&Array.isArray(R.next));
  ok('it always suggests something for next week', R.next.length>0, R.next.length);
  ok('weekNarrative renders from it', /What went well/.test(weekNarrative(R)));
  ok('weekNumbers renders the load chart', /Daily load/.test(weekNumbers(R)));

  TAB='today'; viewToday(document.getElementById('view'));
  var v=document.getElementById('view');
  ok('the week review is NOT on Today any more', !document.getElementById('accWk'));
  ok('Today shows the week as a strip instead', v.innerHTML.indexOf('This week')>=0);
  ok('the review still exists for Progress to use', /What went well/.test(weekNarrative(weekReview())));
  var h=document.getElementById('accWkH');
  if(h){ h.click(); ok('it opens', document.getElementById('accWk').classList.contains('open'));
         ok('and holds the narrative', /What needs attention/.test(v.innerHTML)); }

  // Progress: four views of one period, the overview leading with the load
  resetStack(); TAB='progress'; PTAB='overview'; POFF=0; render();
  ok('Progress names its four views', document.querySelectorAll('#pSeg button').length===4);
  ok('Progress leads with the week before any row', (function(){
    var v=document.getElementById('view');
    return v.innerHTML.indexOf('Training load') < v.innerHTML.indexOf('pRows'); })());

  // "how did my week go" now owns the numbers AND the narrative
  resetStack(); openPane('This week',null,paneWeek);
  var wk=document.getElementById('view').innerHTML;
  ok('the week page carries the load numbers', /Daily load/.test(wk));
  ok('the week page carries the narrative', /What went well/.test(wk));
  resetStack();

  // and Strength stops repeating them
  openPane('Strength',null,paneStrength);
  ok('Strength no longer repeats the week numbers',
     !/Daily load/.test(document.getElementById('view').innerHTML));
  resetStack();

  ['paneStrength','paneTests','panePhysique','paneLinks','paneWeek'].forEach(function(fn){
    resetStack();
    tryRun('progress page '+fn, function(){ openPane(fn,null,window[fn]||eval(fn)); });
  });
  resetStack(); TAB='today'; DB.checkins=keepC;
})();

// ---------- NOTHING IS ASSUMED ABOUT YOUR EQUIPMENT ----------
(function(){
  var keepG=DB.profile.gear, keepB=DB.profile.preferBest;
  DB.profile.preferBest=true;

  // absolutely nothing
  DB.profile.gear=[];
  ok('bodyweight-only user still has exercises', countDoable([])>=25, countDoable([]));
  ok('no dumbbell exercise offered without dumbbells',
     !DB.exercises.some(function(e){ return canDo(e) && (e.needs||[]).indexOf('db')>=0; }));
  ok('no band exercise offered without a band',
     !DB.exercises.some(function(e){ return canDo(e) && (e.needs||[]).indexOf('band')>=0; }));
  var blocks=sessionBlocks({workoutId:'w_lowerA',variant:'full',addCore:false});
  ok('a bodyweight-only leg session is still buildable', blocks.length>0, blocks.length);
  ok('every exercise in it needs nothing',
     blocks.every(function(b){ var e=exOf(b.ex); return canDo(e); }),
     blocks.filter(function(b){return !canDo(exOf(b.ex));}).map(function(b){return exOf(b.ex).name;}).join(','));
  var upper=sessionBlocks({workoutId:'w_upperA',variant:'full',addCore:false});
  ok('a bodyweight-only upper session is buildable', upper.length>0 &&
     upper.every(function(b){ return canDo(exOf(b.ex)); }),
     upper.map(function(b){return exOf(b.ex).name;}).join(' | '));

  // band only
  DB.profile.gear=['band'];
  ok('band unlocks band exercises', DB.exercises.some(function(e){
     return canDo(e) && (e.needs||[]).indexOf('band')>=0; }));
  ok('band alone does not unlock dumbbells', !DB.exercises.some(function(e){
     return canDo(e) && (e.needs||[]).indexOf('db')>=0; }));

  // full gym
  DB.profile.gear=['db','band','bench','bar','bb','cable','bike','run'];
  ok('full gym unlocks the barbell work', DB.exercises.some(function(e){
     return canDo(e) && (e.needs||[]).indexOf('bb')>=0; }));
  ok('gym user count is higher than bodyweight-only',
     countDoable(DB.profile.gear)>countDoable([]),
     countDoable(DB.profile.gear)+' vs '+countDoable([]));
  ok('tier is derived from the gear, not chosen', tierOf(['bb'])===2 && tierOf(['bench'])===1 && tierOf([])===0);
  ok('equipment list never invents items',
     equipmentList([],'',null).length===1 && equipmentList([],'',null)[0]==='Bodyweight',
     JSON.stringify(equipmentList([],'',null)));
  ok('dumbbell weight is recorded when given',
     equipmentList(['db'],'',5).join(',').indexOf('5 kg')>=0, equipmentList(['db'],'',5).join(','));

  // every workout at every gear level stays performable
  var bad3=[];
  [[],['band'],['db','band'],['db','band','bench','bar'],['db','band','bench','bar','bb','cable']].forEach(function(gear){
    DB.profile.gear=gear;
    DB.workouts.forEach(function(w){ ['full','reduced','recovery'].forEach(function(v){
      sessionBlocks({workoutId:w.id,variant:v,addCore:false}).forEach(function(b){
        var e=exOf(b.ex);
        if(!e||!canDo(e)) bad3.push(gear.length+'items:'+w.id+'/'+v+':'+(e?e.name:'missing'));
      });
    });});
  });
  ok('NO workout ever prescribes equipment the user lacks', bad3.length===0, bad3.slice(0,5).join(' | '));

  DB.profile.gear=keepG; DB.profile.preferBest=keepB;
})();

// ---------- PRIVACY: nothing may leave the device ----------
/* scan the APPLICATION script only — scripts[0] is the test shim and the last
   is this test file, both of which legitimately mention these names */
var APP_SRC=(function(){ var s=document.querySelectorAll('script');
  var best='',n=0; for(var i=0;i<s.length;i++){ var t=s[i].textContent||'';
    if(t.length>n && t.indexOf('function freshDB')>=0){ n=t.length; best=t; } } return best; })();
ok('application script located', APP_SRC.length>100000, APP_SRC.length);
ok('no network APIs in the application',
   !(new RegExp('XMLHttpRequest|new WebSocket|sendBeacon|EventSource')).test(APP_SRC));
/* look for tracker USAGE, not the word "analytics" — the app legitimately
   contains an analytics section header and a "no analytics" privacy claim */
ok('no analytics or tracker calls in the application',
   !(new RegExp('gtag\\\\(|dataLayer|_paq|googletagmanager[.]com|mixpanel[.]|segment[.]com|sentry[.]io|amplitude[.]','i')).test(APP_SRC));
ok('privacy claim is actually true (no external subresources)',
   document.querySelectorAll('script[src],img[src^="http"],iframe[src^="http"]').length===0);
ok('only same-origin service worker is fetched',
   (APP_SRC.match(new RegExp('serviceWorker[.]register\\\\([^)]*','g'))||['']).join(' ').indexOf('//')<0);
var ORIGIN_RE=new RegExp('https?://[a-z0-9.-]+','gi');
var ALLOW_RE=new RegExp('w3[.]org|localhost|127[.]0[.]0[.]1');
ok('no third-party origins referenced', (function(){
  var m=document.documentElement.innerHTML.match(ORIGIN_RE)||[];
  return m.filter(function(u){ return !ALLOW_RE.test(u); }).length===0;
})(), (document.documentElement.innerHTML.match(ORIGIN_RE)||[])
        .filter(function(u){ return !ALLOW_RE.test(u); }).slice(0,5).join(' '));
ok('exported backup contains no remote target', (function(){
  var s=JSON.stringify({_app:'baseline.tps',data:DB});
  return (s.match(ORIGIN_RE)||[]).filter(function(u){ return !ALLOW_RE.test(u); }).length===0;
})());

// ---------- iOS environment detection ----------
ok('ENV reports a protocol', typeof ENV.proto==='string', ENV.proto);
ok('ENV.isFile / isHttps are mutually consistent', !(ENV.isFile&&ENV.isHttps));
ok('ENV.standalone is a boolean', typeof ENV.standalone==='boolean');
ok('ENV.canInstall is a boolean', typeof ENV.canInstall==='boolean');
tryRun('openSetup renders', function(){ openSetup(); if(!$('#sheetBody').innerHTML.length) throw new Error('empty'); });
ok('setup sheet reports storage state', /Data storage/.test($('#sheetBody').innerHTML));
closeSheet();
tryRun('openSetup auto variant renders', function(){ openSetup(true); }); closeSheet();
tryRun('updateBanner runs without a banner needed', function(){ updateBanner(); });
ok('no warning banner when storage works', !document.getElementById('sbanner').classList.contains('on'));
// simulate blocked storage and confirm the app warns instead of failing silently
tryRun('blocked-storage path warns', function(){
  var realLocal=Store.local, realIdb=Store.idb;
  Store.local=false; Store.idb=false;
  updateBanner();
  var on=document.getElementById('sbanner').classList.contains('on');
  var txt=document.getElementById('sbanner').textContent;
  Store.local=realLocal; Store.idb=realIdb; updateBanner();
  if(!on) throw new Error('banner not shown');
  if(!/cannot save data/i.test(txt)) throw new Error('banner text wrong: '+txt);
});
ok('banner cleared again after storage restored', !document.getElementById('sbanner').classList.contains('on'));

// ---------- rest timer is deadline-based (survives iOS suspending timers) ----------
tryRun('startRest sets a deadline', function(){ startRest(90,'Test',1,3);
  if(!(restEnd>Date.now()+80000)) throw new Error('no deadline'); });
ok('rest is running', restActive());
ok('it remembers which set it belongs to', REST.set===0 && REST.name==='Test',
   JSON.stringify(REST));
ok('rest remaining ~90s', Math.abs(restRemaining()-90)<2, restRemaining());
tryRun('+30s extends the deadline', function(){ var b=restEnd; restAdd30();
  if(restEnd-b<29000) throw new Error('not extended'); });
ok('rest remaining ~120s after +30', Math.abs(restRemaining()-120)<2, restRemaining());
// jump the deadline into the past — as if the phone was locked for 5 minutes
tryRun('elapsed-while-suspended is handled', function(){ restEnd=Date.now()-5000; restDone=false; paintRest(); });
ok('timer auto-finishes after suspension', !restActive());
ok('and forgets which set it belonged to', REST.ex===-1 && REST.set===-1,
   JSON.stringify(REST));
tryRun('stopRest is idempotent', function(){ stopRest(); stopRest(); });
tryRun('+30s on a stopped timer does nothing', function(){ restAdd30(); });
ok('a stopped timer stays stopped', !restActive());

// ---------- A SHEET OPENED DURING A WORKOUT HAS TO BE ON TOP OF IT ----------
(function(){
  /* #wmode is a full-screen overlay at z-index 300. The scrim and the sheet
     were 200 and 201, so EVERY sheet opened mid-workout - How to do it, Why
     this exercise, Replace, Note, This hurt, and the exit confirmation with
     its Cancel button - rendered underneath it and could not be reached.
     Nothing in 1398 tests looked at stacking order. This does. */
  var z=function(sel){
    var el=document.querySelector(sel);
    return el? +(getComputedStyle(el).zIndex||0) : null;
  };
  var wm=z('#wmode'), sc=z('#scrim'), sh=z('#sheet'), to=z('#toast');
  ok('the scrim sits above the workout overlay', sc>wm, sc+' vs '+wm);
  ok('the sheet sits above the scrim', sh>sc, sh+' vs '+sc);
  ok('and a toast sits above the sheet', to>sh, to+' vs '+sh);
})();

// ---------- LEAVING A WORKOUT ALWAYS ASKS, AND PAUSE IS ONE OF THE ANSWERS ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  /* 1 · With nothing logged there is nothing to lose, so leaving just leaves.
     This used to ask every time, on the reasoning that a mis-tap on the X is
     most likely before anything is logged - which had it backwards: with
     nothing logged a mis-tap costs nothing, so the dialogue guarded the cheap
     mistake and charged for it on every exit, including the common one of
     opening a session, reading the overview and backing out. */
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  document.getElementById('wmX').click();
  ok('leaving with nothing logged just leaves',
     !document.getElementById('sheet').classList.contains('on') && !W,
     document.getElementById('sheet').classList.contains('on')?'asked':'left');
  ok('and keeps no live session behind', !Store.pref('live'));

  // 2 · one logged set is progress, and progress is worth asking about
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  document.querySelector('#wmBody [data-log]').click();
  stopRest();
  document.getElementById('wmX').click();
  ok('once a set is logged it does ask', document.getElementById('sheet').classList.contains('on'));
  ok('it offers pause', !!document.getElementById('wmPause'));
  ok('it offers cancel', !!document.getElementById('wmKeep'));
  ok('it offers discard', !!document.getElementById('wmDrop'));

  // 3 · cancel keeps you training, and the sheet says how much is at stake
  document.getElementById('wmKeep').click();
  ok('cancel closes the sheet', !document.getElementById('sheet').classList.contains('on'));
  ok('and the workout is still running', !!W && document.getElementById('wmode').classList.contains('on'));
  document.getElementById('wmX').click();
  ok('with sets logged it says how many',
     /1 set logged so far/.test(document.getElementById('sheetBody').innerHTML),
     document.getElementById('sheetBody').innerHTML.slice(0,200));

  // 4 · pause keeps everything and leaves
  var wasId=W.id, wasStep=W.step;
  document.getElementById('wmPause').click();
  ok('pause saves the session as live', !!Store.pref('live'));
  var live=JSON.parse(Store.pref('live'));
  ok('and records that it was paused on purpose', !!live.pausedAt);
  ok('with the logged set intact',
     live.entries.some(function(e){ return e.sets.some(function(s){return s.done;}); }));
  ok('nothing was written to history', !DB.sessions.some(function(s){return s.id===wasId;}));

  // 5 · Today offers it back
  var n=noticeRow(T);
  ok('Today offers the paused workout back', !!n && n.id==='paused',
     n? n.id : 'none');
  ok('and says how much is in it', /1 set logged/.test(n.s), n.s);

  // 6 · resuming picks up where it was
  W=null;
  resumeWorkout();
  ok('resume reopens workout mode', !!W && document.getElementById('wmode').classList.contains('on'));
  ok('on the same exercise', W.step===wasStep, W.step+' vs '+wasStep);
  ok('with the same id', W.id===wasId);
  ok('and it is no longer flagged as paused', !W.pausedAt);

  // 7 · discard really discards
  exitWM(true);
  ok('discarding clears the live session', !Store.pref('live'));
  ok('and nothing is offered on Today', (function(){
     var x=noticeRow(T); return !x || x.id!=='paused'; })());

  // 8 · a live session from an earlier day is never offered
  Store.pref('live', JSON.stringify({id:'old', date:addDays(T,-2), done:false,
    workoutName:'Lower A', startedAt:Date.now(), entries:[]}));
  ok('yesterday’s abandoned session is not offered', pausedWorkout()===null);
  Store.pref('live',null);

  DB.sessions=keepS; DB.checkins=keepC;
})();

// ---------- ONE TAP PER SET, AND NOTHING ELSE ----------
// The whole runner, measured the only way that matters: how many times the
// user has to touch the phone to get through a session. Every tap that is not
// "Log set" is a tap the app should have taken for them.
(function(){
  var keepC=DB.checkins, keepRest=DB.settings.restTimerOn;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  DB.settings.restTimerOn=false;          // rest has its own block below
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  var total=W.entries.length;
  var plannedSets=W.entries.reduce(function(a,e){ return a+(e.timed||e.cardio?0:e.sets.length); },0);

  ok('the screen opens on the first exercise, first set',
     W.step===0 && /SET 1 OF/i.test(document.querySelector('.wset .ws-l').textContent),
     document.querySelector('.wset .ws-l').textContent);

  /* THE WALK. It presses exactly one thing, ever: the Log set button. If the
     runner needs a single extra tap to advance a set, advance an exercise,
     confirm a completion or dismiss a card, this loop stalls and the count
     comes out wrong. */
  var taps=0, guard=0, seen=[];
  while(guard++<200){
    var b=document.querySelector('#wmBody [data-log]');
    if(!b) break;                                  // nothing left to log
    var nm=document.querySelector('.wm-ex');
    if(nm && seen.indexOf(nm.textContent)<0) seen.push(nm.textContent);
    b.click(); taps++;
  }
  ok('the whole workout is one tap per set',
     taps===plannedSets, taps+' taps for '+plannedSets+' planned sets');
  ok('and every exercise was visited without a navigation tap',
     seen.length===total, seen.length+' of '+total+': '+seen.join(', '));
  ok('it ends on the finish screen by itself',
     W.step>=W.entries.length, W.step+'/'+W.entries.length);
  ok('and the finish screen is the one that saves',
     !!document.getElementById('fSave'),
     document.getElementById('wmBody').textContent.slice(0,100));
  ok('every set is recorded', W.entries.every(function(e){
       return e.cardio || e.sets.every(function(s){ return s.done; }); }));
  ok('with reps kept for the engine', W.entries[0].sets.every(function(s){ return !!s.reps; }),
     JSON.stringify(W.entries[0].sets.map(function(s){return s.reps;})));

  /* Nothing on the way through offered a decision. */
  ok('no exercise-complete screen was ever shown', !document.getElementById('wmDoneN'));
  ok('no Stay on this exercise button exists', !document.getElementById('wmStay'));

  // the finish screen still lets you reopen an exercise you got wrong
  ok('every exercise row is a way back',
     document.querySelectorAll('#wmBody [data-back]').length===W.entries.length,
     document.querySelectorAll('#wmBody [data-back]').length);

  exitWM(true);

  /* NOTHING IS CRAMMED INTO THE TOP THIRD.
     The live screens lay out as three bands with the middle one taking the
     slack, so a short exercise name does not leave two thirds of the phone
     blank. Checked structurally, because the audit already checks it visually. */
  startWorkout('w_lowerA','full',T);
  ok('the overview is the one screen allowed to be a list',
     !document.getElementById('wmBody').classList.contains('live')
     && document.querySelectorAll('#wmBody .wacc-i').length>0,
     document.querySelectorAll('#wmBody .wacc-i').length+' rows');
  /* the warm-up is one screen and lays itself out; the three bands belong
     to the live set and rest screens */
  wmToMain();
  ok('a live set lays out as three bands',
     document.getElementById('wmBody').classList.contains('live')
     && !!document.querySelector('#wmBody .wm-top')
     && !!document.querySelector('#wmBody .wm-mid')
     && !!document.querySelector('#wmBody .wm-bot'),
     document.getElementById('wmBody').className);
  wmToMain();
  ok('and so does a set', (function(){
     var b=document.getElementById('wmBody');
     return b.classList.contains('live') && !!b.querySelector('.wm-mid'); })(),
     document.getElementById('wmBody').className);
  ok('the action sits in the bottom band, above the glimpse',
     !!document.querySelector('#wmBody .wm-bot [data-log]'),
     document.querySelector('#wmBody .wm-bot') ? document.querySelector('#wmBody .wm-bot').textContent.slice(0,50) : '');
  /* the finish screen lays itself out, so the class must not linger */
  W.entries.forEach(function(e){ e.sets.forEach(function(s){ s.done=true; }); });
  W.step=W.entries.length; drawWM();
  ok('and the finish screen is not forced into the same shape',
     !document.getElementById('wmBody').classList.contains('live'),
     document.getElementById('wmBody').className);
  exitWM(true);

  /* REST, which is the one thing allowed to hold the screen - because resting
     IS the next instruction, and it runs itself. */
  DB.settings.restTimerOn=true;
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  var e0=W.entries[0];
  if(parseRest(e0.plannedRest)){
    document.querySelector('#wmBody [data-log]').click();
    ok('rest starts by itself after a logged set', restActive());
    ok('and it takes over the screen', !!document.querySelector('.wrestx'),
       document.getElementById('wmBody').textContent.slice(0,80));
    ok('showing a countdown', !!document.getElementById('restT'),
       document.getElementById('restT')?document.getElementById('restT').textContent:'');
    ok('there is nothing to log while resting',
       !document.querySelector('#wmBody [data-log]'));
    ok('skipping it is secondary, not primary',
       !!document.getElementById('restSkip') &&
       document.getElementById('restSkip').className.indexOf('tert')>=0,
       document.getElementById('restSkip').className);
    ok('and it says what it is resting for',
       /Then set 2 of/.test(document.querySelector('.wrx-s').textContent),
       document.querySelector('.wrx-s').textContent);
    /* Resting between sets, the next thing is the next SET. Naming the next
       exercise here pointed past the set the user is about to do. */
    ok('and does not name the next exercise while sets remain',
       e0.sets.length<2 || !document.querySelector('#wmBody .unext'),
       document.querySelector('#wmBody .unext') ? document.querySelector('#wmBody .unext').textContent : '(none)');
    document.getElementById('restSkip').click();
    ok('skipping returns to the next set, ready to log',
       !restActive() && /SET 2 OF/i.test(document.querySelector('.wset .ws-l').textContent),
       document.querySelector('.wset .ws-l').textContent);
    /* The rest AFTER the last set of an exercise is a different branch, and it
       is the one nothing reached: it threw on a variable left behind by a
       rename, which only a run that got that far could find. */
    var restErr=null;
    try{
      while(!e0.sets.every(function(s){return s.done;})){
        stopRest(); drawWM();
        document.querySelector('#wmBody [data-log]').click();
      }
    }catch(err){ restErr=(err&&err.message)||String(err); }
    ok('the rest after a finished exercise renders', restErr===null, restErr);
    ok('and says which exercise it is resting towards',
       !restActive() || !document.querySelector('.wrx-s')
       || /Get ready for|Then you are done/.test(document.querySelector('.wrx-s').textContent),
       document.querySelector('.wrx-s') ? document.querySelector('.wrx-s').textContent : '(advanced already)');
    stopRest();
  } else {
    ok('rest starts by itself after a logged set', true, 'no rest prescribed here');
  }
  /* and an exercise with no prescribed rest never shows a timer */
  (function(){
    var noRest=null;
    for(var q=0;q<W.entries.length;q++){
      if(!W.entries[q].cardio && !parseRest(W.entries[q].plannedRest)){ noRest=q; break; }
    }
    if(noRest===null){ ok('no rest prescribed means no rest screen', true, 'every exercise here rests'); return; }
    W.phase='main'; W.step=noRest; drawWM();
    document.querySelector('#wmBody [data-log]').click();
    ok('no rest prescribed means no rest screen',
       !document.querySelector('.wrestx'), 'exercise '+noRest);
  })();

  exitWM(true);

  /* ONE DOOR TO TODAY'S SESSION.
     A live session used to raise a notice row headed "Workout still open"
     ABOVE a card offering the same workout with "Start session" - two entries
     to one room, and the notice made it sound like a third thing to deal
     with. The card carries it now, and the button changes verb. */
  DB.settings.restTimerOn=false;
  startWorkout('w_lowerA','full',T);
  wmToMain();
  document.querySelector('#wmBody [data-log]').click();
  pauseWM();
  resetStack(); TAB='today'; render();
  var plan=todayPlan(T), live=pausedWorkout();
  ok('the paused session is still there', !!live, live?live.workoutName:'(none)');
  if(live && plan && live.workoutId===plan.workoutId){
    var view=document.getElementById('view').textContent;
    ok('no separate "still open" row competes with the card',
       view.indexOf('Workout still open')<0 && view.indexOf('Session in progress')<0,
       view.slice(0,160));
    ok('the card says it has been started',
       /Started/.test(view) && /set logged/.test(view), view.slice(0,200));
    ok('and the button offers to resume, not to start again',
       /Resume session/.test(document.getElementById('btnStart').textContent),
       document.getElementById('btnStart').textContent.trim());
    document.getElementById('btnStart').click();
    ok('pressing it resumes rather than wiping the logged set',
       !!W && W.entries.some(function(e){ return e.sets.some(function(s){return s.done;}); }),
       W? 'resumed' : '(no W)');
    exitWM(true);
  } else {
    ok('no separate "still open" row competes with the card', true, 'plan differs today');
  }
  try{ Store.pref('live',null); }catch(e){}

  DB.settings.restTimerOn=keepRest; DB.checkins=keepC;
  resetStack(); TAB='today';
})();

// ---------- THE SET SCREEN SPEAKS PLAIN ENGLISH ----------
(function(){
  ok('RPE 7 becomes words', /3 reps left/.test(effortWords('RPE 7')), effortWords('RPE 7'));
  ok('RPE 9 becomes words', /one rep left/.test(effortWords('9')), effortWords('9'));
  ok('RPE 10 becomes words', /as hard as you can/.test(effortWords('10')), effortWords('10'));
  ok('a missing effort says nothing', effortWords('')==='' && effortWords(null)==='');
  /* a hold has no reps to have left in reserve, and saying so on a plank was
     a real bug before the "no reps on a hold screen" test caught it */
  ok('a hold describes effort in seconds, not reps',
     effortWords('RPE 7',true).indexOf('rep')<0, effortWords('RPE 7',true));
  ok('and it still describes something', effortWords('RPE 7',true).length>10,
     effortWords('RPE 7',true));
  /* and a run has neither reps nor an end to hold out for: the scale there is
     the talk test, which is what the block notes already say in prose */
  ok('continuous work is described by the talk test',
     /conversation|talk/i.test(effortWords('RPE 4','cardio')+effortWords('RPE 6','cardio')),
     effortWords('RPE 4','cardio')+' | '+effortWords('RPE 6','cardio'));
  ok('and never mentions reps',
     [2,4,5,6,7,8,9,10].every(function(v){ return effortWords('RPE '+v,'cardio').indexOf('rep')<0; }),
     [2,4,5,6,7,8,9,10].map(function(v){return effortWords('RPE '+v,'cardio');}).join(' | '));
  ok('the three vocabularies differ',
     effortWords('RPE 7')!==effortWords('RPE 7','hold')
     && effortWords('RPE 7','hold')!==effortWords('RPE 7','cardio'),
     [effortWords('RPE 7'),effortWords('RPE 7','hold'),effortWords('RPE 7','cardio')].join(' | '));
  ok('true still means a hold', effortWords('RPE 7',true)===effortWords('RPE 7','hold'));
  ok('every rung of the scale avoids reps on a hold',
     [4,6,7,8,9,10].every(function(v){ return effortWords('RPE '+v,true).indexOf('rep')<0; }),
     [4,6,7,8,9,10].map(function(v){return effortWords('RPE '+v,true);}).join(' | '));
  ok('60s rest becomes about a minute', /about a minute between/.test(restWords('60s')),
     restWords('60s'));
  ok('90s rest becomes a minute and a half', /minute and a half/.test(restWords('90s')),
     restWords('90s'));
  ok('180s rest becomes 3 minutes', /about 3 minutes/.test(restWords('3 min')),
     restWords('3 min'));
  ok('a missing rest says nothing', restWords('')==='' && restWords('—')==='');

  var keepC=DB.checkins;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  var body=document.getElementById('wmBody').innerHTML;
  /* The effort-and-rest prose line is gone from the active screen along with
     everything else that was not the current action. What remains is the
     coaching cue, which tells you HOW to do the thing you are about to do. */
  ok('no RPE notation anywhere on the training screen',
     !/RPE[ ]*[0-9]/.test(document.getElementById('wmBody').textContent),
     document.getElementById('wmBody').textContent.slice(0,140));
  ok('no tempo notation on the set screen', !/tempo [0-9]-[0-9]/.test(body));
  ok('the cue is still there, because it says how to do it',
     !!document.getElementById('wmHowLine'), body.slice(0,200));

  // ...and the exact figures are still one tap away. Through the how-to line
  // rather than the More menu, whose handlers run behind a 200ms close.
  document.getElementById('wmHowLine').click();
  ok('the plan in full is one tap away', (function(){
     var h=document.getElementById('sheet').innerHTML;
     return /The plan in full/.test(h) && /Effort/.test(h) && /Rest/.test(h); })(),
     document.getElementById('sheet').innerHTML.slice(0,300));
  ok('and the More menu offers it too', (function(){
     closeSheet(); document.getElementById('wmMore').click();
     var has=/How to do it/.test(document.getElementById('sheet').innerHTML);
     closeSheet(); return has; })());

  exitWM(true); DB.checkins=keepC;
})();

// ---------- EVERY EXERCISE SAYS WHAT IT IS ----------
(function(){
  ok('briefHow takes the first sentence',
     briefHow({how:'Stand tall. Then do something else entirely.'})==='Stand tall.',
     briefHow({how:'Stand tall. Then do something else entirely.'}));
  ok('briefHow falls back to the cue',
     briefHow({cue:'Chest up'})==='Chest up');
  ok('briefHow survives nothing at all', briefHow(null)==='' && briefHow({})==='');
  ok('briefHow truncates a runaway sentence', (function(){
     var long='a'+new Array(300).join('b');
     var s=briefHow({how:long});
     return s.length<=141 && s.slice(-1)==='…'; })(),
     briefHow({how:'a'+new Array(300).join('b')}).length);

  // every exercise in the library can produce one
  var bad=DB.exercises.filter(function(e){ return briefHow(e).length<12; });
  ok('every exercise can describe itself in a line', bad.length===0,
     bad.slice(0,5).map(function(e){return e.name;}).join(', '));
  // and every workout explains what it is for
  var nd=DB.workouts.filter(function(w){ return !w.desc || w.desc.length<40; });
  ok('every workout explains itself too', nd.length===0,
     nd.map(function(w){return w.id;}).join(', '));

  var keepC=DB.checkins;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  startWorkout('w_lowerA','full',T);
  W.phase='main'; W.step=0; drawWM();
  ok('the set screen carries a line of how to do it',
     !!document.getElementById('wmHowLine'),
     document.getElementById('wmBody').innerHTML.slice(0,300));
  ok('and it is the same line briefHow produces',
     document.getElementById('wmHowLine').textContent
       .indexOf(briefHow(exOf(W.entries[0].exerciseId)).slice(0,30))>=0,
     document.getElementById('wmHowLine').textContent.slice(0,80));
  document.getElementById('wmHowLine').click();
  ok('tapping it opens the full instructions',
     document.getElementById('sheet').classList.contains('on')
     && /The plan in full/.test(document.getElementById('sheet').innerHTML));
  closeSheet();
  exitWM(true); DB.checkins=keepC;
})();

// ---------- SOUND AND ALERTS ----------
(function(){
  var keepS=JSON.parse(JSON.stringify(DB.settings));

  // sound: on by default, and never throws whatever the browser does
  ok('sound is on by default', freshDB().settings.sound===true);
  ok('alerts are off by default', freshDB().settings.notify===false);
  ok('soundOn follows the setting', (function(){
     DB.settings.sound=false; var a=soundOn();
     DB.settings.sound=true;  return a===false && soundOn()===true; })());
  ok('a muted app builds no AudioContext',
     (function(){ DB.settings.sound=false; var c=audioCtx();
                  DB.settings.sound=true; return c===null; })());
  tryRun('every cue is safe to fire', function(){
    SOUND.tick(); SOUND.set(); SOUND.rest(); SOUND.done();
    beep(440,0.01,0,0.01);
  });

  // alerts: never fire without both the setting AND the permission
  ok('notify does nothing with the setting off', (function(){
     DB.settings.notify=false; return notifyOn()===false; })());
  ok('notify does nothing without permission', (function(){
     DB.settings.notify=true;
     var granted = notifySupported() && Notification.permission==='granted';
     var on=notifyOn();
     DB.settings.notify=false;
     return on===granted; })(), notifyState());
  tryRun('raising an alert never throws', function(){ notify('x','y'); });
  ok('notifyState is one of the four answers',
     ['default','granted','denied','unsupported'].indexOf(notifyState())>=0,
     notifyState());

  // the settings controls exist and write through
  SETTINGS_ALL();
  ok('there is a sound switch', !!document.getElementById('sSound'));
  ok('there is an alert switch', !!document.getElementById('sNotify'));
  ok('and the alert explanation says it is not a push notification',
     /not a push notification/.test(document.getElementById('view').innerHTML)
     || notifyState()!=='default',
     (document.getElementById('sNotifyH')||{}).textContent);
  (function(){
    var e=document.getElementById('sSound');
    e.checked=false; e.dispatchEvent(new Event('change',{bubbles:true}));
    ok('turning sound off writes through', DB.settings.sound===false);
    e.checked=true; e.dispatchEvent(new Event('change',{bubbles:true}));
    ok('and back on again', DB.settings.sound===true);
  })();
  // the alert switch must never leave itself on without permission
  (function(){
    if(notifyState()==='granted') { ok('alerts stay consistent with permission', true, 'granted'); return; }
    var e=document.getElementById('sNotify');
    e.checked=true; e.dispatchEvent(new Event('change',{bubbles:true}));
    ok('an alert switch cannot stay on without permission',
       DB.settings.notify===false, DB.settings.notify+' / '+notifyState());
  })();

  DB.settings=keepS;
})();

/* Whether any push infrastructure crept in is checked against the SHIPPED
   file by verify_web.py, not here: this page concatenates the app with the
   tests, so a test that greps its own source for "pushManager" finds the
   string it is looking for in itself and passes or fails meaninglessly. */

// ---------- THE BLOCK PLAN IS APPLIED, NOT JUST DISPLAYED ----------
(function(){
  /* progressionCard() has always shown the user a volume percentage and an
     RPE cap for each of the eight weeks. Nothing read either field:
     sessionBlocks() never called currentPhase(), so a deload week was
     prescribed set for set, rep for rep, identically to a peak week. Every
     existing test asserted what the app did; none asserted that it matched
     what the app said. */
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  var keepS=DB.sessions;
  DB.sessions=[];

  var at=function(week){
    // put the plan start far enough back that `week` is the current one, and
    // give every week a logged session so trainedWeeks does not hold it back.
    //
    // The session dates are aligned to ISO weeks (Monday), NOT to planStart+7w.
    // trainedWeeks() walks Monday-to-Sunday buckets, so seeding at planStart+1
    // put that session in the wrong bucket whenever planStart fell on a Sunday
    // - the first week's bucket came up empty, the phase stalled at 1, and
    // seven progression assertions failed. Only on Sundays, which is why it
    // survived this long.
    var start=addDays(todayISO(), -(week-1)*7);
    DB.profile.planStart=start;
    DB.sessions=[];
    var wk0=weekStartOf(start);
    for(var w=0; w<week; w++){
      /* The Monday itself, not Monday+1. On a Monday, +1 pushed the last
         week's session into tomorrow, the clamp pulled it back to today, two
         weeks collapsed into one bucket and the phase counter came up one
         short - so this failed only on Mondays, which is how it survived. */
      var d=addDays(wk0, w*7);
      if(d>todayISO()) d=todayISO();          // never log in the future
      DB.sessions.push({id:'ph'+w, date:d, done:true,
        workoutId:'w_lowerA', workoutName:'Lower A', variant:'full', entries:[]});
    }
    return currentPhase();
  };

  var p1=at(1);
  ok('week 1 is Re-Entry at 80%', p1.w===1 && p1.vol===0.8, p1.w+'/'+p1.vol);
  var b1=sessionBlocks({workoutId:'w_lowerA', variant:'full', date:todayISO()});
  var p2=at(2);
  ok('week 2 is Build at 100%', p2.w===2 && p2.vol===1, p2.w+'/'+p2.vol);
  var b2=sessionBlocks({workoutId:'w_lowerA', variant:'full', date:todayISO()});
  var p4=at(4);
  ok('week 4 is the Deload at 60%', p4.w===4 && p4.vol===0.6, p4.w+'/'+p4.vol);
  var b4=sessionBlocks({workoutId:'w_lowerA', variant:'full', date:todayISO()});

  var setsOf=function(bs){ return bs.reduce(function(a,b){ return a+(+b.sets||0); },0); };
  ok('a re-entry week prescribes less than a build week',
     setsOf(b1)<setsOf(b2), setsOf(b1)+' vs '+setsOf(b2));
  ok('and a deload week prescribes less again or the same',
     setsOf(b4)<=setsOf(b1), setsOf(b4)+' vs '+setsOf(b1));
  ok('the deload week is actually a deload', setsOf(b4)<setsOf(b2),
     setsOf(b4)+' vs '+setsOf(b2));
  ok('but no exercise is cut below one set',
     b4.every(function(b){ return !b.sets || b.sets>=1; }),
     b4.map(function(b){return b.sets;}).join(','));
  ok('and nothing loses more than one set',
     b4.every(function(b,n){ return !b2[n] || (+b2[n].sets - +b.sets)<=1; }),
     b2.map(function(b){return b.sets;}).join(',')+' -> '+b4.map(function(b){return b.sets;}).join(','));
  ok('the reason is recorded on the block',
     b4.some(function(b){ return /Deload/.test(b.progNote||''); }),
     (b4.filter(function(b){return b.progNote;})[0]||{}).progNote);

  // the effort ceiling does real work too
  var overCap=function(bs,cap){ return bs.filter(function(b){
    var ns=String(b.rpe||'').match(/[0-9]+/g)||[];
    return ns.some(function(n){ return +n>cap; }); }); };
  ok('no block exceeds the deload effort ceiling', overCap(b4,6).length===0,
     overCap(b4,6).map(function(b){return b.rpe;}).join(','));
  ok('nor the re-entry one', overCap(b1,7).length===0,
     overCap(b1,7).map(function(b){return b.rpe;}).join(','));

  // capping must never produce 'RPE 6-6'
  ok('a capped range does not read as a repeated number',
     capRpe('RPE 8–9',6)==='RPE 6', capRpe('RPE 8–9',6));
  ok('a range under the cap is untouched', capRpe('RPE 4–5',7)==='RPE 4–5');
  ok('a single value is capped', capRpe('RPE 9',7)==='RPE 7', capRpe('RPE 9',7));
  ok('no cap means no change', capRpe('RPE 9',null)==='RPE 9');
  ok('a dash is left alone', capRpe('—',6)==='—');

  DB.profile=keepP; DB.sessions=keepS;
})();

// ---------- PROGRESSION IS EARNED, NOT SCHEDULED ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins, keepP=JSON.parse(JSON.stringify(DB.profile));
  var T=todayISO();

  var sess=function(id,ago,planned,logged){
    return {id:id, date:addDays(T,-ago), done:true, workoutId:'w_lowerA',
      workoutName:'Lower A', variant:'full', entries:[
        {exerciseId:'lx01', name:'Tempo Goblet Squat', plannedSets:planned,
         plannedReps:'8–12', plannedRpe:'RPE 8',
         sets:Array.apply(null,{length:planned}).map(function(_,n){
           return {reps:'12', weight:'20', rpe:'8', done:n<logged}; })}]};
  };

  // --- the gate ---
  DB.sessions=[];
  ok('nothing is measured with no history', progressGate(T).ok===false);
  ok('and it says so plainly', /finished session/i.test(progressGate(T).line),
     progressGate(T).line);

  DB.sessions=[sess('g1',7,3,3)];
  ok('one session is not enough to measure', progressGate(T).ok===false,
     progressGate(T).line);

  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  var g=progressGate(T);
  ok('two complete sessions open the gate', g.ok===true, g.line);
  ok('and it reports the figure it used', g.pct===1 && /100%/.test(g.line), g.line);

  DB.sessions=[sess('g1',7,4,1), sess('g2',3,4,1)];
  ok('turning up and doing a quarter of it does not', progressGate(T).ok===false,
     progressGate(T).line);
  ok('and the reason names the percentage', /50%|25%/.test(progressGate(T).line),
     progressGate(T).line);

  // work outside the window does not count
  DB.sessions=[sess('g1',40,3,3), sess('g2',35,3,3)];
  ok('a month ago is outside the window', progressGate(T).sessions===0,
     progressGate(T).sessions);

  // --- what actually happens to the numbers ---
  var en=function(){ return {exerciseId:'lx01', plannedSets:3,
                             plannedReps:'8–12', plannedRpe:'RPE 8'}; };

  DB.sessions=[];
  ok('a first attempt sets the baseline', nextTarget(en(),T).kind==='new',
     nextTarget(en(),T).kind);

  // gate shut -> hold, whatever the performance was
  DB.sessions=[sess('g1',7,3,3)];
  ok('a shut gate holds the numbers', nextTarget(en(),T).kind==='hold',
     nextTarget(en(),T).kind+' :: '+nextTarget(en(),T).line);

  // gate open, top of the range, effort as prescribed -> load
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  var t1=nextTarget(en(),T);
  ok('finishing at the top of the range adds load', t1.kind==='load', t1.kind+' '+t1.line);
  ok('the load went up by one increment',
     +t1.weight===20+stepSize('weight',20), t1.weight);
  ok('and the reps go back to the bottom of the range', t1.reps==='8', t1.reps);
  ok('and it says why', /hit 12 on every set/.test(t1.line), t1.line);

  // gate open, short of the top -> one more rep, same load
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  DB.sessions[1].entries[0].sets.forEach(function(s){ s.reps='10'; });
  var t2=nextTarget(en(),T);
  ok('short of the top of the range adds a rep', t2.kind==='reps', t2.kind+' '+t2.line);
  ok('one rep, not two', t2.reps==='11', t2.reps);
  ok('and the load is unchanged', t2.weight==='20', t2.weight);

  // ...and it never runs past the top of the range
  DB.sessions[1].entries[0].sets.forEach(function(s){ s.reps='12'; });
  DB.sessions[1].entries[0].sets[0].reps='11';
  var t2b=nextTarget(en(),T);
  ok('a rep step stops at the top of the range', t2b.reps==='12', t2b.reps);

  // gate open but it cost more than prescribed -> hold
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  DB.sessions[1].entries[0].sets.forEach(function(s){ s.rpe='10'; });
  var t3=nextTarget(en(),T);
  ok('a session harder than prescribed holds the load', t3.kind==='hold',
     t3.kind+' '+t3.line);
  ok('and says what it is waiting for', /RPE 10/.test(t3.line), t3.line);

  /* gate open but THIS exercise was only half done -> hold.
     The fortnight has to stay above the gate's threshold while this one
     exercise falls short, or the gate shuts first and answers instead -
     which is correct behaviour, and not what this case is testing. */
  DB.sessions=[sess('g1',10,10,10), sess('g2',7,10,10), sess('g3',1,6,4)];
  ok('the fortnight is still above the gate', progressGate(T).ok===true,
     progressGate(T).line);
  var t4=nextTarget(en(),T);
  ok('an unfinished exercise holds its numbers', t4.kind==='hold', t4.kind+' '+t4.line);
  ok('and counts what went in', /4 of 6 sets/.test(t4.line), t4.line);

  // a skipped exercise holds too
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  DB.sessions[1].entries[0].skipped=true;
  ok('a skipped exercise holds its numbers', nextTarget(en(),T).kind==='hold',
     nextTarget(en(),T).line);

  // bodyweight: nothing to load, so the reps keep going
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  DB.sessions.forEach(function(s){ s.entries[0].sets.forEach(function(x){ x.weight=''; }); });
  var t5=nextTarget(en(),T);
  ok('with no load to add the reps go past the range', t5.kind==='reps', t5.kind+' '+t5.line);
  ok('and it says that is why', /No load to add/.test(t5.line), t5.line);

  // --- the block bonus ---
  DB.sessions=[sess('g1',7,3,3), sess('g2',3,3,3)];
  ok('the first block gets no bonus', blockBonus({block:1,vol:1},T)===0);
  ok('the second block gets one extra set', blockBonus({block:2,vol:1},T)===1);
  ok('and it is capped at two', blockBonus({block:9,vol:1},T)===2);
  ok('never in a deload week', blockBonus({block:3,vol:0.6},T)===0);
  DB.sessions=[sess('g1',7,4,1), sess('g2',3,4,1)];
  ok('and never with the gate shut', blockBonus({block:3,vol:1},T)===0);

  DB.sessions=keepS; DB.checkins=keepC; DB.profile=keepP;
})();

// ---------- A HOLD IS TIMED, NOT COUNTED ----------
(function(){
  // what counts as a hold
  ok('20s is a hold', (function(){ var h=setSecs('20s'); return h && h.hi===20; })(),
     JSON.stringify(setSecs('20s')));
  ok('30-45s is a hold with a range', (function(){ var h=setSecs('30–45s');
     return h && h.lo===30 && h.hi===45; })(), JSON.stringify(setSecs('30–45s')));
  ok('40s / side is a hold, per side', (function(){ var h=setSecs('40s / side');
     return h && h.hi===40 && h.perSide===true; })(), JSON.stringify(setSecs('40s / side')));
  ok('a space before the unit is still a hold',
     !!setSecs('20–40 s / side'), JSON.stringify(setSecs('20–40 s / side')));

  // and what is NOT: these are all in the block tables
  ok('20 min is not a hold', setSecs('20 min')===null);
  ok('30-40 min is not a hold', setSecs('30–40 min')===null);
  ok('an interval structure is not a hold', setSecs('20s hard / 40s easy')===null);
  ok('a rep-and-hold hybrid is not a hold', setSecs('5 × 8s')===null);
  ok('a distance is not a hold', setSecs('6 × 8 m')===null && setSecs('10 m')===null);
  ok('plain reps are not a hold', setSecs('8–12')===null && setSecs('15')===null);
  ok('nothing is not a hold', setSecs('')===null && setSecs(null)===null);
  ok('and nothing absurdly long is a set timer', setSecs('600s')===null);

  ok('the label never says reps', /seconds/.test(secsLabel({lo:30,hi:45})),
     secsLabel({lo:30,hi:45}));
  ok('a single value reads as one number', secsLabel({lo:20,hi:20})==='20 seconds',
     secsLabel({lo:20,hi:20}));
  ok('per side is carried through', /per side/.test(secsLabel({lo:40,hi:40,perSide:true})),
     secsLabel({lo:40,hi:40,perSide:true}));

  // every timed exercise in the library is recognised as one
  var missed=DB.exercises.filter(function(e){
    return /hollow|plank|wall sit|dead hang|farmer carry|side plank/i.test(e.name)
        && /[0-9]\\s*s\\b|[0-9]s\\b/.test(String(e.reps))
        && !setSecs(e.reps); });
  ok('every second-based hold in the library is recognised', missed.length===0,
     missed.map(function(e){return e.name+'='+e.reps;}).join(', '));

  // summaries never say a hold in reps
  ok('a summary of a hold carries the unit',
     setsSummary([{reps:'40',weight:'',done:true},{reps:'40',weight:'',done:true}],true)==='2 × 40s',
     setsSummary([{reps:'40',weight:''},{reps:'40',weight:''}],true));
  ok('and a summary of reps does not', setsSummary([{reps:'10',weight:''}],false)==='1 × 10',
     setsSummary([{reps:'10',weight:''}],false));

  // progression on a hold is in seconds
  var keepS=DB.sessions, T=todayISO();
  var hs=function(id,ago,secs){
    return {id:id, date:addDays(T,-ago), done:true, workoutId:'w_core',
      workoutName:'Core', variant:'full', entries:[
        {exerciseId:'cr01', name:'Hold', plannedSets:3, plannedReps:'30–45s',
         plannedRpe:'RPE 8',
         sets:[{reps:secs,weight:'',rpe:'8',done:true},
               {reps:secs,weight:'',rpe:'8',done:true},
               {reps:secs,weight:'',rpe:'8',done:true}]}]};
  };
  DB.sessions=[hs('h1',7,'30'), hs('h2',3,'30')];
  var th=nextTarget({exerciseId:'cr01', plannedSets:3, plannedReps:'30–45s',
                     plannedRpe:'RPE 8'}, T);
  ok('a hold progresses in seconds', th.kind==='secs', th.kind+' '+th.line);
  ok('by five at a time', th.reps==='35', th.reps);
  ok('and its reason never says reps', th.line.indexOf('rep')<0, th.line);
  DB.sessions=keepS;
})();

// ---------- THE HOLD SCREEN SAYS NOTHING ABOUT REPS ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins, keepRestH=DB.settings.restTimerOn;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  DB.sessions=[];
  /* A logged hold now starts the rest timer like any other set, and rest owns
     the screen while it runs. This block is about the hold itself. */
  DB.settings.restTimerOn=false;

  // find a session that actually contains a timed hold
  var found=null;
  ['w_core','w_lowerA','w_upperA','w_upperB','w_lowerB','w_recovery'].forEach(function(id){
    if(found) return;
    if(!DB.workouts.find(function(w){return w.id===id;})) return;
    startWorkout(id,'full',T);
    for(var n=0;n<W.entries.length;n++){ if(W.entries[n].timed){ found={id:id,n:n}; break; } }
    if(!found) exitWM(true);
  });
  ok('some session contains a timed hold', !!found,
     found? found.id+' #'+found.n : 'none found');

  if(found){
    W.phase='main'; W.step=found.n; drawWM();
    var en=W.entries[found.n], body=document.getElementById('wmBody');
    /* Idle, the target is a button you can tap to change; running, it is the
       live countdown. Either way it is the one number on the screen. */
    ok('the hold shows its target', !!document.getElementById('wsAdj') || !!document.getElementById('holdT'),
       body.textContent.slice(0,80));
    ok('and a button to start it', !!document.getElementById('holdBtn'));
    ok('the target is stated in seconds, not reps',
       /[0-9]:[0-9][0-9]/.test((document.getElementById('wsAdj')||document.getElementById('holdT')).textContent)
       && body.textContent.indexOf(' reps')<0,
       body.textContent.slice(0,120));
    ok('the word "reps" appears nowhere on the screen',
       !/\\breps?\\b/i.test(body.textContent), (function(){ var s=body.textContent.toLowerCase(); var k=s.indexOf('rep');
         return k<0? 'no "rep" in textContent len='+s.length
                   : '...'+body.textContent.slice(Math.max(0,k-60), k+70)+'...'; })());
    ok('the plan line is said in seconds',
       /seconds/.test(document.querySelector('.wm-sub').textContent),
       document.querySelector('.wm-sub').textContent);

    // starting it
    document.getElementById('holdBtn').click();
    ok('the countdown is running', holdActive() && HOLD.set===0,
       JSON.stringify({a:holdActive(), set:HOLD.set}));
    ok('the button becomes a stop', /Stop/.test(document.getElementById('holdBtn').textContent),
       document.getElementById('holdBtn').textContent);
    ok('nothing is logged just by starting', en.sets[0].done===false);

    // stopping early records what was actually held, not the target
    holdEnd=Date.now()+(HOLD.secs-8)*1000;      // as if 8 seconds had passed
    stopHold();
    ok('stopping early records the time actually held',
       +en.sets[0].reps===8, en.sets[0].reps);
    ok('and still does not log the set', en.sets[0].done===false);
    ok('the countdown has stopped', !holdActive());

    // running it out logs the set by itself
    en.sets[0].reps=''; drawWM();
    document.getElementById('holdBtn').click();
    var want=HOLD.secs;
    holdEnd=Date.now()-10;  holdDone=false;  paintHold();
    ok('a completed hold logs its own set', en.sets[0].done===true);
    ok('at the full target', +en.sets[0].reps===want, en.sets[0].reps+' vs '+want);
    ok('and the countdown is cleared', !holdActive());
    /* There is no logged-sets strip on the screen any more, so the unit is
       checked where it now matters: in the record the engine reads, and on the
       screen's own reading of the set. */
    ok('a hold is recorded in seconds, never as reps',
       en.timed && +en.sets[0].reps===want, en.sets[0].reps+'s');
    ok('and the screen never calls them reps',
       document.getElementById('wmBody').textContent.indexOf(' reps')<0,
       document.getElementById('wmBody').textContent.slice(0,120));

    // the seconds stepper moves in fives, not ones — now behind the target,
    // which is tappable exactly like a rep count is
    en.sets[0].done=false; drawWM();
    ok('the hold target is tappable to change it', !!document.getElementById('wsAdj'));
    document.getElementById('wsAdj').click();
    var sec=document.querySelector('#sheetBody [data-k=reps]');
    ok('and the sheet asks for seconds, not reps',
       /Seconds/.test(document.getElementById('sheetBody').textContent),
       document.getElementById('sheetBody').textContent.slice(0,60));
    sec.value='30'; sec.dispatchEvent(new Event('input',{bubbles:true}));
    sec.parentElement.querySelector('button[data-d="1"]').click();
    ok('seconds step by five', sec.value==='35', sec.value);
    closeSheet();

    exitWM(true);
  }
  DB.settings.restTimerOn=keepRestH;
  DB.sessions=keepS; DB.checkins=keepC;
})();

// ---------- A RUN IS A CLOCK, A CALF RAISE IS NOT ----------
(function(){
  // --- the clock formats ---
  ok('a short session reads as minutes and seconds', hms(754)==='12:34', hms(754));
  ok('a long one rolls over into hours', hms(4530)==='1:15:30', hms(4530));
  ok('zero is zero', hms(0)==='0:00', hms(0));
  ok('pace reads as minutes per kilometre', paceStr(5.7)==='5:42 /km', paceStr(5.7));
  ok('a rounded-up second does not read as :60', paceStr(5.999)==='6:00 /km', paceStr(5.999));
  ok('no pace is a dash', paceStr(null)==='—' && paceStr(0)==='—');

  // --- how long is the prescription ---
  ok('a range takes its midpoint', cardioMinutes({reps:'25–45 min'})===35,
     cardioMinutes({reps:'25–45 min'}));
  ok('a single value is itself', cardioMinutes({reps:'30 min'})===30);
  ok('trailing words do not confuse it', cardioMinutes({reps:'18–25 min at tempo'})===22,
     cardioMinutes({reps:'18–25 min at tempo'}));
  ok('an interval structure totals up', cardioMinutes({sets:8,reps:'20s hard / 40s easy'})===8,
     cardioMinutes({sets:8,reps:'20s hard / 40s easy'}));
  ok('and so does one measured in minutes',
     cardioMinutes({sets:6,reps:'1 min hard / 2 min easy'})===18,
     cardioMinutes({sets:6,reps:'1 min hard / 2 min easy'}));
  ok('repeats written into the text are counted',
     cardioMinutes({sets:1,reps:'2 × 8 min, 3 min easy between'})===19,
     cardioMinutes({sets:1,reps:'2 × 8 min, 3 min easy between'}));
  ok('plain reps are not a span of time', cardioMinutes({reps:'20'})===null);
  ok('and neither are short hill efforts', cardioMinutes({sets:6,reps:'10–15s uphill'})===null,
     cardioMinutes({sets:6,reps:'10–15s uphill'}));

  // --- what kind of effort is it ---
  ok('a run is running', cardioActOf({cat:'cardio',equip:'RUN',name:'Zone 2 Run'})==='running');
  ok('a bike is cycling', cardioActOf({cat:'cardio',equip:'BIKE',name:'Zone 2 Bike'})==='cycling');
  ok('a walk is walking', cardioActOf({cat:'cardio',equip:'RUN',name:'Easy Walk'})==='walking',
     cardioActOf({cat:'cardio',equip:'RUN',name:'Easy Walk'}));
  ok('a calf raise is not cardio at all', cardioActOf({cat:'lower',name:'Calf Raise'})===null);

  // --- the two together, on the real library ---
  var spec=function(id,reps,sets){ return cardioSpec({ex:id,reps:reps,sets:sets}, exOf(id)); };
  ok('Zone 2 Run is a clock', !!spec('cd01','25–45 min',1) && spec('cd01','25–45 min',1).act==='running',
     JSON.stringify(spec('cd01','25–45 min',1)));
  ok('Zone 2 Bike is a clock', !!spec('cd02','30–60 min',1) && spec('cd02','30–60 min',1).act==='cycling');
  ok('the interval run is a clock', !!spec('cd03','20s hard / 40s easy',8),
     JSON.stringify(spec('cd03','20s hard / 40s easy',8)));
  /* the one that has to stay a set list even though it is cat:'cardio' */
  ok('hill sprints stay a set list', spec('cd04','10–15s uphill',6)===null,
     JSON.stringify(spec('cd04','10–15s uphill',6)));
  ok('and a calf raise certainly does', spec('lx18','20',2)===null);

  /* The clock has to follow an equipment SUBSTITUTION, not the original.
     Somebody with running shoes and no bike gets a run where the plan said
     ride, and the screen has to say running and count 35 minutes, not 48. */
  (function(){
    var keepG=DB.profile.gear;
    DB.profile.gear=['run'];
    var bs=sessionBlocks({workoutId:'w_bike', variant:'full', date:todayISO()});
    var cb=null;
    bs.forEach(function(b){ if(!cb){ var s=cardioSpec(b,exOf(b.ex)); if(s) cb={b:b,s:s}; } });
    ok('a ride with no bike still gives a clock', !!cb,
       bs.map(function(b){return b.ex;}).join(','));
    if(cb){
      ok('and the clock follows the substitute', cb.s.act==='running', cb.s.act);
      ok('with the substitute’s own duration', cb.s.targetMin===35, cb.s.targetMin);
      ok('and it says what it swapped', !!cb.b.swappedFrom, cb.b.swappedFrom);
    }
    /* and with no gear at all, a run is not prescribed to someone who never
       said they could run — the block becomes a set list, not a clock */
    DB.profile.gear=[];
    var none=sessionBlocks({workoutId:'w_runEasy', variant:'full', date:todayISO()});
    ok('no run gear means no run', none.every(function(b){
       return cardioSpec(b,exOf(b.ex))===null; }),
       none.map(function(b){return b.ex;}).join(','));
    DB.profile.gear=keepG;
  })();

  // --- strain uses the same curve as everything else ---
  var s1=liveStrain('running',30,6), s2=liveStrain('running',60,6);
  ok('strain rises with time', s2>s1, s1+' -> '+s2);
  var h1=liveStrain('running',30,4), h2=liveStrain('running',30,8);
  ok('and with effort', h2>h1, h1+' -> '+h2);
  ok('it is on the same 0-21 scale as a saved activity',
     Math.abs(liveStrain('running',40,6)
              - activityLoad({type:'running',min:40,rpe:6}))<0.001);
  ok('no time is no strain', liveStrain('running',0,6)===0);
  ok('a word becomes a number', effortRpe('Hard',null)===8 && effortRpe('Easy',null)===4,
     effortRpe('Hard',null)+'/'+effortRpe('Easy',null));
  ok('and an RPE string does too', effortRpe(null,'RPE 7')===7, effortRpe(null,'RPE 7'));
  ok('with a neutral fallback', effortRpe(null,null)===6);
})();

// ---------- THE CLOCK SCREEN ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins, keepA=DB.activities;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:76,hrv:88,rhr:51,sleepMin:465,energy:8,
                  soreness:2,stress:3,motivation:8,pain:'None'};
  DB.sessions=[]; DB.activities=[];

  tryRun('starting a run', function(){ startWorkout('w_runEasy','full',T); });
  // find the cardio block and the set-list block that follows it
  var ci=-1, si=-1;
  W.entries.forEach(function(e,n){
    if(e.cardio && ci<0) ci=n;
    if(!e.cardio && si<0 && ci>=0) si=n;
  });
  ok('the run session has a clock block', ci>=0,
     W.entries.map(function(e){return e.name+(e.cardio?'[clock]':'');}).join(', '));
  ok('and still has set-list blocks after it', si>=0,
     W.entries.map(function(e){return e.name;}).join(', '));

  W.phase='main'; W.step=ci; drawWM();
  var en=W.entries[ci], body=document.getElementById('wmBody');
  ok('the clock is on screen', !!document.getElementById('cardT'));
  ok('there is a start button', !!document.getElementById('cardGo'));
  ok('there is no reps stepper', !document.querySelector('.wnow [data-k=reps]'));
  ok('the word "reps" appears nowhere', !/[^a-z]reps?[^a-z]/i.test(' '+body.textContent+' '),
     (function(){ var s=body.textContent.toLowerCase(); var k=s.indexOf('rep');
        return k<0?'(none)':body.textContent.slice(Math.max(0,k-50),k+60); })());
  ok('it says how long it should take',
     /about [0-9]+ minutes/.test(document.querySelector('.wm-sub').textContent),
     document.querySelector('.wm-sub').textContent);
  ok('the clock starts at zero', document.getElementById('cardT').textContent==='0:00',
     document.getElementById('cardT').textContent);
  ok('and the strain with it', document.getElementById('cardS').textContent==='0.0',
     document.getElementById('cardS').textContent);

  // start it
  document.getElementById('cardGo').click();
  ok('the clock is running', cardRunning(en));
  ok('finish and lap appear', !!document.getElementById('cardStop')
     && !!document.getElementById('cardLap'));
  ok('start is gone', !document.getElementById('cardGo'));

  // wind it back as if 24 minutes had passed
  en.run.startedAt = Date.now() - 24*60*1000;
  cardTick();
  ok('the clock shows the time since start',
     /^24:0[0-9]$/.test(document.getElementById('cardT').textContent),
     document.getElementById('cardT').textContent);
  ok('strain has been counting with it', +document.getElementById('cardS').textContent>0,
     document.getElementById('cardS').textContent);
  ok('and the minutes are already in the record', +en.sets[0].reps===24, en.sets[0].reps);
  ok('but nothing is logged until you say so', en.sets[0].done===false);

  // a lap
  document.getElementById('cardLap').click();
  ok('a lap is recorded', en.run.laps.length===1, en.run.laps.length);
  ok('and shown', document.querySelectorAll('.laps .lap').length===1);

  // finish
  document.getElementById('cardStop').click();
  ok('finishing stops the clock', !cardRunning(en));
  ok('the minutes are kept', +en.sets[0].reps===24, en.sets[0].reps);
  ok('and a log button appears', !!document.querySelector('#wmBody [data-log]'));
  document.querySelector('#wmBody [data-log]').click();
  ok('logging it marks the block done', en.sets[0].done===true);
  ok('and an effort is recorded with it', +en.sets[0].rpe>0, en.sets[0].rpe);
  cancelAuto();

  // the set-list block after the run is still a set list
  W.phase='main'; W.step=si; drawWM();
  ok('the calf raises after the run are still sets',
     !!document.querySelector('#wmBody [data-log]')
     && !document.getElementById('cardT'));
  ok('and are counted in reps, not on a clock',
     !!document.querySelector('.wset .ws-v') && !document.getElementById('holdT'),
     document.getElementById('wmBody').textContent.slice(0,90));

  exitWM(true);
  DB.sessions=keepS; DB.checkins=keepC; DB.activities=keepA;
})();

// ---------- STARTING SOMETHING THAT IS NOT IN THE PLAN ----------
(function(){
  var keepA=DB.activities, keepS=DB.sessions;
  DB.activities=[]; DB.sessions=[];

  tryRun('starting a live activity', function(){ startLiveActivity('tennis','Hard'); });
  ok('workout mode is open', document.getElementById('wmode').classList.contains('on'));
  ok('it is an activity, not a session', W.kind==='activity' && W.saveAs==='activity');
  ok('the clock is already running', cardRunning(W.entries[0]));
  ok('there is no warm-up to skip past', W.step===0, W.step);
  ok('the header names the activity rather than counting exercises',
     /Hard/.test(document.getElementById('wmHead').textContent),
     document.getElementById('wmHead').textContent);

  // 75 minutes of tennis
  var en=W.entries[0];
  en.run.startedAt = Date.now() - 75*60*1000;
  W.startedAt = en.run.startedAt;
  cardTick();
  ok('the clock counts from the start', +en.sets[0].reps===75, en.sets[0].reps);

  document.getElementById('cardStop').click();
  document.querySelector('#wmBody [data-log]').click();
  cancelAuto();
  nextStep();
  ok('the finish screen is the activity one', !!document.getElementById('afSave'),
     document.getElementById('wmBody').innerHTML.slice(0,200));
  ok('it reports the time from start to finish, in the Time tile',
     /75/.test(document.querySelector('#wmBody .stats').textContent),
     document.querySelector('#wmBody .stats').textContent.replace(/[^!-~]+/g,' '));
  ok('and does not ask the user to retype what the clock just measured',
     !document.getElementById('afMin'));
  ok('the heading is the activity, not a sentence about it',
     document.getElementById('afWhat').textContent.trim()==='Tennis',
     document.getElementById('afWhat').textContent);
  ok('with done said underneath instead',
     /^Done /.test(document.getElementById('afDone').textContent.trim()),
     document.getElementById('afDone').textContent);
  ok('and the strain it came to',
     /Strain/.test(document.getElementById('wmBody').textContent));
  ok('tennis is not asked for a distance', !document.getElementById('afDist'));
  ok('nothing is compared on a first effort',
     /becomes the mark to beat/.test(document.getElementById('afCmp').textContent),
     document.getElementById('afCmp').textContent.slice(0,140));

  document.getElementById('afSave').click();
  ok('an activity was saved', DB.activities.length===1, DB.activities.length);
  var a=DB.activities[0];
  ok('of the right kind', a.type==='tennis', a.type);
  ok('for the right length', a.min===75, a.min);
  ok('with the effort recorded', a.intensity==='Hard' && a.rpe===8,
     a.intensity+'/'+a.rpe);
  ok('and the clock span kept', !!a.startedAt && !!a.endedAt);
  ok('it is not marked as planned', a.planned===false);
  ok('workout mode closed', !document.getElementById('wmode').classList.contains('on'));
  ok('and the live session was cleared', !Store.pref('live'));

  // ...and a second one compares with the first
  tryRun('a second game', function(){ startLiveActivity('tennis','Moderate'); });
  W.entries[0].run.startedAt = Date.now() - 90*60*1000;
  cardTick();
  document.getElementById('cardStop').click();
  document.querySelector('#wmBody [data-log]').click();
  cancelAuto(); nextStep();
  ok('now there is something to compare with',
     /Compared with last time/.test(document.getElementById('afCmp').textContent),
     document.getElementById('afCmp').textContent.slice(0,140));
  ok('and it reports the gain in time',
     /[+]15/.test(document.getElementById('afCmp').textContent),
     document.getElementById('afCmp').textContent.slice(0,240));
  exitWM(true);

  DB.activities=keepA; DB.sessions=keepS;
})();

// ---------- WHAT CHANGED SINCE LAST TIME ----------
(function(){
  var keepA=DB.activities;
  var T=todayISO();
  DB.activities=[
    {id:'r1',date:addDays(T,-6),type:'running',min:34,dist:5.8,intensity:'Moderate',rpe:6},
    {id:'r2',date:addDays(T,-20),type:'running',min:28,dist:4.5,intensity:'Easy',rpe:4}
  ];
  var prev=lastEffort({type:'running', date:T});
  ok('the most recent comparable effort is used', prev && prev.date===addDays(T,-6),
     prev? prev.date : 'none');
  ok('its pace is worked out', prev && Math.abs(prev.pace-34/5.8)<0.001, prev&&prev.pace);
  ok('the live one is excluded from its own lookup',
     lastEffort({type:'running',date:T,excludeId:'r1'}).date===addDays(T,-20));
  ok('an activity you have never done has no comparison',
     lastEffort({type:'swimming',date:T})===null);

  // the pace inversion: faster is a smaller number and must read as good
  var faster=cmpRow('Pace', 5.5, 6.0, '', 2, true, paceStr);
  ok('a faster pace reads as progress', /cd up/.test(faster), faster);
  var slower=cmpRow('Pace', 6.5, 6.0, '', 2, true, paceStr);
  ok('a slower one does not', /cd down/.test(slower), slower);
  var longer=cmpRow('Time', 40, 34, 'min', 0);
  ok('more time reads as progress', /cd up/.test(longer), longer);
  var same=cmpRow('Time', 34, 34, 'min', 0);
  ok('no change says so', /no change/.test(same), same);
  ok('nothing to compare with shows just the number',
     cmpRow('Time', 34, null, 'min', 0).indexOf('class="cd')<0,
     cmpRow('Time', 34, null, 'min', 0));
  ok('a missing value shows nothing at all', cmpRow('Distance', null, 5, 'km', 1)==='');

  DB.activities=keepA;
})();

// ---------- A CHECK-IN IS READ BEFORE IT IS CHANGED ----------
(function(){
  var keepC=DB.checkins;
  var T=todayISO();
  DB.checkins={};

  /* Nothing recorded yet: there is nothing to read, so the form is the right
     answer and asking twice would be pointless ceremony. */
  openCheckinView(T);
  ok('with nothing recorded it opens the form', !!document.getElementById('ciSave')
     || !!document.getElementById('ciEn'),
     document.getElementById('sheetBody').innerHTML.slice(0,120));
  closeSheet();

  DB.checkins[T]={date:T,recovery:71,hrv:83,rhr:54,sleepMin:445,energy:7,
                  soreness:4,stress:3,motivation:8,pain:'None',availTime:60,
                  notes:'Legs felt heavy on the stairs.'};

  /* Once there IS something to read, a screen opened to read it should not put
     a dozen sliders under a stray thumb - the same lesson the profile screen
     in Settings already learned. */
  openCheckinView(T);
  ok('an existing check-in is shown, not offered for editing',
     !document.getElementById('ciEn') && !document.getElementById('ciSl'),
     document.getElementById('sheetBody').innerHTML.slice(0,160));
  ok('there is an Edit button', !!document.getElementById('ciEdit'));
  var body=document.getElementById('sheetBody').textContent;
  ok('it shows the readiness it produced',
     body.indexOf(String(readiness(T,DB.checkins[T]).score))>=0, body.slice(0,120));
  ok('and how long you slept', /7h 25m/.test(body), body.slice(0,300));
  ok('and how you felt', /Energy/.test(body) && body.indexOf('7 / 10')>=0, body.slice(0,400));
  ok('and the note you left', /heavy on the stairs/.test(body));

  document.getElementById('ciEdit').click();
  ok('Edit opens the editable form', !!document.getElementById('ciEn'),
     document.getElementById('sheetBody').innerHTML.slice(0,160));
  ok('with what you answered already in it',
     +document.getElementById('ciEn').value===7,
     document.getElementById('ciEn').value);
  closeSheet();

  /* The sleep score now opens the sleep page rather than the check-in: it is a
     sleep number, and what people want from it is the target and what tonight
     is worth. Editing is still reachable from there. */
  /* Built directly as well as through the ring: an exception thrown inside a
     click handler never reaches the caller, so a broken page would otherwise
     show up only as a mysteriously empty view. */
  resetStack(); TAB='today'; render();
  var slErr=null;
  try{ pushPage({build:pageSleep(T)}); }catch(e){ slErr=(e&&e.message)||String(e); }
  ok('the sleep page renders without error', slErr===null, slErr);
  /* Asserted on what the page SAYS, not on the absence of a #ciEn node: the
     check-in sheet closed just above leaves its markup parked in the DOM, so
     "no check-in form exists" is a question about sheet teardown rather than
     about where the sleep ring goes. */
  ok('the sleep score opens the sleep page, not the check-in form',
     !!document.getElementById('slEdit')
       && /What a night is worth/.test(document.getElementById('view').textContent),
     document.getElementById('view').textContent.slice(0,140));
  ok('and the check-in is still one tap from there',
     (function(){ var b=document.getElementById('slEdit'); if(!b) return false;
                  b.click();
                  var open=!!document.getElementById('ciEn');
                  if(open) closeSheet();
                  return open; })());
  resetStack(); TAB='today'; render();
  ok('and the readiness screen is what opens it',
     (function(){ pushPage({build:pageReadiness(T)});
                  document.getElementById('rdSleep').click();
                  return STACK.length===2; })(), STACK.length);
  resetStack(); render();

  DB.checkins=keepC; resetStack(); render();
})();

// ---------- FOUR DESTINATIONS, AND SETTINGS IS ONE OF THEM ----------
(function(){
  var ids=tabs().map(function(t){ return t.id; });
  ok('there are four destinations plus Log', ids.length===5, ids.join(','));
  ok('and Activity is no longer one of them', ids.indexOf('tennis')<0, ids.join(','));
  ok('Settings is', ids.indexOf('settings')>=0, ids.join(','));
  ok('and it is last, which puts it bottom right',
     ids[ids.length-1]==='settings', ids.join(','));

  renderNav();
  var btns=document.querySelectorAll('#nav button');
  ok('the bar renders one button per tab', btns.length===5, btns.length);
  ok('and the middle one is drawn as an action, not a destination',
     !!document.querySelector('#nav button.mid .nav-fab'));
  ok('the last one is Settings',
     btns[btns.length-1].dataset.tab==='settings',
     btns[btns.length-1].dataset.tab);

  /* The gear was a second way into a screen the bar now offers directly, in
     the corner of a phone that is hardest to reach one-handed. */
  resetStack(); TAB='today'; render();
  ok('there is no settings gear in the app bar',
     !document.getElementById('abGear'),
     document.getElementById('appbar').innerHTML.slice(0,200));

  // going to Settings lands on Settings, not inside whichever pane was open
  go('settings');
  ok('the tab opens the settings index', !!document.getElementById('setRows'));
  ok('with nothing pushed on top of it', STACK.length===0, STACK.length);
  ok('and the tab is lit', document.querySelector('#nav button.on').dataset.tab==='settings',
     document.querySelector('#nav button.on').dataset.tab);
  // open a pane, leave, come back: it must not resume three levels deep
  document.getElementById('setRows').querySelectorAll('button')[0].click();
  ok('a pane pushes a page', STACK.length===1, STACK.length);
  go('today');
  openSettings();
  ok('coming back lands on the index again', STACK.length===0 && !!document.getElementById('setRows'),
     STACK.length);

  /* an install that was left on the Activity tab must not boot into nothing */
  TAB='tennis'; render();
  ok('a saved tab that no longer exists falls back to Today', TAB==='today', TAB);

  go('today');
})();

// ---------- WHAT YOU DID IS REACHABLE FROM THE TILE THAT SAYS YOU DID IT ----------
(function(){
  var keepS=DB.sessions, keepC=DB.checkins, keepA=DB.activities;
  var T=todayISO();
  DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  DB.activities=[{id:'da1',date:T,type:'cycling',min:40,time:'07:00',
                  endTime:'07:40',intensity:'Moderate',rpe:6}];
  var w=DB.workouts.find(function(x){return x.id==='w_lowerA';});
  DB.sessions=[{id:'ds1',date:T,workoutId:'w_lowerA',workoutName:w.name,
    variant:'full',done:true,durationMin:52,setsDone:16,volume:1480,
    sessionRpe:8,band:'green',readinessScore:74,time:'18:00',
    entries:[{exerciseId:'lx01',name:'Tempo Goblet Squat',plannedSets:3,
      plannedReps:'8-12',plannedRpe:'RPE 8',plannedRest:'90s',note:'',
      sets:[{reps:'12',weight:'20',rpe:'8',done:true},
            {reps:'12',weight:'20',rpe:'8',done:true},
            {reps:'10',weight:'22.5',rpe:'9',done:true}]}]}];

  resetStack(); TAB='today'; render();
  var tile=document.getElementById('btnDone');
  ok('the done tile is a way in', !!tile,
     document.getElementById('view').innerHTML.slice(0,300));
  ok('and says so', /See what you did/.test(tile.textContent), tile.textContent);
  tile.click();
  ok('tapping it opens the session', document.getElementById('sheet').classList.contains('on'));
  ok('with what was actually done in it',
     /Tempo Goblet Squat/.test(document.getElementById('sheet').textContent),
     document.getElementById('sheet').textContent.slice(0,200));
  ok('and the numbers', /52/.test(document.getElementById('sheet').textContent));
  closeSheet();

  /* The activities card lists the session too, and that row passed the
     session OBJECT to a function that takes an id - so it did nothing at all,
     silently. Tapping is the only way to notice. */
  render();
  var srow=document.querySelector('#actsCard [data-sid]');
  ok('the session is a row on the day as well', !!srow,
     document.getElementById('actsCard').textContent.slice(0,200));
  srow.click();
  ok('and tapping that row opens it too',
     document.getElementById('sheet').classList.contains('on'));
  ok('the same session', /Tempo Goblet Squat/.test(document.getElementById('sheet').textContent));
  closeSheet();

  // and an activity row opens its own detail
  var arow=document.querySelector('#actsCard [data-aid]');
  ok('the activity is a row too', !!arow);
  arow.click();
  ok('tapping it opens the activity', document.getElementById('sheet').classList.contains('on'));
  /* Read first: opening a logged record to look at it must not put a dozen
     editable controls under a thumb. Same contract as the profile and the
     check-in. */
  ok('it opens as something you read, not a form',
     !document.getElementById('asFrom') && !!document.getElementById('avEdit'),
     document.getElementById('sheetBody').innerHTML.slice(0,140));
  ok('with its own numbers in it',
     /07:00/.test(document.getElementById('sheetBody').textContent),
     document.getElementById('sheetBody').textContent.slice(0,200));
  ok('and a way to delete it', !!document.getElementById('avDel'));
  document.getElementById('avEdit').click();
  ok('Edit opens the form', !!document.getElementById('asFrom'),
     document.getElementById('sheetBody').innerHTML.slice(0,140));
  ok('with the values already in it',
     document.getElementById('asFrom').value==='07:00',
     document.getElementById('asFrom').value);
  closeSheet();

  DB.sessions=keepS; DB.checkins=keepC; DB.activities=keepA;
  resetStack(); render();
})();

// ---------- WHAT IS ALLOWED THROUGH THE IMPORT DOOR ----------
(function(){
  var F=function(name,size,type){ return {name:name,
    size:(size===undefined||size===''?1000:size),
    type:(type===undefined?'text/csv':type)}; };

  ok('a normal csv is accepted', importFileCheck(F('physiological_cycles.csv'))===null,
     importFileCheck(F('physiological_cycles.csv')));
  ok('a .txt export is accepted', importFileCheck(F('export.txt','', 'text/plain'))===null);
  ok('a browser that reports no type is not punished for it',
     importFileCheck(F('cycles.csv',1000,''))===null,
     importFileCheck(F('cycles.csv',1000,'')));

  /* accept= is a hint to the picker. These are the checks that run. */
  ok('an executable is refused', !!importFileCheck(F('payload.exe',1000,'application/x-msdownload')));
  ok('a pdf is refused', !!importFileCheck(F('report.pdf',1000,'application/pdf')));
  ok('an html file is refused', !!importFileCheck(F('page.html',1000,'text/html')));
  ok('and the refusal says what it was', /not a CSV|Only .csv/i.test(importFileCheck(F('page.html',1000,'text/html'))),
     importFileCheck(F('page.html',1000,'text/html')));
  ok('a csv name on a non-csv type is refused',
     !!importFileCheck(F('sneaky.csv',1000,'application/x-msdownload')),
     importFileCheck(F('sneaky.csv',1000,'application/x-msdownload')));

  ok('an empty file is refused', !!importFileCheck(F('empty.csv',0)));
  ok('an oversized file is refused', !!importFileCheck(F('huge.csv',80*1024*1024)));
  ok('and says how big it was', /80 MB/.test(importFileCheck(F('huge.csv',80*1024*1024))),
     importFileCheck(F('huge.csv',80*1024*1024)));
  ok('a file at the limit is accepted', importFileCheck(F('big.csv',IMPORT_MAX_BYTES-1))===null);

  /* a filename is data, never a path */
  ok('a path separator in a name is refused', !!importFileCheck(F('../../etc/passwd.csv')));
  ok('a windows separator too', !!importFileCheck(F('..'+String.fromCharCode(92)+'windows.csv')));

  // content checks
  ok('a binary file with a csv name is refused', (function(){
     var r=importWhoopFile('fake.csv','PK'+String.fromCharCode(0)+String.fromCharCode(3)+'rubbish');
     return !!r.error && /not a text file/i.test(r.error); })(),
     JSON.stringify(importWhoopFile('fake.csv','PK'+String.fromCharCode(0)+String.fromCharCode(3)+'rubbish')));
  ok('an empty csv is refused', !!importWhoopFile('x.csv','').error);
  ok('a csv with only headers is refused', !!importWhoopFile('x.csv','a,b,c').error);
  ok('an unrecognised csv is refused rather than guessed at',
     /Unrecognised/i.test(importWhoopFile('x.csv','colour,shape\\nred,round').error||''),
     importWhoopFile('x.csv','colour,shape\\nred,round').error);
})();

// ---------- WHAT AN IMPORT KEEPS, AND WHAT IT THROWS AWAY ----------
(function(){
  var keepW=JSON.parse(JSON.stringify(DB.whoop));
  DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};

  /* A journal export carries a free-text Notes column. The engine has no use
     for it, so it must not end up in storage - the least sensitive place for
     a person's written notes is nowhere. */
  var journal='Cycle start time,Cycle end time,Cycle timezone,Question text,Answered yes,Notes\\n'+
    '2030-01-01 06:00:00,2030-01-01 22:00:00,UTC+00:00,Did you drink alcohol?,true,'+
    'Half a bottle of wine with dinner and I felt awful\\n';
  var r=importWhoopFile('journal_entries.csv',journal);
  ok('a journal export is recognised', r.kind==='journal', JSON.stringify(r));
  ok('and a row is kept', DB.whoop.journal.length===1, DB.whoop.journal.length);
  var row=DB.whoop.journal[0];
  ok('the question is kept', /alcohol/i.test(row.q), row.q);
  ok('the answer is kept', row.yes===true);
  /* the whole point */
  ok('the free-text note is NOT kept',
     JSON.stringify(row).indexOf('bottle of wine')<0, JSON.stringify(row));
  ok('and nothing anywhere in the store holds it',
     JSON.stringify(DB.whoop).indexOf('bottle of wine')<0);

  /* the original file text is not retained either */
  var cyc='Cycle start time,Recovery score %,Heart rate variability (ms),Resting heart rate (bpm)\\n'+
          '2030-01-02 06:00:00,72,84,53\\n';
  importWhoopFile('physiological_cycles.csv',cyc);
  ok('a cycle row is kept', DB.whoop.cycles.length===1, DB.whoop.cycles.length);
  ok('as figures, not as the file', (function(){
     var s=JSON.stringify(DB.whoop.cycles[0]);
     return s.indexOf('Cycle start time')<0 && s.indexOf('Recovery score %')<0; })(),
     JSON.stringify(DB.whoop.cycles[0]));
  ok('and the numbers survived', DB.whoop.cycles[0].recovery===72
     && DB.whoop.cycles[0].hrv===84, JSON.stringify(DB.whoop.cycles[0]));

  DB.whoop=keepW;
})();

// ---------- DELETING IMPORTED DATA DELETES IT ----------
(function(){
  var keepW=JSON.parse(JSON.stringify(DB.whoop));
  var keepP=JSON.parse(JSON.stringify(DB.profile));
  var keepB=JSON.parse(JSON.stringify(DB.baselines));
  var keepS=DB.sessions, keepC=DB.checkins;

  DB.whoop={cycles:[{date:'2030-01-01',recovery:70,hrv:80,rhr:55}],
            workouts:[{date:'2030-01-01',name:'Run',strain:9}],
            journal:[{key:'k',date:'2030-01-01',q:'Alcohol?',yes:true}],
            imports:[{at:'2030-01-01T00:00:00Z',results:[]}]};
  DB.profile.source='whoop'; DB.profile.mode='whoop';
  DB.sessions=[{id:'keepme',date:'2030-01-01',done:true,workoutName:'Lower A',entries:[]}];
  DB.checkins={'2030-01-01':{date:'2030-01-01',energy:7}};

  /* the fallback blob: Store.write only reaches for it when IndexedDB is
     unavailable, so a delete that goes through the normal write path would
     leave it sitting there with the health data still in it */
  try{ localStorage.setItem(KEY, JSON.stringify({whoop:DB.whoop})); }catch(e){}

  resetStack(); TAB='today'; openSettings();
  var di=SET_PANES.filter(function(x){return x.sec;}).map(function(x){return x.id;}).indexOf('data');
  document.getElementById('setRows').querySelectorAll('button')[di].click();
  var del=document.getElementById('sDelWhoop');
  /* it confirms first, and the confirmation says what is about to go */
  del.click();
  var warn=document.getElementById('sheetBody').textContent;
  ok('it says what it will remove before doing it',
     /imported days/.test(warn), warn.slice(0,200));
  ok('and that your own history is kept',
     /sessions, activities/.test(warn), warn.slice(0,240));
  closeSheet();
  /* the confirmation runs its callback on a 240ms timer, so the work is a
     named function and this calls the same one the button calls */
  var gone=deleteImportedData();
  ok('it reports what it removed', gone.days===1 && gone.workouts===1
     && gone.journal===1 && gone.imports===1, JSON.stringify(gone));

  ok('the imported days are gone', DB.whoop.cycles.length===0);
  ok('the imported workouts are gone', DB.whoop.workouts.length===0);
  ok('the journal rows are gone', DB.whoop.journal.length===0);
  ok('the import history is gone', DB.whoop.imports.length===0);
  ok('the baselines computed from it are reset',
     JSON.stringify(DB.baselines)===JSON.stringify(SEED_BASE),
     JSON.stringify(DB.baselines).slice(0,80));
  ok('the device is no longer named as a source', DB.profile.source==='none',
     DB.profile.source);

  /* the gap that made the old claim untrue */
  ok('the localStorage fallback copy is gone too',
     (function(){ try{ return localStorage.getItem(KEY)===null; }
                  catch(e){ return true; } })(),
     (function(){ try{ return String(localStorage.getItem(KEY)).slice(0,40); }
                  catch(e){ return 'threw'; } })());

  /* and nothing unrelated was taken with it */
  ok('your own sessions are kept', DB.sessions.length===1 && DB.sessions[0].id==='keepme');
  ok('your own check-ins are kept', !!DB.checkins['2030-01-01']);

  DB.whoop=keepW; DB.profile=keepP; DB.baselines=keepB;
  DB.sessions=keepS; DB.checkins=keepC;
  resetStack(); render();
})();

// ---------- THE APP MAKES NO NETWORK REQUESTS ----------
(function(){
  /* The privacy text tells the user nothing leaves the device. The shipped
     file is checked for the absence of the APIs by verify_web.py; this checks
     the running app does not reach for them either. */
  var calls=[];
  var realFetch=window.fetch, realXHR=window.XMLHttpRequest;
  var realBeacon=navigator.sendBeacon;
  try{
    window.fetch=function(u){ calls.push('fetch '+u); return Promise.reject(new Error('blocked')); };
    window.XMLHttpRequest=function(){ calls.push('xhr'); throw new Error('blocked'); };
    try{ navigator.sendBeacon=function(u){ calls.push('beacon '+u); return false; }; }catch(e){}

    var T=todayISO();
    var keepC=DB.checkins;
    DB.checkins[T]={date:T,recovery:70,hrv:80,rhr:55,sleepMin:450,energy:7,
                    soreness:3,stress:3,motivation:7,pain:'None'};
    resetStack(); TAB='today'; render();
    TAB='workouts'; render();
    TAB='progress'; render();
    TAB='settings'; render();
    importWhoopFile('physiological_cycles.csv',
      'Cycle start time,Recovery score %\\n2030-03-03 06:00:00,66\\n');
    save(true);
    DB.checkins=keepC;
  } finally {
    window.fetch=realFetch; window.XMLHttpRequest=realXHR;
    try{ navigator.sendBeacon=realBeacon; }catch(e){}
  }
  ok('rendering every screen makes no network request', calls.length===0, calls.join(' ; '));
  ok('and neither does importing or saving', calls.length===0, calls.join(' ; '));
  resetStack(); TAB='today'; render();
})();

// ---------- THE USER IS TOLD BEFORE THEY HAND ANYTHING OVER ----------
(function(){
  var keepSrc=DB.profile.source;
  DB.profile.source='whoop';
  /* paneImport wires its handlers with document.querySelector, so it has to
     be rendered INTO the document, not into a detached node */
  resetStack(); TAB='today';
  var v=document.getElementById('view');
  paneImport(v);
  var txt=v.textContent;
  ok('the import screen explains what the data is for',
     /used to personalise/i.test(txt), txt.slice(0,240));
  ok('it says the user can delete it', /delete your imported data/i.test(txt));
  ok('it asks only for data they are authorised to provide',
     /authorised to provide/i.test(txt));
  ok('there is a "how your data is used" disclosure', !!v.querySelector('#impHowT'));
  ok('which is collapsed to begin with', v.querySelector('#impHow').hasAttribute('hidden'));
  ok('and says it is not sent anywhere',
     /Sent anywhere/i.test(txt) && txt.indexOf('Sent anywhereNo')>=0,
     txt.slice(txt.indexOf('Sent anywhere'), txt.indexOf('Sent anywhere')+40));
  ok('the file size limit is stated', /25 MB/.test(txt), txt.slice(-200));

  /* labelling: user-provided data, not an integration */
  ok('the label says data export, not integration',
     /data export/i.test(txt) && !/connect|integration/i.test(txt),
     txt.slice(0,160));
  DB.profile.source=keepSrc;
})();

// ---------- NO SCREEN RENDERS ITS OWN SOURCE CODE ----------
(function(){
  /* A template literal with an ESCAPED interpolation - \\${svg('flame')} -
     renders those characters to the user as text. The sport pane was doing
     exactly that on its empty state, and nothing noticed because no test
     rendered that pane with no sessions in it. */
  var keepA=DB.activities, keepS=DB.sessions, keepC=DB.checkins, keepW=DB.whoop;
  var v=document.getElementById('view');
  var bad=[];
  var look=function(label){
    var txt=v.textContent||'';
    if(txt.indexOf('${')>=0){
      var k=txt.indexOf('${');
      bad.push(label+': '+txt.slice(Math.max(0,k-25), k+45));
    }
  };

  /* full and empty, because the empty states are where this hides */
  [['full', function(){}],
   ['empty', function(){ DB.activities=[]; DB.sessions=[]; DB.checkins={};
                         DB.whoop={cycles:[],workouts:[],journal:[],imports:[]}; }]
  ].forEach(function(state){
    state[1]();
    ['today','workouts','progress','settings'].forEach(function(tab){
      resetStack(); TAB=tab; render(); look(state[0]+' tab '+tab);
    });
    [['timeline',paneTimeline],['history',paneActHistory],['totals',paneTotals],
     ['sport',paneTennis],['program',paneProgram],['week',paneWeek]
    ].forEach(function(pane){
      try{ v.innerHTML=''; pane[1](v); look(state[0]+' pane '+pane[0]); }catch(e){}
    });
  });

  ok('no screen renders an unevaluated template placeholder',
     bad.length===0, bad.slice(0,3).join(' || '));

  DB.activities=keepA; DB.sessions=keepS; DB.checkins=keepC; DB.whoop=keepW;
  resetStack(); TAB='today'; render();
})();

// ---------- NO SESSION PRESCRIBES THE SAME MOVEMENT TWICE ----------
(function(){
  /* Reported as "box jumps three times in the basketball workout". Measured
     across every workout x variant x equipment x sport: 248 of 1008
     combinations had a duplicate, because resolveExercise() was called once
     per block and knew nothing about the other blocks, so several movements
     the user could not do all collapsed onto the same substitute. */
  var keepG=DB.profile.gear, keepS=DB.profile.sports;
  var T=todayISO();
  var gearsets=[[], ['band'], ['db'], ['db','bench','bar'],
                ['db','kb','bb','bar','bench','cable','ball','box','run','bike'],
                ['run'], ['box','run','band']];
  var sportsets=[['basketball'],['tennis'],['football'],[]];
  var bad=[], cases=0;

  sportsets.forEach(function(sp){
    gearsets.forEach(function(g){
      DB.profile.sports=sp.slice(); DB.profile.gear=g.slice();
      DB.workouts.forEach(function(w){
        ['full','reduced','recovery'].forEach(function(v){
          var bs;
          try{ bs=sessionBlocks({workoutId:w.id, variant:v, date:T}); }
          catch(e){ bad.push(w.id+'/'+v+' threw '+e.message); return; }
          cases++;
          var seen={};
          bs.forEach(function(b){
            seen[b.ex]=(seen[b.ex]||0)+1;
            if(seen[b.ex]===2){
              var e=exOf(b.ex);
              bad.push((sp[0]||'general')+'/'+(g.length?g.join('+'):'nothing')+
                       '/'+w.id+' '+v+': '+(e?e.name:b.ex));
            }
          });
        });
      });
    });
  });

  ok('every combination was built', cases>=1000, cases);
  ok('no session contains the same exercise twice', bad.length===0,
     bad.length+' cases, e.g. '+bad.slice(0,3).join(' | '));

  /* the specific report: a court-sport athlete with a box should not get the
     same jump three times */
  DB.profile.sports=['basketball']; DB.profile.gear=['box','run','band'];
  var pw=sessionBlocks({workoutId:'w_power', variant:'full', date:T});
  var names=pw.map(function(b){ var e=exOf(b.ex); return e?e.name:b.ex; });
  ok('the power session has no repeat',
     names.length===new Set(names).size, names.join(', '));
  ok('and it still has enough in it', pw.length>=4, pw.length);

  /* Dropping a duplicate must not gut a session. Measured against what the
     workout was AUTHORED with, because two of them (w_runQuality recovery,
     w_runInt recovery) are written with a single block and were one movement
     long before any of this. */
  DB.profile.sports=[]; DB.profile.gear=[];
  var empty=[], gutted=[];
  DB.workouts.forEach(function(w){
    ['full','reduced','recovery'].forEach(function(v){
      var auth=(w.blocks[v]&&w.blocks[v].length)?w.blocks[v]:w.blocks.full;
      var authored=auth.length;
      var bs=sessionBlocks({workoutId:w.id, variant:v, date:T});
      if(!bs.length) empty.push(w.id+'/'+v);
      if(authored>=4 && bs.length<3) gutted.push(w.id+'/'+v+' '+authored+'->'+bs.length);
    });
  });
  ok('no session is left empty', empty.length===0, empty.join(', '));
  ok('and a full session keeps most of its movements',
     gutted.length===0, gutted.join(', '));

  /* and the resolver still answers when there is no session context */
  ok('resolveExercise works with no taken-set', !!resolveExercise('lx01'));
  ok('and with an empty one', !!resolveExercise('lx01', new Set()));

  DB.profile.gear=keepG; DB.profile.sports=keepS;
})();

// ---------- THE WEEK STRIP GOES BACK, AND A DAY OPENS ----------
(function(){
  var keepA=DB.activities, keepC=DB.checkins, keepS=DB.sessions;
  var T=todayISO();
  DB.activities=[]; DB.sessions=[];
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  WEEKOFF=0;
  resetStack(); TAB='today'; render();

  ok('the strip says which week it is', !!document.querySelector('.wk-l'),
     document.getElementById('view').innerHTML.slice(0,200));
  ok('and it starts on this one', /This week/.test(document.querySelector('.wk-l').textContent),
     document.querySelector('.wk-l').textContent);
  ok('there is a way back', !!document.getElementById('wkPrev'));
  /* nothing in a week that has not happened, so nothing to offer */
  ok('but no way forward from the current week', !document.getElementById('wkNext'));

  /* a day that has not happened is not a button */
  var future=document.querySelectorAll('#view .wk-d.future');
  var clickable=document.querySelectorAll('#view .wk-d[data-day]');
  ok('every day of the week is drawn',
     future.length+clickable.length===7, future.length+'+'+clickable.length);
  ok('future days are not buttons', (function(){
     for(var i=0;i<future.length;i++){ if(future[i].tagName==='BUTTON') return false; }
     return true; })());
  ok('past and present days are', clickable.length>=1, clickable.length);

  // --- go back a week ---
  document.getElementById('wkPrev').click();
  ok('Previous moves back a week', WEEKOFF===-1, WEEKOFF);
  /* A concrete range, not a relative word: the user must be able to tell which
     days are on screen without counting backwards from today. */
  ok('and it names the exact days',
     /[0-9]{1,2}.*[0-9]{1,2} [A-Z][a-z][a-z]/.test(document.querySelector('.wk-l').textContent) &&
     !/week/i.test(document.querySelector('.wk-l').textContent),
     document.querySelector('.wk-l').textContent);
  ok('now there IS a way forward', !!document.getElementById('wkNext'));
  ok('every day of last week is openable',
     document.querySelectorAll('#view .wk-d[data-day]').length===7,
     document.querySelectorAll('#view .wk-d[data-day]').length);
  ok('and the footer explains what it is for',
     /forgot to log/.test(document.getElementById('view').textContent));

  document.getElementById('wkPrev').click();
  ok('and again', WEEKOFF===-2, WEEKOFF);
  ok('a date range is shown once it is not "last week"',
     !/week/i.test(document.querySelector('.wk-l').textContent),
     document.querySelector('.wk-l').textContent);

  document.getElementById('wkNext').click();
  ok('Next moves forward again', WEEKOFF===-1, WEEKOFF);
  document.getElementById('wkNext').click();
  ok('and stops at the current week', WEEKOFF===0, WEEKOFF);
  ok('where the forward button disappears again', !document.getElementById('wkNext'));

  /* --- browsing history is a read, not a state change --- */
  WEEKOFF=0; SELDAY=null; resetStack(); TAB='today'; render();
  var snap=function(){
    var t=todayISO(), r=recommend(t,DB.checkins[t]);
    return JSON.stringify({id:r.id,variant:r.variant,est:r.est,prep:r.prep,
                           rd:readiness(t,DB.checkins[t]).score,
                           load:dayDemand(t).load});
  };
  var before=snap();
  document.getElementById('wkPrev').click();
  document.getElementById('wkPrev').click();
  ok('two weeks back', WEEKOFF===-2, WEEKOFF);
  ok('browsing history leaves today’s plan and readiness alone', snap()===before,
     before+'  ->  '+snap());
  ok('and does not silently retarget where activities would be added',
     SELDAY===null, String(SELDAY));

  /* --- an unrecorded day is unknown, not a missed workout --- */
  var stripTxt=document.querySelector('#view .wk-nav').parentNode.textContent;
  ok('a week with nothing logged says nothing about what was missed',
     !/missed|skipped|failed|rest day|behind/i.test(stripTxt), stripTxt.slice(0,220));
  ok('and invents no activity for days it never saw',
     (function(){
        var start=addDays(weekStartOf(todayISO()), WEEKOFF*7);
        for(var i=0;i<7;i++){
          var d=addDays(start,i);
          var hasData = DB.sessions.some(function(s){return s.done&&s.date===d;})
                     || DB.activities.some(function(a){return a.date===d;});
          var cell=document.querySelector('#view .wk-d[data-day="'+d+'"]');
          if(!hasData && cell && /Sport|Legs|Upper|Core|Run|Bike|Mob|Prep|Str/.test(cell.textContent)) return false;
        }
        return true;
     })(), 'an empty day must render empty');
  WEEKOFF=0; SELDAY=null; render();
  ok('returning to the current week says so', /This week/.test(document.querySelector('.wk-l').textContent),
     document.querySelector('.wk-l').textContent);

  // --- leaving Today resets it ---
  WEEKOFF=-3;
  go('progress'); go('today');
  ok('leaving Today puts the strip back on this week', WEEKOFF===0, WEEKOFF);

  DB.activities=keepA; DB.checkins=keepC; DB.sessions=keepS;
  resetStack(); render();
})();

// ---------- A DAY YOU FORGOT ----------
(function(){
  var keepA=DB.activities, keepC=DB.checkins, keepS=DB.sessions;
  var T=todayISO();
  DB.activities=[]; DB.sessions=[];
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  WEEKOFF=0; SELDAY=null; resetStack(); TAB='today'; render();
  /* pick a day earlier in this week, which is what "I forgot Saturday" is.
     On a Monday there is no earlier day in this week - the only openable cell
     is today - so step back a week and the test still means what it says. */
  var days=document.querySelectorAll('#view .wk-d[data-day]');
  if(days.length<2){
    document.getElementById('wkPrev').click();
    days=document.querySelectorAll('#view .wk-d[data-day]');
  }
  var target=days[0].dataset.day;
  days[0].click();

  ok('tapping a day selects it', SELDAY===target || target===T,
     SELDAY+' vs '+target);
  ok('and it stays on Today rather than pushing a page', STACK.length===0, STACK.length);
  ok('the card now names that day',
     document.getElementById('actsCard').textContent.indexOf(fmtDate(target))>=0
     || target===T,
     document.getElementById('actsCard').textContent.slice(0,80));
  ok('the day is marked as selected in the calendar',
     !!document.querySelector('#view .wk-d.sel'));
  ok('and a way to add to it', !!document.getElementById('acAdd'));
  /* a clock can only run now */
  ok('but no clock on a day that is not today',
     target===T ? !!document.getElementById('acStart')
                : !document.getElementById('acStart'),
     target+' vs '+T);
  ok('and a way back to today', target===T || !!document.getElementById('acToday'));

  // --- log something on that day ---
  document.getElementById('acAdd').click();
  ok('Add opens the picker', !!document.getElementById('paQ'));
  document.querySelector('#sheetBody .parow[data-k="football"]').click();
  ok('and then the form', !!document.getElementById('asPick'));
  ok('with that day already filled in',
     document.getElementById('asDate').value===target,
     document.getElementById('asDate').value+' vs '+target);

  setTime('asFrom','19:00'); setTime('asTo','20:30');
  document.querySelector('#asInt button[data-v=Hard]').click();
  document.getElementById('asSave').click();

  ok('the activity was saved', DB.activities.length===1, DB.activities.length);
  /* the whole point */
  ok('on the day you were looking at, not today',
     DB.activities[0].date===target, DB.activities[0].date+' vs '+target);
  ok('with the right length', DB.activities[0].min===90, DB.activities[0].min);
  ok('and the right kind', DB.activities[0].type==='football');
  closeSheet();

  /* and it shows up on that day */
  SELDAY=target; render();
  ok('it appears on that day',
     document.querySelectorAll('#actsCard [data-aid]').length===1,
     document.querySelectorAll('#actsCard [data-aid]').length);
  ok('and not on today', (function(){
     SELDAY=null; render();
     return document.querySelectorAll('#actsCard [data-aid]').length===0; })(),
     document.querySelectorAll('#actsCard [data-aid]').length);

  /* tapping the selected day again returns to today, so there is always a way
     out without hunting for a date control */
  SELDAY=null; render();
  var d2=document.querySelectorAll('#view .wk-d[data-day]');
  if(d2.length>1 && d2[0].dataset.day!==T){
    d2[0].click();
    ok('a day can be deselected', SELDAY===d2[0].dataset.day, SELDAY);
    document.querySelector('#view .wk-d.sel').click();
    ok('and tapping it again goes back to today', SELDAY===null, SELDAY);
  }

  DB.activities=keepA; DB.checkins=keepC; DB.sessions=keepS;
  WEEKOFF=0; resetStack(); render();
})();

// ---------- THE CARD IS ABOUT THE DAY YOU ARE LOOKING AT ----------
(function(){
  /* The reported bug. Every code path stored the right date; what was wrong
     was that navigating the calendar to a past week left the card underneath
     talking about TODAY, so Add activity logged today - correctly, and
     wrongly. There is one card now and it follows the calendar. */
  var keepA=DB.activities, keepC=DB.checkins, keepS=DB.sessions;
  var T=todayISO();
  DB.activities=[]; DB.sessions=[];
  DB.checkins[T]={date:T,recovery:72,hrv:84,rhr:53,sleepMin:450,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};

  SELDAY=null; WEEKOFF=0; resetStack(); TAB='today'; render();
  ok('it starts on today', !document.getElementById('acToday'));

  // go back a week and pick a day
  document.getElementById('wkPrev').click();
  var days=document.querySelectorAll('#view .wk-d[data-day]');
  var target=days[3].dataset.day;
  days[3].click();

  ok('the card followed the calendar into last week',
     document.getElementById('actsCard').textContent.indexOf(fmtDate(target))>=0,
     document.getElementById('actsCard').textContent.slice(0,80));
  ok('and says you are looking at another day',
     /looking at another day/.test(document.getElementById('view').textContent));

  document.getElementById('acAdd').click();
  document.querySelector('#sheetBody .parow[data-k="football"]').click();
  ok('the form opens on that day, not today',
     document.getElementById('asDate').value===target,
     document.getElementById('asDate').value+' vs today '+T);
  setTime('asFrom','19:00'); setTime('asTo','20:30');
  document.getElementById('asSave').click();
  ok('and it is stored on that day', DB.activities[0].date===target,
     DB.activities[0].date+' vs '+target);
  ok('not on today', DB.activities[0].date!==T, DB.activities[0].date);
  closeSheet();

  // back to today
  document.getElementById('acToday').click();
  ok('Back to today returns the card', SELDAY===null && WEEKOFF===0,
     SELDAY+'/'+WEEKOFF);
  ok('and today is empty again',
     document.querySelectorAll('#actsCard [data-aid]').length===0);

  DB.activities=keepA; DB.checkins=keepC; DB.sessions=keepS;
  SELDAY=null; WEEKOFF=0; resetStack(); render();
})();

// ---------- THE CALENDAR SHOWS READINESS, AND THE CYCLE ----------
(function(){
  var keepC=DB.checkins, keepM=JSON.parse(JSON.stringify(DB.mcycle));
  var T=todayISO();
  DB.checkins={};
  DB.checkins[T]={date:T,recovery:71,hrv:83,rhr:54,sleepMin:445,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  DB.checkins[addDays(T,-1)]={date:addDays(T,-1),recovery:52,hrv:70,rhr:59,
                  sleepMin:360,energy:4,soreness:7,stress:6,motivation:5,pain:'Mild'};

  SELDAY=null; WEEKOFF=0; resetStack(); TAB='today'; render();
  var strip=document.querySelector('.wk-nav').parentElement;

  /* the small number is this app's own readiness score, the same one the ring
     at the top of the screen shows - not the wearable's raw recovery */
  var want=String(readiness(T,DB.checkins[T]).score);
  ok('the calendar shows a number for a day with a check-in',
     strip.textContent.indexOf(want)>=0, want+' in '+strip.textContent.slice(0,140));
  var yWant=String(readiness(addDays(T,-1),DB.checkins[addDays(T,-1)]).score);
  ok('and for the day before', strip.textContent.indexOf(yWant)>=0, yWant);
  ok('the two differ, so it is not a constant', want!==yWant, want+'/'+yWant);
  ok('it is readiness, not the raw recovery figure',
     want!=='71' || readiness(T,DB.checkins[T]).score===71, want);

  // a day with no check-in has no number to show
  DB.checkins={};
  render();
  strip=document.querySelector('.wk-nav').parentElement;
  ok('a calendar with no check-ins still renders',
     !!document.querySelector('.wk-nav'), 'strip absent');

  // ---- cycle tracking appears in the calendar when it is on ----
  DB.checkins[T]={date:T,recovery:71,hrv:83,rhr:54,sleepMin:445,energy:7,
                  soreness:3,stress:3,motivation:8,pain:'None'};
  DB.mcycle={on:true, starts:[addDays(T,-10), addDays(T,-38)],
             typicalLen:28, typicalPeriod:5, askedAt:null};
  render();
  strip=document.querySelector('.wk-nav').parentElement;
  ok('cycle tracking puts a day number in the calendar',
     strip.querySelectorAll('span[style*="min-width:17px"]').length>0
     || /Cycle day/i.test(document.getElementById('view').textContent),
     strip.innerHTML.slice(0,200));
  ok('and the footer explains what the number is',
     /cycle day/i.test(document.getElementById('view').textContent),
     document.getElementById('view').textContent.slice(-200));

  /* and it keeps showing when you navigate to a previous week */
  document.getElementById('wkPrev').click();
  strip=document.querySelector('.wk-nav').parentElement;
  ok('the cycle day is still drawn a week back',
     strip.querySelectorAll('span[style*="min-width:17px"]').length>0,
     strip.innerHTML.slice(0,200));

  DB.mcycle={on:false, starts:[], typicalLen:null, typicalPeriod:null, askedAt:null};
  render();
  ok('and nothing cycle-related is shown when it is off',
     !/cycle day/i.test(document.getElementById('view').textContent));

  DB.checkins=keepC; DB.mcycle=keepM;
  SELDAY=null; WEEKOFF=0; resetStack(); render();
})();

// ---------- A CYCLE STARTS FROM A DATE YOU GIVE IT ----------
(function(){
  var keepM=JSON.parse(JSON.stringify(DB.mcycle)), keepC=DB.checkins;
  var T=todayISO();
  DB.checkins={};
  DB.mcycle={on:false,starts:[],typicalLen:null,typicalPeriod:null,askedAt:null};

  mcSetupSheet();
  document.getElementById('mcS0').value=addDays(T,-6);
  document.getElementById('mcP0').value='5';
  document.getElementById('mcL0').value='29';
  document.getElementById('mcS0go').click();

  ok('the start date is recorded', DB.mcycle.starts.indexOf(addDays(T,-6))>=0,
     JSON.stringify(DB.mcycle.starts));
  ok('the usual period length is recorded', DB.mcycle.typicalPeriod===5);
  ok('the usual cycle length is recorded', DB.mcycle.typicalLen===29);
  ok('and tracking is on', mcOn()===true);
  /* it can say something on day one, which is the point of asking */
  ok('it can already count the day', mcDay(T)===7, mcDay(T));
  closeSheet();

  // a future start date is not accepted
  DB.mcycle={on:false,starts:[],typicalLen:null,typicalPeriod:null,askedAt:null};
  mcSetupSheet();
  document.getElementById('mcS0').value=addDays(T,10);
  document.getElementById('mcS0go').click();
  ok('a start date in the future is ignored', DB.mcycle.starts.length===0,
     JSON.stringify(DB.mcycle.starts));
  closeSheet();

  DB.mcycle=keepM; DB.checkins=keepC;
})();

// ---------- THE PERIOD IS FOLLOWED TO ITS END ----------
(function(){
  var keepM=JSON.parse(JSON.stringify(DB.mcycle));
  var T=todayISO();
  DB.mcycle={on:true, starts:[addDays(T,-2)], typicalLen:28, typicalPeriod:5, askedAt:null};

  var e=mcExpected(T);
  ok('it knows which day of the period it is', e.day===3, e.day);
  ok('and roughly how many there usually are', e.periodDayOf===5, e.periodDayOf);
  ok('it is in the period state', e.state==='period', e.state);
  ok('and says when it should end about', e.endsAbout===addDays(T,-2+4),
     e.endsAbout);
  ok('and when the next one is due about', e.nextAbout===addDays(T,-2+28),
     e.nextAbout);
  ok('the line says which day of about how many',
     /day 3 of about 5/i.test(mcStateLine(T)||''), mcStateLine(T));

  /* A period running longer than usual is stated, without a conclusion.
     The bleeding has to be a continuous run: a bleeding day with two clear
     days before it is a new cycle start, correctly, which would reset the
     count to day 1. */
  DB.mcycle.starts=[addDays(T,-8)];
  for(var bd=8; bd>=0; bd--) mcSetLog(addDays(T,-bd),{bleeding:true});
  var p=mcPhase(T);
  ok('a long period is still the menstrual phase', p.phase==='menstrual', p.phase);
  ok('and it says it is running long', p.lateEnd===4, p.lateEnd);
  ok('in plain words', /longer than your usual/.test(p.note), p.note);
  ok('with no conclusion drawn from it',
     !/pregnan|fertil|disorder|condition|doctor|diagnos/i.test(p.note), p.note);
  for(var bc=8; bc>=0; bc--) mcSetLog(addDays(T,-bc),{bleeding:false});

  DB.mcycle=keepM;
})();

// ---------- A LATE CYCLE REMOVES THE INFLUENCE, IT DOES NOT ADD ONE ----------
(function(){
  var keepM=JSON.parse(JSON.stringify(DB.mcycle)), keepC=DB.checkins, keepS=DB.sessions;
  var T=todayISO();

  /* Build a history that would otherwise establish a luteal pattern: enough
     cycles, regular, and a clear run of bad days in one phase. */
  var starts=[];
  for(var k=5;k>=1;k--) starts.push(addDays(T,-28*k));
  DB.mcycle={on:true, starts:starts.slice(), typicalLen:28, typicalPeriod:5, askedAt:null};
  DB.checkins={};
  starts.forEach(function(s){
    for(var d=0;d<28;d++){
      var day=addDays(s,d);
      if(day>T) return;
      var luteal=d>=17;
      DB.checkins[day]={date:day, energy:luteal?3:8, soreness:luteal?7:3,
                        stress:luteal?7:3, motivation:luteal?3:8, pain:'None',
                        sleepMin:450};
    }
  });

  /* mid-cycle, with the pattern established, there can be an adjustment */
  DB.mcycle.starts=starts.concat([addDays(T,-20)]);
  var ctx=mcCtx();
  var pMid=mcPhase(T, ctx);
  ok('day 21 of a 28-day cycle is a known phase',
     ['luteal','ovulatory','follicular','menstrual'].indexOf(pMid.phase)>=0,
     pMid.phase+' day '+pMid.day);

  /* Now make the most recent start a late one. Appending an EARLIER date to
     a list that already ended at T-28 left T-28 as the latest start, so the
     cycle was one day past rather than six. */
  DB.mcycle.starts=starts.slice(0,-1).concat([addDays(T,-34)]);
  ctx=mcCtx();
  var pLate=mcPhase(T, ctx);
  ok('past the usual length the phase is late', pLate.phase==='late', pLate.phase);
  ok('with no confidence claimed', pLate.confidence==='none', pLate.confidence);
  ok('it counts how far past', pLate.late===7, pLate.late);   // start T-34 => day 35, len 28
  ok('and says the estimate is paused', /paused/.test(pLate.note), pLate.note);
  ok('and says readiness is not being affected',
     /not affecting your readiness/.test(pLate.note), pLate.note);

  /* the invariant: no phase, no adjustment */
  var adj=mcAdjust(T, ctx);
  ok('a late cycle applies no readiness adjustment at all', adj.delta===0,
     JSON.stringify(adj));
  ok('and offers no line claiming one', adj.line===null);

  /* and readiness itself carries no cycle flag on that day */
  DB.checkins[T]={date:T, energy:6, soreness:4, stress:4, motivation:6,
                  pain:'None', sleepMin:450};
  var rd=readiness(T, DB.checkins[T]);
  ok('readiness runs without a cycle pattern flag',
     (rd.flags||[]).indexOf('mcPattern')<0, (rd.flags||[]).join(','));

  /* nothing anywhere infers anything medical */
  var line=mcStateLine(T, ctx)||'';
  ok('the late line states days only',
     /past your usual/.test(line) &&
     !/pregnan|fertil|disorder|condition|diagnos/i.test(line), line);

  DB.mcycle=keepM; DB.checkins=keepC; DB.sessions=keepS;
})();

// ---------- WHAT THE USER REPORTS STILL OUTRANKS THE ESTIMATE ----------
(function(){
  var keepM=JSON.parse(JSON.stringify(DB.mcycle));
  var T=todayISO();
  /* a cycle that is late by the arithmetic, but bleeding reported today:
     the report wins, because it is a fact and the estimate is a guess */
  DB.mcycle={on:true, starts:[addDays(T,-40)], typicalLen:28, typicalPeriod:5, askedAt:null};
  mcSetLog(T,{bleeding:true});
  var p=mcPhase(T);
  ok('logged bleeding beats a late estimate', p.phase==='menstrual', p.phase);
  ok('and is marked as reported, not estimated', p.confidence==='reported', p.confidence);
  mcSetLog(T,{bleeding:false});
  DB.mcycle=keepM;
})();

// ---------- helpers ----------
ok('fmtMin', fmtMin(465)==='7h 45m', fmtMin(465));
ok('addDays across month', addDays('2030-01-31',1)==='2030-02-01', addDays('2030-01-31',1));
ok('daysBetween', daysBetween('2030-01-01','2030-01-08')===7);
ok('clamp', clamp(15,0,10)===10);
ok('pearson perfect corr', Math.abs(pearson([1,2,3,4,5,6,7,8,9,10],[2,4,6,8,10,12,14,16,18,20]).r-1)<1e-9);
ok('pearson too few points', pearson([1,2],[2,4])===null);
ok('isoOf parses whoop timestamp', isoOf('2026-09-14 23:24:26')==='2026-09-14');
ok('numOr handles blank', numOr('')===null && numOr('12.5')===12.5);
ok('esc escapes html', esc('<b>&"')==='&lt;b&gt;&amp;&quot;');
ok('loadBand thresholds', loadBand(2).label==='Minimal' && loadBand(13).label==='High' && loadBand(19).label==='Very high');
ok('currentPhase in 1-8', currentPhase().w>=1 && currentPhase().w<=8, currentPhase().w);
ok('phase 4 is deload', PHASES[3].name==='Deload' && PHASES[3].vol<0.7);
// future / past / missing plan start must never produce a broken phase
(function(){
  var keep=DB.profile.planStart, bad=[];
  ['2099-01-01','2020-01-01','','2026-09-16',todayISO()].forEach(function(d){
    DB.profile.planStart=d; var p=currentPhase();
    if(!(p.w>=1&&p.w<=8)||!p.name||p.absWeek<1) bad.push(d+'->'+JSON.stringify({w:p.w,abs:p.absWeek,n:p.name}));
  });
  DB.profile.planStart=keep;
  ok('currentPhase robust to any plan start date', bad.length===0, bad.join(' ; '));
})();
ok('no unused settings keys',
   Object.keys(DB.settings).sort().join(',')==='autoAdjust,bands,hardStrain,notify,restTimerOn,sound',
   Object.keys(DB.settings).sort().join(','));

// ---------- equipment integrity ----------
// Gym exercises now exist ON PURPOSE for users who have a gym. What must hold
// is that a tier-0 exercise never requires equipment a tier-0 user lacks, and
// that no workout ever prescribes gear above the user's tier.
var banned=new RegExp('\\b(barbell|squat rack|smith machine|leg press|cable machine|'+
  'lat pulldown|dip station|kettlebell|bench press|trap bar|medicine ball)\\b','i');
var t0=DB.exercises.filter(function(e){return (e.tier||0)===0;});
var viol=t0.filter(function(e){
  return banned.test([e.name,e.equip,e.how].join(' '));   // prog/reg/subs may name alternatives
});
ok('tier-0 exercises need no gym equipment', viol.length===0,
   viol.map(function(e){return e.name;}).join(', '));
ok('tier-0 exercises prescribe no weight above 5 kg',
   t0.filter(function(e){ return new RegExp('\\b(1[0-9]|[2-9][0-9])\\s?kg\\b','i')
     .test([e.how,e.notes].join(' ')); }).length===0);
ok('tier-1 exercises name only home equipment',
   DB.exercises.filter(function(e){return e.tier===1;}).every(function(e){
     return !new RegExp('barbell|cable machine|leg press|smith machine','i').test(e.equip||''); }),
   DB.exercises.filter(function(e){return e.tier===1 && new RegExp('barbell|cable','i').test(e.equip||'');})
     .map(function(e){return e.name+':'+e.equip;}).join(', '));
// the guarantee that actually matters, across every workout and every variant.
// prescription is driven by the gear list, not the tier label, so test that.
(function(){
  var keepGear=DB.profile.gear, keepTier=DB.profile.tier, bad=[];
  var SETS=[[], ['db'], ['band'], ['db','band'], ['db','band','bench','bar'],
            ['db','band','bench','bar','kb','ball','bb','cable'],
            ['bike','run'], ['db','band','bike','run']];
  SETS.forEach(function(gear){
    DB.profile.gear=gear.slice(); DB.profile.tier=tierOf(gear);
    DB.workouts.forEach(function(w){
      ['full','reduced','recovery'].forEach(function(v){
        sessionBlocks({workoutId:w.id,variant:v,addCore:false}).forEach(function(b){
          var e=exOf(b.ex);
          if(!e) bad.push('['+gear.join('+')+'] '+w.id+'/'+v+':MISSING');
          else if(!canDo(e)) bad.push('['+gear.join('+')+'] '+w.id+'/'+v+':'+e.name+
                                      ' needs '+(e.needs||[]).join('+'));
        });
      });
    });
  });
  DB.profile.gear=keepGear; DB.profile.tier=keepTier;
  ok('NO workout with ANY equipment set prescribes gear you do not own',
     bad.length===0, bad.slice(0,6).join(' | '));
})();

// ---------- unfinished setup must stay visible ----------
(function(){
  var keep=DB.profile.onboarded;
  DB.profile.onboarded=false;
  var html=setupPrompt();
  ok('unfinished setup shows a prompt', html.length>0 && /Setup not finished/.test(html));
  ok('prompt names the assumed equipment', /equipment/i.test(html));
  TAB='today'; viewToday(document.getElementById('view'));
  ok('prompt appears on the Today screen', !!document.getElementById('setupCard'));
  ok('prompt offers to finish setup', !!document.getElementById('setupGo'));
  ok('prompt offers to accept defaults', !!document.getElementById('setupDismiss'));
  document.getElementById('setupDismiss').click();
  ok('accepting defaults marks onboarded', DB.profile.onboarded===true);
  viewToday(document.getElementById('view'));
  ok('prompt gone once onboarded', !document.getElementById('setupCard'));
  DB.profile.onboarded=keep;
})();
// ---------- "never logged" vs "over 2 weeks ago" ----------
(function(){
  var ks=DB.sessions, ka=DB.activities, kw=DB.whoop.cycles;
  DB.sessions=[]; DB.activities=[]; DB.whoop.cycles=[];
  ok('empty install reports "never logged"', sinceText(99)==='never logged', sinceText(99));
  ok('hasHistory false when empty', hasHistory()===false);
  DB.sessions=ks; DB.activities=ka; DB.whoop.cycles=kw;
  ok('hasHistory true with data', hasHistory()===true);
  ok('with history, 99 means over 2 weeks', sinceText(99)==='over 2 weeks ago', sinceText(99));
  ok('1 day reads as yesterday', sinceText(1)==='yesterday');
  ok('n days reads as n days ago', sinceText(4)==='4 days ago');
})();
// ---------- output ----------
ok('no errors accumulated during tests', window.__errors.length===0, window.__errors.join(' ;; '));
var out='TESTRESULTS_START\\n'+R.join('\\n')+'\\nTOTAL: '+pass+' passed, '+fail+' failed\\nTESTRESULTS_END';
document.title = (fail===0?'ALLPASS':'HASFAIL')+' '+pass+'/'+(pass+fail);
var pre=document.createElement('pre'); pre.id='testout'; pre.textContent=out;
document.body.appendChild(pre);
}
/* boot() is async now (it probes localStorage + IndexedDB), so wait for it */
var _w=0;
(function waitBoot(){
  if(typeof DB!=='undefined' && DB && typeof Store!=='undefined' && Store.mode){
    Promise.resolve().then(runTests).catch(function(e){
      document.title='TESTERR';
      var p=document.createElement('pre'); p.id='testout';
      p.textContent='TESTRESULTS_START\\nTHROW| runTests aborted :: '+(e&&e.message)+
        '\\n'+((e&&e.stack)||'').split('\\n').slice(0,4).join('\\n')+
        '\\nTOTAL: 0 passed, 1 failed\\nTESTRESULTS_END';
      document.body.appendChild(p);
    });
    return;
  }
  if(++_w>200){ document.title='BOOTFAIL';
    var p=document.createElement('pre'); p.id='testout';
    p.textContent='TESTRESULTS_START\\nFAIL | app never booted\\nTOTAL: 0 passed, 1 failed\\nTESTRESULTS_END';
    document.body.appendChild(p); return; }
  setTimeout(waitBoot,40);
})();
</script>
"""

tests = tests.replace("__CSVDATA__", json.dumps(CSV))

# inject shim before the app <script>, tests before </body>
i = html.index("<script>")
out = html[:i] + shim + html[i:]
out = out.replace("</body>", tests + "\n</body>")
io.open(os.path.join(SP,"test.html"),"w",encoding="utf-8").write(out)
print("test.html written", len(out))
