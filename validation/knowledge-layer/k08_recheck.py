# Kernel: rigorous recheck of EppJob.odb geometry / U3 / RF3 / PEEQ / deformed area.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from odbAccess import openOdb
odb = openOdb('EppJob.odb', readOnly=True)
steps = list(odb.steps.keys())
step = odb.steps[steps[-1]]
fr = step.frames[-1]
out = {'job': 'EppJob', 'step': steps[-1], 'nframes': len(step.frames),
       'frame_index': len(step.frames)-1, 'frame_time': fr.frameValue}

inst = odb.rootAssembly.instances['B-1']
# initial nodal coords
nodes = inst.nodes
x0 = [n.coordinates[0] for n in nodes]
y0 = [n.coordinates[1] for n in nodes]
z0 = [n.coordinates[2] for n in nodes]
out['init_bbox'] = {
  'x': [round(min(x0),4), round(max(x0),4)],
  'y': [round(min(y0),4), round(max(y0),4)],
  'z': [round(min(z0),4), round(max(z0),4)],
}
out['init_height'] = round(max(z0)-min(z0), 4)
out['init_xy'] = [round(max(x0)-min(x0),4), round(max(y0)-min(y0),4)]

# deformed coords = coords + U
U = fr.fieldOutputs['U']
# map node label -> disp
disp = {}
for v in U.values:
    disp[v.nodeLabel] = v.data
deform_x=[]; deform_y=[]; deform_z=[]
for n in nodes:
    d = disp.get(n.label, (0.0,0.0,0.0))
    deform_x.append(n.coordinates[0]+d[0])
    deform_y.append(n.coordinates[1]+d[1])
    deform_z.append(n.coordinates[2]+d[2])
out['deform_bbox'] = {
  'x': [round(min(deform_x),4), round(max(deform_x),4)],
  'y': [round(min(deform_y),4), round(max(deform_y),4)],
  'z': [round(min(deform_z),4), round(max(deform_z),4)],
}
out['deform_height'] = round(max(deform_z)-min(deform_z),4)
out['deform_xy'] = [round(max(deform_x)-min(deform_x),4), round(max(deform_y)-min(deform_y),4)]

# top face U3 (nodes near init z=10)
top_u3 = [disp[n.label][2] for n in nodes if abs(n.coordinates[2]-10.0) < 1e-6]
bot_u3 = [disp[n.label][2] for n in nodes if abs(n.coordinates[2]-0.0) < 1e-6]
out['top_U3_minmax'] = [round(min(top_u3),5), round(max(top_u3),5)]
out['bot_U3_minmax'] = [round(min(bot_u3),5), round(max(bot_u3),5)]

# RF3 sum on FIXED set
rf = fr.fieldOutputs['RF']
reg = odb.rootAssembly.nodeSets['FIXED']
tot=[0.0,0.0,0.0]; nrf=0
for v in rf.getSubset(region=reg).values:
    nrf+=1
    for i in range(3): tot[i]+=v.data[i]
out['rf_nodes']=nrf
out['RF_total']=[round(x,3) for x in tot]
out['RF3_mag']=round(abs(tot[2]),3)

# PEEQ distribution
peeq = fr.fieldOutputs['PEEQ']
pvals=[float(v.data) for v in peeq.values]
out['PEEQ_minmax']=[round(min(pvals),6), round(max(pvals),6)]
out['PEEQ_mean']=round(sum(pvals)/len(pvals),6)

# Mises distribution
s = fr.fieldOutputs['S']
mises=[]
for v in s.values:
    d=v.data
    m=(((d[0]-d[1])**2+(d[1]-d[2])**2+(d[2]-d[0])**2+6*(d[3]**2+d[4]**2+d[5]**2))/2.0)**0.5
    mises.append(m)
out['mises_minmax']=[round(min(mises),3), round(max(mises),3)]
odb.close()
print(json.dumps(out, default=float))
