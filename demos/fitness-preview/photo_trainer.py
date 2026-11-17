"""Animate the original generated trainer pixels as a layered cutout."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render import pose, smooth

ROOT = Path(__file__).resolve().parent
SOURCE = Image.open(ROOT / 'trainer-concept.png').convert('RGB').crop((0,0,568,1024)).resize((425,775))
OUTLINE = [(201,48),(209,21),(224,8),(245,6),(264,22),(275,57),(270,93),(257,120),
           (268,137),(304,147),(321,172),(333,213),(360,250),(381,294),(398,325),
           (418,359),(420,401),(407,397),(395,374),(386,366),(379,341),(352,313),
           (324,277),(301,238),(290,210),(280,255),(290,286),(310,339),(317,384),
           (313,439),(301,494),(308,529),(321,570),(316,630),(314,672),(333,710),(337,735),
           (285,736),(283,712),(290,674),(288,650),(277,601),(267,557),(263,504),(252,448),
           (237,379),(234,374),(229,423),(214,486),(203,530),(198,574),(179,627),(172,674),
           (181,706),(182,735),(131,736),(134,712),(146,675),(151,647),(146,574),(150,547),
           (161,516),(163,492),(154,449),(151,399),(155,357),(168,310),(187,271),(190,246),
           (177,216),(161,244),(143,283),(102,326),(81,347),(76,370),(64,377),(55,400),
           (44,400),(44,368),(58,343),(72,317),(94,279),(121,243),(138,207),(142,172),
           (153,154),(170,142),(193,137),(207,129),(203,114),(196,97),(198,76)]
raw = np.asarray(SOURCE)
silhouette = np.zeros(raw.shape[:2], np.uint8)
cv2.fillPoly(silhouette, [np.int32(OUTLINE)], 1)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(11,11))
inner = cv2.erode(silhouette, kernel)>0
outer = cv2.dilate(silhouette, kernel)>0
labels = np.where(silhouette,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
labels[inner] = cv2.GC_FGD
labels[~outer] = cv2.GC_BGD
cv2.grabCut(raw,labels,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
alpha = Image.fromarray(((labels%2)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.55))
PHOTO = SOURCE.convert('RGBA')
PHOTO.putalpha(alpha)


def part(points):
    mask = Image.new('L',PHOTO.size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    mask = np.minimum(np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5))), np.asarray(alpha))
    tree = PHOTO.copy()
    tree.putalpha(Image.fromarray(mask))
    return tree


HEAD = part([(190,0),(279,0),(279,125),(264,149),(233,155),(197,144),(190,116)])
TORSO = part([(163,152),(202,130),(266,130),(306,152),(291,208),(282,252),(301,313),
              (321,350),(316,391),(239,382),(229,382),(151,390),(145,357),(177,263),(173,220)])
PIECES = [
    (
        ([ (145,341),(231,341),(239,383),(220,459),(206,527),(156,535),(145,470) ],(193,365),(181,519)),
        ([ (152,488),(208,488),(206,549),(183,626),(175,683),(142,683),(141,581) ],(181,519),(162,665)),
        ([ (141,662),(175,662),(189,744),(125,744) ],(162,665),(155,735)),
        ([ (140,143),(186,140),(194,163),(171,219),(147,260),(108,256),(124,213) ],(167,171),(130,251)),
        ([ (120,233),(157,248),(141,290),(82,350),(57,341),(87,277) ],(130,251),(71,338)),
        ([ (55,322),(86,334),(82,378),(57,407),(37,406),(40,366) ],(71,338),(51,391)),
    ),
    (
        ([(233,341),(319,341),(327,461),(307,530),(262,535),(243,456),(230,382)],(277,365),(287,515)),
        ([(256,488),(307,488),(326,574),(317,683),(286,683),(263,569)],(287,515),(306,665)),
        ([(287,661),(316,661),(344,743),(278,743)],(306,665),(314,735)),
        ([(278,139),(319,143),(333,202),(354,247),(320,267),(291,221),(277,181)],(301,171),(336,254)),
        ([(316,242),(348,231),(381,287),(408,342),(383,358),(349,317),(321,278)],(336,254),(394,343)),
        ([(378,334),(405,331),(424,369),(424,406),(403,405),(384,374)],(394,343),(416,392)),
    ),
]
PIECES = [[(part(outline), a, b) for outline,a,b in side] for side in PIECES]


def warp(layer, image, source_a, source_b, target_a, target_b, thick=.62):
    p, q = np.array(target_a), np.array(target_b)
    u, v = np.array(source_a), np.array(source_b)
    axis = v-u
    stride = q-p
    length = float(np.linalg.norm(stride))
    if length < 2:
        return
    normal = np.array([-stride[1],stride[0]]) / length
    from_basis = np.array([axis,[-axis[1],axis[0]]]).T
    to_basis = np.array([stride,normal*np.linalg.norm(axis)*thick]).T
    matrix = to_basis @ np.linalg.inv(from_basis)
    inv = np.linalg.inv(matrix)
    box = image.getbbox()
    points = np.array([(box[0],box[1]),(box[2],box[1]),(box[0],box[3]),(box[2],box[3])])
    points = (points-u) @ matrix.T + p
    x,y = np.floor(points.min(axis=0)).astype(int)-2
    right,bottom = np.ceil(points.max(axis=0)).astype(int)+2
    offset = u + inv @ ([x,y]-p)
    coeff = (*inv[0],offset[0],*inv[1],offset[1])
    tile = image.transform((right-x,bottom-y),Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC)
    layer.alpha_composite(tile,(x,y))


def face(t, speech):
    blink = max(max(0,1-abs(t-mark)/.10) for mark in (2.4,6.2,12.5,16.8,21.1,27.8,34.2,38.6,43.7,48.1,53.7,58.2,62.4,69.1))
    if speech < .08 and blink < .05:
        return HEAD
    image = HEAD.copy()
    d = ImageDraw.Draw(image)
    for x,y in ((222,72),(248,71)):
        if blink > .14:
            height = max(1, round(3*blink))
            d.ellipse((x-8,y-height,x+8,y+height),fill=(151,93,60,255))
            d.arc((x-8,y-4,x+8,y+3),30,150,fill=(66,39,29,255),width=2)
    if speech >= .08:
        width = 9 + int(2 * math.sin(t*26))
        height = 2 + round(6 * speech)
        d.ellipse((234-width,98-height,234+width,98+height),fill=(146,75,55,255))
        d.ellipse((236-width,99-height,232+width,97+height),fill=(67,32,26,255))
        if height >= 4:
            d.line((230,96,238,96),fill=(223,184,152,255),width=1)
    return image


def trainer(frame,mode,move,t,absolute_time,speech):
    hip,neck,head,limbs = pose(mode,move,t)
    scale = 222
    cx = 530 if mode=='workout' else 555
    yaw = -.42 if mode=='workout' and move==1 else .08
    floor = 601
    breath = math.sin(absolute_time*2.4)*1.05

    def pt(p):
        x,y,z=p
        return np.array([cx+scale*(x*math.cos(yaw)+z*math.sin(yaw)),floor-scale*(y+.16*z)])

    layer = Image.new('RGBA',frame.size)
    projected = []
    for i, (thigh,knee,foot,shoulder,elbow,hand) in enumerate(limbs):
        hip_side, knee_pos, ankle = pt(thigh), pt(knee), pt(foot)
        p_sh, p_el, p_hand = pt(shoulder), pt(elbow), pt(hand)
        side = -1 if i==0 else 1
        # Position the hand texture from wrist to fingertips instead of bending
        # the forearm texture all the way to the end of the hand.
        hand_dir = (p_hand-p_el) / max(1,np.linalg.norm(p_hand-p_el))
        bend_in = .18 * math.sin(t*3.3)
        hand_dir = np.array([hand_dir[0]+bend_in,hand_dir[1]])
        toe = ankle + [side*3, 37]
        # The rig ankle point is just above the sole.
        ankle = ankle + [0,-21]
        toe = ankle + [side*4,39]
        knee_pos += [0,7]
        hip_side += [side*8,-6]
        projected.append([(hip_side,knee_pos),(knee_pos,ankle),(ankle,toe),
                          (p_sh,p_el),(p_el,p_hand),(p_hand,p_hand+hand_dir*32)])
    for i in (0,1):
        for j in (2,1,0):
            warp(layer,*PIECES[i][j],*projected[i][j],.60)
    n = pt(neck) + [0,1+breath]
    h = pt(hip)+[0,-5]
    warp(layer,TORSO,(233,143),(234,362),n,h,.60)
    for i in (0,1):
        for j in (5,4,3):
            warp(layer,*PIECES[i][j],*projected[i][j],.60)
    upper = n + [-3*math.sin(t*1.4),-76]
    warp(layer,face(absolute_time,speech),(234,140),(234,17),n,upper,.60)
    frame.paste(layer,(0,0),layer)
