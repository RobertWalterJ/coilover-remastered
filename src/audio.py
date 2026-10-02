# -*- coding: utf-8 -*-
"""A proper sound layer: five engines, twelve surfaces, dampers, bush, weather.

WHY THIS IS SYNTHESISED AND NOT SAMPLED. Robert asked whether I could fetch
audio assets. I can, and for a few things recordings would genuinely win, but
not for most of what he listed, and not here:

  * the game is one offline HTML file that a service worker caches whole, and
    a usable set of surface loops is megabytes
  * he ships his own work licence free, and even CC0 brings attribution
    bookkeeping into a repo that currently has none to do
  * and the decisive one: almost everything on his list is a CONTINUOUS sound
    that has to track a number. Tyre scrub follows slip angle, roll noise
    follows surface and speed, a damper thud follows compression velocity, a
    bush swish follows how close the branch was. A loop can be crossfaded
    toward those. A filtered noise bed simply IS those.

Recordings still beat synthesis for one shots with complicated spectra: a real
gravel crunch, a loon, water on a shore. Those are worth revisiting with CC0
sources if he wants them. Everything below works without them.

WHAT WAS ALREADY THERE, and it is good: a baked firing pulse loop crossfaded
between on throttle and off, two sub octaves, a turbo whine, a waveshaper and
a compressor, plus four noise beds for wind, scrub, roll and chassis rattle.
This does not replace any of it. It adds the five things it did not have.

ONE. FIVE ENGINES INSTEAD OF ONE. The bake was hard coded to a five cylinder,
so every truck in the game sounded like the same truck. Cylinder count,
resonance, decay, noise and firing unevenness are now per vehicle, and the
buffers are rebaked when you change car. That is a bigger perceived change
than any amount of extra layering:

    Bracken   5 uneven cylinders, low and lumpy, lots of induction noise
    Marisol   6, lower still and gruffer, a working truck
    Kestrel   4, buzzier and more even, higher resonance
    Serrano   8, even firing, a hard flat bark
    Veloce   10, highest and smoothest, almost no unevenness left

Fitting engine parts also sharpens the voice, so an upgrade is audible before
the speedometer proves it.

TWO. THE ROAD UNDER THE TYRES, which was one noise bed for all twelve
surfaces. Each surface now has its own filter colour, level, low rumble share
and looseness, crossfaded as the wheels cross from asphalt to gravel to bog.
Looseness also throws stones: short clicks at a rate set by speed, which is
what gravel actually sounds like from inside a car.

THREE. DAMPERS AND SPRINGS, which had only a chassis rattle driven by how much
the suspension was moving on average. Now each corner is watched for its own
compression velocity, and three things can happen: a low thud into bump, a
lighter metallic clank on rebound, and a hard clonk when a damper runs out of
travel and bottoms. The bottom out is the one that matters, because it is the
sound that tells you the landing was too big, and it arrives at the exact
moment the suspension says so rather than being guessed from the camera.

FOUR. BRUSH. Now that there are 19,258 plants, driving through them should
cost you something to hear. `updateFlora` already walks every instance to fill
its buffers, so it keeps the small ones within 40 m in a list; the sound tick
narrows that to 14 m a few times a second, and the frame test is then against
a handful. Grass hisses, a shrub swishes, a sapling whips.

FIVE. THE PLACE ITSELF. Each map gets a quiet bed and a few voices: dry thin
wind and cicadas in the heat for the desert, wind through trees and a loon at
dawn and dusk for the Shield, a low traffic hum for the city. All of it sits
around a fiftieth of the engine's level, because ambience you notice is
ambience that is too loud.

AND SNOW, ready for step 9. It is not a surface in `SURF` yet, so it is
applied as a modifier on whatever surface is underneath, keyed off the same
`FLORA.snow` flag the flora uses: the top end comes off the roll noise, the
level drops, the stones stop, and a soft squeak comes in under it.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# =====================================================================
# 1. the engine bake becomes per vehicle
# =====================================================================
sub("""    var CYL=5, REF_RPM=3000;
    var firesPerSec=REF_RPM/60*CYL/2;              /* 125 a second at the reference */
    var EVENTS=CYL*25;                             /* a whole number of firing cycles */
    function bakeEngine(o){
      var dur=EVENTS/firesPerSec;""",
"""    var REF_RPM=3000;
    function bakeEngine(o){
      var CYL=o.cyl||5;
      var firesPerSec=REF_RPM/60*CYL/2;            /* 125 a second for a five */
      var EVENTS=CYL*25;                           /* a whole number of cycles */
      var dur=EVENTS/firesPerSec;""")

sub("""    var bufOn =bakeEngine({f1:112,f2:171,decay:52,noise:0.50,amp:1.0,uneven:0.055,ampVar:0.16});
    var bufOff=bakeEngine({f1:118,f2:181,decay:104,noise:0.26,amp:0.7,uneven:0.040,ampVar:0.10});""",
"""    /* the voices, one per truck. See src/audio.py. */
    var VOICES={
      bracken:{cyl:5,  f1:104, f2:158, decay:44, noise:0.60, uneven:0.080, ampVar:0.22},
      marisol:{cyl:6,  f1:88,  f2:134, decay:38, noise:0.66, uneven:0.058, ampVar:0.17},
      kestrel:{cyl:4,  f1:126, f2:193, decay:58, noise:0.46, uneven:0.034, ampVar:0.13},
      serrano:{cyl:8,  f1:98,  f2:154, decay:66, noise:0.40, uneven:0.020, ampVar:0.10},
      veloce :{cyl:10, f1:140, f2:221, decay:86, noise:0.30, uneven:0.011, ampVar:0.07}
    };
    function voiceFor(i){
      var id=(VEHICLES[i]||VEHICLES[0]).id;
      var v=VOICES[id]||VOICES.bracken;
      /* a built engine is sharper and angrier, so the upgrade is audible
         before the speedometer has had a chance to prove it */
      var lv=0;
      try{ lv=(upLevels(id).eng)||0; }catch(_){}
      return {cyl:v.cyl, f1:v.f1*(1+lv*0.012), f2:v.f2*(1+lv*0.012),
              decay:v.decay*(1-lv*0.045), noise:v.noise*(1+lv*0.10),
              uneven:v.uneven, ampVar:v.ampVar};
    }
    function bakePair(i){
      var v=voiceFor(i);
      return [bakeEngine({cyl:v.cyl, f1:v.f1, f2:v.f2, decay:v.decay,
                          noise:v.noise, amp:1.0, uneven:v.uneven, ampVar:v.ampVar}),
              bakeEngine({cyl:v.cyl, f1:v.f1*1.055, f2:v.f2*1.058, decay:v.decay*2.0,
                          noise:v.noise*0.52, amp:0.7, uneven:v.uneven*0.72,
                          ampVar:v.ampVar*0.62})];
    }
    var pair=bakePair(typeof VEH==='number'? VEH : 0);
    var bufOn=pair[0], bufOff=pair[1];""")

sub("""       wind  :noiseBed('bandpass',520,0.7),
       scrub :noiseBed('bandpass',1700,2.4),
       sand  :noiseBed('bandpass',2900,0.9),
       rattle:noiseBed('bandpass',780,3.0),
       gear:1, burble:0, starter:null};""",
"""       wind  :noiseBed('bandpass',520,0.7),
       scrub :noiseBed('bandpass',1700,2.4),
       sand  :noiseBed('bandpass',2900,0.9),
       roll  :noiseBed('lowpass',320,0.8),     /* the rumble under the hiss */
       rattle:noiseBed('bandpass',780,3.0),
       squeak:noiseBed('bandpass',2300,6.0),   /* packed snow under a tyre */
       amb   :noiseBed('bandpass',600,0.6),    /* the place itself */
       amb2  :noiseBed('bandpass',2200,1.4),
       bakePair:bakePair, voiceFor:voiceFor,
       gear:1, burble:0, starter:null, voice:(typeof VEH==='number'? VEH:0),
       stone:0, brushT:0, brushCool:0, call:3+Math.random()*6, chirp:0, voices:0,
       /* so the headless harness can prove these fire, rather than me
          squinting at a waveform and hoping */
       dbg:{bump:0, rebound:0, bottom:0, brush:0, stone:0, surf:-1}};""")

# ---- swapping the voice when the truck changes
sub("""/* a starter motor, then it catches */""",
r"""/* A buffer cannot be changed once its source has started, so a voice change
   builds new sources into the same gains and throws the old pair away. */
function setEngineVoice(i){
  if(!A || A.voice===i) return;
  try{
    var pair=A.bakePair(i), t=A.ctx.currentTime;
    var on=A.ctx.createBufferSource(); on.buffer=pair[0]; on.loop=true;
    var off=A.ctx.createBufferSource(); off.buffer=pair[1]; off.loop=true;
    on.playbackRate.value=A.srcOn.playbackRate.value;
    off.playbackRate.value=A.srcOff.playbackRate.value;
    on.connect(A.gOn); off.connect(A.gOff);
    on.start(); off.start();
    try{ A.srcOn.stop(t+0.05); A.srcOff.stop(t+0.05); }catch(_){}
    A.srcOn=on; A.srcOff=off; A.voice=i;
  }catch(e){}
}

/* a starter motor, then it catches */""")

sub("""    /* the upgraded spec, not the showroom one */
    var V=(typeof upSpec==='function')? upSpec(i) : VEHICLES[i];
    VEH=i;""",
"""    /* the upgraded spec, not the showroom one */
    var V=(typeof upSpec==='function')? upSpec(i) : VEHICLES[i];
    VEH=i;
    /* and its own engine note */
    if(typeof setEngineVoice==='function') setEngineVoice(i);""")

# =====================================================================
# 2. what the road sounds like
# =====================================================================
sub("""var TOPS=[9,17,25,33,44];""",
r"""/* ---- what each surface sounds like ----
   Parallel to SURF. `f` and `Q` colour the hiss, `g` sets its level, `lo` is
   how much of it is low rumble instead, and `loose` is how readily it throws
   stones at the arches. See src/audio.py. */
var SURF_SND=[
  /* 0 hard sand */ {f:1500,Q:0.80,g:0.055,lo:0.10,loose:0.30},
  /* 1 deep sand */ {f:1050,Q:0.55,g:0.085,lo:0.42,loose:0.10},
  /* 2 rock      */ {f:2700,Q:1.10,g:0.050,lo:0.16,loose:0.55},
  /* 3 riverbed  */ {f:2200,Q:0.90,g:0.034,lo:0.08,loose:0.18},
  /* 4 asphalt   */ {f:3300,Q:0.70,g:0.030,lo:0.05,loose:0.00},
  /* 5 pan       */ {f:2000,Q:0.80,g:0.030,lo:0.06,loose:0.04},
  /* 6 sidewalk  */ {f:2800,Q:0.80,g:0.036,lo:0.06,loose:0.08},
  /* 7 grass     */ {f:1800,Q:0.50,g:0.052,lo:0.22,loose:0.14},
  /* 8 granite   */ {f:3000,Q:1.20,g:0.040,lo:0.10,loose:0.26},
  /* 9 muskeg    */ {f:700, Q:0.50,g:0.072,lo:0.60,loose:0.03},
  /* 10 gravel   */ {f:2400,Q:0.70,g:0.072,lo:0.20,loose:1.00},
  /* 11 water    */ {f:900, Q:0.40,g:0.092,lo:0.55,loose:0.26}
];

/* A BUDGET, and it is not only belt and braces. Every sound below schedules
   its own node and lets it die, which is fine at sixty frames a second and
   not fine when the frame rate hitches: four corners, both thresholds, a few
   skipped frames, and a hundred nodes land on the compressor inside a
   millisecond. The headless harness reaches that state by design, because it
   runs ten seconds of simulation inside a fraction of a real one, and it put
   a constant minus eight on the master with the compressor pinned at minus
   155 dB. The game cannot get there on its own, but a slow phone could get
   closer than it should, so nothing new starts above two dozen live voices. */
function voice(){
  if(!A) return false;
  if((A.voices||0)>=24) return false;
  A.voices=(A.voices||0)+1;
  return true;
}
function voiceDone(src,when){
  if(!A) return;
  var ms=Math.max(0,(when-A.ctx.currentTime))*1000+60;
  setTimeout(function(){ A.voices=Math.max(0,(A.voices||1)-1); }, ms);
}

/* a short click, for a stone off the arch or a twig under a wheel */
function tick(vol,freq,Q,dur){
  if(!voice()) return;
  var t=A.ctx.currentTime;
  var src=A.ctx.createBufferSource(); src.buffer=A.buf;
  src.playbackRate.value=0.7+Math.random()*0.9;
  var f=A.ctx.createBiquadFilter(); f.type='bandpass';
  f.frequency.value=freq; f.Q.value=Q||3.0;
  var g=A.ctx.createGain();
  g.gain.setValueAtTime(0.0001,t);
  g.gain.exponentialRampToValueAtTime(vol,t+0.002);
  g.gain.exponentialRampToValueAtTime(0.0004,t+(dur||0.035));
  src.connect(f); f.connect(g); g.connect(A.comp);
  src.start(t); src.stop(t+(dur||0.035)+0.02); voiceDone(src,t+(dur||0.035));
}

/* a swept noise burst, for brush and for water */
function swish(vol,f0,f1,dur,Q){
  if(!voice()) return;
  var t=A.ctx.currentTime;
  var src=A.ctx.createBufferSource(); src.buffer=A.buf;
  src.playbackRate.value=0.85+Math.random()*0.4;
  var f=A.ctx.createBiquadFilter(); f.type='bandpass'; f.Q.value=Q||0.9;
  f.frequency.setValueAtTime(f0,t);
  f.frequency.exponentialRampToValueAtTime(Math.max(60,f1),t+dur);
  var g=A.ctx.createGain();
  g.gain.setValueAtTime(0.0001,t);
  g.gain.exponentialRampToValueAtTime(vol,t+dur*0.22);
  g.gain.exponentialRampToValueAtTime(0.0005,t+dur);
  src.connect(f); f.connect(g); g.connect(A.comp);
  src.start(t); src.stop(t+dur+0.03); voiceDone(src,t+dur);
}

/* a damper event: low body for bump, brighter and shorter for rebound */
function thud(vol,freq,dur,ring){
  if(!voice()) return;
  var t=A.ctx.currentTime;
  var src=A.ctx.createBufferSource(); src.buffer=A.buf;
  var f=A.ctx.createBiquadFilter(); f.type='lowpass';
  f.frequency.value=freq; f.Q.value=1.6;
  var g=A.ctx.createGain();
  g.gain.setValueAtTime(0.0001,t);
  g.gain.exponentialRampToValueAtTime(vol,t+0.004);
  g.gain.exponentialRampToValueAtTime(0.0005,t+dur);
  src.connect(f); f.connect(g); g.connect(A.comp);
  src.start(t); src.stop(t+dur+0.03); voiceDone(src,t+dur);
  if(ring){
    /* the metal the damper is bolted to */
    var o=A.ctx.createOscillator(), og=A.ctx.createGain();
    o.type='triangle'; o.frequency.value=ring*(0.92+Math.random()*0.16);
    og.gain.setValueAtTime(vol*0.26,t);
    og.gain.exponentialRampToValueAtTime(0.0004,t+dur*1.5);
    o.connect(og); og.connect(A.comp); o.start(t); o.stop(t+dur*1.6);
  }
}

var TOPS=[9,17,25,33,44];""")

# =====================================================================
# 3. the tick: surfaces, dampers, brush, place
# =====================================================================
# `c2.surf` holds the SURF ENTRY, not its index, so `surf|0` was 0 for every
# wheel and the Shield sounded like hard sand. Keep the index alongside it.
sub("""    var sf=SURF[surfaceAt(c2.cp.x,c2.cp.z,1-Math.abs(c2.nrm.y))];
    var kS=Math.min(1,dt*5.0);
    c2.surf=sf;""",
"""    var sfI=surfaceAt(c2.cp.x,c2.cp.z,1-Math.abs(c2.nrm.y));
    var sf=SURF[sfI];
    var kS=Math.min(1,dt*5.0);
    c2.surf=sf; c2.surfI=sfI;      /* the entry for the solver, the index for the sound */""")

sub("""  var onGround=S.grounded>0;
  A.sand.g.gain.setTargetAtTime(onGround?Math.min(0.055,speed*0.0032):0,t,0.09);

  var slip=0;
  for(var i=0;i<4;i++) if(corners[i].contact) slip+=Math.abs(corners[i].alphaF)+corners[i].slip*0.06;
  A.scrub.g.gain.setTargetAtTime(Math.min(0.14,slip*0.085),t,0.05);
  A.scrub.f.frequency.setTargetAtTime(1300+Math.min(1400,slip*900),t,0.08);

  A.rattle.g.gain.setTargetAtTime(Math.min(0.075,S.susAct*2.6),t,0.05);
}""",
r"""  var onGround=S.grounded>0;

  /* ---- the surface under the wheels ----
     The loudest vote wins, which in practice means the pair of wheels that
     are actually on the thing you are driving across. */
  var votes=[0,0,0,0,0,0,0,0,0,0,0,0], best=0, bestN=-1, i;
  for(i=0;i<4;i++) if(corners[i].contact){
    var sv=corners[i].surfI|0; if(sv<0||sv>11) sv=0;
    votes[sv]++; if(votes[sv]>bestN){ bestN=votes[sv]; best=sv; }
  }
  var SP=SURF_SND[best]||SURF_SND[0];
  A.dbg.surf=best;
  var snowy=(typeof FLORA!=='undefined' && FLORA.snow);
  var roll=onGround? Math.min(1, speed/22) : 0;
  var hiss=SP.g*roll*(snowy?0.45:1);
  A.sand.g.gain.setTargetAtTime(hiss*(1-SP.lo),t,0.12);
  A.sand.f.frequency.setTargetAtTime(SP.f*(snowy?0.55:1)*(0.75+roll*0.45),t,0.14);
  A.sand.f.Q.setTargetAtTime(SP.Q,t,0.2);
  A.roll.g.gain.setTargetAtTime(hiss*SP.lo*1.6,t,0.12);
  A.roll.f.frequency.setTargetAtTime(170+speed*7,t,0.15);
  /* snow packs rather than hisses, so it squeaks instead */
  A.squeak.g.gain.setTargetAtTime(snowy? Math.min(0.030, roll*0.034):0, t, 0.16);
  A.squeak.f.frequency.setTargetAtTime(1900+speed*26,t,0.18);

  /* stones off the arches, at a rate the surface sets */
  if(onGround && !snowy && SP.loose>0.02 && speed>4){
    A.stone-=dt;
    if(A.stone<=0){
      tick(0.016+Math.random()*0.030*SP.loose, 1200+Math.random()*2400, 4.0, 0.030);
      A.dbg.stone++;
      A.stone=0.055+Math.random()*0.42/(SP.loose*Math.min(1,speed/13)+0.08);
    }
  }

  var slip=0;
  for(i=0;i<4;i++) if(corners[i].contact) slip+=Math.abs(corners[i].alphaF)+corners[i].slip*0.06;
  A.scrub.g.gain.setTargetAtTime(Math.min(0.14,slip*0.085)*(snowy?0.5:1),t,0.05);
  /* a slide sounds different on gravel than on tarmac */
  A.scrub.f.frequency.setTargetAtTime(SP.f*0.62+Math.min(1400,slip*900),t,0.08);

  A.rattle.g.gain.setTargetAtTime(Math.min(0.075,S.susAct*2.6),t,0.05);

  /* ---- dampers ----
     Each corner on its own. The average that drives the rattle above cannot
     tell a landing from a washboard, and the whole point of a damper sound is
     that it arrives on the event. */
  for(i=0;i<4;i++){
    var c=corners[i];
    if(c.aLen===undefined){ c.aLen=c.len; c.aCool=0; c.aBott=false; continue; }
    var dv=(c.aLen-c.len)/Math.max(0.002,dt);     /* positive into bump */
    c.aLen=c.len;
    c.aCool=Math.max(0,(c.aCool||0)-dt);
    /* bottomed out: the sound that tells you the landing was too big */
    var bott=(c.contact && c.len<=SUS_MIN+0.012);
    if(bott && !c.aBott && dv>0.6){
      thud(Math.min(0.42,0.13+dv*0.055), 170, 0.16, 118);
      A.dbg.bottom++; c.aCool=0.11;
    }
    c.aBott=bott;
    if(c.aCool>0) continue;
    if(dv>1.5){                                    /* into bump */
      thud(Math.min(0.22,(dv-1.5)*0.045), 240, 0.085, 0);
      A.dbg.bump++; c.aCool=0.07;
    }else if(dv<-1.9){                             /* and back out again */
      tick(Math.min(0.10,(-dv-1.9)*0.022), 620+Math.random()*520, 5.0, 0.055);
      A.dbg.rebound++; c.aCool=0.09;
    }
  }

  /* ---- brush ----
     updateFlora keeps what is within 40 m; narrow that to 14 m a few times a
     second and the per frame test is against a handful. */
  if(typeof FLORA!=='undefined' && FLORA.near){
    A.brushT-=dt;
    if(A.brushT<=0){
      A.brushT=0.22;
      var nr=FLORA.near, keep=[];
      for(var q=0;q<nr.length;q++){
        var dx=nr[q].x-S.p.x, dz=nr[q].z-S.p.z;
        if(dx*dx+dz*dz<196) keep.push(nr[q]);
      }
      A.brush=keep;
    }
    A.brushCool=Math.max(0,A.brushCool-dt);
    if(A.brush && A.brushCool<=0 && speed>2.5){
      var reach=1.5+speed*0.03;
      for(var b=0;b<A.brush.length;b++){
        var e=A.brush[b], ex=e.x-S.p.x, ez=e.z-S.p.z;
        if(ex*ex+ez*ez>reach*reach) continue;
        var hard=Math.min(1,speed/18);
        if(e.h<0.8)      swish(0.030+hard*0.040, 3400, 1500, 0.13, 0.7);  /* grass */
        else if(e.h<2.2) swish(0.045+hard*0.060, 2600, 900,  0.20, 0.6);  /* shrub */
        else             swish(0.055+hard*0.075, 1700, 520,  0.26, 0.5);  /* sapling */
        A.dbg.brush++;
        A.brushCool=0.09+Math.random()*0.10;
        break;
      }
    }
  }

  /* ---- the place itself ----
     Quiet, and never the same two beds on two maps. */
  var night=(typeof TOD!=='undefined'? (TOD.night||0) : 0);
  if(MAP===1){
    A.amb.f.frequency.setTargetAtTime(150,t,0.5);
    A.amb.g.gain.setTargetAtTime(0.013*(1-night*0.45),t,0.8);
    A.amb2.f.frequency.setTargetAtTime(1800,t,0.5);
    A.amb2.g.gain.setTargetAtTime(0.004,t,0.8);
  }else if(MAP===2){
    /* wind through trees, louder where there are more of them */
    var trees=(FLORA.near? Math.min(1,FLORA.near.length/260):0);
    A.amb.f.frequency.setTargetAtTime(520+trees*260,t,0.6);
    A.amb.g.gain.setTargetAtTime(0.008+trees*0.014,t,0.9);
    A.amb2.g.gain.setTargetAtTime(night*0.006,t,1.2);     /* night insects */
    A.amb2.f.frequency.setTargetAtTime(4200,t,0.6);
    A.call-=dt;
    if(A.call<=0){
      A.call=9+Math.random()*22;
      /* a loon, at the two ends of the day */
      if(night>0.12 && night<0.92 && A.ctx){
        var o=A.ctx.createOscillator(), g2=A.ctx.createGain();
        o.type='sine';
        o.frequency.setValueAtTime(430,t);
        o.frequency.exponentialRampToValueAtTime(880,t+0.42);
        o.frequency.exponentialRampToValueAtTime(610,t+1.25);
        g2.gain.setValueAtTime(0.0001,t);
        g2.gain.exponentialRampToValueAtTime(0.028,t+0.14);
        g2.gain.setValueAtTime(0.028,t+0.90);
        g2.gain.exponentialRampToValueAtTime(0.0004,t+1.40);
        o.connect(g2); g2.connect(A.comp); o.start(t); o.stop(t+1.45);
      }
    }
  }else{
    /* thin dry wind, and cicadas in the heat */
    A.amb.f.frequency.setTargetAtTime(380,t,0.6);
    A.amb.g.gain.setTargetAtTime(0.009,t,0.9);
    var heat=Math.max(0,1-night*1.8);
    A.amb2.f.frequency.setTargetAtTime(5200,t,0.6);
    A.amb2.g.gain.setTargetAtTime(heat*0.007*(0.7+0.3*Math.sin(t*7.3)),t,0.35);
  }
}""")

# =====================================================================
# 4. flora keeps a near list for the brush
# =====================================================================
sub("""var FLORA={group:null, meshes:[], at:null, map:-1, snow:false};""",
"""var FLORA={group:null, meshes:[], at:null, map:-1, snow:false,
           list:null, size:null, near:null};""")

sub("""        mapGroup(i).add(grp);
        FLORA.group=grp;
        FLORA.at=null;
        updateFlora(true);""",
"""        /* the raw placements and how tall each variant is, so the sound tick
           can tell grass from a sapling without walking the meshes */
        FLORA.list=list;
        FLORA.size={};
        for(var sv in man){
          var ss=man[sv].size_m_xyz_blender||[0,0,0];
          FLORA.size[sv]=ss[2]||0;
        }
        mapGroup(i).add(grp);
        FLORA.group=grp;
        FLORA.at=null;
        updateFlora(true);""")

sub("""  FLORA.at={x:px, z:pz, fx:fx, fz:fz};
  updateCity(px, pz, fx, fz);""",
"""  FLORA.at={x:px, z:pz, fx:fx, fz:fz};
  updateCity(px, pz, fx, fz);
  /* and the short list the sound tick brushes against. Only the small stuff:
     a boulder is a collision, not a swish. */
  if(FLORA.list){
    var near=[], L=FLORA.list;
    for(var q2=0;q2<L.length;q2++){
      var e2=L[q2], ax=e2.x-px, az=e2.z-pz;
      if(ax*ax+az*az>1600) continue;
      var hh=(FLORA.size[e2.model]||0)*(e2.s||1);
      if(hh>3.2) continue;
      near.push({x:e2.x, z:e2.z, h:hh});
    }
    FLORA.near=near;
  }else FLORA.near=null;""")

sub("""function clearFlora(){
  if(FLORA.group && FLORA.group.parent) FLORA.group.parent.remove(FLORA.group);
  FLORA.group=null; FLORA.meshes=[]; FLORA.at=null; FLORA.map=-1;
}""",
"""function clearFlora(){
  if(FLORA.group && FLORA.group.parent) FLORA.group.parent.remove(FLORA.group);
  FLORA.group=null; FLORA.meshes=[]; FLORA.at=null; FLORA.map=-1;
  FLORA.list=null; FLORA.size=null; FLORA.near=null;
}""")

# the harness needs to see the flora near list too
sub("""    deckAt:deckAt,envHeight:envHeight,surfaceAt:surfaceAt,""",
"""    deckAt:deckAt,envHeight:envHeight,surfaceAt:surfaceAt,FLORA:FLORA,SURF:SURF,""")

# =====================================================================
# 5. two things the harness exposed
# =====================================================================
# The headless tick ran the per frame layer but not updateFlora, so the brush
# list the sound reads was whatever the real frame loop had last left behind.
# A harness that does not run the code it is testing is worse than no harness.
sub("""        if(window.__fa>=1/60){ sync(1/60); updateLightPool(); updateCam(1/60); revs(1/60); hud(1/60); popStep(1/60); audioTick(1/60); window.__fa-=1/60; }""",
"""        if(window.__fa>=1/60){ sync(1/60); updateLightPool(); updateCam(1/60);
          if(typeof updateFlora==='function') updateFlora(false);
          revs(1/60); hud(1/60); popStep(1/60); audioTick(1/60); window.__fa-=1/60; }""")

# And in the air no wheel votes, so `best` fell back to index 0 and the filter
# jumped to hard sand on the way down. The gain is zero while airborne so it
# was never heard, but it snapped audibly on landing. Hold the last surface.
sub("""  var votes=[0,0,0,0,0,0,0,0,0,0,0,0], best=0, bestN=-1, i;""",
"""  var votes=[0,0,0,0,0,0,0,0,0,0,0,0], best=(A.dbg.surf>=0?A.dbg.surf:0), bestN=-1, i;""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
