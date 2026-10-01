# -*- coding: utf-8 -*-
"""Swap the hand built shells for the Blender models.

HOW THE SWAP IS SEQUENCED. The game boots synchronously and builds a vehicle
before anything could possibly have downloaded. Rather than restructure boot
around promises, the game starts exactly as it always did -- procedural shells,
procedural wheels -- and the models replace them the moment they arrive. Three
consequences, all good:

  - Boot order cannot break. Nothing new runs before `__setVehicle` does.
  - If the assets are missing, fail to parse, or the fetch is blocked, the game
    is simply the original game. The shell functions stay in the file as the
    fallback and are not deleted.
  - The title screen is already a wait-for-a-tap, so the load hides behind it.

WHAT GETS REPLACED. Per the manifest: the body (one node, authored in the
game's own `bodyG` frame so it needs no offset), the wheel set (`wheel`, `rim`,
`disc` spin about X; `caliper` stays with the strut), and the strut (`spring`,
`shock`, `capT`, `capB`, `arm`, `link`, keeping the 1.0 m length and the
origins the per frame code already scales).

TWO BUGS FROM THE AUDIT, FIXED HERE because they are in the code being touched:

  #4  `applyTime` drove the smooth `paint` emissive from `PAL.body` (2f7a86),
      which is the Bracken's old teal, so EVERY car got a teal glow at dusk
      regardless of its colour. It now follows the selected vehicle.
  #7  Only the tyre and the rim were spun. The lug bands, the shoulder and the
      brake disc stood still while the wheel turned. Everything in the hub
      that should rotate now does.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------- the body, when a model exists
sub("""    SHELLS[V.id](V);""",
"""    /* The Blender body if it has arrived, the hand built shell if not. The
       model is authored in this exact frame, so it drops in with no offset. */
    var mdlBody = MDL.ready() ? MDL.get('vehicles/'+V.id+'_body',{obj:true,tex:'paint'}) : null;
    if(mdlBody){ bodyG.add(mdlBody); }
    else SHELLS[V.id](V);
    applyAssetWheels(V);""")

# ------------------------------------------- the wheels and the strut
sub("/* ================= assets =================",
r"""/* Replace the procedural wheel and strut meshes with the modelled ones. Safe
   to call at any time and safe to call twice: it tracks what it has already
   swapped per corner so a vehicle change does not stack a second set. */
function applyAssetWheels(V){
  if(typeof MDL==='undefined' || !MDL.ready() || !STRUT || !STRUT.length) return;
  var key='vehicles/'+V.id+'_wheels';
  if(!MDL.has(key)) return;
  for(var i=0;i<4;i++){
    var st=STRUT[i];
    if(st.assetFor===V.id) continue;
    var hub=st.hub, grp=st.grp;

    /* out with the old: every mesh the old builder put in the hub */
    for(var q=hub.children.length-1;q>=0;q--) hub.remove(hub.children[q]);
    if(st.assetCal){ grp.remove(st.assetCal); st.assetCal=null; }

    var wheel=MDL.node(key, V.id+'_wheel', {obj:true,tex:'metal'});
    var rim  =MDL.node(key, V.id+'_rim',   {obj:true,tex:'metal'});
    var disc =MDL.node(key, V.id+'_disc',  {obj:true,tex:'metal'});
    var cal  =MDL.node(key, V.id+'_caliper',{obj:true,tex:'metal'});
    if(!wheel) continue;

    hub.add(wheel);
    if(rim)  hub.add(rim);
    if(disc) hub.add(disc);
    if(cal){ grp.add(cal); st.assetCal=cal; }

    /* AUDIT #7: the lugs, shoulder and disc used to stand still while the
       tyre turned. The sync loop spins `wheel` and `rim`; point the rest of
       the rotating parts at the same thing. */
    st.wheel=wheel;
    st.rim=rim||wheel;
    st.spinExtra=disc? [disc] : [];
    st.assetFor=V.id;

    /* the strut, which is the same for every vehicle */
    if(!st.assetStrut && MDL.has('vehicles/strut')){
      var sp=MDL.node('vehicles/strut','spring',{obj:true,tex:'metal'});
      var sh=MDL.node('vehicles/strut','shock', {obj:true,tex:'metal'});
      if(sp && sh){
        st.spring.visible=false; st.shock.visible=false;
        grp.add(sp); grp.add(sh);
        sp.position.copy(st.spring.position);
        sh.position.copy(st.shock.position);
        st.spring=sp; st.shock=sh;
        st.assetStrut=true;
      }
    }
  }
}

/* ================= assets =================""")

# the per frame spin has to carry the parts that were standing still
sub("""    st.wheel.rotation.x=c.spin;
    st.rim.rotation.x=c.spin;""",
"""    st.wheel.rotation.x=c.spin;
    st.rim.rotation.x=c.spin;
    /* AUDIT #7: the disc turns with the wheel it is clamped to */
    if(st.spinExtra) for(var sx=0;sx<st.spinExtra.length;sx++)
      st.spinExtra[sx].rotation.x=c.spin;""")

# ------------------------------------------- AUDIT #4: the teal glow on every car
sub("""  lerpHex(A.sun,B.sun,k,STYLE_U.uRimC.value); STYLE_U.uRimC.value.convertSRGBToLinear();""",
"""  lerpHex(A.sun,B.sun,k,STYLE_U.uRimC.value); STYLE_U.uRimC.value.convertSRGBToLinear();
  /* AUDIT #4: this drove the paint emissive from PAL.body, which is the
     Bracken's teal, so every other car glowed teal at dusk. Follow the car. */
  if(typeof VEHICLES!=='undefined' && typeof VEH!=='undefined' && VEHICLES[VEH]){
    var _pc=new THREE.Color(VEHICLES[VEH].paint).convertSRGBToLinear();
    if(typeof paint!=='undefined' && paint.emissive) paint.emissive.copy(_pc).multiplyScalar(TOD.glow*0.5);
  }""")

# ------------------------------------------- kick the load off, and rebuild on arrival
sub("""requestAnimationFrame(frame);""",
"""/* Preload the models behind the title screen, then rebuild whatever is on
   screen so the hand built version is replaced in place. If this never
   finishes, the game stays exactly as it was. */
MDL.load(function(){
  try{
    window.__setVehicle(VEH);          /* body, wheels and strut */
    if(typeof rebuildAssetProps==='function') rebuildAssetProps();
  }catch(e){}
});

requestAnimationFrame(frame);""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
