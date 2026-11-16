"""Procedural scenes for space, ocean, earth and technology thought experiments."""

import math

from PIL import Image, ImageDraw


def science_frames(size, beat, duration, fps, *, domain, topic, disclose=False, shot=0, previous_level=None):
    for number in range(round(duration*fps)):
        seconds = number / fps
        camera = beat.camera
        if duration >= 18:
            # Alternate wide, overhead and close coverage within a long narrated beat.
            views = ('shore', 'aerial', 'pasture')
            camera = views[(views.index(camera) + int(3 * seconds / duration)) % len(views)]
        level = beat.forage
        if topic == 'tides' and previous_level is not None:
            blend = min(1, seconds / min(6, duration))
            level = previous_level + (level - previous_level) * blend
        yield science_frame(size,domain,topic,level,camera,seconds,
                            disclose=disclose and number < fps*3, shot=shot)


def science_frame(size, domain, topic, intensity, camera, seconds=0, *, disclose=False, shot=0):
    palette = {'space':'#0a1632','ocean':'#135b83','earth':'#547e8d','technology':'#17233a'}
    image = Image.new('RGB',size,palette[domain])
    draw = ImageDraw.Draw(image)
    sx,sy=size[0]/1920,size[1]/1080
    shift = {'aerial':0,'shore':-100,'pasture':80}[camera] + (shot % 5 - 2) * 24
    travel = math.sin(seconds*.38)
    level = max(0,min(1,intensity))

    def polygon(points,fill):
        draw.polygon([(round(x*sx),round(y*sy)) for x,y in points],fill=fill)

    def line(points,fill,width=4):
        draw.line([(round(x*sx),round(y*sy)) for x,y in points],fill=fill,width=max(1,round(width*sx)))

    def ellipse(x,y,rx,ry,fill,outline=None):
        draw.ellipse(tuple(round(v*k) for v,k in zip((x-rx,y-ry,x+rx,y+ry),(sx,sy,sx,sy))),
                     fill=fill,outline=outline,width=max(1,round(4*sx)))

    if domain == 'ocean' and topic == 'tides':
        from .tidal_marsh import tidal_frame
        image = tidal_frame(size, intensity, camera, seconds, shot=shot)
        draw = ImageDraw.Draw(image)
    elif domain == 'space':
        for i in range(100):
            x,y=(i*157+53)%1920,(i*113+91)%1080
            ellipse(x,y,2+i%3,2+i%3,('#f4dda6' if i%7==0 else '#aebee2'))
        x,y=1000+shift+15*travel,580
        radius=250 if camera=='aerial' else 315
        if topic in ('moon','shadows'):
            ellipse(x-375,y-180,105+145*level,105+145*level,'#cfcbcb','#f2e2c2')
        if topic == 'rings':
            ellipse(x,y+34,590,112,None,'#d8bd87')
            ellipse(x,y+34,505,88,None,'#a3a9ba')
        ellipse(x,y,radius,radius,'#2269a0','#61c7db')
        polygon([(x-radius*.84,y-radius*.39),(x-radius*.28,y-radius*.78),
                 (x+radius*.21,y-radius*.69),(x+radius*.02,y-radius*.11),
                 (x-radius*.26,y+radius*.1),(x-radius*.44,y+radius*.57),
                 (x-radius*.78,y+radius*.2)],'#6fa878')
        polygon([(x+radius*.29,y-radius*.13),(x+radius*.76,y-radius*.25),
                 (x+radius*.92,y+radius*.25),(x+radius*.46,y+radius*.69)],'#4b896e')
        if topic == 'daylight':
            line([(x+90-100*level,y-radius),(x+66-100*level,y+radius)],'#f8cf73',7)
        if topic == 'rings':
            line([(x-500,y+80),(x-300,y+117),(x+170,y+128),(x+480,y+85)],'#f0cb8d',12)
    elif domain == 'ocean':
        surface=330+16*travel
        polygon([(0,surface),(1920,surface),(1920,1080),(0,1080)],'#127cb0')
        polygon([(0,850),(510,760),(930,660),(1350,470),(1920,420),(1920,1080),(0,1080)],'#d4ab72')
        polygon([(0,950),(550,850),(1000,770),(1400,600),(1920,570),(1920,1080),(0,1080)],'#8f805f')
        for i in range(25):
            y=surface+45+(i*37)%420
            x=(i*153+48*travel)%1380
            if y < 700-x*.20:
                line([(x,y),(x+95,y),(x+140,y-8)],'#67c8e5')
        if topic == 'sea ice':
            for i in range(round(16*(1-level))+2):
                x,y=(i*121)%1420,surface+42+(i*32)%170
                polygon([(x,y),(x+90,y-15),(x+141,y+10),(x+70,y+27)],'#c7eef0')
        elif topic == 'reefs':
            for i in range(13):
                x,y=450+i*62,790-i*8
                line([(x,y),(x+8,y-67*(1-level)),(x+30,y-93*(1-level))],'#e57e76',10)
                line([(x+7,y-35),(x-22,y-65)],'#d98a79',7)
        else:
            # Vegetation at the water's edge ties the scene to the coastal ecosystem.
            for i in range(15):
                x,y=1460+i*30,467-i*2+shift*.15
                blade = 26+(i*11)%34
                polygon([(x-10,y),(x-17,y-blade),(x,y-9),(x+9,y-blade*.85),
                         (x+12,y-9),(x+22,y-blade*.58),(x+18,y)],'#5e8a58')
            if topic == 'currents':
                y=surface+125+115*level
                line([(80,y),(420,y-30),(720,y+45),(976,y+20)],'#9af1ee',11)
                polygon([(976,y+20),(925,y-4),(927,y+54)],'#9af1ee')
    elif domain == 'earth':
        polygon([(0,618),(300,455),(680,626),(1080,255),(1510,628),(1920,493),(1920,1080),(0,1080)],'#536e69')
        polygon([(720,650),(1080,255),(1410,635),(1120,525),(1010,588)],'#9d9885')
        snow=290+165*level if topic=='albedo' else 350
        polygon([(1080,255),(1080+(snow-255)*.86,snow),(1065,snow-45),
                 (1080-(snow-255)*.90,snow)],'#e4eedf')
        polygon([(0,787),(450,687),(1000,788),(1460,665),(1920,710),(1920,1080),(0,1080)],'#708841')
        if topic=='rivers':
            polygon([(0,920),(450,687),(775,756),(380,1080),(0,1080)],'#667f3d')
            polygon([(1220,1080),(1460,665),(1920,710),(1920,1080)],'#82974a')
            if level > .45:
                polygon([(1070,660),(1180,795),(1470,1080),(1210,1080),
                         (1040,810)],'#ad8152')
                polygon([(1100,831),(1202,909),(1360,1080),(1300,1080)],'#d9aa66')
            left, right = 1210-550*level, 1470-550*level
            polygon([(1000,620),(1095,620),(1180-350*level,795),(right,1080),
                     (left,1080),(1040-315*level,810)],'#49b8d7')
            polygon([(1020,638),(1074,642),(1125-350*level,793),
                     (right-80,1080),(left+40,1080),(1070-315*level,810)],'#248fab')
            for i in range(15):
                t = (i+1)/16
                y = 813+265*t
                start = (1040-315*level)*(1-t)+left*t+22+9*travel
                line([(start,y),(start+24+35*t,y-3)],'#98e1de',3)
            for i in range(35):
                x, y = 240+(i*149)%1480, 748+(i*67)%314
                t = max(0,(y-810)/270)
                lo = (1040-315*level)*(1-t)+left*t
                hi = (1180-350*level)*(1-t)+right*t
                if lo-25 < x < hi+28 or (level > .45 and 1015 < x < 1500):
                    continue
                height = 18+(i*13)%49
                polygon([(x-14,y),(x-22,y-height*.7),(x-5,y-9),(x,y-height),
                         (x+7,y-8),(x+20,y-height*.64),(x+14,y)],'#3b673d')
        else:
            for i in range(6):
                if topic=='clouds' and i/6<level:
                    continue
                x=160+i*280+20*travel
                polygon([(x,320),(x+46,293),(x+113,302),(x+148,327),(x+26,330)],'#c2ddd7')
            if topic=='wind':
                for i in range(4):
                    x,y=235+i*390,605+i%2*75
                    end=x+(170 if level<.5 else -170)
                    line([(x,y),(end,y+18)],'#f0c969',8)
                    polygon([(end,y+18),(end+(28 if level>=.5 else -28),y+2),
                             (end+(28 if level>=.5 else -28),y+34)],'#f0c969')
    else:
        polygon([(0,835),(900,654),(1920,825),(1920,1080),(0,1080)],'#253953')
        nodes=[]
        for i in range(12):
            x=135+i*148+shift*.3
            height=155+(i*137)%390
            top=790-height
            polygon([(x,790),(x,top),(x+102,top-24),(x+102,790)],'#365070')
            for row in range(4):
                for col in range(3):
                    y=top+45+row*30
                    if y<775 and (i+row+col)%10>=round(level*8):
                        l=x+15+col*22
                        polygon([(l,y),(l+12,y),(l+12,y+15),(l,y+15)],'#f5c978')
            nodes.append((x+50,top-45))
        if topic in ('internet','network','navigation'):
            x,y=900+shift,201
            ellipse(x,y,46,28,'#bbdce7')
            for a,b in nodes[::2]:
                if (a%320)/320>level:
                    line([(x,y),(a,b)],'#66c3db',4)
        else:
            for i in range(5):
                x=615+i*137
                polygon([(x,942),(x,887),(x+104,887),(x+104,942)],
                        '#e7b858' if i<round(level*5) else '#415f7a')
    if topic == 'tides':
        from .editing import paint_tide_indicator
        paint_tide_indicator(image, level)
    elif camera != 'aerial':
        width, height = image.size
        dx, dy = round(width * .07), round(height * .07)
        horizontal = (shot % 3) * dx // 2 if camera == 'shore' else dx + (shot % 3) * dx // 2
        image = image.resize(size, Image.Resampling.BILINEAR,
                             box=(horizontal, dy, width - 2*dx + horizontal, height - dy))
        draw = ImageDraw.Draw(image)
    if disclose:
        from PIL import ImageFont
        from .visuals import FONT
        draw.text((round(64*sx),round(1014*sy)),'ILLUSTRATIVE SIMULATION',
                  font=ImageFont.truetype(str(FONT),round(24*sx)),fill='#f9f0d8',
                  stroke_width=max(1,round(sx)),stroke_fill='#182027')
    return image
