"""CPU-only guided morph of three full-body poses (OpenCV + FFmpeg)."""
from pathlib import Path
import subprocess

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SCALE = 2
SIZE = (320 * SCALE, 445 * SCALE)
OUTPUT_SIZE = (1920, 1080)

# Matching silhouette landmarks, clockwise from the crown, then interior face,
# shoulder, elbow, wrist, ribcage, waist, hip, knee, calf and shoe.
POSES = [
    [(90,12),(108,5),(124,12),(130,25),(136,43),(130,55),(122,61),
     (120,70),(145,79),(192,79),(243,80),(256,85),(246,90),(193,96),
     (143,103),(140,123),(128,143),(128,174),(131,193),(130,223),
     (123,260),(112,296),(111,328),(109,364),(108,387),(119,402),
     (144,410),(149,419),(143,426),(112,430),(81,425),(79,419),
     (83,399),(82,370),(78,336),(82,308),(89,280),(88,252),
     (77,220),(77,198),(95,169),(91,137),(84,116),(79,85),
     (74,108),(63,107),(53,79),(55,54),(58,29),(70,14),
     (118,34),(126,48),(106,89),(151,91),(224,86),(114,119),(110,169),
     (103,217),(100,294),(96,352),(96,398),(119,416)],
    [(315,48),(336,41),(351,46),(359,57),(367,76),(365,89),(354,98),
     (352,108),(376,117),(421,117),(474,119),(488,125),(477,130),(429,134),
     (364,141),(358,162),(342,183),(324,212),(329,229),(350,251),
     (370,274),(378,294),(366,324),(351,354),(340,384),(345,399),
     (371,410),(376,419),(372,425),(341,430),(308,425),(305,418),
     (310,396),(313,372),(323,340),(336,314),(347,295),(323,279),
     (287,264),(270,246),(268,226),(284,205),(297,186),(304,153),
     (307,108),(300,139),(290,123),(286,98),(290,68),(303,49),
     (351,69),(358,84),(334,125),(379,129),(453,124),(328,160),(312,201),
     (306,240),(360,291),(336,350),(325,396),(345,416)],
    [(548,124),(570,115),(586,120),(595,131),(601,147),(599,163),(586,173),
     (583,184),(610,192),(660,192),(706,195),(718,199),(711,205),(664,211),
     (595,214),(589,234),(567,252),(543,276),(558,277),(583,281),
     (605,292),(615,307),(605,329),(583,361),(570,387),(578,402),
     (603,411),(609,418),(604,425),(573,430),(541,426),(538,419),
     (542,398),(553,374),(563,346),(579,319),(588,305),(565,320),
     (532,328),(507,326),(490,315),(482,298),(487,279),(506,256),
     (519,222),(521,186),(512,171),(522,152),(525,136),(534,126),
     (585,144),(594,159),(565,200),(618,204),(686,200),(557,229),(533,261),
     (519,296),(599,305),(572,354),(557,398),(576,416)],
]
EDGE_COUNT = 50
# Correspondences along the same garment seam in each of the three poses.
STRIPE = np.float32([
    [(159,265),(155,298),(156,331),(156,357),(151,390),
     (145,419),(138,447),(132,469),(131,500),(134,528),(139,565)],
    [(440,311),(433,326),(433,341),(444,357),(464,374),
     (486,390),(506,409),(522,433),(510,462),(493,505),(476,566)],
    [(747,406),(744,421),(751,432),(770,438),(798,437),
     (826,436),(851,438),(873,450),(854,482),(837,520),(818,566)],
]) * (720 / 1050)
FOOT_X = [112,341,573]


def load_poses():
    sheet=cv2.imread(str(ROOT/"squat-keyframes.png"))
    if sheet is None:
        raise FileNotFoundError("squat-keyframes.png")
    sheet=cv2.resize(sheet,(720*SCALE,450*SCALE), interpolation=cv2.INTER_CUBIC)
    actors, landmarks=[],[]
    for i, coords in enumerate(POSES):
        points=np.asarray(coords,dtype=np.float32)*SCALE
        # Work on the original position for segmentation, then align planted feet.
        silhouette=np.zeros(sheet.shape[:2],np.uint8)
        cv2.fillPoly(silhouette,[np.round(points[:EDGE_COUNT]).astype(np.int32)],1)
        brush=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15*SCALE,15*SCALE))
        labels=np.where(silhouette,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
        labels[cv2.erode(silhouette,brush)>0]=cv2.GC_FGD
        labels[cv2.dilate(silhouette,brush)==0]=cv2.GC_BGD
        cv2.grabCut(sheet,labels,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
        alpha=cv2.GaussianBlur(((labels%2)*255).astype(np.uint8),(3,3),.5)
        # Composite premultiplied pixels so the gray studio never bleeds into the jungle.
        rgba=np.dstack(((sheet*(alpha[...,None]/255.)).round().astype(np.uint8),alpha))
        transform=np.float32([[1,0,(128-FOOT_X[i])*SCALE],[0,1,0]])
        actors.append(cv2.warpAffine(rgba,transform,SIZE))
        points[:,0]+=(128-FOOT_X[i])*SCALE
        border=np.float32([(1,1),(318,1),(318,443),(1,443)])*SCALE
        stripe=STRIPE[i].copy()*SCALE
        stripe[:,0]+=(128-FOOT_X[i])*SCALE
        landmarks.append(np.vstack((points,border,stripe)))
    return actors, landmarks


GRID_SIZE = (81, 113)
GRID = np.stack(np.meshgrid(np.linspace(0, SIZE[0]-1, GRID_SIZE[0], dtype=np.float32),
                             np.linspace(0, SIZE[1]-1, GRID_SIZE[1], dtype=np.float32)), axis=-1)
NORMALIZE = np.float32(max(SIZE))
PIXELS = np.stack(np.meshgrid(np.arange(SIZE[0],dtype=np.float32),
                               np.arange(SIZE[1],dtype=np.float32)),axis=-1)


def basis(query, anchors):
    distances = np.sum((query[..., None, :] - anchors)**2, axis=-1)
    return distances * np.log(np.maximum(distances, 1e-9))


def warp_pair(a, b, old_a, old_b, new):
    """Smooth inverse warps with one shared field for the two source poses."""
    anchors = new / NORMALIZE
    affine = np.column_stack((np.ones(len(new), np.float32), anchors))
    radial = basis(anchors, anchors)
    regularization=np.full(len(new),.00025,np.float32)
    regularization[-STRIPE.shape[1]:]=.000012
    radial.flat[::len(new)+1] += regularization
    system = np.block([[radial, affine], [affine.T, np.zeros((3,3), np.float32)]])
    values = np.column_stack((old_a,old_b)) / NORMALIZE
    coefficients = np.linalg.solve(system, np.vstack((values, np.zeros((3,4),np.float32))))
    grid = GRID / NORMALIZE
    field = (basis(grid, anchors) @ coefficients[:-3] + coefficients[-3]
             + grid @ coefficients[-2:])*NORMALIZE
    mapped=[]
    for image, offset in ((a,0),(b,2)):
        motion=field[...,offset:offset+2]-GRID
        coords=PIXELS+cv2.resize(motion,SIZE,interpolation=cv2.INTER_CUBIC)
        mapped.append(cv2.remap(image, coords, None, cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT))
    return mapped


def smoothstep(x):
    x=np.clip(x,0,1)
    return float(x*x*x*(10+x*(-15+6*x)))


def squat_depth(seconds):
    if seconds < 2.38:
        return 2*smoothstep((seconds-.50)/1.88)
    if seconds < 2.68:
        return 2.
    return 2*(1-smoothstep((seconds-2.68)/1.54))


def curve_poses(points, depth):
    """Monotone cubic path with a shared tangent through the middle key pose."""
    left=points[1]-points[0]
    right=points[2]-points[1]
    middle=np.zeros_like(left)
    mask=left*right>0
    middle[mask]=2*left[mask]*right[mask]/(left[mask]+right[mask])
    j=min(1,int(depth))
    t=depth-j
    tangent=(left,middle,right)
    target=((2*t**3-3*t*t+1)*points[j]+(t**3-2*t*t+t)*tangent[j]
            + (-2*t**3+3*t*t)*points[j+1]+(t**3-t*t)*tangent[j+1])
    # Stabilize the toes and heel throughout the shot.
    target[25:33]=points[0][25:33]
    target[61]=points[0][61]
    return j,t,target


def feather_rows(image, start, end):
    mask=np.clip((end-np.arange(SIZE[1])/SCALE)/(end-start),0,1)
    return np.rint(image*mask[:,None,None]).astype(np.uint8)


def preserve_head(layer, hair_and_face, first, dst):
    # Keep the same face texture and head proportions through descent and rise.
    anchor=[0,4,7,50,51]
    matrix,_=cv2.estimateAffinePartial2D(first[anchor],dst[anchor],method=cv2.LMEDS)
    if matrix is None:
        return layer
    warped=cv2.warpAffine(hair_and_face,matrix,SIZE,flags=cv2.INTER_LINEAR)
    mask=np.zeros((SIZE[1],SIZE[0]),dtype=np.uint8)
    region=np.ascontiguousarray(dst[[0,1,2,3,4,5,6,7,8,52,43,44,45,46,47,48,49]])
    cv2.fillConvexPoly(mask,cv2.convexHull(np.round(region).astype(np.int32)),255)
    mask=cv2.dilate(mask,np.ones((21,21),np.uint8))
    mask=cv2.GaussianBlur(mask,(27,27),6).astype(np.float32)/255
    row=np.arange(SIZE[1],dtype=np.float32)[:,None]
    fade=np.clip((dst[52,1]+14*SCALE-row)/(28*SCALE),0,1)
    mask=(mask*fade)[:,:,None]
    return np.rint(layer*(1-mask)+warped*mask).astype(np.uint8)


def main():
    cv2.setNumThreads(2)
    actors, points=load_poses()
    background=cv2.imread(str(ROOT.parent/"jungle.png"))
    background=cv2.resize(background,OUTPUT_SIZE,interpolation=cv2.INTER_CUBIC)
    y,x=108,654
    dims=(638,888)
    shadow=background.copy()
    cv2.ellipse(shadow,(x+254,y+856),(80,13),0,0,360,(32,29,17),-1,cv2.LINE_AA)
    cv2.addWeighted(background,.73,shadow,.27,0,dst=background)
    first_head=feather_rows(actors[0],98,121)
    output=ROOT/"squat-cpu-preview.mp4"
    with subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","bgr24",
                            "-video_size","1920x1080","-framerate","24","-i","-","-c:v","libx264",
                            "-threads","2","-preset","fast","-crf","18","-pix_fmt","yuv420p",
                            "-movflags","+faststart",str(output)],stdin=subprocess.PIPE) as ff:
        for i in range(144):
            j,t,dst=curve_poses(points,squat_depth(i/24))
            a,b=warp_pair(actors[j],actors[j+1],points[j],points[j+1],dst)
            source=cv2.addWeighted(a,1-t,b,t,0)
            # A partially covered silhouette is a solid surface, not a dissolve.
            # Recover its color from the contributing pose before tightening alpha.
            alpha=source[...,3:4].astype(np.float32)
            tight=np.clip((alpha-35.)*(255./171.),0,255)
            color_scale=np.divide(tight,alpha,out=np.zeros_like(alpha),where=alpha>0)
            source=np.concatenate(((source[...,:3]*color_scale).clip(0,255),tight),axis=2).astype(np.uint8)
            source=preserve_head(source,first_head,points[0],dst)
            actor=cv2.resize(source,dims,interpolation=cv2.INTER_LINEAR)
            alpha=actor[:,:,3:4].astype(np.float32)/255
            frame=background.copy()
            target=frame[y:y+dims[1],x:x+dims[0]]
            target[:]=np.clip(np.rint(target*(1-alpha)+actor[:,:,:3]),0,255).astype(np.uint8)
            ff.stdin.write(frame.tobytes())
        ff.stdin.close()
        if ff.wait():
            raise RuntimeError("FFmpeg encoding failed")


if __name__=="__main__":
    main()
