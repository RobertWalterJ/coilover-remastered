# -*- coding: utf-8 -*-
"""Parts you fit to a truck, so the Bracken can become the fast one.

ROBERT'S ACTUAL COMPLAINT, which is the brief: the first jeep is still his
favourite and it is "waay too slow. fine at the start of the game, but let's
make it super fun." So the Bracken's numbers do not move at all at level
zero. What changes is that there is now somewhere for the money to go.

WHERE THE MONEY COMES FROM, without breaking what is already there. Career
points gate the other vehicles and the other maps, and `have()` reads
`PROG.career` directly. If parts were paid for out of that number, buying a
set of tyres would take the Veloce away again, which is absurd. So career
stays the LIFETIME total and never falls, and a second number tracks what has
been spent. The fund is the difference. The same points therefore do two jobs,
proving you got there and buying the parts, and neither interferes with the
other.

FOUR PARTS, THREE LEVELS, PER VEHICLE. Fitted parts are stored per vehicle id,
so building up the Bracken does nothing for the Serrano, and the choice of
which truck to pour it into is the actual decision.

    Engine       drive x1.20 a level           pulls harder, keeps pulling
    Gearbox      vmax x1.09, drag x0.92        longer legs down a straight
    Suspension   travel, spring and damping    soaks up landings
    Tyres        grip x1.055 a level           holds on longer

A fully built Bracken, against the showroom car and against the Veloce:

                  stock Bracken   built Bracken   stock Veloce
    drive              22,000          38,000         52,000
    drag (cd)            0.44           0.343           0.20
    grip              1.00/0.92       1.17/1.08      1.16/1.20
    travel (m)           0.69            0.90           0.64

    0 to 100 km/h         5.8 s           3.8 s
    top in 16 s           104             153            160

which is the shape of the thing. A built Bracken runs with the Veloce and
still has 0.9 m of travel and four driven wheels, so it is the better car
everywhere that is not a straight line. It costs 90,000 in parts to get
there, against 78,000 to unlock the Veloce outright, so it is the more
expensive road and it should be: you asked for it by name.

AND ONE SAFEGUARD, LEARNED THE HARD WAY. Torque is not free. The Veloce was
undriveable at 52 kN because the friction ellipse scales longitudinal and
lateral force down together, so a saturated tyre has no grip left to steer
with; it needed traction control before it was usable at all. 36 kN in a
1,400 kg truck is well under that, but an upgraded engine now also raises a
traction control floor, so the last engine part can never be the thing that
ruins a car someone has spent twenty thousand points on.

HOW IT IS SHOWN. The garage already draws comparison bars straight off the
spec, so the bars are now drawn off the UPGRADED spec and move the moment a
part goes on. Each part is a row with its name, three pips, one plain line
saying what it does, and a price. No percentages, no progress bars, no
countdown: pips are a count of things fitted, which is a different animal.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------------------------------- styles
sub("""  .gnav{display:flex;align-items:center;gap:10px;margin-bottom:2px}""",
"""  .fund{display:flex;align-items:baseline;gap:8px;font-weight:600;font-size:10px;
        text-transform:uppercase;letter-spacing:.14em;color:var(--mute);margin:2px 0 9px}
  .fund b{font-size:15px;letter-spacing:0;color:var(--cream);font-weight:700}
  .parts{display:flex;flex-direction:column;gap:7px;margin:0 0 12px}
  .part{display:flex;align-items:center;gap:10px}
  .part .pn{flex:1;min-width:0}
  .part .pt{display:flex;align-items:center;gap:7px;font-weight:600;font-size:10px;
            text-transform:uppercase;letter-spacing:.14em;color:var(--cream)}
  .part .pips{display:flex;gap:3px}
  .part .pips u{width:12px;height:5px;border-radius:2px;background:#2c2233;display:block}
  .part .pips u.on{background:var(--amber)}
  .part .pd{font-size:11px;color:var(--mute);line-height:1.3;margin-top:3px}
  .part .pbuy{flex:0 0 96px;margin-top:0;padding:9px 0;font-size:11px;letter-spacing:.06em}
  .part .pbuy.max{opacity:.55}
  .part .pbuy.short{color:var(--mute)}
  .gnav{display:flex;align-items:center;gap:10px;margin-bottom:2px}""")

# --------------------------------------------------------------------- markup
sub("""    <div class="gnav">
      <button class="go ghost gprev" id="g-prev" aria-label="Previous vehicle">&lt;</button>""",
"""    <div class="fund">Parts fund <b id="g-fund">0</b></div>
    <div class="parts" id="g-parts"></div>
    <div class="gnav">
      <button class="go ghost gprev" id="g-prev" aria-label="Previous vehicle">&lt;</button>""")

# ------------------------------------------------------------------ the parts
sub("""function priceOf(o){ return o.unlock||0; }""",
r"""function priceOf(o){ return o.unlock||0; }

/* ---- parts ----
   Four of them, three levels each, fitted per vehicle. See src/upgrades.py
   for why these multipliers and not others. */
var PARTS=[
  {k:'eng',  name:'Engine',     why:'Pulls harder, and keeps pulling'},
  {k:'box',  name:'Gearbox',    why:'Longer legs down a straight'},
  {k:'sus',  name:'Suspension', why:'Soaks up landings instead of bouncing'},
  {k:'tyre', name:'Tyres',      why:'Holds on longer before it lets go'}
];
var PART_PRICE=[2500, 6000, 14000];
function upLevels(id){
  var u=PROG.up[id];
  if(!u){ u=PROG.up[id]={eng:0,box:0,sus:0,tyre:0}; }
  return u;
}
function upPrice(lvl){ return PART_PRICE[lvl]||0; }
function bank(){ return Math.max(0, PROG.career-(PROG.spent||0)); }

/* The spec the solver and the garage both read. One function, so a bar can
   never disagree with the car it is describing. */
function upSpec(i){
  var base=VEHICLES[i], V={}, kk;
  for(kk in base) V[kk]=base[kk];
  var u=upLevels(base.id);

  if(u.eng){
    V.drive=base.drive*Math.pow(1.20,u.eng);
    /* Torque is not free: the friction ellipse takes lateral grip away from a
       saturated tyre, which is what made the Veloce undriveable at 52 kN. An
       upgraded engine raises a traction control floor so the last part fitted
       can never be the one that ruins the car. */
    if(u.eng>=2) V.tc=Math.max(base.tc||0, 0.95);
  }
  if(u.box){
    V.vmax=(base.vmax||52)*Math.pow(1.09,u.box);
    /* Top speed here is drag limited long before it is gearing limited, so
       the part that matters is the drag, not the ratio. Measured: raising
       vmax alone moved the Bracken's terminal speed by almost nothing. */
    V.cd=(base.cd===undefined?0.357:base.cd)*Math.pow(0.92,u.box);
  }
  if(u.sus){
    V.susMax=base.susMax+0.07*u.sus;
    V.k=base.k*Math.pow(1.05,u.sus);
    V.dBump=base.dBump*Math.pow(1.07,u.sus);
    V.dReb=base.dReb*Math.pow(1.07,u.sus);
  }
  if(u.tyre){
    V.muF=base.muF*Math.pow(1.055,u.tyre);
    V.muR=base.muR*Math.pow(1.055,u.tyre);
    V.brake=base.brake*Math.pow(1.04,u.tyre);
    V.tyreW=base.tyreW+0.03*u.tyre;        /* and they look the part */
  }
  return V;
}

function fitPart(k){
  var V=VEHICLES[VEH], u=upLevels(V.id), lvl=u[k]||0;
  if(lvl>=3) return;
  var price=upPrice(lvl);
  if(bank()<price){
    popHold('Parts fund short', commas(price-bank())+' points to go', 2);
    return;
  }
  u[k]=lvl+1;
  PROG.spent=(PROG.spent||0)+price;
  saveProg();
  var P=null;
  for(var q=0;q<PARTS.length;q++) if(PARTS[q].k===k) P=PARTS[q];
  popHold((P?P.name:'Part')+' fitted', V.name, 2);
  pickVehicle(VEH);          /* rebuild the car, resettle it, redraw the card */
}""")

# ---------------------------------------------------------- the solver reads it
sub("""    var V=VEHICLES[i]; VEH=i;""",
"""    /* the upgraded spec, not the showroom one */
    var V=(typeof upSpec==='function')? upSpec(i) : VEHICLES[i];
    VEH=i;""")

# ------------------------------------------------------------------- the card
sub("""function garageCard(){
  var V=VEHICLES[VEH];""",
"""function garageCard(){
  var V=upSpec(VEH);""")

sub("""  document.getElementById('g-dots').innerHTML=d;""",
r"""  document.getElementById('g-dots').innerHTML=d;

  /* the parts, drawn from the same levels the spec above was built from */
  var fd=document.getElementById('g-fund');
  if(fd) fd.textContent=commas(bank());
  var fw=document.querySelector('#garage .fund');
  var pe=document.getElementById('g-parts');
  /* no fitting parts to a truck you do not own yet */
  var owned=have(VEHICLES[VEH]);
  if(fw) fw.hidden=!owned;
  if(pe) pe.hidden=!owned;
  if(pe && owned){
    var u=upLevels(VEHICLES[VEH].id), h='';
    for(var pi=0;pi<PARTS.length;pi++){
      var P=PARTS[pi], lv=u[P.k]||0, pips='';
      for(var z=0;z<3;z++) pips+='<u class="'+(z<lv?'on':'')+'"></u>';
      var btn;
      if(lv>=3) btn='<button class="go ghost pbuy max" disabled>Fitted</button>';
      else{
        var pr=upPrice(lv), can=bank()>=pr;
        btn='<button class="go ghost pbuy'+(can?'':' short')+'" data-part="'+P.k+'">'+
            commas(pr)+'</button>';
      }
      h+='<div class="part"><div class="pn"><div class="pt">'+P.name+
         '<span class="pips">'+pips+'</span></div><div class="pd">'+P.why+
         '</div></div>'+btn+'</div>';
    }
    pe.innerHTML=h;
  }""")

# one delegated handler, bound once
sub("""document.getElementById('b-garage').addEventListener('click',openGarage);""",
"""document.getElementById('g-parts').addEventListener('click',function(ev){
  var b=ev.target.closest? ev.target.closest('.pbuy') : null;
  if(b && b.getAttribute('data-part')) fitPart(b.getAttribute('data-part'));
});
document.getElementById('b-garage').addEventListener('click',openGarage);""")

# ------------------------------------------------------------- saved and loaded
sub("""var PROG={ odo:0, air:0, gates:0, found:{}, jump:[0,0,0], jumpAt:[null,null,null],""",
"""var PROG={ up:{}, spent:0,
           odo:0, air:0, gates:0, found:{}, jump:[0,0,0], jumpAt:[null,null,null],""")

sub("""    PROG.feat=o.feat||{};""",
"""    PROG.feat=o.feat||{};
    PROG.up=o.up||{};
    PROG.spent=o.spent||0;""")

sub("""      feat:PROG.feat}));""",
"""      feat:PROG.feat, up:PROG.up, spent:PROG.spent}));""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
