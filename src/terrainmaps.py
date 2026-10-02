# -*- coding: utf-8 -*-
"""Work order step 7: the ground takes its colour from the painted maps.

WHAT CHANGES. The terrain's colour and its texture blend came from rules
evaluated per face: lerp by height, lerp by slope, lerp by a lake mask. Those
rules were written looking at the result, and they are coarse, because a rule
cannot know that this particular hollow holds a pond and that one does not.

The pack ships `colour_1m.png` and `surf_1m.png` per map, 561 by 561 at one
metre a sample, painted from the same height functions the physics reads. So
the ground can simply be looked up:

  colour_1m.png   RGB, the ground colour, sRGB
  surf_1m.png     R = playa or lakebed, G = bare rock, B = road or gravel

R and G go straight into the two blend weights the shader already has
(`surfW`), which choose between the playa and rock photographs. B has no slot
yet: a third grain would need a third sampler, and the grain pack does ship
`gravel_track_128.png` for exactly that, so it is noted rather than dropped.

WHAT DOES NOT CHANGE, deliberately. The per face value step stays. That is the
quarter-stop brightness jitter that makes one facet differ from the one beside
it, and it is what gives the posterised lighting something to terrace. Pulling
colour from a smooth map without it would flatten the whole landscape into one
even wash, which is the opposite of the look.

LOADING. Images are asynchronous and `buildTerrain` is not, so the maps load
behind the title screen like the models, and the terrain is rebuilt once when
they arrive. If they never arrive, the rules still run and the game is the
game.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------------------------- the lookup
sub("/* ================= assets =================",
r"""/* ---- step 7: the painted ground ----
   561 by 561 at one metre a sample over a 560 m world, painted from the same
   height functions the physics reads, so what is drawn and what is felt agree
   by construction rather than by two sets of rules happening to match. */
var TMAP={};
var TMAP_FILE={0:'desert', 1:'city', 2:'shield'};
function loadTerrainMaps(i, done){
  var id=TMAP_FILE[i];
  if(!id || TMAP[i]) { done && done(); return; }
  TMAP[i]='loading';
  var got=0, out={};
  ['colour','surf'].forEach(function(which){
    var im=new Image();
    im.onload=function(){
      var cv=document.createElement('canvas');
      cv.width=im.width; cv.height=im.height;
      var cx=cv.getContext('2d');
      cx.drawImage(im,0,0);
      out[which]=cx.getImageData(0,0,im.width,im.height);
      out.n=im.width;
      if(++got===2){ TMAP[i]=out; done && done(); }
    };
    im.onerror=function(){ if(++got===2){ TMAP[i]=(out.colour||out.surf)? out : null; done && done(); } };
    im.src='assets/terrain/'+id+'/'+which+'_1m.png';
  });
}
/* world metres to a sample, clamped at the edges */
function tmapAt(T, x, z){
  var n=T.n, half=n*0.5;
  var cx=Math.round(x+half), cy=Math.round(z+half);
  if(cx<0) cx=0; else if(cx>=n) cx=n-1;
  if(cy<0) cy=0; else if(cy>=n) cy=n-1;
  return (cy*n+cx)*4;
}

/* ================= assets =================""")

# ------------------------------------------------------- colour from the map
sub("""    }else{
    c.copy(cLow).lerp(cMid, sstep(-11,-2,my));
    c.lerp(cHigh, sstep(1,13,my));
    c.lerp(cPlaya, lakeMask(mx,mz));
    c.lerp(cRock, sstep(0.15,0.40,slope));
    }""",
"""    }else{
    c.copy(cLow).lerp(cMid, sstep(-11,-2,my));
    c.lerp(cHigh, sstep(1,13,my));
    c.lerp(cPlaya, lakeMask(mx,mz));
    c.lerp(cRock, sstep(0.15,0.40,slope));
    }
    /* The painted map wins where there is one. It was made from these same
       height functions, so it agrees with the ground by construction instead
       of by two sets of rules happening to land in the same place. */
    if(TM && TM.colour){
      var ci=tmapAt(TM,mx,mz), cd=TM.colour.data;
      c.setRGB(cd[ci]/255, cd[ci+1]/255, cd[ci+2]/255).convertSRGBToLinear();
    }""")

# ------------------------------------------------- and the blend weights
sub("""    var lkw=(MAP===1?panMask(mx,mz):(MAP===2?(1-sstep(0.94,1.06,shLakeD(mx,mz))):lakeMask(mx,mz)));
    var rkw=(MAP===1? sstep(BUILD,BUILD+1.3,streetD(mx,mz))
           : (MAP===2? Math.max(sstep(0.18,0.44,slope), sstep(0.32,0.68,shDome(mx,mz)))
           : sstep(0.16,0.44,slope)));""",
"""    var lkw, rkw;
    if(TM && TM.surf){
      /* R playa or lakebed, G bare rock. B is road or gravel and has no
         sampler yet; grain/gravel_track_128.png is the one it wants. */
      var si=tmapAt(TM,mx,mz), sd=TM.surf.data;
      lkw=sd[si]/255; rkw=sd[si+1]/255;
    }else{
      lkw=(MAP===1?panMask(mx,mz):(MAP===2?(1-sstep(0.94,1.06,shLakeD(mx,mz))):lakeMask(mx,mz)));
      rkw=(MAP===1? sstep(BUILD,BUILD+1.3,streetD(mx,mz))
         : (MAP===2? Math.max(sstep(0.18,0.44,slope), sstep(0.32,0.68,shDome(mx,mz)))
         : sstep(0.16,0.44,slope)));
    }""")

# the face loop needs the map for this world in scope
sub("""  var cLow=sc(PAL.low), cMid=sc(PAL.mid), cHigh=sc(PAL.high),
      cRock=sc(PAL.rock), cPlaya=sc(PAL.playa);""",
"""  var cLow=sc(PAL.low), cMid=sc(PAL.mid), cHigh=sc(PAL.high),
      cRock=sc(PAL.rock), cPlaya=sc(PAL.playa);
  var TM=(TMAP[MAP] && TMAP[MAP]!=='loading')? TMAP[MAP] : null;""")

# ------------------------------------------------- load them, then rebuild
sub("""    if(typeof addRoads==='function') addRoads(MAP);""",
"""    if(typeof addRoads==='function') addRoads(MAP);
    /* the painted ground, then one rebuild to use it */
    loadTerrainMaps(MAP, function(){ buildTerrain(); });""")

sub("""  if(typeof addRoads==='function') addRoads(i);""",
"""  if(typeof addRoads==='function') addRoads(i);
  loadTerrainMaps(i, function(){ buildTerrain(); });""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
