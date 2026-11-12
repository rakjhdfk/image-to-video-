"""Story-specific blocking and illustrated objects for the sixty connected shots.

These are lightweight 2D rig poses and drawn props, not diffusion video. Props
are spatial scene objects, not caption cards. Coordinates are native 1280x720.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw

TAU=math.tau

def ease(v):
    v=max(0.,min(1.,v));return v*v*(3-2*v)

def active_casters(shot,t):
    """Explicit caster gating; a powerless Kael never emits a spell stream."""
    i=shot['id'];u=t/10
    casts={1:set(),2:{'riven'},3:{'mira'},5:set(),7:{'riven'},
           13:{'mira'},14:{'riven'},15:set(),16:set(),17:set(),
           18:set(),19:{'elder'},20:{'mira','riven'},21:set(),22:{'riven'},
           23:{'elder'},24:{'mira','riven'},25:set(),26:{'mira'},
           27:{'riven'},28:{'riven'},29:set(),30:set(),31:set(),32:{'kael'},
           33:set(),34:set(),35:set(),36:{'kael','mira'},37:{'kael'},
           38:{'mira'},39:{'riven'},40:{'kael','mira'},41:{'kael','mira','riven'},
           42:{'mira'},43:{'riven'} if u<.7 else {'riven','kael'},
           44:{'kael','mira','riven'},45:{'mira'},46:{'elder','kael','mira','riven'},
           47:{'kael','mira','riven'},48:set(),49:set(),50:set(),51:set(),
           52:{'elder'},53:set(),54:{'elder'} if u>.5 else set(),55:{'mira','riven'},
           56:set(),57:{'kael'},58:{'kael'},59:set()}
    return casts.get(i,set())


def override_motion(shot,name,base,t):
    """Return a copy of base with individual acting and story-specific paths."""
    b=dict(base);i=shot['id'];u=max(0,min(1,t/10));e=ease(u)
    # At rest only a speaking actor gestures; observers breathe and look on.
    b['pose']='talk' if b.get('speaking') else 'idle'
    b['phase']=t+i*.13
    b['expression']='determined'
    # Set facial states the human rig actually recognises.
    if i in [0,1,3,4,8,11,13,14,50,58]:b['expression']='smile'
    if i in [6,9,10,16,29,31,37,48,49,51,52]:b['expression']='sad'
    if i in [5,17,18,21,30,33,56,59]:b['expression']='surprised'
    if i in [22,24,27,28,38,39,40,42,43,44,45,46,47]:b['expression']='determined'
    if i in [0,1,2,3,4,5,11,53,54,55]:
        b['pose']='walk';b['phase']=t*.95+i*.11
        b['x']=base['x']-60+120*e
    if i==1 and name=='kael':
        b.update(x=530+90*e,pose='point' if .38<u<.72 else 'walk',facing=1)
    if i==2:
        if name=='riven':
            b.update(x=800-180*e,pose='run' if u<.7 else 'talk',y=660-65*math.sin(math.pi*min(1,u/.65)),phase=t*1.4,facing=-1)
        elif name=='kael':b.update(x=390+75*e,pose='idle' if u<.6 else 'walk',facing=1)
    if i==3:
        if name=='mira':b.update(x=720-90*e,pose='weave' if .2<u<.72 else 'walk',facing=-1)
        if name=='kael':b.update(x=470,pose='idle',facing=1,expression='smile')
        if name=='riven':b.update(x=970+30*e,pose='idle',facing=-1)
    if i in [6,7,9,10]:
        if name=='kael':b.update(pose='listen' if i!=7 else 'talk',facing=1,x=480)
        if name=='riven':b.update(pose='weave' if i==7 and u<.45 else ('talk' if b.get('speaking') else 'idle'))
        if name=='elder':b.update(x=820,facing=-1,pose='talk' if b.get('speaking') else 'idle')
    if i==8:
        if name=='kael':b.update(x=350+275*e,pose='run' if u<.5 else 'kneel',phase=t*1.25 if u<.5 else .4,expression='determined',facing=1)
        if name=='mira':b.update(x=870,pose='point' if u>.65 else 'idle',expression='smile',facing=-1)
        if name=='riven':b.update(x=1060,pose='idle',expression='smile',facing=-1)
    if 12<=i<=17:
        caster='mira' if i==13 else 'riven' if i==14 else 'kael' if i>=15 else 'elder'
        watchers=[n for n in shot['characters'] if n!=caster]
        if name==caster:
            b.update(x=530 if i!=12 else 1000,facing=1,pose='ceremony' if (i in [13,14] or i in [15,16,17] and u>.3 or i==12) else 'walk',phase=t*.7)
            if i==15:b['x']=410+120*ease(min(1,u*2))
            if i in [16,17]:b['expression']='surprised'
        elif name in watchers:
            j=watchers.index(name);positions=[220,920,1090]
            b.update(x=positions[j],pose='idle' if not b.get('speaking') else 'talk',facing=1 if positions[j]<640 else -1)
            if i>=16:b['expression']='surprised'
    if i in [18,19,21,23]:
        b['expression']='surprised' if name!='elder' else 'determined'
        if i==19 and name=='elder':b.update(pose='seal',x=960,phase=t*.5)
        elif name=='kael':b.update(pose='listen',x=330)
        elif name=='mira':b.update(pose='point',x=550)
        elif name=='riven':b.update(pose='battle',x=760)
    if i==20:
        if name=='mira':b.update(x=550,pose='weave',facing=1,phase=t*.65)
        if name=='riven':b.update(x=835,pose='point',facing=1)
        if name=='kael':b.update(x=270+160*e,pose='walk',facing=-1)
    if i==22:
        if name=='riven':b.update(x=400+165*e,pose='attack',phase=.2+t*.65,facing=1)
        else:b.update(pose='idle',x=230 if name=='kael' else 710,facing=1)
    if 23<=i<=29:
        if name=='kael':
            if i==23:b.update(x=330+50*e,pose='point',facing=1)
            elif i==24:b.update(x=300+285*e,pose='run' if u<.75 else 'kneel',phase=t*1.4,facing=1)
            elif i in [25,26]:b.update(x=620,y=660,scale=.90,pose='kneel',phase=.5+.12*math.sin(t*2),facing=1)
            elif i==27:b.update(x=620-135*e,pose='walk',phase=t*.8,facing=-1)
            elif i==28:b.update(x=480+85*e,pose='point',facing=1)
            elif i==29:b.update(x=560-155*e,pose='fall' if u>.35 else 'dodge',phase=t*.5,y=660,expression='surprised')
        elif name=='mira':
            if i in [24,26]:b.update(x=1020,pose='weave',phase=t*.6,facing=-1)
            elif i==27:b.update(x=330,pose='rescue',phase=.4,facing=1)
            else:b.update(x=890,pose='idle',facing=-1)
        elif name=='riven':
            b.update(x=260 if i in [24,26] else 900,pose='battle' if i in [24,27,28] else 'idle',phase=t*.6,facing=1)
            if i==28:b.update(x=820-230*e,pose='dodge' if u<.5 else 'kneel',phase=.5)
        elif name=='elder':b.update(x=1080,pose='seal',phase=.3)
    if 30<=i<=35:
        if name=='kael':b.update(x=600,y=660,pose='listen' if i in [30,31,33] else 'weave' if i==32 else 'point' if i==34 else 'walk',phase=t*.6,facing=1,expression='surprised' if i<33 else 'determined')
        elif name=='mira':b.update(x=900,pose='weave' if i==35 else 'idle',phase=.3,facing=-1)
        elif name=='riven':b.update(x=1050,pose='battle',phase=t*.4,facing=1)
    if i==36:
        b.update(x=510 if name=='kael' else 850,pose='weave',phase=t*.45,facing=1 if name=='kael' else -1)
    if i==37:
        if name=='kael':b.update(x=530,pose='listen',expression='sad',phase=t*.4)
        else:b.update(x=880 if name=='mira' else 1080,pose='idle',expression='surprised',facing=-1)
    if 38<=i<=47:
        # Each participant has one job, rather than all actors cycling attacks.
        b.update(x={'kael':350,'mira':650,'riven':830,'elder':190}.get(name,base['x']),pose='idle',phase=t*.45,facing=1)
        if i==38:
            if name=='mira':b.update(pose='weave',x=640,phase=.1+t*.45)
            if name=='riven':b.update(pose='walk',x=780-95*e,facing=-1)
            if name=='kael':b.update(pose='walk',x=230+110*e)
        if i==39:
            if name=='riven':b.update(pose='kneel',x=410,phase=.6)
            if name=='mira':b.update(x=670,pose='weave',phase=.5+t*.4)
            if name=='kael':b.update(x=260,pose='point')
        if i==40:
            if name=='kael':b.update(x=470,pose='weave' if u<.35 or u>.7 else 'dodge',phase=t*.6,expression='surprised' if .35<u<.7 else 'determined')
            if name=='mira':b.update(x=720,pose='weave',phase=.5+t*.8)
            if name=='riven':b.update(x=250,pose='idle')
        if i==41:
            b.update(x={'kael':300,'mira':610,'riven':810}.get(name,180),pose='walk' if u<.3 else 'weave',phase=t*.5)
        if i==42 and name=='mira':b.update(pose='weave',y=675,phase=.4+t*.3)
        if i==43:
            if name=='riven':b.update(x=310,pose='kneel',phase=.5+(.1 if 2<t<3 or 5<t<6 or 7.5<t<9 else 0))
            if name=='mira':b.update(x=600,pose='weave',phase=.6)
            if name=='kael':b.update(x=760,pose='weave' if u>.65 else 'point',phase=t*.45)
        if i==44:
            b.update(pose='weave',phase=t*.3)
        if i==45:
            if name=='riven':b.update(x=670-160*e,pose='rescue',phase=t*.5,facing=-1)
            if name=='kael':b.update(x=570-150*e,pose='dodge',phase=.35+t*.35,expression='surprised')
            if name=='mira':b.update(x=760,pose='weave',phase=t*.5)
        if i==46:
            b.update(pose='point' if name=='elder' else 'weave',phase=t*.35)
        if i==47:
            if name=='kael':b.update(x=470,pose='seal',phase=t*.35)
            else:b.update(pose='weave' if u<.65 else 'idle',phase=t*.4)
    if 48<=i<=53:
        b.update(x={'kael':550,'mira':760,'riven':350,'elder':990}.get(name,base['x']),facing=-1 if name in ['mira','elder'] else 1,phase=t*.5)
        if i==48:
            b['pose']='kneel' if name in ['kael','riven'] else 'rescue' if name=='mira' else 'idle';b['expression']='sad'
        elif i==49:
            b['pose']='listen' if name=='kael' else 'idle';b['expression']='sad'
        elif i==50:
            b['pose']='point' if name=='riven' else 'listen' if name=='mira' else 'idle';b['expression']='sad' if name=='kael' else 'smile'
        elif i==51:
            b['pose']='talk' if name=='elder' else 'listen';b['expression']='sad'
        elif i==52:
            b['pose']='point' if name=='elder' else 'listen';b['expression']='surprised'
        elif i==53:
            b['pose']='walk';b['x']+=80*e;b['expression']='determined'
    if i in [54,55]:
        b['pose']='walk';b['x']=base['x']-75+130*e;b['phase']=t*.8
        if i==55:b['y']=base['y']+24*e
        if name=='elder':b['x']=1050+60*e
    if i==56:
        b.update(x={'kael':490,'mira':255,'riven':900,'elder':1080}.get(name,base['x']),pose='listen',expression='surprised',phase=t*.4)
    if i in [57,58]:
        b.update(x={'kael':620,'mira':450,'riven':820,'elder':1040}.get(name,base['x']),pose='seal' if name=='kael' else 'point' if name in ['mira','riven'] else 'idle',phase=t*.4,expression='determined' if i==57 else 'smile')
    if i==59:
        b.update(pose='walk' if u<.65 else 'listen',phase=t*.6,expression='surprised' if u>.65 else 'smile')
    return b


def draw_props(frame,shot,t,anchors=None,before=False,camera=(1.,0.,0.)):
    """Draw original scene props; anchors, if present, are projected already."""
    i=shot['id'];u=max(0,min(1,t/10));z,cx,cy=camera
    layer=Image.new('RGBA',frame.size);d=ImageDraw.Draw(layer,'RGBA')
    def p(x,y):return ((x-cx-640)*z+640,(y-cy-360)*z+360)
    def line(pts,fill,width=2):d.line([p(*a) for a in pts],fill=fill,width=max(1,round(width*z)),joint='curve')
    def poly(pts,fill,outline=(25,30,48,255),width=2):
        a=[p(*v) for v in pts];d.polygon(a,fill=fill)
        if outline:d.line(a+[a[0]],fill=outline,width=max(1,round(width*z)),joint='curve')
    def ellipse(box,fill,outline=None,width=2):
        a=p(box[0],box[1]);b=p(box[2],box[3]);d.ellipse((*a,*b),fill=fill,outline=outline,width=max(1,round(width*z)))
    def glow(pts,col,width=2):
        line(pts,(*col,35),width*7);line(pts,(*col,150),width*3);line(pts,(*col,255),width)
    def hand_anchor(name,which='right_hand',fallback=(640,400)):
        if anchors and name in anchors:return anchors[name].get(which,p(*fallback))
        return p(*fallback)
    def screenline(pts,col,width=2):d.line(pts,fill=col,width=max(1,round(width*z)),joint='curve')
    def ribbon_screen(x,y,angle=0,length=48):
        cs,sn=math.cos(angle),math.sin(angle)
        pts=[]
        for k in range(20):
            a=(k/19-.5)*length;b=math.sin(k*.65+t*2)*3
            pts.append((x+a*cs-b*sn,y+a*sn+b*cs))
        screenline(pts,(34,86,102,255),10)
        screenline(pts,(222,180,110,255),2)
        for k in range(2,18,3):
            a=pts[k];screenline([(a[0]-3,a[1]-4),(a[0]+3,a[1]+4)],(236,207,146,255),1)
    def child(x,y,s=.75,lying=False):
        # Small, normally proportioned anonymous student; not a chibi head rig.
        def q(a,b):
            if lying:a,b=-b*.85,a*.85
            return (x+a*s,y+b*s)
        if lying:
            pts=[q(-11,-105),q(12,-105),q(17,-47),q(-17,-47)];poly(pts,(94,96,119,255))
            for side in [-1,1]:line([q(side*9,-48),q(side*10,-18),q(side*12,0)],(45,51,75,255),8)
        else:
            poly([q(-12,-106),q(13,-106),q(16,-47),q(-16,-47)],(94,96,119,255))
            for side in [-1,1]:line([q(side*9,-48),q(side*10,-18),q(side*12,0)],(45,51,75,255),8)
        # Head is rendered as a cel-shaded polygon, with pointed original hair.
        poly([q(-11,-128),q(-13,-115),q(-7,-104),q(0,-99),q(10,-108),q(13,-119),q(6,-132)],(221,177,151,255))
        poly([q(-13,-116),q(-18,-127),q(-9,-131),q(-4,-139),q(4,-134),q(12,-136),q(16,-124),q(10,-114),q(6,-125),q(-1,-119),q(-7,-126)],(49,39,52,255))
        if not lying:
            line([q(-12,-99),q(-23,-65),q(-20,-50)],(203,163,142,255),5)
            line([q(12,-99),q(23,-65),q(17,-49)],(203,163,142,255),5)
        line([q(-6,-115),q(-1,-115)],(32,37,54,255),1)
        line([q(5,-116),q(9,-116)],(32,37,54,255),1)
    # Far objects should be occluded by characters, while held objects are drawn
    # in the after pass using exact current hand anchors.
    if before:
        if i==2:
            poly([(580,585),(760,585),(790,630),(555,630)],(92,62,55,255));poly([(590,530),(745,530),(760,585),(580,585)],(118,82,65,255))
            for xx in [590,747]:ellipse((xx-22,615,xx+22,659),(43,45,60,255),(140,110,79,255),3)
        if 12<=i<=17:
            # The same crystal persists across all tests at the same location.
            ellipse((565,621,720,654),(63,56,75,255),(166,138,92,255),3)
            poly([(600,615),(610,545),(670,545),(684,615)],(85,87,112,255),(188,169,117,255),3)
            color=(102,186,212,255) if i<16 else (40,46,65,255)
            poly([(640,252),(691,345),(680,493),(640,550),(597,493),(589,345)],color,(199,223,230,255),3)
            poly([(640,252),(639,478),(597,493),(589,345)],(63,126,173,235) if i<16 else (28,31,52,255),None)
            line([(640,252),(639,478),(680,493),(691,345)],(186,222,238,235),2)
            if i in [13,14]:
                col=(222,234,255) if i==13 else (255,104,129)
                for j in range(5):
                    a=t*.6+j*TAU/5;ellipse((640+math.cos(a)*72-4,400+math.sin(a)*115-4,640+math.cos(a)*72+4,400+math.sin(a)*115+4),(*col,210))
            if i in [16,17]:
                pts=[(640,275),(627,332),(651,367),(633,411),(650,454),(636,518)]
                line(pts,(7,10,21,255),4)
                if i==17:glow(pts,(85,237,218),1)
        if 23<=i<=27:
            # A visible person beneath a real load makes the rescue legible.
            freed=ease(u) if i==26 else 1 if i==27 else 0
            if i<27:child(760-72*freed,612+2*math.sin(t),.72,lying=True)
            else:child(500-120*ease(u),644,.62)
            lift=36*ease(u) if i==26 else 36 if i==27 else 0
            poly([(688,509-lift),(966,537-lift),(963,580-lift),(685,553-lift)],(105,112,132,255),(34,40,60,255),3)
            poly([(688,509-lift),(966,537-lift),(949,521-lift),(704,491-lift)],(151,154,171,255),None)
            for xx in [730,815,905]:line([(xx,516-lift),(xx-9,548-lift)],(67,76,98,255),2)
            for xx,yy in [(680,646),(890,654),(1010,637),(812,672)]:poly([(xx,yy),(xx+19,yy-15),(xx+35,yy+2),(xx+17,yy+10)],(112,118,137,255))
            if i in [25,26,27]:
                poly([(643,541),(670,514),(694,550)],(111,91,77,255));line([(620,500),(810,555-lift)],(69,78,92,255),10);line([(620,498),(810,553-lift)],(176,182,187,255),3)
        if i in [36,37,38,48,50]:
            for k in range(4):poly([(730+k*9,662-k*29),(864-k*7,662-k*29),(853-k*6,639-k*29),(740+k*7,639-k*29)],(128+k*6,140+k*4,162+k*3,255))
            if i==36:
                glow([(640,505),(705,550),(790,557),(796,638)],(90,244,219),3)
        if i==8:
            child(750,654,.67)
            if u<.7:
                rx=650+80*math.sin(u*4);ry=410+180*ease(u)
                ribbon_screen(*p(rx,ry),angle=t*.6,length=32*z)
        if i in [56,57,58,59]:
            # One active ring and six sealed sockets, not seven simultaneous spells.
            ellipse((522,337,742,557),(22,32,56,200),(110,167,178,255),4)
            for j in range(7):
                a=-math.pi/2+j*TAU/7;xx=640+math.cos(a)*332;yy=404+math.sin(a)*146
                col=(89,215,194,255) if j==0 else (94,64,79,255)
                if i==59 and j==1 and u>.6:col=(235,80,107,210+round(40*math.sin(t*4)))
                poly([(xx,yy-27),(xx+21,yy),(xx,yy+27),(xx-21,yy)],(23,28,47,235),col,3)
            col=(110,245,211) if i<58 else (255,219,138)
            gap=1.1*(1-ease(u)) if i==58 else 1.1
            pts=[]
            for j in range(121):
                a=gap+(TAU-gap*2)*j/120+t*.05;pts.append((640+math.cos(a)*100,437+math.sin(a)*100))
            glow(pts,col,3)
        frame.alpha_composite(layer)
        return

    # Held objects and precise contact lines belong in front of the body rig.
    if i in [3,6,9,10,11,15,16,17,29,30,31,32,33,34,35,36,37,49,51,52,53,56,57,58]:
        if anchors and 'kael' in anchors:
            hx,hy=hand_anchor('kael','right_hand')
            if i in [3,31,37,49,56]:ribbon_screen(hx,hy+9*z,angle=-.25,length=48*z)
            if i>=29:
                amp=(7 if i in [29,30,31,33,34,35] else 11)*z
                col=(93,238,213,200) if i!=49 else (103,165,169,130)
                for k in range(3):
                    a=k*TAU/3+t*.35;pts=[(hx+math.cos(a+j*.45)*amp,hy+math.sin(a+j*.45)*amp*.7) for j in range(9)]
                    screenline(pts,col,1)
    if i==3 and anchors and 'mira' in anchors and 'kael' in anchors:
        a=hand_anchor('mira');b=hand_anchor('kael','left_hand');screenline([a,((a[0]+b[0])/2,min(a[1],b[1])-28*z),b],(218,231,255,235),2)
    if i==8 and u>.65 and anchors and 'kael' in anchors:
        hx,hy=hand_anchor('kael');ribbon_screen(hx,hy,angle=.2,length=30*z)
    if i in [25,26] and anchors and 'kael' in anchors:
        hx,hy=hand_anchor('kael');screenline([(hx,hy),p(640,510)],(179,188,194,255),5)
    if i==26 and anchors and 'mira' in anchors:
        hx,hy=hand_anchor('mira');screenline([(hx,hy),p(670,514),p(694,550)],(219,233,255,255),2)
    if i==31:
        # A translucent remembered hand overlays the present, without relocating Kael.
        if anchors and 'kael' in anchors:
            hx,hy=hand_anchor('kael');op=round(100*math.sin(math.pi*u))
            d.polygon([(hx-36*z,hy-50*z),(hx-12*z,hy-53*z),(hx+4*z,hy-17*z),(hx-6*z,hy+7*z),(hx-22*z,hy+4*z)],fill=(225,201,178,op))
    if i==32:
        xx=650+10*math.sin(t);yy=470-45*math.sin(math.pi*u)
        poly([(xx-12,yy),(xx-4,yy-17),(xx+17,yy-5),(xx+10,yy+12)],(141,151,171,255),(58,71,91,255),2)
    if i in [39,43]:
        # Explicit low ground pulses: three measured attacks in shot43.
        launches=[1.,4.,7.] if i==43 else [2.]
        for launch in launches:
            age=t-launch
            if 0<age<2.0:
                xx=350+age/2*560
                pts=[(xx+j*8,650+math.sin(j*2+age*8)*9) for j in range(13)]
                glow(pts,(255,76,112),2)
    if i in [40,44,46,47]:
        if anchors and 'kael' in anchors:
            a=hand_anchor('kael');target=p(930,485 if i!=47 else 594)
            pts=[a,((a[0]+target[0])/2,a[1]-40*z),target]
            screenline(pts,(90,240,215,230),2)
            if i==40 and .32<u<.65:
                screenline([(a[0]-15*z,a[1]-15*z),(a[0]+12*z,a[1]+9*z),(a[0]-5*z,a[1]+28*z)],(255,106,137,255),3)
    if i==50 and anchors and 'mira' in anchors:
        hx,hy=hand_anchor('mira');d.polygon([(hx-23*z,hy-12*z),(hx+22*z,hy-16*z),(hx+27*z,hy+23*z),(hx-19*z,hy+25*z)],fill=(230,219,187,255),outline=(62,66,83,255))
        for k in range(4):screenline([(hx-14*z,hy+(-3+k*5)*z),(hx+15*z,hy+(-5+k*5)*z)],(124,121,113,255),1)
    if i in [52,53]:
        if anchors and 'kael' in anchors:
            hx,hy=hand_anchor('kael');target=p(1160,510)
            screenline([(hx,hy),((hx+target[0])/2,hy+30*z),target],(122,237,216,175),2)
    frame.alpha_composite(layer)
