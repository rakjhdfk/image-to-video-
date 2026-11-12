"""Original articulated, cel-shaded fantasy-anime character drawings.

The renderer is local and deterministic. It does not claim diffusion-quality art.
``phase`` is continuous time in seconds. Coordinates refer to the feet at scale=1,
where a young adult stands approximately 440 pixels tall. All character features
are redrawn from persistent designs, with separately posed limbs, faces and hair.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TAU=math.tau
INK='#111827'
DESIGNS={
 'kael':dict(id='KAEL_ARDYN_01',name='Kael Ardyn',age=19,hair='#151b2d',hairlight='#34475d',coat='#14273d',coatlight='#23445d',coatshadow='#0c1728',trim='#6aadb4',iris='#42c8b8',skin='#e7b394',shade='#bc8178',shirt='#dce7e7',accent='#6fdad2',voice='young_indian_english_male'),
 'mira':dict(id='MIRA_VEYNE_01',name='Mira Veyne',age=20,hair='#cbd4e8',hairlight='#f0f5ff',coat='#34374f',coatlight='#505976',coatshadow='#202237',trim='#c4b5e5',iris='#a788ed',skin='#f0c6b4',shade='#c08d91',shirt='#dfe4ef',accent='#d7c1ff',voice='young_indian_english_female'),
 'riven':dict(id='RIVEN_SOL_01',name='Riven Sol',age=21,hair='#622536',hairlight='#b14a50',coat='#24212d',coatlight='#493143',coatshadow='#151623',trim='#dd5664',iris='#e6a260',skin='#dca58b',shade='#aa6b68',shirt='#302b3b',accent='#fa6c77',voice='young_indian_english_male_energetic'),
 'elder':dict(id='ACADEMY_ELDER_01',name='The Academy Elder',age=70,hair='#d6d6dc',hairlight='#ffffff',coat='#272638',coatlight='#474158',coatshadow='#171827',trim='#c6ab63',iris='#9e9caf',skin='#d7b29d',shade='#a07e7d',shirt='#9c94aa',accent='#ffdf88',voice='older_indian_english_male'),
}

def _font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/segoeui.ttf','C:/Windows/Fonts/arial.ttf']:
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def _clamp(v,a,b):return max(a,min(b,v))
def _limb_polygon(a,b,r1,r2):
    dx,dy=b[0]-a[0],b[1]-a[1];length=max(.001,math.hypot(dx,dy));nx,ny=-dy/length,dx/length
    return [(a[0]+nx*r1,a[1]+ny*r1),(b[0]+nx*r2,b[1]+ny*r2),(b[0]-nx*r2,b[1]-ny*r2),(a[0]-nx*r1,a[1]-ny*r1)]

def draw_character(image:Image.Image,name:str,x:float,y:float,scale:float=1.,pose:str='talk',phase:float=0.,expression:str='determined',speaking:bool=False,facing:int=1,magic:str='none',view:str='three-quarter',face_phase:float|None=None,mouth_open:float|None=None):
    """Draw one original human rig in place and return world-space body anchors.

    ``pose`` supports walk/run, ceremony, rescue, listen, weave, battle/attack,
    dodge, fall, kneel, seal, point, talk and idle. Additional shot-action text is
    classified by these keywords. Front/side/back views support reference sheets.
    ``face_phase`` separates the face clock from frozen body poses; ``mouth_open``
    is an optional normalized speech envelope, not phoneme-level lip alignment.
    """
    name=str(name).lower()
    if name not in DESIGNS:return {}
    c=DESIGNS[name];s=max(.02,float(scale));face=1 if facing>=0 else -1
    draw=ImageDraw.Draw(image)
    t=float(phase);ft=t if face_phase is None else float(face_phase);pose=str(pose).lower();expr=str(expression).lower()
    is_run=any(v in pose for v in ['run','rescue','dash','chase'])
    is_walk=is_run or any(v in pose for v in ['walk','approach','enter','leave'])
    is_battle=any(v in pose for v in ['battle','attack','strike','combat','block','dodge','defend'])
    is_weave=any(v in pose for v in ['weave','spell','seal','ceremony','awaken','summon','cast'])
    fallen=any(v in pose for v in ['fall','collapse','kneel'])
    cyc=t*(9.2 if is_run else 5.3)
    bob=(-5*abs(math.sin(cyc)) if is_run else -2.3*abs(math.sin(cyc))) if is_walk else math.sin(t*1.8)*1.15
    if fallen:bob=48
    lean=.11 if is_run else (.055*math.sin(t*1.6) if is_battle else -.035 if fallen else 0)
    view_x=.68 if view=='side' else 1
    def pt(p):
        xx,yy=p
        xx+=(yy+210)*lean
        return (x+xx*s*face*view_x,y+(yy+bob)*s)
    def poly(points,fill,outline=INK,width=1):
        pp=[pt(p) for p in points];draw.polygon(pp,fill=fill)
        if outline and width:draw.line(pp+[pp[0]],fill=outline,width=max(1,round(width*s)),joint='curve')
    def line(points,fill,width=1):draw.line([pt(p) for p in points],fill=fill,width=max(1,round(width*s)),joint='curve')
    def ellipse(box,fill,outline=None,width=1):
        a=pt((box[0],box[1]));b=pt((box[2],box[3]));bb=(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
        draw.ellipse(bb,fill=fill,outline=outline,width=max(1,round(width*s)))
    def segment(a,b,r1,r2,fill,accent=True):
        poly(_limb_polygon(a,b,r1,r2),fill,width=1.2)
        if accent:
            dx,dy=b[0]-a[0],b[1]-a[1];line([(a[0]+r1*.5,a[1]+4),(b[0]+r2*.4,b[1]-4)],c['coatlight'],2)
    def hand(p,angle=0,open_hand=False):
        hx,hy=p;co,si=math.cos(angle),math.sin(angle)
        def hp(a,b):return (hx+a*co-b*si,hy+a*si+b*co)
        if open_hand:
            poly([hp(-6,-4),hp(-8,3),hp(-14,8),hp(-13,13),hp(-6,10),hp(-5,25),hp(-1,27),hp(0,11),hp(2,29),hp(6,28),hp(5,11),hp(9,24),hp(12,22),hp(9,8),hp(14,18),hp(17,15),hp(11,2),hp(6,-5)],c['skin'],width=.8)
            line([hp(-6,5),hp(5,5),hp(9,9)],c['shade'],.8)
        else:
            poly([hp(-6,-5),hp(6,-5),hp(11,3),hp(9,13),hp(3,17),hp(-6,13),hp(-10,6)],c['skin'],width=.8)
            line([hp(-5,1),hp(5,3),hp(5,10)],c['shade'],.8)
            line([hp(-5,7),hp(0,9)],c['shade'],.8)
    # Rig: independently computed hips, knees, ankles and shoulders.
    hip_l=(-17,-200);hip_r=(18,-200)
    if is_walk:
        step=math.sin(cyc);stride=48 if is_run else 31
        knee_l=(-20+step*stride*.52,-108-abs(step)*7);knee_r=(21-step*stride*.52,-108-abs(step)*7)
        ankle_l=(-22+step*stride,-22-max(0,-step)*(20 if is_run else 9));ankle_r=(22-step*stride,-22-max(0,step)*(20 if is_run else 9))
    elif is_battle:
        step=math.sin(t*3.2);knee_l=(-40-step*4,-105);knee_r=(40+step*4,-107);ankle_l=(-63-step*7,-20);ankle_r=(57+step*6,-20)
    elif fallen:
        knee_l=(-38,-105);knee_r=(55,-75);ankle_l=(-65,-25);ankle_r=(65,-20)
    else:
        knee_l=(-20,-106);knee_r=(22,-106);ankle_l=(-23,-22);ankle_r=(24,-22)
    shoulder_l=(-40,-335);shoulder_r=(40,-335)
    elbow_l=(-53,-267);elbow_r=(53,-267);wrist_l=(-55,-211);wrist_r=(58,-211)
    if is_walk:
        swing=math.sin(cyc)*(.95 if is_run else .55)
        elbow_l=(-48-swing*20,-274);elbow_r=(47+swing*20,-274)
        wrist_l=(-53-swing*48,-221+abs(swing)*13);wrist_r=(54+swing*48,-221+abs(swing)*13)
    elif is_weave:
        pulse=math.sin(t*2.1)
        elbow_l=(-69,-294-pulse*3);elbow_r=(72,-292+pulse*4)
        wrist_l=(-82,-332+pulse*9);wrist_r=(99,-345-pulse*5)
        if 'seal' in pose:wrist_l=(-59,-263);wrist_r=(59,-263);elbow_l=(-69,-286);elbow_r=(68,-286)
    elif is_battle:
        a=math.sin(t*3.4);b=math.cos(t*3.4)
        elbow_l=(-64,-290+a*14);wrist_l=(-38+a*32,-331+b*10)
        elbow_r=(68+a*20,-310+b*7);wrist_r=(110+a*39,-314+b*37)
        if 'dodge' in pose:elbow_r=(75,-310);wrist_r=(77,-363)
    elif 'listen' in pose:
        elbow_r=(64,-300);wrist_r=(33,-369)
    elif 'point' in pose:
        elbow_r=(94,-323);wrist_r=(142,-334)
    elif fallen:
        elbow_l=(-72,-268);wrist_l=(-89,-217);elbow_r=(56,-276);wrist_r=(40,-230)
    elif speaking:
        gest=math.sin(t*3.1)
        elbow_r=(64,-284+gest*5);wrist_r=(81+gest*6,-297+gest*8)
    if name=='elder':elbow_r=(60,-275);wrist_r=(65,-243)
    # Long back hair is behind the costume and limbs, with independently drifting tips.
    drift=math.sin(t*2.2)*4+(5 if is_run else 0)
    if name=='mira':
        poly([(-25,-423),(-40,-398),(-45,-350),(-47,-292),(-39+drift,-236),(-32+drift,-270),(-22,-251),(-15,-326),(25,-274),(33+drift,-244),(43+drift,-284),(40,-358),(31,-413),(16,-435)],'#a2b0cb',width=1.3)
        poly([(-24,-420),(-34,-385),(-33,-322),(-28+drift,-274),(-20,-315),(-12,-383)],c['hairlight'],outline=None)
        line([(-36,-397),(-39,-344),(-35+drift,-288)],'#e5edfa',2)
        line([(28,-396),(33,-338),(34+drift,-280)],'#eff3ff',2)
    # Back sleeve and far leg: deeper cel shade creates a stable near/far ordering.
    segment(shoulder_l,elbow_l,14,11,c['coatshadow']);segment(elbow_l,wrist_l,11,8,c['coat'])
    if name!='elder':
        poly([(-28,-229),(28,-229),(33,-199),(17,-187),(0,-199),(-18,-187),(-32,-200)],'#22283b',width=1)
        for hip,knee,ankle,is_near in [(hip_l,knee_l,ankle_l,False),(hip_r,knee_r,ankle_r,True)]:
            leg='#252b40' if is_near else '#181f32'
            segment(hip,knee,15,11,leg,False);segment(knee,ankle,11,8,leg,False)
            line([(knee[0]+3,knee[1]+5),(ankle[0]+2,ankle[1]-4)],'#41485b',1.5)
            ax,ay=ankle
            poly([(ax-11,ay-14),(ax+10,ay-14),(ax+11,ay+8),(ax+25,ay+14),(ax+24,ay+22),(ax-13,ay+22)],'#172032',width=1.3)
            poly([(ax-9,ay-12),(ax+8,ay-12),(ax+8,ay+8),(ax-8,ay+9)],'#303d54',outline=None)
            line([(ax-9,ay-3),(ax+9,ay-3)],c['trim'],2)
            line([(ax-11,ay+18),(ax+22,ay+18)],'#546071',1.3)
    # Coat tails and flutter are independent of the trouser motion.
    flutter=math.sin(t*3.4)*(9 if is_walk or is_battle else 2)
    if name=='kael':
        poly([(-39,-322),(-41,-228),(-55+flutter,-132),(-12,-143),(-1,-209),(14,-141),(58+flutter,-156),(39,-241),(38,-322)],c['coatshadow'],width=1.5)
        poly([(-38,-285),(-36,-223),(-43+flutter,-155),(-20,-158),(-8,-239)],c['coatlight'],outline=None)
        poly([(25,-277),(33,-224),(44+flutter,-167),(22,-161),(7,-237)],c['coat'],outline=None)
        line([(-40+flutter,-148),(-19,-149)],c['trim'],2)
        line([(23,-149),(50+flutter,-161)],c['trim'],2)
    elif name=='mira':
        poly([(-32,-251),(-47+flutter,-161),(-39,-151),(-21,-155),(-3,-147),(18,-154),(36,-150),(48+flutter,-162),(32,-252)],c['coatshadow'],width=1.5)
        for xx in [-29,-12,9,28]:line([(xx,-240),(xx*1.45+flutter*.6,-162)],c['coatlight'],2)
        line([(-43+flutter,-160),(-25,-160),(-3,-154),(19,-161),(43+flutter,-160)],c['trim'],2)
    elif name=='elder':
        poly([(-40,-332),(-54,-259),(-47,-189),(-67,-17),(-35,-4),(0,-12),(29,-3),(71,-18),(49,-192),(51,-269),(37,-333)],c['coatshadow'],width=1.8)
        poly([(-28,-326),(-29,-211),(-43,-22),(-20,-17),(-6,-208),(9,-323)],c['coatlight'],outline=None)
        poly([(16,-322),(24,-201),(45,-23),(25,-16),(7,-196),(-2,-322)],'#373347',outline=None)
        line([(-48,-25),(-30,-18),(-11,-23)],c['trim'],2)
        line([(18,-24),(33,-17),(58,-25)],c['trim'],2)
        for zz in [-160,-118,-77]:line([(-40,zz),(-34,zz+8)],'#6d6278',1)
    # Tailored torso with overlaid shoulder structure, collar and two levels of trim.
    torso=[(-29,-349),(-45,-330),(-35,-271),(-29,-217),(30,-217),(38,-279),(43,-329),(25,-349)]
    poly(torso,c['coat'],width=1.7)
    poly([(-27,-345),(-39,-327),(-32,-274),(-25,-226),(-8,-225),(-5,-340)],c['coatlight'],outline=None)
    poly([(13,-339),(33,-329),(34,-278),(28,-222),(13,-223)],c['coatshadow'],outline=None)
    # Neck with a shadow under the jaw.
    poly([(-10,-372),(-12,-345),(0,-335),(13,-346),(12,-373)],c['skin'],width=1)
    poly([(-9,-370),(-8,-355),(10,-348),(12,-372)],c['shade'],outline=None)
    if name=='mira':
        poly([(-16,-353),(-27,-340),(-10,-303),(0,-337)],'#e0e6f2',width=1)
        poly([(14,-354),(26,-340),(11,-305),(0,-337)],'#b8bfd3',width=1)
        poly([(-6,-336),(5,-337),(9,-314),(0,-300),(-7,-315)],'#9b82c8',width=.8)
        ellipse((-5,-323,6,-313),c['accent'],INK,.8)
    elif name=='elder':
        poly([(-19,-350),(-34,-336),(-21,-291),(-1,-329)],'#797084',width=1)
        poly([(17,-350),(31,-337),(20,-293),(0,-329)],'#544a63',width=1)
    else:
        poly([(-14,-352),(-28,-344),(-20,-302),(-3,-329)],c['shirt'],width=1)
        poly([(12,-352),(27,-343),(21,-302),(2,-329)],c['coatlight'],width=1)
        poly([(-4,-337),(6,-336),(8,-300),(0,-294),(-6,-301)],'#273448',width=.8)
    # Contrasting shoulder panels and fine piping.
    poly([(-33,-346),(-48,-333),(-44,-315),(-26,-329)],c['coatshadow'],width=1)
    poly([(32,-346),(47,-333),(44,-316),(27,-330)],c['coatlight'],width=1)
    line([(-40,-334),(-27,-340),(-19,-318)],c['trim'],1.5)
    line([(39,-334),(28,-340),(19,-318)],c['trim'],1.5)
    line([(-12,-301),(-15,-232)],c['trim'],1.2)
    line([(14,-301),(16,-232)],c['coatlight'],1.2)
    # Coat seams, pocket flaps, brass buttons, belt and academy emblem.
    poly([(-30,-273),(-18,-271),(-18,-261),(-29,-261)],c['coatshadow'],width=.7)
    poly([(18,-271),(29,-273),(28,-261),(19,-260)],c['coatshadow'],width=.7)
    line([(-30,-270),(-18,-269)],c['trim'],1)
    for yy in [-286,-267,-248]:ellipse((-4,yy,0,yy+4),c['trim'])
    poly([(-32,-232),(31,-232),(32,-218),(-31,-218)],'#3b3041' if name=='mira' else '#22202c',width=1)
    poly([(-8,-232),(9,-232),(9,-218),(-8,-218)],c['trim'],width=.7)
    poly([(-4,-229),(5,-229),(5,-221),(-4,-221)],'#23283b',outline=None)
    # Signature origin diamond / silver-thread crest / lightning pin.
    if name=='riven':
        poly([(24,-326),(17,-311),(24,-313),(20,-300),(34,-318),(27,-316),(32,-326)],c['accent'],outline=None)
        line([(-33,-314),(-25,-287)],'#a94a59',3)
        poly([(-42,-237),(-32,-237),(-31,-218),(-40,-219)],'#a14b56',width=.7)
    else:
        poly([(27,-320),(34,-311),(27,-301),(20,-311)],c['trim'],width=.8)
        poly([(27,-316),(30,-311),(27,-306),(24,-311)],c['iris'],outline=None)
    # Near sleeve with elbow structure, cuffs and hand articulation.
    segment(shoulder_r,elbow_r,15 if name!='elder' else 21,11 if name!='elder' else 19,c['coat'])
    segment(elbow_r,wrist_r,11 if name!='elder' else 19,8 if name!='elder' else 17,c['coatlight'])
    line([(shoulder_r[0]+9,shoulder_r[1]+9),(elbow_r[0]+6,elbow_r[1]-4)],c['trim'],1.4)
    for wp in [wrist_l,wrist_r]:
        poly([(wp[0]-9,wp[1]-9),(wp[0]+9,wp[1]-9),(wp[0]+9,wp[1]),(wp[0]-9,wp[1])],c['coatshadow'],width=.8)
        line([(wp[0]-8,wp[1]-5),(wp[0]+8,wp[1]-5)],c['trim'],1.8)
    hand(wrist_l, -.5 if is_weave else .12, is_weave)
    hand(wrist_r, -.9 if is_battle else -.35 if is_weave else -.12, is_weave or 'point' in pose)
    # A back view retains the same costume/hair volume but hides the face.
    if view=='back':
        poly([(-26,-346),(-17,-327),(0,-313),(18,-327),(27,-346)],c['coatlight'],width=1)
        poly([(0,-315),(18,-290),(0,-264),(-18,-290)],c['trim'],width=1)
        poly([(0,-308),(12,-290),(0,-272),(-12,-290)],c['coatshadow'],outline=None)
        line([(0,-302),(0,-277)],c['trim'],1.5)
    # Head: pointed chin, asymmetric anime facial planes and an ear.
    tilt=(-2 if name=='mira' else 0)+(1.5*math.sin(t*1.8) if 'listen' in pose else 0)
    def fp(p):return (p[0]+tilt,p[1])
    face_shape=[(-25,-422),(-30,-407),(-27,-383),(-18,-370),(1,-360),(22,-372),(30,-389),(27,-418),(11,-430),(-11,-430)]
    if view=='side':face_shape=[(-18,-421),(-27,-404),(-21,-382),(-8,-365),(10,-359),(24,-365),(28,-376),(38,-380),(30,-385),(44,-389),(31,-395),(29,-415),(14,-429),(-6,-430)]
    poly([fp(p) for p in face_shape],c['skin'],width=1.2)
    poly([fp(p) for p in [(16,-424),(27,-416),(29,-389),(21,-373),(1,-360),(11,-376),(15,-395)]],c['shade'],outline=None)
    ellipse((-34+tilt,-404,-23+tilt,-386),c['skin'],INK,.7)
    line([(-29+tilt,-399),(-31+tilt,-395),(-27+tilt,-391)],c['shade'],1)
    if view=='back':
        poly([(-28,-421),(-31,-397),(-24,-371),(0,-365),(26,-375),(31,-400),(23,-423),(0,-434)],c['hair'],width=1)
    else:
        # Slightly narrowed far eye and strong upper lash are deliberate anime design.
        blink=(ft%4.35<.105 and ft>.1) or any(v in expr for v in ['laugh','closed','serene'])
        shocked=any(v in expr for v in ['shock','surpris','afraid','fear','terrifi'])
        angry=any(v in expr for v in ['ang','determin','brave','focused','fierce'])
        tired=any(v in expr for v in ['sad','tired','pain','exhaust','worried'])
        eyes=[(6,-400,16,9)] if view=='side' else [(-19,-399,17,10),(8,-400,16,9)]
        for idx,(ex,ey,ew,eh) in enumerate(eyes):
            ex+=tilt
            if shocked:eh+=3
            if tired:eh-=2
            if blink:
                line([(ex,ey+2),(ex+ew*.45,ey+4),(ex+ew,ey+1)],INK,1.5)
            else:
                poly([(ex,ey),(ex+ew*.45,ey-2),(ex+ew,ey+1),(ex+ew-2,ey+eh-2),(ex+ew*.45,ey+eh),(ex+1,ey+eh-2)],'#f1f2f3',outline=None)
                irisx=ex+ew*.57
                ellipse((irisx-4,ey-1,irisx+4,ey+eh),c['iris'])
                ellipse((irisx-2,ey,irisx+2,ey+eh-1),'#152538')
                ellipse((irisx-2.5,ey,irisx+.4,ey+3),'#ffffff')
                line([(ex-1,ey),(ex+ew*.45,ey-2),(ex+ew+1,ey+1)],INK,2)
                line([(ex+1,ey+eh-1),(ex+ew*.5,ey+eh),(ex+ew-1,ey+eh-2)],'#815f67',.7)
            browy=ey-9 if shocked else ey-7
            slope=3 if (angry and idx==0) or (tired and idx==1) else -2 if angry or tired else 0
            line([(ex,browy-slope),(ex+ew,browy+slope)],c['hair'] if name!='mira' else '#75809f',1.7)
        if view=='side':
            line([(31+tilt,-395),(42+tilt,-389),(32+tilt,-386)],c['shade'],.9)
            line([(29+tilt,-377),(36+tilt,-378)],'#7b4d56',1)
        else:
            line([(3+tilt,-397),(1+tilt,-386),(6+tilt,-384)],c['shade'],.9)
            line([(1+tilt,-382),(5+tilt,-382)],'#9f716b',.8)
        if view=='side':
            pass
        elif speaking:
            opening=2+5*(.5+.5*math.sin(ft*18)) if mouth_open is None else 7*_clamp(float(mouth_open),0.,1.)
            if opening<.35:
                line([(-5+tilt,-374),(8+tilt,-374)],'#7b4d56',1)
            else:
                ellipse((-5+tilt,-376,9+tilt,-376+opening),'#552a3e',INK,.7)
                if opening>2:line([(-3+tilt,-375),(7+tilt,-375)],'#f7e5dc',1.3)
                if opening>5:ellipse((-2+tilt,-372,6+tilt,-370),'#bd6c7c')
        elif shocked:
            ellipse((0+tilt,-376,7+tilt,-368),'#743c4c',INK,.7)
        elif any(v in expr for v in ['smile','happy','hope','confiden','laugh']):
            line([(-5+tilt,-374),(1+tilt,-371),(9+tilt,-374)],'#7b4d56',1)
        elif tired:
            line([(-5+tilt,-371),(1+tilt,-373),(8+tilt,-371)],'#845c61',1)
        else:line([(-5+tilt,-373),(8+tilt,-374)],'#7b4d56',1)
        if name=='elder':
            # Older face planes, measured gaze and a forked white beard.
            for ex in [-21,9]:line([(ex,-384),(ex+7,-383)],'#a18584',.8)
            line([(-22,-409),(-10,-411)],'#aa9090',.8)
            poly([(-18,-376),(-13,-367),(-9,-349),(0,-336),(8,-351),(19,-370),(17,-379),(8,-374),(1,-377),(-7,-374)],c['hair'],width=.9)
            poly([(-4,-367),(0,-342),(7,-361),(7,-371)],c['hairlight'],outline=None)
            poly([(-15,-379),(-4,-381),(1,-377),(6,-381),(17,-379),(11,-374),(1,-376),(-9,-374)],c['hairlight'],width=.5)
    # Crown hair and the distinctive continuous silhouette of every character.
    if name=='kael':
        hp=[(-32,-394),(-38,-410),(-30,-417),(-39,-427),(-24,-426),(-27,-439),(-13,-434),(-6,-448),(4,-438),(19,-444),(22,-433),(35,-430),(28,-418),(33,-406),(24,-391),(19,-415),(9,-403),(4,-419),(-8,-406),(-10,-421),(-22,-404),(-23,-389)]
        poly([(a+tilt,b+(math.sin(t*2.3+a)*1 if b<-425 else 0)) for a,b in hp],c['hair'],width=1.2)
        poly([(-28+tilt,-426),(-13+tilt,-432),(-18+tilt,-418),(-23+tilt,-410)],c['hairlight'],outline=None)
        poly([(-5+tilt,-438),(13+tilt,-436),(6+tilt,-423),(5+tilt,-432)],'#28394f',outline=None)
        line([(16+tilt,-431),(23+tilt,-422),(24+tilt,-411)],'#3b4e62',1)
    elif name=='mira':
        poly([(-31,-393),(-34,-415),(-25,-431),(-8,-440),(12,-437),(28,-427),(33,-410),(29,-384),(22,-400),(17,-418),(7,-405),(3,-422),(-5,-410),(-12,-422),(-22,-404),(-25,-385)],c['hair'],width=1)
        poly([(-25,-423),(-10,-433),(-2,-433),(-10,-416),(-11,-426),(-24,-408)],c['hairlight'],outline=None)
        poly([(7,-432),(21,-426),(27,-411),(23,-398),(18,-417),(12,-414)],'#eef3ff',outline=None)
        line([(-24,-404),(-27,-385),(-25,-362)],'#e9efff',2)
        poly([(-27,-413),(-23,-407),(-28,-401),(-34,-407)],'#9a81b2',width=.8)
        ellipse((-30,-409,-26,-405),'#e5c98e')
    elif name=='riven':
        poly([(-30,-391),(-35,-407),(-29,-417),(-39,-425),(-24,-424),(-27,-436),(-13,-432),(-5,-444),(4,-435),(17,-441),(20,-429),(34,-428),(29,-417),(37,-414),(29,-395),(22,-403),(19,-418),(8,-411),(2,-423),(-7,-410),(-16,-421),(-23,-402)],c['hair'],width=1.2)
        poly([(-23,-428),(-13,-430),(-15,-416)],c['hairlight'],outline=None)
        poly([(-4,-437),(12,-434),(17,-424),(7,-425)],'#a34149',outline=None)
        line([(25,-418),(29,-410),(26,-400)],'#b5595b',1.2)
    else:
        poly([(-31,-389),(-35,-407),(-27,-426),(-12,-438),(9,-438),(27,-427),(34,-409),(30,-389),(25,-378),(22,-401),(14,-419),(2,-423),(-11,-419),(-24,-401),(-24,-380)],c['hair'],width=1)
        poly([(-26,-416),(-9,-432),(11,-431),(24,-419),(12,-423),(0,-426),(-12,-422)],c['hairlight'],outline=None)
        line([(-30,-400),(-27,-387)],'#fffaff',2)
        line([(28,-398),(26,-386)],'#fffaff',2)
    # Staff belongs to the Elder's persistent right-hand anchor.
    if name=='elder':
        sx=wrist_r[0]+2
        line([(sx,0),(sx,-417)],'#493321',7)
        line([(sx-1,-3),(sx-1,-412)],'#c4a66b',3)
        for yy in [-300,-291,-282]:line([(sx-4,yy),(sx+4,yy)],'#eed498',2)
        poly([(sx,-442),(sx+13,-422),(sx,-402),(sx-13,-422)],'#d9b969',width=1.2)
        poly([(sx,-435),(sx+7,-422),(sx,-410),(sx-7,-422)],'#fff1af',width=.8)
        line([(sx-20,-427),(sx-18,-412),(sx-8,-402),(sx+8,-402),(sx+18,-412),(sx+20,-427)],'#ad9051',3)
    return {'left_hand':pt(wrist_l),'right_hand':pt(wrist_r),'head':pt((2,-399)),'body':pt((0,-275)),'feet':(x,y)}

def generate_references(outputdir):
    """Create original model, expression and action sheets for persistent cast."""
    out=Path(outputdir);out.mkdir(parents=True,exist_ok=True)
    label=_font(20);small=_font(16);title=_font(27)
    paths=[]
    for name,c in DESIGNS.items():
        char_dir=out/name;char_dir.mkdir(exist_ok=True)
        sheet=Image.new('RGB',(1500,700),'#e5e8f0');d=ImageDraw.Draw(sheet)
        d.text((30,20),f"{c['name']}  |  {c['id']}",font=title,fill=INK)
        for i,v in enumerate(['front','side','back','three-quarter']):
            xx=190+i*375
            d.line((xx-150,620,xx+150,620),fill='#bdc6d5',width=1)
            draw_character(sheet,name,xx,620,1.10,'idle',1.,'calm',False,1,'none',v)
            d.text((xx-50,650),v.upper(),font=small,fill='#344157')
        p=char_dir/'turnaround.png';sheet.save(p);paths.append(str(p))
        expressions=['calm','determined','shocked','sad','angry','hopeful','tired','confident']
        sheet=Image.new('RGB',(1600,820),'#e8ebf2');d=ImageDraw.Draw(sheet)
        d.text((25,15),c['name']+' — EXPRESSION LIBRARY',font=title,fill=INK)
        for i,e in enumerate(expressions):
            col=i%4;row=i//4;xx=200+col*400;yy=780+row*380
            # Head-and-shoulders rendering is naturally cropped into each cell.
            tile=Image.new('RGB',(385,350),'#e8ebf2')
            draw_character(tile,name,192,1080,2.35,'talk',1.75,e,False)
            sheet.paste(tile,(col*400+7,row*380+58))
            d.text((col*400+135,row*380+395),e,font=label,fill='#344157')
        p=char_dir/'expressions.png';sheet.save(p);paths.append(str(p))
        actions=['walk','run','weave','battle','rescue','listen','fall','seal']
        sheet=Image.new('RGB',(1800,1180),'#e6eaf1');d=ImageDraw.Draw(sheet)
        d.text((25,18),c['name']+' — ACTION LIBRARY',font=title,fill=INK)
        for i,a in enumerate(actions):
            xx=225+(i%4)*450;yy=555+(i//4)*560
            draw_character(sheet,name,xx,yy,1.0,a,1.25,'focused',a=='listen')
            d.text((xx-35,yy+15),a.upper(),font=small,fill='#344157')
        p=char_dir/'actions.png';sheet.save(p);paths.append(str(p))
        (char_dir/'identity.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
    manifest={'renderer':'original procedural cel-shaded articulated 2D drawings','characters':DESIGNS,'voice_only':{'ancient':{'identity':'ancient magical consciousness','visual':'abstract origin glyphs; no humanoid body'},'narrator':{'identity':'off-screen cinematic narrator','visual':None}},'references':paths,'quality_note':'These are generated original vector-style rig references, not high-detail hand-drawn or diffusion-generated anime assets.'}
    (out/'characters.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    import argparse,time
    p=argparse.ArgumentParser();p.add_argument('--output',default='output/characters');args=p.parse_args()
    start=time.perf_counter();generate_references(args.output)
    print('Reference sheets generated in',round(time.perf_counter()-start,2),'seconds')
