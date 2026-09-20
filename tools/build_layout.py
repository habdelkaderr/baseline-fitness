import io, os, json
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)

SP=_os.path.join(PROJECT,"build","httest")
D=_os.path.join(PROJECT,"private","whoop-data")
html=io.open(_os.path.join(PROJECT,"build","baseline.html"),encoding="utf-8").read()
def _csv(f):
    """Optional, for the same reason as in build_test.py: the audit must not
    need anybody's private export to measure a layout."""
    p=os.path.join(D,f)
    return io.open(p,encoding="utf-8").read() if os.path.isfile(p) else ""
CSV={f: _csv(f) for f in ["physiological_cycles.csv","workouts.csv"]}

shim = """<script>
(function(){ var mem={};
 try{Object.defineProperty(window,'localStorage',{value:{getItem:function(k){return k in mem?mem[k]:null;},
  setItem:function(k,v){mem[k]=String(v);},removeItem:function(k){delete mem[k];},clear:function(){mem={};},
  key:function(i){return Object.keys(mem)[i]||null;},get length(){return Object.keys(mem).length;}},configurable:true});}catch(e){}
 window.__errors=[]; window.onerror=function(m,s,l,c){window.__errors.push(m+' @'+l);};
})();</script>
"""

audit = """<script>
var CSVDATA=__CSVDATA__;
function runAudit(){ try{ return runAuditInner(); }
  catch(e){
    /* "never booted" is what the harness reported when this threw, which is
       true and useless. Say what actually happened. */
    var pre=document.createElement('pre'); pre.id='out';
    pre.textContent='LAYOUT_START\\nAUDIT THREW: '+(e&&e.message)+
      '\\n'+((e&&e.stack)||'')+'\\nLAYOUT_END';
    document.body.appendChild(pre);
    window.__REPORT=['AUDIT THREW: '+(e&&e.message)]; window.__BAD=1;
    document.title='AUDITTHREW';
  }
}
function runAuditInner(){
var REPORT=[];
// load real data so views are populated
importWhoopFile('physiological_cycles.csv', CSVDATA['physiological_cycles.csv']);
importWhoopFile('workouts.csv', CSVDATA['workouts.csv']);
recomputeBaselines();
var T=todayISO();
// seed realistic state so nothing renders as an empty state
DB.checkins[T]={date:T,recovery:74,hrv:86,rhr:52,sleepMin:455,sleepNeed:503,sleepPerf:78,prevStrain:11.2,
  energy:7,soreness:4,stress:4,motivation:8,pain:'None',sportToday:false,availTime:60,notes:'Felt good on court yesterday.'};
DB.checkins[addDays(T,-1)]={date:addDays(T,-1),recovery:58,hrv:76,rhr:56,sleepMin:395,energy:5,soreness:6,stress:5,motivation:6,pain:'Mild'};
DB.activities=[
 {id:'la1',date:addDays(T,-1),type:'tennis',min:105,rpe:8,planned:true,time:'18:00',format:'Singles',subtype:'Match',intensity:'Hard',notes:'Three sets.'},
 {id:'la2',date:addDays(T,-2),type:'running',min:38,dist:6.4,pace:'5:56',rpe:5,planned:true,time:'07:30',intensity:'Moderate'},
 {id:'la3',date:addDays(T,-3),type:'football',min:75,rpe:9,planned:false,time:'20:00',intensity:'Hard',notes:'Unplanned 5-a-side.'},
 {id:'la4',date:addDays(T,-4),type:'cycling',min:45,dist:18,rpe:3,planned:true,time:'09:00',intensity:'Easy'},
 {id:'la5',date:T,type:'walking',min:25,rpe:2,planned:false,time:'08:15'}
];
DB.tests=[{id:'x1',testId:'t_cmj',date:addDays(T,-60),value:42},{id:'x2',testId:'t_cmj',date:addDays(T,-30),value:45},
          {id:'x3',testId:'t_cmj',date:T,value:47.5},{id:'x4',testId:'t_pushup',date:addDays(T,-30),value:22},
          {id:'x5',testId:'t_pushup',date:T,value:28},{id:'x6',testId:'t_505',date:addDays(T,-30),value:5.4},
          {id:'x7',testId:'t_505',date:T,value:5.1}];
DB.physique=[{id:'p1',date:addDays(T,-60),weight:78.5,waist:84,chest:99,arm:34,shoulders:118,thigh:56},
             {id:'p2',date:addDays(T,-30),weight:78.0,waist:82.5,chest:100,arm:34.8,shoulders:119.5,thigh:56.5},
             {id:'p3',date:T,weight:77.6,waist:81,chest:101,arm:35.4,shoulders:121,thigh:57}];
// a couple of completed sessions
['w_lowerA','w_upperA','w_power'].forEach(function(wid,n){
  var w=DB.workouts.find(function(x){return x.id===wid;});
  DB.sessions.push({id:'ls'+n,date:addDays(T,-(n*3+2)),workoutId:wid,workoutName:w.name,variant:'full',done:true,
    durationMin:48,setsDone:18,volume:1240,sessionRpe:8,band:'green',readinessScore:78,time:'08:00',
    entries:w.blocks.full.slice(0,4).map(function(b){var e=exOf(b.ex);
      return {exerciseId:b.ex,name:e.name,plannedSets:b.sets||3,plannedReps:b.reps||e.reps,plannedRpe:b.rpe||e.rpe,
        plannedRest:b.rest||e.rest,note:'',sets:[{reps:'10',weight:'5',rpe:'8',done:true},{reps:'10',weight:'5',rpe:'8',done:true},{reps:'9',weight:'5',rpe:'9',done:true}]};})});
});
save(true);

var WIDTH=window.innerWidth, HEIGHT=window.innerHeight;

/* ---- contrast, as a reusable check ----
   Flattens translucent colours onto whatever is actually behind them and
   applies the WCAG AA threshold, with the large-text allowance. */
function contrastIssues(root){
  var issues=[];
    function parse(c){
    var m=/rgba?\\(([^)]+)\\)/.exec(c); if(!m) return null;
    var p=m[1].split(',').map(function(x){return parseFloat(x);});
    return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1};
  }
  function lum(c){
    var f=function(v){ v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4); };
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b);
  }
  function over(fg,bg){   // flatten a translucent colour onto its backdrop
    if(fg.a>=1) return fg;
    return {r:fg.r*fg.a+bg.r*(1-fg.a), g:fg.g*fg.a+bg.g*(1-fg.a), b:fg.b*fg.a+bg.b*(1-fg.a), a:1};
  }
  function ratio(a,b){
    var l1=lum(a), l2=lum(b);
    return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
  }
  function bgOf(el){
    var n=el, base={r:255,g:255,b:255,a:1};
    while(n && n!==document.documentElement){
      var c=parse(getComputedStyle(n).backgroundColor);
      if(c && c.a>0){ if(c.a>=1) return c; base=over(c,base); }
      n=n.parentElement;
    }
    var root=parse(getComputedStyle(document.body).backgroundColor);
    return root&&root.a>=1?root:base;
  }
  function offstage(el){
    /* a closed sheet and an inactive workout screen stay in the DOM; their
       contents are not on screen and must not be audited */
    var n=el;
    while(n && n!==document.body){
      if(n.id==='sheet' && !n.classList.contains('on')) return true;
      if(n.id==='wmode' && !n.classList.contains('on')) return true;
      if(n.classList && n.classList.contains('hide')) return true;
      n=n.parentElement;
    }
    return false;
  }
  function hex(c){
    var h=function(v){ return ('0'+Math.round(v).toString(16)).slice(-2); };
    return '#'+h(c.r)+h(c.g)+h(c.b);
  }
  var low=[];
  var seen=0;
  Array.prototype.slice.call(root.querySelectorAll(
    'p,span,div,h1,h2,h3,h4,button,label,li,td,a')).forEach(function(el){
    if(low.length>=8) return;
    if(offstage(el)) return;
    // only elements that directly own visible text
    var txt='';
    for(var i=0;i<el.childNodes.length;i++)
      if(el.childNodes[i].nodeType===3) txt+=el.childNodes[i].textContent;
    txt=txt.trim();
    if(txt.length<2) return;
    var r=el.getBoundingClientRect(); if(r.width<2||r.height<2) return;
    var cs=getComputedStyle(el);
    if(cs.visibility==='hidden'||cs.opacity==='0') return;
    var fg=parse(cs.color); if(!fg) return;
    var bg=bgOf(el);
    var eff=over(fg,bg);
    var cr=ratio(eff,bg);
    var fs=parseFloat(cs.fontSize), fw=parseInt(cs.fontWeight,10)||400;
    var large = fs>=24 || (fs>=18.66 && fw>=700);
    var need = large?3:4.5;
    seen++;
    if(cr < need-0.05)
      low.push(txt.slice(0,18)+' ['+cr.toFixed(2)+':1 need '+need+', '+
               hex(eff)+' on '+hex(bg)+', '+Math.round(fs)+'px/'+fw+']');
  });
  
  if(low.length) issues.push('LOW CONTRAST ('+low.length+' of '+seen+' checked): '+low.slice(0,5).join(' | '));
  if(!seen) issues.push('CONTRAST CHECK EXAMINED NOTHING - the check is not working');
  return issues;
}

/* ---- overlapping and touching siblings ----
   The audit measured overflow, touch targets and contrast, and never checked
   whether two things sat on top of each other. Reported overlaps in Progress
   and in the cycle sheet went straight past it.

   Only in-flow siblings are compared: absolutely positioned, fixed, sticky and
   transformed elements are allowed to overlap by design, as are collapsed
   accordion bodies. A true intersection is an ISSUE; a zero gap between two
   cards is reported separately, because that is what a missing margin looks
   like before it becomes an overlap. */
function flowIssues(root){
  var issues=[], touching=[];
  function inFlow(el){
    var cs=getComputedStyle(el);
    if(cs.position!=='static' && cs.position!=='relative') return false;
    if(cs.display==='none' || cs.visibility==='hidden') return false;
    if(cs.transform && cs.transform!=='none') return false;
    if(cs.float && cs.float!=='none') return false;
    return true;
  }
  function offstage(el){
    var n=el;
    while(n && n!==document.body){
      if(n.classList && n.classList.contains('acc-b')
         && n.parentElement && !n.parentElement.classList.contains('open')) return true;
      if(n.hasAttribute && n.hasAttribute('hidden')) return true;
      n=n.parentElement;
    }
    return false;
  }
  var BLOCKS='.card,.rec,.rows,.stats,.btn.block,.btn-row,.field,.sec-t,.rdrow,.empty,.note,.slider-row';
  Array.prototype.slice.call(root.querySelectorAll(BLOCKS)).forEach(function(el){
    if(issues.length>=6) return;
    if(!inFlow(el) || offstage(el)) return;
    var r=el.getBoundingClientRect();
    if(r.width<2||r.height<2) return;
    var sib=el.nextElementSibling;
    if(!sib || !sib.matches || !sib.matches(BLOCKS)) return;
    if(!inFlow(sib) || offstage(sib)) return;
    var r2=sib.getBoundingClientRect();
    if(r2.width<2||r2.height<2) return;
    var name=function(e){
      return (e.className||e.tagName||'?').toString().split(' ').slice(0,2).join('.')
             + (e.id?'#'+e.id:'');
    };
    /* vertical stacking: the gap between one bottom and the next top */
    var gap=Math.round(r2.top-r.bottom);
    var xOverlap=Math.min(r.right,r2.right)-Math.max(r.left,r2.left);
    if(xOverlap<=2) return;                 // side by side, not stacked
    if(gap<-2){
      issues.push('OVERLAP '+name(el)+' / '+name(sib)+' by '+(-gap)+'px');
    } else if(gap===0 && touching.length<6){
      touching.push(name(el)+' / '+name(sib));
    }
  });
  if(touching.length) issues.push('TOUCHING (no gap): '+touching.join(' | '));
  return issues;
}

function auditView(label){
  var issues=[];
  issues=issues.concat(flowIssues(document.getElementById('view')));
  // horizontal overflow of the page
  var de=document.documentElement;
  if(de.scrollWidth > WIDTH+1) issues.push('PAGE OVERFLOW: scrollWidth '+de.scrollWidth+' > '+WIDTH);
  // elements sticking out past the viewport
  var over=[];
  Array.prototype.slice.call(document.querySelectorAll('#view *, .nav *, .appbar *')).forEach(function(el){
    var r=el.getBoundingClientRect();
    if(r.width===0&&r.height===0) return;
    if(r.right > WIDTH+1.5 || r.left < -1.5){
      // allow deliberate horizontal scrollers
      var p=el.closest('.swipe, .chart-wrap, [style*="overflow-x"]');
      if(!p) over.push(el.tagName.toLowerCase()+'.'+(el.className||'').toString().split(' ')[0]+' ['+Math.round(r.left)+'→'+Math.round(r.right)+']');
    }
  });
  if(over.length) issues.push('ELEMENTS OUTSIDE VIEWPORT ('+over.length+'): '+over.slice(0,6).join(' | '));
  // small touch targets
  var small=[];
  Array.prototype.slice.call(document.querySelectorAll('#view button, .nav button, .appbar button')).forEach(function(b){
    var r=b.getBoundingClientRect();
    if(r.width===0&&r.height===0) return;
    if(r.height < 30 || r.width < 26) small.push((b.textContent||b.className).trim().slice(0,22)+' ['+Math.round(r.width)+'x'+Math.round(r.height)+']');
  });
  if(small.length) issues.push('SMALL TOUCH TARGETS ('+small.length+'): '+small.slice(0,6).join(' | '));
  // inputs smaller than 16px cause iOS zoom-on-focus
  var zoom=[];
  Array.prototype.slice.call(document.querySelectorAll('#view input, #view textarea, #view select')).forEach(function(i){
    var fs=parseFloat(getComputedStyle(i).fontSize);
    if(fs<16 && i.type!=='range' && i.type!=='checkbox') zoom.push(i.id||i.className);
  });
  if(zoom.length) issues.push('INPUTS <16px (iOS will zoom): '+zoom.slice(0,5).join(','));
  issues=issues.concat(contrastIssues(document));
  // unreadable text
  var tiny=[];
  // unreadable text
  var tiny=[];
  Array.prototype.slice.call(document.querySelectorAll('#view *')).forEach(function(el){
    if(!el.childNodes.length) return;
    var hasText=Array.prototype.some.call(el.childNodes,function(n){return n.nodeType===3&&n.textContent.trim().length>2;});
    if(!hasText) return;
    var fs=parseFloat(getComputedStyle(el).fontSize);
    if(fs<8.5) tiny.push(el.textContent.trim().slice(0,18)+' ('+fs+'px)');
  });
  if(tiny.length) issues.push('TEXT UNDER 8.5px: '+tiny.slice(0,5).join(' | '));
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | '+label+(issues.length?'\\n        '+issues.join('\\n        '):''));
  return issues.length;
}

var bad=0;
/* The four primary destinations, each now a row index. */
['today','workouts','tennis','progress'].forEach(function(tab){
  resetStack(); TAB=tab; renderNav(); render();
  bad+=auditView(tab);
});
/* Every pushed page, audited at the depth a user actually reaches it.
   Reached by clicking the row rather than by calling the pane, so the audit
   also proves the row is wired. */
[['workouts','wRows'],['progress','pRows'],['tennis','aRows']].forEach(function(spec){
  resetStack(); TAB=spec[0]; renderNav(); render();
  var n=(document.getElementById(spec[1])||{querySelectorAll:function(){return [];}})
          .querySelectorAll('button').length;
  for(var i=0;i<n;i++){
    resetStack(); TAB=spec[0]; render();
    var b=document.getElementById(spec[1]).querySelectorAll('button')[i];
    /* the row title only: textContent would drag the subtitle in with it */
    var tt=b.querySelector('.rw-t');
    var label=((tt?tt.textContent:b.textContent)||'').trim().slice(0,20);
    b.click();
    bad+=auditView(spec[0]+' > '+label);
  }
});
/* Metrics and Settings, reached the way the app reaches them */
resetStack(); TAB='today'; renderNav();
openMetrics();
bad+=auditView('metrics');
['trends','sleep','baselines','import'].forEach(function(id,i){
  resetStack(); HTAB=null; openMetrics();
  var rows=document.getElementById('hRows');
  var b=rows&&rows.querySelectorAll('button')[i];
  if(!b) return;
  b.click();
  bad+=auditView('metrics > '+id);
});
/* Cycle screens. Tracking is switched on HERE rather than in the seeded demo
   data above, because the demo seed is the one the shipped app and every
   screenshot use and it must contain no cycle data at all. Wiped again below. */
(function(){
  DB.mcycle={on:true, starts:[addDays(T,-26),addDays(T,-54)],
             typicalLen:28, typicalPeriod:5, askedAt:null};
  [0,1,2,3,4].forEach(function(i){
    var d=addDays(T,-26+i);
    DB.checkins[d]=Object.assign({date:d,energy:5,soreness:5,stress:4,motivation:5,
      sleepMin:430,pain:'None'},DB.checkins[d]||{});
    DB.checkins[d].mc={bleeding:true, flow:i<2?'Heavy':'Light', cramps:i<2?7:3,
                       symptoms:['Cramps','Low mood'], feel:i<2?'discomfort':'normal'};
  });
  DB.checkins[T]=Object.assign({},DB.checkins[T]||{});
  DB.checkins[T].mc={bleeding:false, cramps:2, feel:'normal', symptoms:[]};
  /* the profile editor is a pushed page, not a sheet - auditing it as a sheet
   inspects an empty closed panel, which is what the "examined nothing" guard
   caught the last time I made this mistake */
['metric','imperial'].forEach(function(u){
  DB.profile.units=u; DB.profile.heightCm=182; DB.profile.weightKg=77.5;
  PROF_EDIT=false;
  resetStack(); openSettings();
  var pi=SET_PANES.map(function(x){return x.id;}).indexOf('profile');
  document.getElementById('setRows').querySelectorAll('button')[pi].click();
  bad+=auditView('settings > profile ('+u+')');
  document.getElementById('profEdit').click();
  bad+=auditView('settings > profile editing ('+u+')');
});
PROF_EDIT=false; DB.profile.units='metric';

resetStack(); TAB='today'; renderNav(); render();
  bad+=auditView('today + cycle row');
  resetStack(); openCycle();
  bad+=auditView('cycle page');
  mcSheet(T);
  (function(){
    var s=document.getElementById('sheet'), issues=[];
    if(s.getBoundingClientRect().width>WIDTH+1) issues.push('cycle sheet wider than viewport');
    issues=issues.concat(contrastIssues(s));
    REPORT.push((issues.length?'ISSUE':'OK   ')+' | sheet: cycle log'
      +(issues.length?'\\n        '+issues.join('\\n        '):''));
    bad+=issues.length;
  })();
  closeSheet();
  resetStack(); openSettings();
  var ci=SET_PANES.map(function(x){return x.id;}).indexOf('cycle');
  document.getElementById('setRows').querySelectorAll('button')[ci].click();
  bad+=auditView('settings > cycle (on)');
  /* and leave no cycle data behind for the rest of the audit */
  mcWipe();
  /* the profile editor is a pushed page, not a sheet - auditing it as a sheet
   inspects an empty closed panel, which is what the "examined nothing" guard
   caught the last time I made this mistake */
['metric','imperial'].forEach(function(u){
  DB.profile.units=u; DB.profile.heightCm=182; DB.profile.weightKg=77.5;
  PROF_EDIT=false;
  resetStack(); openSettings();
  var pi=SET_PANES.map(function(x){return x.id;}).indexOf('profile');
  document.getElementById('setRows').querySelectorAll('button')[pi].click();
  bad+=auditView('settings > profile ('+u+')');
  document.getElementById('profEdit').click();
  bad+=auditView('settings > profile editing ('+u+')');
});
PROF_EDIT=false; DB.profile.units='metric';

resetStack(); TAB='today'; renderNav(); render();
})();

resetStack(); openSettings();
bad+=auditView('settings');
SET_PANES.forEach(function(g,i){
  resetStack(); openSettings();
  var b=document.getElementById('setRows').querySelectorAll('button')[i];
  b.click();
  bad+=auditView('settings > '+g.id);
});
/* the profile editor is a pushed page, not a sheet - auditing it as a sheet
   inspects an empty closed panel, which is what the "examined nothing" guard
   caught the last time I made this mistake */
['metric','imperial'].forEach(function(u){
  DB.profile.units=u; DB.profile.heightCm=182; DB.profile.weightKg=77.5;
  PROF_EDIT=false;
  resetStack(); openSettings();
  var pi=SET_PANES.map(function(x){return x.id;}).indexOf('profile');
  document.getElementById('setRows').querySelectorAll('button')[pi].click();
  bad+=auditView('settings > profile ('+u+')');
  document.getElementById('profEdit').click();
  bad+=auditView('settings > profile editing ('+u+')');
});
PROF_EDIT=false; DB.profile.units='metric';

resetStack(); TAB='today'; renderNav(); render();
// sheets
[['check-in',function(){openCheckin(T);}],['activity',function(){activitySheet(null,T);}],
 ['preview',function(){previewWorkout('w_lowerA','full');}],['edit workout',function(){editWorkout('w_lowerA');}],
 ['exercise',function(){exerciseSheet('lx02');}],['schedule',function(){editSchedule();}],
 ['setup name',function(){startSetup();SETUP_AT('name');}],
 ['setup wearable',function(){startSetup();SETUP.draft.source='garmin';SETUP_AT('device');}],
 ['setup custom wearable',function(){startSetup();SETUP.draft.source='other';SETUP_AT('device');}],
 ['setup no wearable',function(){startSetup();SETUP.draft.source=null;SETUP_AT('device');}],
 ['setup sports',function(){startSetup();SETUP.draft.sports=['tennis','football'];SETUP_AT('sports');}],
 ['setup sports empty',function(){startSetup();SETUP.draft.sports=[];SETUP_AT('sports');}],
 ['setup goals',function(){startSetup();SETUP.draft.physiques=['muscle','lean'];SETUP_AT('goals');}],
 ['setup goals empty',function(){startSetup();SETUP.draft.physiques=[];SETUP_AT('goals');}],
 ['setup equipment: where',function(){
    startSetup(); SETUP.draft.place=null; SETUP.draft.gear=[]; SETUP_AT('gear'); }],
 ['setup equipment: home',function(){
    startSetup(); SETUP.draft.place='home';
    SETUP.draft.gear=['db','kb','ball','band','bench'];
    SETUP.draft.gearKg={db:24,kb:16,ball:9};
    SETUP_AT('gear'); }],
 ['setup equipment: gym',function(){
    startSetup(); SETUP.draft.place='gym';
    SETUP.draft.gear=GYM_GEAR.slice(); SETUP.gearOpen=false;
    SETUP_AT('gear'); }],
 ['setup equipment: gym list open',function(){
    startSetup(); SETUP.draft.place='gym';
    SETUP.draft.gear=GYM_GEAR.slice(); SETUP.gearOpen=true;
    SETUP_AT('gear'); }],
 ['setup schedule',function(){startSetup();SETUP_AT('sched');}],
 ['setup about you',function(){startSetup();SETUP_AT('body');}],
 /* every card of the walkthrough: the longest body is the one that overflows */
 ['cycle disable',function(){DB.mcycle={on:true,starts:[],typicalLen:null,typicalPeriod:null,askedAt:null};resetStack();openSettings();var i=SET_PANES.map(function(x){return x.id;}).indexOf('cycle');document.getElementById('setRows').querySelectorAll('button')[i].click();document.getElementById('sMcOff').click();}],
 ['away mode',function(){openAway();}],


 ['session detail',function(){sessionDetail(DB.sessions[0].id);}],
 ['day load',function(){resetStack();TAB='today';render();
   /* the timeline is a pushed page under Today now, not a tab */
   openPane('Recent days',null,paneTimeline);
   var b=document.querySelector('[data-dd]'); if(b)b.click();}],
 ['tour 1',function(){openTour();}],
 ['tour 3',function(){openTour();TOURSTEP=2;drawTour();}],
 ['tour last',function(){openTour();TOURSTEP=TOUR.length-1;drawTour();}]
].forEach(function(p){
  p[1]();
  var s=document.getElementById('sheet'), issues=[];
  var r=s.getBoundingClientRect();
  if(r.width>WIDTH+1) issues.push('sheet wider than viewport '+Math.round(r.width));
  var body=document.getElementById('sheetBody');
  if(body.scrollWidth>body.clientWidth+2) issues.push('sheet body scrolls horizontally '+body.scrollWidth+'>'+body.clientWidth);
  var small=[];
  Array.prototype.slice.call(s.querySelectorAll('button')).forEach(function(b){
    var br=b.getBoundingClientRect(); if(br.height===0)return;
    if(br.height<30) small.push((b.textContent||'').trim().slice(0,16)+'['+Math.round(br.height)+']'); });
  if(small.length) issues.push('small buttons in sheet: '+small.slice(0,5).join(','));
  issues=issues.concat(flowIssues(s));
  issues=issues.concat(contrastIssues(s));   // the primary button only exists here
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | sheet: '+p[0]+(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length; closeSheet();
});
/* address wizard steps by id: they have been reordered once already and
   index-based navigation pointed the audit at the wrong screen silently */
function SETUP_AT(id){
  var i=SETUP_STEPS.map(function(x){return x.id;}).indexOf(id);
  if(i<0) throw new Error('no setup step '+id);
  SETUP.step=i; drawSetup();
}

// setup wizard: walk every step and watch what the Continue button does
(function(){
  function R(el){ if(!el) return null; var r=el.getBoundingClientRect();
    return {t:Math.round(r.top),b:Math.round(r.bottom),l:Math.round(r.left),
            w:Math.round(r.width),h:Math.round(r.height)}; }
  var issues=[], prev=null, prevSheet=null;
  startSetup(); SETUP.draft.source='whoop';   // the longest finish label
  /* kill the 280ms slide-in: otherwise every measurement catches the sheet
     mid-animation, still translated off the bottom of the screen */
  var sh=document.getElementById('sheet');
  sh.style.transition='none'; sh.classList.add('on'); void sh.offsetHeight;
  for(var step=0; step<SETUP_STEPS.length; step++){
    SETUP.step=step; drawSetup();
    sh.classList.add('on'); void sh.offsetHeight;
    var sheet=R(document.getElementById('sheet'));
    var body=document.getElementById('sheetBody');
    var rb=R(body), rf=R(document.getElementById('sheetFoot'));
    var next=document.getElementById('setNext'), rn=R(next);
    var tag='step '+(step+1)+' ('+SETUP_STEPS[step].id+')';
    if(!rn){ issues.push(tag+': no Continue button'); continue; }
    if(rn.b>HEIGHT+1) issues.push(tag+': Continue is '+(rn.b-HEIGHT)+'px below the viewport');
    if(rn.h<30) issues.push(tag+': Continue only '+rn.h+'px tall');
    if(rf && rn.b>rf.b+1) issues.push(tag+': Continue overflows its footer by '+(rn.b-rf.b)+'px');
    if(rf && rb && rf.t<rb.b-1) issues.push(tag+': footer overlaps the body by '+(rb.b-rf.t)+'px');
    if(sheet && rf && Math.abs(sheet.b-rf.b)>1) issues.push(tag+': footer not flush with the sheet ('+(sheet.b-rf.b)+'px)');
    if(sheet && sheet.b>HEIGHT+1) issues.push(tag+': sheet extends '+(sheet.b-HEIGHT)+'px past the viewport');
    /* the actual complaint: the button must not move or resize between steps */
    if(prev){
      if(Math.abs(rn.w-prev.w)>2) issues.push(tag+': Continue width jumps '+prev.w+'->'+rn.w);
      if(Math.abs(rn.h-prev.h)>2) issues.push(tag+': Continue height jumps '+prev.h+'->'+rn.h);
      if(Math.abs(rn.b-prev.b)>2) issues.push(tag+': Continue bottom moves '+prev.b+'->'+rn.b);
      if(Math.abs(rn.l-prev.l)>2) issues.push(tag+': Continue shifts sideways '+prev.l+'->'+rn.l);
    }
    prev=rn;
    /* The cause was the sheet resizing itself, not the button. Guard the box
       that was actually wrong, so a future content change cannot bring it
       back quietly. */
    if(sheet){
      if(prevSheet!=null && Math.abs(sheet.w-prevSheet)>2)
        issues.push(tag+': the sheet itself resizes '+prevSheet+'->'+sheet.w);
      prevSheet=sheet.w;
    }
  }
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | setup wizard: Continue button'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length; sh.style.transition=''; closeSheet();
})();

// bottom bar: four fixed tabs that always fill the width
(function(){
  var issues=[];
  var keepSrc=DB.profile.source, keepW=DB.whoop, keepTab=TAB;
  [['with a wearable','whoop'],['without one','none']].forEach(function(pair){
    DB.profile.source=pair[1];
    DB.whoop={cycles:[],workouts:[],journal:[],imports:[]};
    TAB='today'; resetStack(); renderNav();
    var nav=document.getElementById('nav');
    var btns=Array.prototype.slice.call(nav.querySelectorAll('button'));
    var n=btns.length;
    if(!n){ issues.push(pair[0]+': no tabs rendered'); return; }
    if(n!==4) issues.push(pair[0]+': '+n+' buttons, expected 4');
    var side=getComputedStyle(document.querySelector('.nav')).borderRightWidth;
    if(side && parseFloat(side)>0) return;          // sidebar layout, not the bar
    var r0=btns[0].getBoundingClientRect(), rN=btns[n-1].getBoundingClientRect();
    var navR=nav.getBoundingClientRect();
    if(Math.abs(r0.left-navR.left)>2)
      issues.push(pair[0]+': first tab not flush left ('+Math.round(r0.left-navR.left)+'px)');
    if(Math.abs(navR.right-rN.right)>2)
      issues.push(pair[0]+': last tab leaves '+Math.round(navR.right-rN.right)+'px empty on the right');
    var widths=btns.map(function(b){ return Math.round(b.getBoundingClientRect().width); });
    if(Math.max.apply(null,widths)-Math.min.apply(null,widths)>2)
      issues.push(pair[0]+': uneven tab widths '+widths.join('/'));
    // a tab is a touch target, whatever the viewport
    btns.forEach(function(b,i){
      var r=b.getBoundingClientRect();
      if(r.height<44) issues.push(pair[0]+': tab '+(i+1)+' only '+Math.round(r.height)+'px tall');
    });
  });
  DB.profile.source=keepSrc; DB.whoop=keepW; TAB=keepTab; resetStack(); renderNav();
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | bottom bar: four fixed tabs'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();

// the activity picker and the screen before a clock starts
[['sheet: activity picker', function(){ pickActivity(function(){},'Start activity'); }],
 ['sheet: about to start',  function(){ preStartSheet('cycling'); }],
 ['sheet: about to start, with a target', function(){
    preStartSheet('cycling');
    var o=document.getElementById('psOn'); if(o) o.click(); }]
].forEach(function(pair){
  var issues=[];
  try{ pair[1](); }catch(e){ issues.push('threw: '+e.message); }
  var sheet=document.getElementById('sheet');
  if(sheet.scrollWidth>WIDTH+1) issues.push('overflows '+sheet.scrollWidth);
  issues=issues.concat(flowIssues(sheet));
  issues=issues.concat(contrastIssues(sheet));
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | '+pair[0]
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
  closeSheet();
});

// the three rings, with and without anything behind them
(function(){
  var keepC=JSON.parse(JSON.stringify(DB.checkins));
  [['scores with data', true], ['scores with nothing behind them', false]].forEach(function(pair){
    if(!pair[1]) DB.checkins={};
    resetStack(); TAB='today'; render();
    var issues=[];
    var row=document.querySelector('.scores');
    /* With no check-in there is no readiness, no sleep and usually no strain,
       so Today leads with "Check in" instead. Three em-dashes in circles would
       say less than that prompt does, so an absent ring row there is correct -
       but only there. */
    if(!row && document.getElementById('btnCheck')){ /* the check-in prompt */ }
    else if(!row){ issues.push('no ring row on Today'); }
    else {
      if(row.scrollWidth>WIDTH+1) issues.push('rings overflow '+row.scrollWidth);
      var n=row.querySelectorAll('.score').length;
      if(n!==3) issues.push('expected 3 scores, got '+n);
      /* readiness leads: it is not one of three equals */
      if(!row.querySelector('.score.lead')) issues.push('no leading score');
      Array.prototype.forEach.call(row.querySelectorAll('.score'), function(b){
        var r=b.getBoundingClientRect();
        if(r.height<44) issues.push('score target only '+Math.round(r.height)+'px tall');
      });
      issues=issues.concat(flowIssues(row));
      issues=issues.concat(contrastIssues(row));
    }
    REPORT.push((issues.length?'ISSUE':'OK   ')+' | today: '+pair[0]
      +(issues.length?'\\n        '+issues.join('\\n        '):''));
    bad+=issues.length;
  });
  DB.checkins=keepC;
  resetStack(); TAB='today'; render();
})();

// the day's activity list, which is where the two buttons now live
(function(){
  var keepA=DB.activities;
  DB.activities=(DB.activities||[]).concat([
    {id:'lx1',date:T,type:'cycling',min:45,time:'16:00',endTime:'16:45',
     intensity:'Moderate',rpe:6},
    {id:'lx2',date:T,type:'football',min:105,time:'19:30',endTime:'21:15',
     intensity:'Maximal',rpe:9}
  ]);
  resetStack(); TAB='today'; render();
  var issues=[];
  var card=document.getElementById('actsCard');
  if(!card) issues.push('no activities card');
  else {
    if(card.scrollWidth>WIDTH+1) issues.push('overflows '+card.scrollWidth);
    issues=issues.concat(flowIssues(card));
    issues=issues.concat(contrastIssues(card));
  }
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | today: activities card'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
  DB.activities=keepA;
  resetStack(); TAB='today'; render();
})();

// the week strip, on this week and on a past one, plus one day's own screen
(function(){
  var keepOff=WEEKOFF;
  [['this week', 0], ['last week', -1]].forEach(function(pair){
    WEEKOFF=pair[1];
    resetStack(); TAB='today'; render();
    var issues=[];
    var strip=document.querySelector('.wk-nav');
    if(!strip){ issues.push('no week navigation'); }
    else {
      var card=strip.parentElement;
      if(card.scrollWidth>WIDTH+1) issues.push('strip overflows '+card.scrollWidth);
      // the forward control exists only when there is a week to go forward to
      var fwd=document.getElementById('wkNext');
      if(pair[1]===0 && fwd) issues.push('forward offered on the current week');
      if(pair[1]<0 && !fwd) issues.push('no way forward from a past week');
      // every touch target in the strip
      Array.prototype.forEach.call(card.querySelectorAll('button'), function(b){
        var r=b.getBoundingClientRect();
        if(r.height>0 && r.height<36)
          issues.push('strip target only '+Math.round(r.height)+'px tall');
      });
      issues=issues.concat(flowIssues(card));
      issues=issues.concat(contrastIssues(card));
    }
    REPORT.push((issues.length?'ISSUE':'OK   ')+' | today: '+pair[0]
      +(issues.length?'\\n        '+issues.join('\\n        '):''));
    bad+=issues.length;
  });

  // a day other than today SELECTED in the calendar, with something on it
  var keepA=DB.activities, keepSel=SELDAY;
  var d=addDays(T,-3);
  DB.activities=(DB.activities||[]).concat([
    {id:'wk1',date:d,type:'football',min:95,time:'19:00',endTime:'20:35',
     intensity:'Hard',rpe:8}
  ]);
  WEEKOFF=0; SELDAY=d;
  resetStack(); TAB='today'; render();
  (function(){
    var issues=[];
    var v=document.getElementById('view');
    if(v.scrollWidth>WIDTH+1) issues.push('overflows '+v.scrollWidth);
    if(!document.getElementById('acAdd')) issues.push('no way to add to the day');
    if(document.getElementById('acStart')) issues.push('a clock offered on a past day');
    if(!document.getElementById('acToday')) issues.push('no way back to today');
    if(!document.querySelector('#view .wk-d.sel')) issues.push('the day is not marked selected');
    issues=issues.concat(flowIssues(v));
    issues=issues.concat(contrastIssues(v));
    REPORT.push((issues.length?'ISSUE':'OK   ')+' | a selected day'
      +(issues.length?'\\n        '+issues.join('\\n        '):''));
    bad+=issues.length;
  })();
  DB.activities=keepA; SELDAY=keepSel;
  WEEKOFF=keepOff; resetStack(); TAB='today'; render();
})();

// pushed pages: the one navigation idiom has to work at every width
(function(){
  var issues=[];
  var keepTab=TAB; TAB='today'; resetStack();
  /* Settings became a tab, so it is no longer an example of a pushed page.
     Metrics still is, and so is any pane opened from a row. */
  [['Metrics',openMetrics],
   ['Recent days',function(){ openPane('Recent days',null,paneTimeline); }]
  ].forEach(function(pair){
    resetStack();
    try{ pair[1](); }catch(e){ issues.push(pair[0]+': threw '+e.message); return; }
    var bk=document.getElementById('abBack');
    if(!bk){ issues.push(pair[0]+': no back button'); return; }
    var rb=bk.getBoundingClientRect();
    if(rb.width<44||rb.height<44)
      issues.push(pair[0]+': back button only '+Math.round(rb.width)+'x'+Math.round(rb.height));
    var ttl=document.querySelector('#appbar .ttl');
    if(ttl){
      var rt=ttl.getBoundingClientRect();
      if(rt.left<rb.right-1)
        issues.push(pair[0]+': title overlaps the back button by '+Math.round(rb.right-rt.left)+'px');
    }
    if(document.getElementById('abGear'))
      issues.push(pair[0]+': the settings gear is back, and it should be gone');
    var v=document.getElementById('view');
    if(v.scrollWidth>WIDTH+1)
      issues.push(pair[0]+': page overflows by '+(v.scrollWidth-WIDTH)+'px');
    if((v.textContent||'').trim().length<40)
      issues.push(pair[0]+': page rendered almost nothing');
  });
  resetStack(); TAB=keepTab; renderNav(); render();
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | pushed pages'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();

// the warm-up screen, with a movement expanded. It lives in #wmode, not in a
// sheet - auditing it as a sheet inspected an empty closed panel.
startWorkout('w_lowerA','full',T); W.phase='preview'; W.step=0; drawWM();
(function(){
  var r=document.querySelector('#wmBody [data-wu]'); if(r) r.click();
  var wm=document.getElementById('wmode'), issues=[];
  if(wm.scrollWidth>WIDTH+1) issues.push('warm-up overflows '+wm.scrollWidth);
  issues=issues.concat(flowIssues(wm));
  issues=issues.concat(contrastIssues(wm));
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | workout: warm-up expanded'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();
exitWM(true);

// workout mode, in each of the states it actually reaches. It used to be
// audited once, in its opening state, for overflow and target size only.
function auditWM(label){
  var issues=[], wm=document.getElementById('wmode');
  if(wm.scrollWidth>WIDTH+1) issues.push('overflows '+wm.scrollWidth);
  var small=[];
  Array.prototype.slice.call(wm.querySelectorAll('button,input')).forEach(function(b){
    var r=b.getBoundingClientRect(); if(r.height===0)return;
    if(r.height<30) small.push((b.textContent||b.className||'').trim().slice(0,14)+'['+Math.round(r.height)+']'); });
  if(small.length) issues.push('small targets: '+small.slice(0,6).join(','));
  Array.prototype.slice.call(wm.querySelectorAll('input')).forEach(function(i){
    if(parseFloat(getComputedStyle(i).fontSize)<16) issues.push('input <16px: '+i.className); });
  issues=issues.concat(flowIssues(wm));
  issues=issues.concat(contrastIssues(wm));
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | workout: '+label
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
}

// 1 · the opening state: set 1 of n, nothing logged
startWorkout('w_lowerA','full',T); W.phase='main'; W.step=0; drawWM();
auditWM('set 1, nothing logged');

// 2 · a set logged, with the countdown open inside the card it belongs to.
//     The rest strip wraps on a 320px screen, which is exactly the kind of
//     thing the overlap detector is for.
DB.settings.restTimerOn=true;
document.querySelector('#wmBody [data-log]').click();
auditWM('set logged, resting');

// 3 · every set logged: the finished card, on its way to the next exercise
(function(){
  var g=0;
  while(document.querySelector('#wmBody [data-log]') && g++<20){
    document.querySelector('#wmBody [data-log]').click();
  }
  cancelAuto();
})();
auditWM('exercise finished');

// 3b · a session measured in time: a clock, not a set list.
//      The seeded profile owns no gear at all, and resolveExercise correctly
//      refuses to prescribe a run to somebody who never said they can run -
//      it swaps Zone 2 Run for a Cossack Squat. So this block lends the
//      profile somewhere to run for the length of the audit and hands it back.
exitWM(true);
var KEEPGEAR=DB.profile.gear;
DB.profile.gear=(KEEPGEAR||[]).concat(['run','bike']);
(function(){
  startWorkout('w_runEasy','full',T);
  var ci=-1;
  W.entries.forEach(function(e,n){ if(e.cardio && ci<0) ci=n; });
  if(ci<0){ REPORT.push('ISSUE | workout: no cardio block in w_runEasy — '
    +W.entries.map(function(e){return e.name;}).join(', ')); bad++; return; }
  W.phase='main'; W.step=ci; drawWM();
  auditWM('run, ready to start');

  document.getElementById('cardGo').click();
  // wind it back so the clock shows a long, wide time
  W.entries[ci].run.startedAt = Date.now() - 75*60*1000;
  W.entries[ci].run.laps=[Date.now()-40*60*1000, Date.now()-20*60*1000];
  cardTick(); drawWM();
  auditWM('run in progress, 1:15:00 with laps');

  document.getElementById('cardStop').click();
  auditWM('run stopped, ready to log');
})();
exitWM(true);

// 3c · the end of something started from the Activity tab, with its comparison
(function(){
  var keepA=DB.activities;
  DB.activities=[{id:'prev',date:addDays(T,-5),type:'running',min:34,dist:5.8,
                  intensity:'Moderate',rpe:6}];
  startLiveActivity('running','Moderate');
  W.entries[0].run.startedAt = Date.now() - 41*60*1000;
  cardTick();
  document.getElementById('cardStop').click();
  document.querySelector('#wmBody [data-log]').click();
  cancelAuto(); nextStep();
  var dEl=document.getElementById('afDist');
  if(dEl){ dEl.value='7.2'; dEl.dispatchEvent(new Event('input',{bubbles:true})); }
  auditWM('activity finish with the comparison');
  DB.activities=keepA;
})();
exitWM(true);
DB.profile.gear=KEEPGEAR;
startWorkout('w_lowerA','full',T); W.phase='main'; W.step=0; drawWM();
(function(){
  var g=0;
  while(document.querySelector('#wmBody [data-log]') && g++<20){
    document.querySelector('#wmBody [data-log]').click();
  }
  cancelAuto();
})();

// 4 · the exit sheet, ON TOP of the workout overlay. This is the state that
//     was broken: #wmode is z-index 300 and the sheet was 201, so the whole
//     panel - Cancel included - was rendering underneath and unreachable.
document.getElementById('wmX').click();
(function(){
  var sheet=document.getElementById('sheet'), issues=[];
  var wmZ=+(getComputedStyle(document.getElementById('wmode')).zIndex||0);
  var shZ=+(getComputedStyle(sheet).zIndex||0);
  var scZ=+(getComputedStyle(document.getElementById('scrim')).zIndex||0);
  if(!(shZ>wmZ)) issues.push('the exit sheet is BEHIND the workout overlay ('+shZ+' vs '+wmZ+')');
  if(!(scZ>wmZ)) issues.push('the scrim is behind the workout overlay ('+scZ+' vs '+wmZ+')');
  if(!document.getElementById('wmKeep')) issues.push('no Cancel button');
  if(sheet.scrollWidth>WIDTH+1) issues.push('overflows '+sheet.scrollWidth);
  issues=issues.concat(flowIssues(sheet));
  issues=issues.concat(contrastIssues(sheet));
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | workout: exit sheet over the overlay'
    +(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();
closeSheet();
exitWM(true);

// safe-area + fixed-element audit (matters on Dynamic Island / home indicator)
(function(){
  var issues=[];
  var nav=document.querySelector('.nav'), ab=document.querySelector('.appbar'), app=document.getElementById('app');
  var nr=nav.getBoundingClientRect(), ar=ab.getBoundingClientRect();
  /* two valid layouts: bottom bar (phones) or left sidebar (tablet/desktop) */
  var sidebar = nr.height > window.innerHeight*0.8 && nr.width < WIDTH*0.5;
  REPORT.push('       layout: '+(sidebar?'SIDEBAR (desktop/tablet)':'BOTTOM BAR (mobile)'));
  if(nr.left<-0.5||nr.right>WIDTH+0.5) issues.push('nav exceeds viewport horizontally');
  if(ar.top>2) issues.push('appbar not at top ('+Math.round(ar.top)+')');
  if(sidebar){
    if(Math.abs(nr.top)>1.5) issues.push('sidebar not flush to top');
    if(Math.abs(nr.bottom-window.innerHeight)>1.5) issues.push('sidebar not full height');
    var ml=parseFloat(getComputedStyle(app).marginLeft);
    if(ml < nr.width-1) issues.push('#app margin-left ('+ml+') does not clear the sidebar ('+Math.round(nr.width)+'px)');
    if(document.querySelector('.nav-brand') && getComputedStyle(document.querySelector('.nav-brand')).display==='none')
      issues.push('sidebar brand hidden in sidebar layout');
    /* desktop must actually use the horizontal space */
    var vcs=getComputedStyle(document.getElementById('view'));
    if(vcs.display!=='grid') issues.push('desktop content is not multi-column (display:'+vcs.display+')');
  } else {
    if(Math.abs(nr.bottom-window.innerHeight)>1.5) issues.push('bottom nav not flush to viewport bottom ('+Math.round(nr.bottom)+' vs '+window.innerHeight+')');
    var cs=getComputedStyle(document.body);
    if(parseFloat(cs.paddingBottom) < nr.height-1) issues.push('body bottom padding ('+cs.paddingBottom+') does not clear the nav ('+Math.round(nr.height)+'px) — content would hide behind it');
    if(document.querySelector('.nav-brand') && getComputedStyle(document.querySelector('.nav-brand')).display!=='none')
      issues.push('sidebar brand visible in bottom-bar layout');
  }
  // nav buttons must be reachable
  Array.prototype.slice.call(nav.querySelectorAll('button')).forEach(function(b){
    var r=b.getBoundingClientRect();
    if(r.height<40) issues.push('nav button only '+Math.round(r.height)+'px tall');
    if(r.bottom>window.innerHeight+0.5) issues.push('nav button below the fold');
  });
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | fixed chrome & safe areas'+(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();
// every scrollable region should carry momentum scrolling
(function(){
  var issues=[];
  [['.sheet-b','sheet body'],['.wm-b','workout body']].forEach(function(p){
    var el2=document.querySelector(p[0]); if(!el2) return;
    var cs=getComputedStyle(el2);
    if(cs.overflowY!=='auto'&&cs.overflowY!=='scroll') issues.push(p[1]+' is not scrollable');
  });
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | scroll regions'+(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();
// inputs must be >=16px or iOS Safari zooms the page on focus
(function(){
  var issues=[], seen=0;
  ['CHECKIN','ACTIVITY'].forEach(function(){});
  openCheckin(T);
  Array.prototype.slice.call(document.querySelectorAll('#sheet input, #sheet textarea, #sheet select')).forEach(function(i){
    if(i.type==='range'||i.type==='checkbox'||i.type==='file') return;
    seen++;
    var fs=parseFloat(getComputedStyle(i).fontSize);
    if(fs<16) issues.push((i.id||i.className)+' is '+fs+'px');
  });
  closeSheet();
  if(!seen) issues.push('no inputs found to check');
  REPORT.push((issues.length?'ISSUE':'OK   ')+' | form inputs >=16px (no focus zoom), '+seen+' checked'+(issues.length?'\\n        '+issues.join('\\n        '):''));
  bad+=issues.length;
})();

// oversized icons: every inline svg must be smaller than a touch target
(function(){
  var big=[];
  Array.prototype.slice.call(document.querySelectorAll('#view svg, .sheet svg, #wmode svg, .nav svg')).forEach(function(s){
    var r=s.getBoundingClientRect();
    if(r.width>60||r.height>60){
      /* a score arc is a chart drawn at the size it needs to be read, not an
         icon that has escaped its touch target */
      var chart = s.closest('.arc') || s.classList.contains('arc-s');
      if(!chart) big.push((s.getAttribute('class')||s.parentNode.className||'?')+' '+Math.round(r.width)+'x'+Math.round(r.height));
    }
  });
  REPORT.push((big.length?'ISSUE':'OK   ')+' | icon sizing'+(big.length?'\\n        oversized: '+big.slice(0,6).join(' | '):''));
  bad+=big.length?1:0;
})();
REPORT.push('ERRORS: '+(window.__errors.length?window.__errors.join(' ;; '):'none'));
REPORT.push('VIEWPORT: '+WIDTH+'x'+window.innerHeight);
REPORT.push('STORAGE: '+Store.mode+' durable='+Store.durable);
REPORT.push('TOTAL ISSUES: '+bad);
window.__REPORT=REPORT; window.__BAD=bad;
}
/* The app now has two themes, and a colour problem in one is invisible from
   the other. Audit both, pinning the theme explicitly so the result does not
   depend on what the test machine prefers. */
function runBoth(){
  var all=[], total=0;
  ['light','dark'].forEach(function(mode){
    document.documentElement.setAttribute('data-theme',mode);
    window.__REPORT=null; window.__BAD=0;
    runAudit();
    all.push('--- '+mode.toUpperCase()+' THEME ---');
    all=all.concat(window.__REPORT);
    total+=window.__BAD;
    var old=document.getElementById('layoutout'); if(old) old.remove();
  });
  document.documentElement.removeAttribute('data-theme');
  window.__REPORT=all; window.__BAD=total; window.__done=true;
  document.title=(total===0?'LAYOUTOK':'LAYOUTBAD')+' '+total;
  var pre=document.createElement('pre'); pre.id='layoutout';
  pre.textContent='LAYOUT_START\\n'+all.join('\\n')+'\\nLAYOUT_END';
  document.body.appendChild(pre);
}
var _w=0;
(function waitBoot(){
  if(typeof DB!=='undefined' && DB && typeof Store!=='undefined' && Store.mode){ runBoth(); return; }
  if(++_w>200){ document.title='BOOTFAIL'; window.__done=true; window.__REPORT=['ISSUE | app never booted']; window.__BAD=1; return; }
  setTimeout(waitBoot,40);
})();
</script>
"""
audit = audit.replace("__CSVDATA__", json.dumps(CSV))
i = html.index("<script>")
out = html[:i] + shim + html[i:]
out = out.replace("</body>", audit + "\n</body>")
io.open(os.path.join(SP,"layout.html"),"w",encoding="utf-8").write(out)
print("layout.html written")

