"""Local reference-layout edits; base composition and unedited scenery stay intact."""
from pathlib import Path
import colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION='regional-cast-v1'
# Coordinates refer only to the bundled five-child reference, not arbitrary art.
FACES=[(.055,.12,.205,.36),(.245,.205,.37,.395),(.387,.005,.612,.325),
       (.645,.23,.765,.415),(.785,.13,.965,.375)]
ANIMALS=[(.155,.69,.335,.99),(.825,.70,.99,.995)]
PANTS=[(.008,.58,.235,.755),(.24,.58,.375,.74),(.355,.60,.675,.82),
       (.65,.59,.78,.75),(.755,.575,.99,.765)]
COLORS={'coral':'#ff6b78','teal':'#15c8bf','yellow':'#ffdf2b','purple':'#a84ae8',
        'lime':'#8be62b','blue':'#2785ed','pink':'#f25ab8','orange':'#fa9b24'}


def pixel_box(box,size):
    return tuple(round(v*size[i%2]) for i,v in enumerate(box))


def tint_clothing(image,cast):
    """Tint saturated garment pixels inside known clothing areas; retain shading."""
    out=image.convert('RGB').copy()
    for box,child in zip(PANTS,cast['children']):
        area=pixel_box(box,out.size)
        patch=out.crop(area)
        hsv=np.array(patch.convert('HSV'))
        original=np.array(patch).astype(float)
        # Avoid the low-saturation skin, highlights and surrounding dark floor.
        skin=(hsv[:,:,0]>=10)&(hsv[:,:,0]<=28)&(hsv[:,:,1]<180)
        mask=(hsv[:,:,1]>145)&(hsv[:,:,2]>65)&~skin
        color=COLORS[child['color']]
        rgb=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
        hue,saturation,_=colorsys.rgb_to_hsv(*rgb)
        hsv[:,:,0]=round(hue*255)
        hsv[:,:,1]=np.maximum(hsv[:,:,1],round(saturation*200))
        changed=Image.fromarray(hsv,'HSV').convert('RGB')
        blend=Image.fromarray((mask*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.6))
        out.paste(changed,area,blend)
    return out


def refine_thumbnail(target,plan,generate_image,resume=False):
    """Restyle faces locally and replace the two animals with fresh species."""
    target=Path(target)
    cast=plan['thumbnail_cast']
    with Image.open(target) as source:
        canvas=source.convert('RGB')
    folder=target.parent/'thumbnail-regions'
    folder.mkdir(exist_ok=True)
    jobs=[]
    for i,(box,child) in enumerate(zip(FACES,cast['children'])):
        prompt=(f"Cute 3D storybook cartoon portrait of one smiling toddler {child['gender']}, "
                f"{child['face']}, distinct expressive face, happy open smile, soft rounded cheeks. "
                'Single child head, colorful soft party lights, polished animated movie style, no text.')
        jobs.append((f'face-{i}',box,prompt,.82,True))
    for i,(box,species) in enumerate(zip(ANIMALS,cast['animals'])):
        species={'puppies':'puppy','kittens':'kitten','bunnies':'bunny','ducklings':'duckling',
                 'lambs':'lamb','pandas':'panda','baby elephants':'elephant calf',
                 'baby turtles':'turtle','baby deer':'fawn','chicks':'chick'}[species]
        prompt=(f'One adorable baby {species}, cute 3D storybook cartoon, complete animal body, '
                'big expressive eyes, paws on a colorful party floor, vibrant soft light, no children, no text.')
        jobs.append((f'animal-{i}',box,prompt,1.,False))
    for i,(name,box,prompt,strength,face) in enumerate(jobs):
        area=pixel_box(box,canvas.size)
        crop=canvas.crop(area)
        initial=folder/f'{name}-input.png';result=folder/f'{name}-result.png'
        crop.save(initial)
        print(f'Refining thumbnail region {name}: {prompt}',flush=True)
        cached=False
        if resume and result.exists():
            try:
                with Image.open(result) as saved:
                    saved.verify()
                cached=True
            except (OSError,ValueError):
                pass
        if not cached:
            generate_image(prompt,result,seed=plan['seed']+7919*(i+1),width=512,height=512,
                           steps=12,reference_image=initial,strength=strength)
        else:
            print(f'Reusing completed region {name}',flush=True)
        with Image.open(result) as generated:
            patch=generated.convert('RGB').resize(crop.size,Image.Resampling.LANCZOS)
        # Feather only the crop boundary. Everything outside the region remains
        # byte-identical; face crops use an ellipse to preserve nearby shoulders.
        mask=Image.new('L',crop.size)
        draw=ImageDraw.Draw(mask)
        pad=max(0,min((min(crop.size)-1)//2,round(min(crop.size)*.035)))
        if face:
            draw.ellipse((pad,pad,crop.width-pad,crop.height-pad),fill=255)
        else:
            draw.rounded_rectangle((pad,pad,crop.width-pad,crop.height-pad),radius=pad*2,fill=255)
        mask=mask.filter(ImageFilter.GaussianBlur(max(1,min(crop.size)*.035)))
        canvas.paste(patch,area,mask)
    canvas=tint_clothing(canvas,cast)
    canvas.save(target)
