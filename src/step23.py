# -*- coding: utf-8 -*-
"""Work order steps 2 and 3: the loading line, and material roles.

STEP 2, the one missing piece. The loader was already vendored, fetching and
parsing, and cached by the service worker. What it never did was say anything
while it worked. On a phone over a cold connection that is a second or two of
a title screen that looks finished but whose Drive button gives you the old
hand built truck.

So: one short line under the title, "Loading the fleet", which swaps to
"Tap to drive" when the models are in. Deliberately NOT a progress bar and
deliberately not a count: a bar that fills is a countdown wearing a different
hat, and that is a defect under A2.

STEP 3, the gap that matters for everything after it. Materials were being
rebuilt as Phong and run through styleMat, which is what the look needs, but
`userData.role` was being dropped on the floor. Every material in the new GLBs
carries a role in its glTF extras (bark, rock, sand, asphalt, foliage, metal
and so on) and `weather.js` keys entirely off it: no role, no wet darkening,
no snow, no moss, no ice. Step 9 would simply have done nothing.

The role is now carried across onto the rebuilt material, and because
materials are shared by name the role has to be consistent per name, which it
is: the generator assigns one role per material name.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    s = s.replace(old, new, 1); n += 1

# ------------------------------------------------- step 2: the loading line
sub("""<div id="intro">
  <div id="ititle">Coil<em>over</em></div>""",
"""<div id="intro">
  <div id="ititle">Coil<em>over</em></div>
  <div id="iload">Loading the fleet</div>""")

sub("""  #ititle em{font-style:normal;color:var(--amber)}""",
"""  #ititle em{font-style:normal;color:var(--amber)}
  /* One line, no bar and no count. A bar that fills is a countdown in a
     different hat, which is a defect under A2. */
  #iload{position:absolute;left:50%;top:calc(16% + 62px);transform:translateX(-50%);
         font-family:"Chakra Petch",sans-serif;font-weight:600;font-size:11px;
         letter-spacing:.22em;text-transform:uppercase;color:var(--mute);
         text-shadow:0 2px 10px rgba(20,10,6,.9);pointer-events:none;
         animation:fadeIn 1.2s ease both;transition:color .4s}
  #iload.done{color:var(--amber)}""")

sub("    #ititle{top:9%;font-size:38px}",
    "    #ititle{top:9%;font-size:38px}\n    #iload{top:calc(9% + 46px)}")

# ------------------------------------------------- step 3: carry the role across
sub("""  function matFor(name, spec, opts){
    /* The game's own material always wins. Its name is the model's name on
       purpose, and it is the one the rest of the game already drives. */
    if(given[name]) return given[name];
    if(mats[name]) return mats[name];""",
"""  function matFor(name, spec, opts, role){
    /* The game's own material always wins. Its name is the model's name on
       purpose, and it is the one the rest of the game already drives. */
    if(given[name]){
      /* even a game-owned material needs its role, or weather skips it */
      if(role && !given[name].userData.role) given[name].userData.role=role;
      return given[name];
    }
    if(mats[name]) return mats[name];""")

sub("""    mats[name]=styleMat(m, opts||{});
    return mats[name];""",
"""    /* Every material in the pack carries a role in its glTF extras, and
       weather.js keys entirely off it: no role, no wet, no snow, no moss, no
       ice. Carry it across BEFORE styleMat so anything chaining onto
       onBeforeCompile later can see it. */
    if(role) m.userData.role=role;
    mats[name]=styleMat(m, opts||{});
    return mats[name];""")

sub("""      var src=o.material, nm=(src && src.name) || 'trim';
      var spec=(MDL.specOf(nm)) || {color:'#'+(src&&src.color? src.color.getHexString():'888888')};
      o.material=matFor(nm, spec, opts);""",
"""      var src=o.material, nm=(src && src.name) || 'trim';
      var spec=(MDL.specOf(nm)) || {color:'#'+(src&&src.color? src.color.getHexString():'888888')};
      /* GLTFLoader puts glTF material `extras` into material.userData */
      var role=(src && src.userData && src.userData.role) || spec.role || null;
      o.material=matFor(nm, spec, opts, role);""")

# ------------------------------------------------- and the line is driven
sub("""MDL.load(function(){""",
"""var _il=document.getElementById('iload');
MDL.load(function(){
  if(_il){ _il.textContent='Tap to drive'; _il.className='done'; }""")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)
