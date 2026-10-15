import json,sys
from PIL import Image
m=json.load(open('manifest.json'));W,H,CX=560,240,330
def frame(s):
    im=Image.new('RGBA',(W,H),(110,170,230,255))
    for L in m['layers']:
        st=Image.open(L['name']+'.png').convert('RGBA');sx=int(round((s-L['s0'])*L['F']-CX))
        im.alpha_composite(st.crop((sx,0,sx+W,H)))
    return im.resize((W*2,H*2),Image.NEAREST)
out=Image.new('RGBA',(W*2,H*2*4))
for i,s in enumerate([float(x) for x in sys.argv[1:]]):out.paste(frame(s),(0,i*H*2))
out.save('prev.png')
