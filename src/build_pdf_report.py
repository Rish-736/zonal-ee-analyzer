"""
Zonal E/E Architecture — PDF Report Generator v3
Includes three-way zone assignment comparison (Section 5 new)
"""
import sys, os, io, math, struct
sys.path.insert(0, 'src')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)

NAVY=colors.HexColor("#1F4E79"); BLUE=colors.HexColor("#2E75B6")
LBLUE=colors.HexColor("#DEEAF1"); LGRAY=colors.HexColor("#F2F2F2")
DGRAY=colors.HexColor("#595959"); RED=colors.HexColor("#C00000")
LRED=colors.HexColor("#FCE4D6"); GREEN=colors.HexColor("#375623")
LGREEN=colors.HexColor("#E2EFDA"); WHITE=colors.white; BLACK=colors.black
ZONE_HEX={'PTZ':'#E8604C','CHZ':'#F5A623','CBZ':'#4A90D9','FRZ':'#27AE60'}
ZC_HEX='#2C3E50'

ABBREVS=[
    ("ABS","Anti-lock Braking System"),("ACM","Aftertreatment Control Module"),
    ("BCM","Body Control Module"),("CAN","Controller Area Network"),
    ("CBZ","Cab Zone"),("CGW","Central Gateway"),("CHZ","Chassis Zone"),
    ("CPC","Common Powertrain Controller"),("CTP","Common Telematics Platform"),
    ("DCMD","Door Controller — Driver Side"),("DCMP","Door Controller — Passenger Side"),
    ("DEF","Diesel Exhaust Fluid"),("DPF","Diesel Particulate Filter"),
    ("DTCI","Daimler Truck Innovation Center India"),
    ("DTNA","Daimler Trucks North America"),
    ("E/E","Electrical / Electronic"),("ECAS","Electronic Controlled Air Suspension"),
    ("ECM","Engine Control Module"),("ECU","Electronic Control Unit"),
    ("EPS","Electric Power Steering"),("ESC","Electronic Stability Control"),
    ("FCM","Forward Collision Module"),("FCU","Front Climate Control Unit"),
    ("FRZ","Front Zone"),("HVAC","Heating Ventilation and Air Conditioning"),
    ("ICU","Instrument Cluster Unit"),
    ("J1939","SAE Standard for heavy-duty vehicle CAN network"),
    ("LDW","Lane Departure Warning"),("MCM","Motor Control Module"),
    ("MPC","Multi-Purpose Camera"),("MSF","Modular Switch Field"),
    ("NHTSA","National Highway Traffic Safety Administration"),
    ("ONGUARD","OnGuard Headway / Collision Controller"),
    ("OTA","Over-the-Air software update"),("PTZ","Powertrain Zone"),
    ("SAE","Society of Automotive Engineers"),
    ("SAM_CAB","Signal Acquisition Module — Cab"),
    ("SAM_CH","Signal Acquisition Module — Chassis"),
    ("SAS","Steering Angle Sensor"),("SCR","Selective Catalytic Reduction"),
    ("SRS","Supplemental Restraint System (Airbag)"),
    ("TCM","Transmission Control Module"),("TCO","Tachograph"),
    ("TLM","Telematics Module"),("TPMS","Tire Pressure Monitoring System"),
    ("TSN","Time-Sensitive Networking"),("ZC","Zone Controller"),
    ("ZC-CAB","Zone Controller — Cab Zone"),
    ("ZC-CH","Zone Controller — Chassis Zone"),
    ("ZC-FR","Zone Controller — Front Zone"),
    ("ZC-PT","Zone Controller — Powertrain Zone"),
    ("100BASE-T1","Automotive Ethernet — single-pair 100 Mbps"),
]

# ── STYLES ────────────────────────────────────────────────────────────────
def make_styles():
    base=getSampleStyleSheet()
    def add(name,**kw): base.add(ParagraphStyle(name=name,**kw))
    add('CoverTitle',fontName='Helvetica-Bold',fontSize=26,textColor=NAVY,alignment=TA_CENTER,spaceAfter=6,leading=32)
    add('CoverSub',fontName='Helvetica',fontSize=13,textColor=BLUE,alignment=TA_CENTER,spaceAfter=4,leading=18)
    add('CoverMeta',fontName='Helvetica',fontSize=9,textColor=DGRAY,alignment=TA_CENTER,spaceAfter=3,leading=13)
    add('SectionHead',fontName='Helvetica-Bold',fontSize=13,textColor=NAVY,spaceBefore=12,spaceAfter=5,leading=17)
    add('SubHead',fontName='Helvetica-Bold',fontSize=10,textColor=BLUE,spaceBefore=7,spaceAfter=3,leading=14)
    add('Body',fontName='Helvetica',fontSize=9,textColor=BLACK,spaceBefore=3,spaceAfter=4,leading=13,alignment=TA_JUSTIFY)
    add('BodyPlain',fontName='Helvetica',fontSize=9,textColor=BLACK,spaceBefore=3,spaceAfter=4,leading=13)
    add('Caption',fontName='Helvetica-Oblique',fontSize=8,textColor=DGRAY,alignment=TA_CENTER,spaceAfter=6)
    add('BulletItem',fontName='Helvetica',fontSize=9,textColor=BLACK,leftIndent=12,spaceBefore=2,spaceAfter=2,leading=13)
    return base

# ── IMAGE HELPER ──────────────────────────────────────────────────────────
def fig_to_image(fig,width_mm=145):
    buf=io.BytesIO()
    fig.savefig(buf,format='png',dpi=150,bbox_inches='tight',facecolor='white')
    plt.close(fig); buf.seek(16)
    raw=buf.read(8); px_w=struct.unpack('>I',raw[0:4])[0]; px_h=struct.unpack('>I',raw[4:8])[0]
    buf.seek(0); aspect=px_h/px_w; width_pt=width_mm*mm; height_pt=width_pt*aspect
    img=Image(buf,width=width_pt,height=height_pt); img.hAlign='CENTER'; return img

# ── TABLE HELPER ──────────────────────────────────────────────────────────
def make_rl_table(data,col_widths,style_cmds,hdr_fill=NAVY):
    t=Table(data,colWidths=col_widths,repeatRows=1)
    base=[('BACKGROUND',(0,0),(-1,0),hdr_fill),('TEXTCOLOR',(0,0),(-1,0),WHITE),
          ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
          ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
          ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,LGRAY]),
          ('GRID',(0,0),(-1,-1),0.4,colors.HexColor("#CCCCCC")),
          ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
          ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
          ('WORDWRAP',(0,0),(-1,-1),True)]+style_cmds
    t.setStyle(TableStyle(base)); return t

# ── CHART: LEGACY + ZONAL TOPOLOGY PAIR ──────────────────────────────────
def make_topology_pair(g_leg,g_zon,truck_data,vshort):
    G=g_leg; fig,ax=plt.subplots(figsize=(11,6))
    ax.set_facecolor('#F8F9FA'); fig.patch.set_facecolor('white')
    pos=nx.kamada_kawai_layout(G,scale=2.5)
    nc=[ZONE_HEX.get(G.nodes[n].get('zone','CBZ'),'#999') for n in G.nodes()]
    cross=[(u,v) for u,v,d in G.edges(data=True) if d['weight']>0.5]
    intra=[(u,v) for u,v,d in G.edges(data=True) if d['weight']<=0.5]
    nx.draw_networkx_edges(G,pos,edgelist=cross,edge_color='#CC0000',alpha=0.55,width=1.3,ax=ax)
    nx.draw_networkx_edges(G,pos,edgelist=intra,edge_color='#888',alpha=0.4,width=0.8,ax=ax)
    nx.draw_networkx_nodes(G,pos,node_color=nc,node_size=600,ax=ax)
    nx.draw_networkx_labels(G,pos,font_size=6.5,font_weight='bold',font_color='white',ax=ax)
    handles=[mpatches.Patch(color=ZONE_HEX['PTZ'],label='Powertrain Zone'),
             mpatches.Patch(color=ZONE_HEX['CHZ'],label='Chassis Zone'),
             mpatches.Patch(color=ZONE_HEX['CBZ'],label='Cab Zone'),
             mpatches.Patch(color=ZONE_HEX['FRZ'],label='Front Zone'),
             mpatches.Patch(color='#CC0000',label='Cross-zone wire'),
             mpatches.Patch(color='#888',label='Intra-zone wire')]
    ax.legend(handles=handles,loc='lower left',fontsize=6.5,framealpha=0.9)
    ccount=len(cross); tlen=round(sum(d['weight'] for _,_,d in G.edges(data=True)),1)
    ax.set_title(f'{vshort} — Legacy Point-to-Point\n{G.number_of_nodes()} ECUs  |  {ccount} cross-zone wire runs  |  {tlen}m total wire',fontsize=9,fontweight='bold',color='#1F4E79',pad=8)
    ax.axis('off'); plt.tight_layout(); li=fig_to_image(fig,width_mm=140)
    G2=g_zon; fig,ax=plt.subplots(figsize=(11,6))
    ax.set_facecolor('#F8F9FA'); fig.patch.set_facecolor('white')
    zpos={'PTZ':(-3,0),'CHZ':(-1,0),'CBZ':(1,0),'FRZ':(3,0)}
    ctrl={z['zone_controller']:z['id'] for z in truck_data['zones']}
    pos2={}
    for zc,zid in ctrl.items(): pos2[zc]=zpos[zid]
    ze={z['id']:[e['id'] for e in z['ecus']] for z in truck_data['zones']}
    for zid,ecus in ze.items():
        cx,cy=zpos[zid]; n=len(ecus); r2=1.1 if n>4 else 0.85
        for i,ecu in enumerate(ecus):
            angle=(2*math.pi*i/n)-math.pi/2; pos2[ecu]=(cx+r2*math.cos(angle),cy+r2*math.sin(angle))
    bb=[(u,v) for u,v,d in G2.edges(data=True) if d.get('is_backbone')]
    lo=[(u,v) for u,v,d in G2.edges(data=True) if not d.get('is_backbone')]
    nx.draw_networkx_edges(G2,pos2,edgelist=bb,edge_color=ZC_HEX,width=4,alpha=0.85,ax=ax)
    nx.draw_networkx_edges(G2,pos2,edgelist=lo,edge_color='#AAAAAA',width=0.9,alpha=0.6,ax=ax)
    en=[n for n in G2.nodes() if not G2.nodes[n].get('is_controller')]
    ec=[ZONE_HEX.get(G2.nodes[n].get('zone','CBZ'),'#999') for n in en]
    nx.draw_networkx_nodes(G2,pos2,nodelist=en,node_color=ec,node_size=500,ax=ax)
    nx.draw_networkx_labels(G2,pos2,labels={n:n for n in en},font_size=6,font_weight='bold',font_color='white',ax=ax)
    zn=[n for n in G2.nodes() if G2.nodes[n].get('is_controller')]
    nx.draw_networkx_nodes(G2,pos2,nodelist=zn,node_color=ZC_HEX,node_size=1200,ax=ax)
    nx.draw_networkx_labels(G2,pos2,labels={n:n for n in zn},font_size=7,font_weight='bold',font_color='white',ax=ax)
    h2=[mpatches.Patch(color=ZONE_HEX['PTZ'],label='Powertrain Zone'),
        mpatches.Patch(color=ZONE_HEX['CHZ'],label='Chassis Zone'),
        mpatches.Patch(color=ZONE_HEX['CBZ'],label='Cab Zone'),
        mpatches.Patch(color=ZONE_HEX['FRZ'],label='Front Zone'),
        mpatches.Patch(color=ZC_HEX,label='Zone Controller + Backbone')]
    ax.legend(handles=h2,loc='lower left',fontsize=6.5,framealpha=0.9)
    zlen=round(sum(d['weight'] for _,_,d in G2.edges(data=True)),1)
    ax.set_title(f'{vshort} — Proposed 4-Zone Architecture\n{len(en)} ECUs + {len(zn)} Zone Controllers  |  3 backbone segments  |  {zlen}m total wire',fontsize=9,fontweight='bold',color='#1F4E79',pad=8)
    ax.axis('off'); plt.tight_layout(); zi=fig_to_image(fig,width_mm=140); return li,zi

# ── CHART: THREE-WAY TOPOLOGY ─────────────────────────────────────────────
def make_three_way_topology(truck_data, phys_assign, comb_assign,
                             comm_assign, phys_m, comb_m, comm_m, vshort):
    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    fig.patch.set_facecolor('white')

    configs = [
        (phys_assign, phys_m, 'Option A: Physical Zones\n(current industry design)', '#C00000'),
        (comb_assign, comb_m, 'Option B: Combined\n(recommended — balanced)', '#375623'),
        (comm_assign, comm_m, 'Option C: Communication Zones\n(theoretical maximum)', '#2E75B6'),
    ]
    zone_positions = {'PTZ':(-3,0),'CHZ':(-1,0),'CBZ':(1,0),'FRZ':(3,0)}
    ctrl_to_zone = {z['zone_controller']:z['id'] for z in truck_data['zones']}
    zone_id_to_ctrl = {z['id']:z['zone_controller'] for z in truck_data['zones']}

    for ax, (assignment, metrics, title, title_color) in zip(axes, configs):
        ax.set_facecolor('#F8F9FA')

        # position zone controllers
        pos = {}
        for zc, zid in ctrl_to_zone.items():
            pos[zc] = zone_positions[zid]

        # group ECUs by their ASSIGNED zone
        assigned_buckets = {z['id']:[] for z in truck_data['zones']}
        for zone in truck_data['zones']:
            for ecu in zone['ecus']:
                az = assignment.get(ecu['id'], zone['id'])
                if az in assigned_buckets:
                    assigned_buckets[az].append(ecu['id'])

        # place ECUs in circle around their assigned ZC
        for zid, ecus in assigned_buckets.items():
            cx, cy = zone_positions[zid]
            n = len(ecus)
            if n == 0: continue
            radius = 1.15 if n > 5 else (0.9 if n > 2 else 0.75)
            for i, ecu_id in enumerate(ecus):
                angle = (2*math.pi*i/n) - math.pi/2
                pos[ecu_id] = (cx + radius*math.cos(angle),
                               cy + radius*math.sin(angle))

        # draw backbone
        zc_list = [z['zone_controller'] for z in truck_data['zones']]
        for i in range(len(zc_list)-1):
            x0,y0 = pos[zc_list[i]]; x1,y1 = pos[zc_list[i+1]]
            ax.plot([x0,x1],[y0,y1],color=ZC_HEX,linewidth=3.5,alpha=0.85,zorder=2)

        # draw ECU→ZC edges
        for zone in truck_data['zones']:
            for ecu in zone['ecus']:
                ecu_id = ecu['id']
                az = assignment.get(ecu_id, zone['id'])
                assigned_zc = zone_id_to_ctrl.get(az, zone['zone_controller'])
                if ecu_id in pos and assigned_zc in pos:
                    ex,ey = pos[ecu_id]; zx,zy = pos[assigned_zc]
                    ax.plot([ex,zx],[ey,zy],color='#AAAAAA',linewidth=0.8,alpha=0.6,zorder=1)

        # draw ECU nodes coloured by ASSIGNED zone
        for zone in truck_data['zones']:
            for ecu in zone['ecus']:
                ecu_id = ecu['id']
                az = assignment.get(ecu_id, zone['id'])
                color = ZONE_HEX.get(az, '#999')
                if ecu_id in pos:
                    ax.scatter(*pos[ecu_id],s=380,color=color,zorder=4,
                               edgecolors='white',linewidth=0.8)
                    ax.text(pos[ecu_id][0],pos[ecu_id][1],ecu_id,
                            ha='center',va='center',fontsize=5,
                            fontweight='bold',color='white',zorder=5)

        # draw ZC nodes
        for zc in zc_list:
            if zc in pos:
                ax.scatter(*pos[zc],s=800,color=ZC_HEX,zorder=4,
                           edgecolors='white',linewidth=1.0)
                ax.text(pos[zc][0],pos[zc][1],zc,ha='center',va='center',
                        fontsize=6,fontweight='bold',color='white',zorder=5)

        ax.set_title(
            f'{title}\nWire: {metrics["total_wire_m"]}m  '
            f'Cross-zone: {metrics["cross_zone"]}  '
            f'Weight: {metrics["weight_kg"]}kg',
            fontsize=8, fontweight='bold', color=title_color, pad=8)
        ax.axis('off')

    handles = [
        mpatches.Patch(color=ZONE_HEX['PTZ'],label='Powertrain Zone'),
        mpatches.Patch(color=ZONE_HEX['CHZ'],label='Chassis Zone'),
        mpatches.Patch(color=ZONE_HEX['CBZ'],label='Cab Zone'),
        mpatches.Patch(color=ZONE_HEX['FRZ'],label='Front Zone'),
        mpatches.Patch(color=ZC_HEX,label='Zone Controller + Backbone'),
    ]
    fig.legend(handles=handles,loc='lower center',ncol=5,fontsize=8,
               framealpha=0.9,bbox_to_anchor=(0.5,-0.02))
    fig.suptitle(f'{vshort} — Three-Way Zone Assignment Comparison',
                 fontsize=11,fontweight='bold',color='#1F4E79',y=1.01)
    plt.tight_layout()
    return fig_to_image(fig,width_mm=175)

# ── CHART: PARETO CURVE ───────────────────────────────────────────────────
def make_pareto_chart(pareto_data, vehicle_name):
    fig, ax = plt.subplots(figsize=(8,5))
    fig.patch.set_facecolor('white'); ax.set_facecolor('#F8F9FA')
    wires  = [pt['wire_m']     for pt in pareto_data]
    cross  = [pt['cross_zone'] for pt in pareto_data]
    labels = ['A\nPhysical','B\nCombined','C\nComm.']
    colors_ = ['#C00000','#375623','#2E75B6']
    ax.plot(wires,cross,color='#CCCCCC',linewidth=1.5,linestyle='--',zorder=1)
    for w,c,lbl,col in zip(wires,cross,labels,colors_):
        ax.scatter(w,c,s=200,color=col,zorder=3,edgecolors='white',linewidth=1.2)
        ax.annotate(lbl,(w,c),textcoords='offset points',
                    xytext=(8,4),fontsize=9,fontweight='bold',color=col)
    ax.set_xlabel('Total Wire Length (m)',fontsize=10)
    ax.set_ylabel('Cross-Zone Communication Runs',fontsize=10)
    ax.set_title(f'Pareto Tradeoff: Wire Length vs Communication Efficiency\n{vehicle_name}',
                 fontsize=10,fontweight='bold',color='#1F4E79',pad=8)
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--')
    ax.xaxis.grid(True,alpha=0.4,linestyle='--')
    ax.set_axisbelow(True)
    if len(wires) >= 3:
        ax.annotate('Better communication\n(more wire)',
                    xy=(wires[2],cross[2]),xytext=(wires[2]+1,cross[2]-1.5),
                    fontsize=8,color='#2E75B6',
                    arrowprops=dict(arrowstyle='->',color='#2E75B6'))
        ax.annotate('Less wire\n(more cross-zone)',
                    xy=(wires[0],cross[0]),xytext=(wires[0]-9,cross[0]+0.8),
                    fontsize=8,color='#C00000',
                    arrowprops=dict(arrowstyle='->',color='#C00000'))
        ax.annotate('Recommended\nbalance point',
                    xy=(wires[1],cross[1]),xytext=(wires[1]+1,cross[1]+1.2),
                    fontsize=8,color='#375623',fontweight='bold',
                    arrowprops=dict(arrowstyle='->',color='#375623'))
    plt.tight_layout()
    return fig_to_image(fig,width_mm=130)

# ── CHARTS: FLEET ─────────────────────────────────────────────────────────
def make_fleet_bar_chart(fleet_results):
    vehicles=[r['model'].split('(')[0].strip().replace('Mercedes-Benz ','MB ') for r in fleet_results]
    wl=[r['legacy_length_m'] for r in fleet_results]; wz=[r['zonal_length_m'] for r in fleet_results]
    sv=[r['length_reduction'] for r in fleet_results]; cl=[r['cross_zone_legacy'] for r in fleet_results]
    cz=[r['cross_zone_zonal'] for r in fleet_results]
    fig,axes=plt.subplots(1,3,figsize=(16,6)); fig.patch.set_facecolor('white')
    bk=dict(edgecolor='white',linewidth=0.8); x=np.arange(len(vehicles)); w=0.38
    ax=axes[0]; ax.bar(x-w/2,wl,w,color='#C00000',label='Legacy',**bk); ax.bar(x+w/2,wz,w,color='#375623',label='Zonal',**bk)
    for i,(l,z) in enumerate(zip(wl,wz)):
        ax.text(i-w/2,l+0.5,f'{l}m',ha='center',va='bottom',fontsize=7.5,color='#C00000',fontweight='bold')
        ax.text(i+w/2,z+0.5,f'{z}m',ha='center',va='bottom',fontsize=7.5,color='#375623',fontweight='bold')
    ax.set_title('Total Wire Length (m)',fontsize=11,fontweight='bold',color='#1F4E79',pad=10)
    ax.set_xticks(x); ax.set_xticklabels(vehicles,fontsize=9); ax.legend(fontsize=9)
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax=axes[1]; ax.bar(x-w/2,cl,w,color='#C00000',label='Legacy',**bk); ax.bar(x+w/2,cz,w,color='#375623',label='Zonal',**bk)
    for i,(l,z) in enumerate(zip(cl,cz)):
        ax.text(i-w/2,l+0.1,str(l),ha='center',va='bottom',fontsize=8,color='#C00000',fontweight='bold')
        ax.text(i+w/2,z+0.1,str(z),ha='center',va='bottom',fontsize=8,color='#375623',fontweight='bold')
    ax.set_title('Cross-Zone Wire Runs',fontsize=11,fontweight='bold',color='#1F4E79',pad=10)
    ax.set_xticks(x); ax.set_xticklabels(vehicles,fontsize=9); ax.legend(fontsize=9)
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax=axes[2]; bc=['#375623' if s>50 else '#F5A623' for s in sv]
    bars=ax.bar(vehicles,sv,color=bc,**bk)
    for bar,s in zip(bars,sv): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.5,f'{s}%',ha='center',va='bottom',fontsize=9,fontweight='bold')
    ax.set_title('Wire Length Saved (%)',fontsize=11,fontweight='bold',color='#1F4E79',pad=10)
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax.set_ylim(0,max(sv)*1.2); ax.tick_params(axis='x',labelsize=9)
    fig.suptitle('Fleet-Wide Architecture Comparison — Legacy vs Zonal',fontsize=13,fontweight='bold',color='#1F4E79',y=1.02)
    plt.tight_layout(); return fig_to_image(fig,width_mm=160)

def make_efficiency_chart(fleet_results):
    vehicles=[r['model'].split('(')[0].strip().replace('Mercedes-Benz ','MB ') for r in fleet_results]
    hm=[r.get('human_modularity',0) for r in fleet_results]; om=[r.get('optimal_modularity',0) for r in fleet_results]
    eff=[r['zone_efficiency'] for r in fleet_results]
    fig,axes=plt.subplots(1,2,figsize=(14,5)); fig.patch.set_facecolor('white')
    x=np.arange(len(vehicles)); w=0.35
    ax=axes[0]; ax.bar(x-w/2,hm,w,color='#C00000',label='Human-defined zones',edgecolor='white')
    ax.bar(x+w/2,om,w,color='#2E75B6',label='Algorithm-optimal zones',edgecolor='white')
    for i,(h,o) in enumerate(zip(hm,om)):
        ax.text(i-w/2,max(h,0)+0.005,f'{h:.3f}',ha='center',va='bottom',fontsize=7.5,color='#C00000')
        ax.text(i+w/2,o+0.005,f'{o:.3f}',ha='center',va='bottom',fontsize=7.5,color='#2E75B6')
    ax.axhline(0,color='black',linewidth=0.8,linestyle='--')
    ax.set_title('Modularity Score: Human vs Algorithm',fontsize=11,fontweight='bold',color='#1F4E79',pad=8)
    ax.set_xticks(x); ax.set_xticklabels(vehicles,fontsize=9); ax.legend(fontsize=9)
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax=axes[1]; ec=['#27AE60' if e>20 else ('#E74C3C' if e<0 else '#F39C12') for e in eff]
    bars=ax.bar(vehicles,eff,color=ec,edgecolor='white')
    for bar,e in zip(bars,eff):
        ypos=e+0.5 if e>=0 else e-2.5
        ax.text(bar.get_x()+bar.get_width()/2,ypos,f'{e}%',ha='center',va='bottom',fontsize=9,fontweight='bold')
    ax.axhline(0,color='black',linewidth=0.8)
    ax.set_title('Zone Efficiency Score (%)',fontsize=11,fontweight='bold',color='#1F4E79',pad=8)
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True); ax.tick_params(axis='x',labelsize=9)
    fig.suptitle('Zone Boundary Optimality — All 3 Vehicles',fontsize=13,fontweight='bold',color='#1F4E79',y=1.02)
    plt.tight_layout(); return fig_to_image(fig,width_mm=155)

def make_scaling_chart(fleet_results):
    fig,axes=plt.subplots(1,2,figsize=(13,5)); fig.patch.set_facecolor('white')
    names=[r['model'].split('(')[0].strip().replace('Mercedes-Benz ','MB ') for r in fleet_results]
    ecus=[r['ecu_count'] for r in fleet_results]; sv=[r['length_reduction'] for r in fleet_results]
    wt=[r['weight_saved_kg'] for r in fleet_results]; mc=[ZONE_HEX['PTZ'],ZONE_HEX['CHZ'],ZONE_HEX['CBZ']]
    ax=axes[0]
    for i,(e,s,n,c) in enumerate(zip(ecus,sv,names,mc)):
        ax.scatter(e,s,s=220,color=c,zorder=5,edgecolors='white',linewidth=1.5)
        ax.annotate(n,(e,s),textcoords='offset points',xytext=(7,5),fontsize=9)
    ax.set_xlabel('ECU Count',fontsize=10); ax.set_ylabel('Wire Length Saved (%)',fontsize=10)
    ax.set_title('Zonal Benefit vs ECU Count',fontsize=11,fontweight='bold',color='#1F4E79')
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax=axes[1]; bars=ax.bar(names,wt,color=mc,edgecolor='white')
    for bar,w in zip(bars,wt): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.05,f'{w} kg',ha='center',va='bottom',fontsize=9,fontweight='bold')
    ax.set_title('Estimated Harness Weight Saved (kg)',fontsize=11,fontweight='bold',color='#1F4E79')
    ax.set_ylabel('Weight Saved (kg)',fontsize=10); ax.set_facecolor('#F8F9FA')
    ax.spines[['top','right']].set_visible(False); ax.yaxis.grid(True,alpha=0.4,linestyle='--')
    ax.set_axisbelow(True); ax.tick_params(axis='x',labelsize=9)
    plt.tight_layout(); return fig_to_image(fig,width_mm=155)

# ── MAIN REPORT BUILDER ───────────────────────────────────────────────────
def build_pdf_report(all_truck_data,all_metrics,all_opts,all_legacies,
                     all_zonals,fleet_results,ai_sections,
                     three_way_result, output_path):
    styles=make_styles(); story=[]; W=A4[0]-4*cm
    def sp(h=6): return Spacer(1,h)
    def hr(): return HRFlowable(width="100%",thickness=1.5,color=BLUE,spaceAfter=4,spaceBefore=4)
    def pb(): return PageBreak()
    truck_data=all_truck_data[0]; m=all_metrics[0]; opt=all_opts[0]
    VN=["Freightliner Cascadia 126","Western Star 49X","Mercedes-Benz Sprinter 519 CDI"]
    VS=["Cascadia 126","Western Star 49X","MB Sprinter 519"]

    # ── COVER ─────────────────────────────────────────────────────────
    story+=[sp(55)]
    story.append(Paragraph("ZONAL E/E ARCHITECTURE",styles['CoverTitle']))
    story.append(Paragraph("COMPARATIVE STUDY REPORT",styles['CoverTitle']))
    story+=[sp(8)]
    story.append(Paragraph("Legacy Point-to-Point vs 4-Zone Ethernet Architecture",styles['CoverSub']))
    story+=[sp(14),hr(),sp(10)]
    story.append(Paragraph("Fleet Scope:",styles['CoverSub']))
    story.append(Paragraph("Freightliner Cascadia 126 (2020)  |  Western Star 49X (2021)  |  Mercedes-Benz Sprinter 519 CDI (2021)",styles['CoverMeta']))
    total_ecus=sum(r['ecu_count'] for r in fleet_results)
    total_conn=sum(r['connections'] for r in fleet_results)
    story.append(Paragraph(f"Total ECUs modelled: {total_ecus}  |  Total connections modelled: {total_conn}",styles['CoverMeta']))
    story+=[sp(8)]
    story.append(Paragraph("Tool: Zonal E/E Architecture Analyzer  |  AI Review: Groq Llama 3.3 70B",styles['CoverMeta']))
    story.append(Paragraph("Rishit — ECE '28, VIT Vellore  |  DTICI Intern  |  June 2026",styles['CoverMeta']))
    story.append(Paragraph("Primary data source: DTNA SS-1033423, NHTSA public database",styles['CoverMeta']))
    story+=[sp(18),hr(),pb()]

    # ── HOW TO READ ────────────────────────────────────────────────────
    story.append(Paragraph("How to Read This Report",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("This report compares two ways of wiring electronics inside a commercial truck. The <b>old way (Legacy / Point-to-Point)</b> connects every ECU directly to every other ECU it talks to using individual wires. The <b>new way (Zonal Architecture)</b> divides the truck into 4 physical regions. Each ECU connects to a nearby hub (Zone Controller) with a short wire. The 4 hubs talk to each other over one Ethernet cable running along the truck. This tool models 3 vehicles, calculates the difference in wire length, weight, and complexity, checks if zone boundaries are optimal, and computes a recommended zone design balancing wire length and communication efficiency. A full abbreviation guide is on the next page.",styles['Body']))
    story+=[sp(6),pb()]

    # ── ABBREVIATIONS ──────────────────────────────────────────────────
    story.append(Paragraph("Abbreviations and Full Forms",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Every shortform used in this report is listed below.",styles['Body'])); story+=[sp(8)]
    half=(len(ABBREVS)+1)//2; ab_rows=[['Abbreviation','Full Form','Abbreviation','Full Form']]
    for i in range(half):
        left=ABBREVS[i]; right=ABBREVS[i+half] if (i+half)<len(ABBREVS) else ('','')
        ab_rows.append([left[0],left[1],right[0],right[1]])
    cw_ab=[W*0.12,W*0.37,W*0.12,W*0.37]
    ex_ab=[('ALIGN',(0,0),(-1,-1),'LEFT'),
           ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,1),(2,-1),'Helvetica-Bold'),
           ('TEXTCOLOR',(0,1),(0,-1),NAVY),('TEXTCOLOR',(2,1),(2,-1),NAVY),
           ('BACKGROUND',(0,0),(1,0),NAVY),('BACKGROUND',(2,0),(3,0),NAVY),
           ('LINEAFTER',(1,0),(1,-1),1,BLUE)]
    story.append(make_rl_table(ab_rows,cw_ab,ex_ab)); story+=[sp(6),pb()]

    # ── SECTION 1: EXEC SUMMARY ───────────────────────────────────────
    story.append(Paragraph("1. Executive Summary",styles['SectionHead'])); story.append(hr())
    s1=ai_sections.get('SECTION_1_EXECUTIVE_SUMMARY','')
    story.append(Paragraph(s1,styles['Body'])); story+=[sp(10)]
    story.append(Paragraph("1.1  Key Metrics — All Three Vehicles",styles['SubHead'])); story+=[sp(4)]
    sum_data=[['Metric','Freightliner\nCascadia 126','Western Star\n49X','MB Sprinter\n519 CDI']]
    mrows=[('ECU Count','ecu_count','',False),
           ('Legacy Wire Length','legacy_length_m','m',False),
           ('Zonal Wire Length','zonal_length_m','m',False),
           ('Wire Length Saved','length_reduction','%',True),
           ('Cross-Zone Runs: Legacy','cross_zone_legacy','',False),
           ('Cross-Zone Runs: Zonal','cross_zone_zonal','',False),
           ('Harness Weight Saved','weight_saved_kg','kg',True),
           ('Zone Efficiency Score','zone_efficiency','%',False)]
    for label,key,unit,_ in mrows:
        row=[label]+[f"{r[key]}{unit}" for r in fleet_results]; sum_data.append(row)
    cw_sum=[W*0.34,W*0.22,W*0.22,W*0.22]
    ex_sum=[('ALIGN',(1,0),(-1,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
            ('BACKGROUND',(1,4),(3,4),LGREEN),('BACKGROUND',(1,7),(3,7),LGREEN),
            ('TEXTCOLOR',(1,2),(3,2),RED),('TEXTCOLOR',(1,3),(3,3),GREEN),
            ('FONTNAME',(1,4),(3,4),'Helvetica-Bold'),('TEXTCOLOR',(1,4),(3,4),GREEN),
            ('BACKGROUND',(1,5),(3,5),LRED),('BACKGROUND',(1,6),(3,6),LGREEN),
            ('TEXTCOLOR',(1,7),(3,7),BLUE)]
    story.append(make_rl_table(sum_data,cw_sum,ex_sum))
    story.append(Paragraph("Table 1: Key metrics. Green = improvement. Red = legacy (higher is worse).",styles['Caption']))
    story+=[sp(6),pb()]

    # ── SECTION 2: BACKGROUND ─────────────────────────────────────────
    story.append(Paragraph("2. Background — What Is Zonal Architecture?",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("A modern truck has dozens of ECUs — small computers controlling everything from the engine and brakes to the dashboard and door locks.",styles['Body'])); story+=[sp(5)]
    story.append(Paragraph("The Old Way — Legacy Point-to-Point Architecture",styles['SubHead']))
    story.append(Paragraph("If ECU A needs to talk to ECU B, a dedicated wire is run between them. With 22 ECUs and 25 communication pairs on a Cascadia 126, this creates a dense web of wires crossing the full truck. The engine controller (MCM) talking to the dashboard (ICU) needs a wire running ~5.5 meters. Result: 52.5m of wire and 6.3 kg of copper.",styles['Body'])); story+=[sp(5)]
    story.append(Paragraph("The New Way — 4-Zone Ethernet Architecture",styles['SubHead']))
    story.append(Paragraph("The truck is divided into 4 physical regions. Each ECU connects only to a nearby Zone Controller with a short wire (0.5–1.5m). The 4 Zone Controllers communicate over one Ethernet cable (100BASE-T1) running along the truck spine. Result: 24.3m total wire, 2.9 kg, and only 3 cross-vehicle runs instead of 16.",styles['Body'])); story+=[sp(6)]
    explain_data=[['Feature','Legacy Architecture','Zonal Architecture'],
        ['Wiring principle','Direct wire between every communicating pair','Each ECU to local Zone Controller to Ethernet backbone'],
        ['Cross-truck runs','One per communication pair (up to 16 long runs)','Only 3 backbone segments total'],
        ['Wire length (Cascadia)','52.5 m','24.3 m  (-53.7%)'],
        ['Fault isolation','One broken wire can affect the whole system','Fault stays within the affected zone'],
        ['Scalability','Complexity grows fast with each new ECU','Each new ECU adds only one short local wire'],
        ['Industry status','Current standard on most trucks in service','Target for next-generation truck platforms']]
    cw_ex=[W*0.25,W*0.375,W*0.375]
    ex_ex=[('ALIGN',(0,0),(-1,-1),'LEFT'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
           ('BACKGROUND',(2,3),(2,3),LGREEN),('TEXTCOLOR',(2,3),(2,3),GREEN),
           ('FONTNAME',(2,3),(2,3),'Helvetica-Bold')]
    story.append(make_rl_table(explain_data,cw_ex,ex_ex))
    story.append(Paragraph("Table 2: Legacy vs zonal architecture comparison.",styles['Caption'])); story+=[sp(6),pb()]

    # ── SECTION 3: VEHICLE CONFIGS ────────────────────────────────────
    story.append(Paragraph("3. Vehicle Configurations and Zone Layouts",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Three vehicles were modelled. ECUs were assigned to zones based on actual mounting location, cross-referenced with official DTNA and Mercedes-Benz documentation.",styles['Body'])); story+=[sp(8)]
    for i,(td,r) in enumerate(zip(all_truck_data,fleet_results)):
        story.append(Paragraph(f"3.{i+1}  {VN[i]}",styles['SubHead']))
        story.append(Paragraph(f"<b>Total ECUs:</b> {td['metadata']['total_ecus']}  |  <b>Connections:</b> {len(td['connections'])}  |  <b>Source:</b> {td['metadata'].get('source','—')}",styles['BodyPlain'])); story+=[sp(4)]
        zd=[['Zone','ID','Zone Controller','ECUs in Zone','Count']]
        for z in td['zones']:
            eids=', '.join(e['id'] for e in z['ecus'])
            zd.append([z['name'],z['id'],z['zone_controller'],eids,str(len(z['ecus']))])
        cw_z=[W*0.22,W*0.07,W*0.16,W*0.46,W*0.09]
        ex_z=[('ALIGN',(0,0),(0,-1),'LEFT'),('ALIGN',(3,1),(3,-1),'LEFT'),
              ('ALIGN',(4,0),(4,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold')]
        story.append(make_rl_table(zd,cw_z,ex_z))
        story.append(Paragraph(f"Table 3.{i+1}: Zone layout — {VN[i]}",styles['Caption'])); story+=[sp(6)]
    story+=[pb()]

    # ── SECTION 4: TOPOLOGY DIAGRAMS ─────────────────────────────────
    story.append(Paragraph("4. Network Topology Diagrams — All Three Vehicles",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Each vehicle shown in legacy layout (red = cross-zone wires) and proposed 4-zone zonal layout (dark hubs = Zone Controllers).",styles['Body'])); story+=[sp(10)]
    for i,(td,lg,zn) in enumerate(zip(all_truck_data,all_legacies,all_zonals)):
        story.append(Paragraph(f"4.{i+1}  {VN[i]}",styles['SubHead']))
        li,zi=make_topology_pair(lg,zn,td,VS[i]); r=fleet_results[i]
        story.append(li)
        story.append(Paragraph(f"Legacy: {r['ecu_count']} ECUs  |  {r['cross_zone_legacy']} cross-zone runs  |  {r['legacy_length_m']}m",styles['Caption'])); story+=[sp(8)]
        story.append(zi)
        story.append(Paragraph(f"Zonal: {r['ecu_count']} ECUs + 4 ZCs  |  3 backbone segments  |  {r['zonal_length_m']}m  |  {r['length_reduction']}% reduction",styles['Caption']))
        if i<2: story+=[sp(6),pb()]
    story+=[sp(6),pb()]

    # ── SECTION 5: THREE-WAY ZONE COMPARISON ─────────────────────────
    story.append(Paragraph("5. Zone Assignment Optimization — Three-Way Comparison",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph(
        "This section answers the question: <b>what is the best possible zone design?</b><br/><br/>"
        "The tool computes three zone assignment strategies and compares them side by side. "
        "<b>Option A</b> is the current industry design — ECUs grouped by physical location. "
        "<b>Option C</b> is the theoretical communication-optimal design — ECUs grouped purely by "
        "who they talk to, ignoring physical constraints. This is not implementable in practice "
        "because some ECUs would need to connect to a Zone Controller far away, defeating the "
        "purpose of short local stubs. <b>Option B</b> is the recommended balanced design — "
        "it only moves ECUs where (1) the communication benefit is clear AND (2) the wire cost "
        "stays within adjacent-zone range (3.0m or less). This is the practically implementable "
        "optimum.<br/><br/>"
        "<b>Why do zones need optimizing at all?</b> Zones are currently drawn based on physical "
        "location — where each ECU is bolted on the truck. But communication patterns do not "
        "follow geography. The engine controller (MCM) talks constantly to the dashboard (ICU) "
        "even though they are on opposite ends of the truck. A graph algorithm called Greedy "
        "Modularity Community Detection confirms this — it finds that the mathematically optimal "
        "zone groupings based purely on communication patterns produce a completely different "
        "layout from the physical zones (7% match on the Cascadia, confirming the tradeoff is "
        "structural). The top communication hubs — ICU with 12 connections, CPC with 6, ABS with "
        "4 — all communicate heavily across zone boundaries, which is exactly why the current "
        "physical zone design produces 16 cross-zone runs. Option B reduces this to 7 by moving "
        "ECUs to zones where most of their communication partners already live, while keeping all "
        "wire stubs within the adjacent-zone distance limit.",
        styles['Body'])); story+=[sp(10)]
    story.append(make_three_way_topology(
        all_truck_data[0],
        three_way_result['physical_assignment'],
        three_way_result['combined_assignment'],
        three_way_result['comm_assignment'],
        three_way_result['physical_metrics'],
        three_way_result['combined_metrics'],
        three_way_result['comm_metrics'],
        "Freightliner Cascadia 126"))
    story.append(Paragraph(
        "Figure D: Three-way zone assignment comparison. Node colour shows the ASSIGNED zone "
        "(not physical mounting zone). Option B ECUs that moved appear in a different colour "
        "from their physical location.",styles['Caption'])); story+=[sp(10)]

    # three-way summary table
    tw_p = three_way_result['physical_metrics']
    tw_c = three_way_result['combined_metrics']
    tw_m = three_way_result['comm_metrics']
    col_data=[
        ["Metric",
         "Option A\nPhysical (current)",
         "Option B\nCombined (recommended)",
         "Option C\nCommunication (theoretical)"],
        ["Total wire length",
         f"{tw_p['total_wire_m']} m",
         f"{tw_c['total_wire_m']} m",
         f"{tw_m['total_wire_m']} m"],
        ["Cross-zone runs",
         str(tw_p['cross_zone']),
         str(tw_c['cross_zone']),
         str(tw_m['cross_zone'])],
        ["Est. harness weight",
         f"{tw_p['weight_kg']} kg",
         f"{tw_c['weight_kg']} kg",
         f"{tw_m['weight_kg']} kg"],
        ["Physically feasible","YES","YES","NO — some ECUs too far from ZC"],
    ]
    cw_col=[W*0.28,W*0.24,W*0.24,W*0.24]
    ex_col=[('ALIGN',(1,0),(-1,-1),'CENTER'),
            ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
            ('BACKGROUND',(2,1),(2,3),LGREEN),
            ('TEXTCOLOR',(1,1),(1,-1),RED),
            ('TEXTCOLOR',(2,1),(2,3),GREEN),
            ('FONTNAME',(2,1),(2,3),'Helvetica-Bold'),
            ('BACKGROUND',(3,4),(3,4),LRED)]
    story.append(make_rl_table(col_data,cw_col,ex_col))
    story.append(Paragraph(
        "Table D: Three-way comparison. Option B (green) is the recommended implementable design.",
        styles['Caption'])); story+=[sp(8)]

    # ECU reassignment table
    changes = three_way_result['changes']
    if changes:
        story.append(Paragraph("5.1  Recommended Zone Changes",styles['SubHead']))
        story.append(Paragraph(
            f"The optimizer recommends moving {len(changes)} ECUs from their physical zone. "
            "All moves keep wire cost within 3.0m (adjacent zone range) while significantly "
            "reducing cross-zone traffic from "
            f"{tw_p['cross_zone']} to {tw_c['cross_zone']} runs.",
            styles['Body'])); story+=[sp(4)]
        chg_data=[["ECU","Current Zone","Recommended Zone","Reason"]]
        for c in changes:
            chg_data.append([c['ecu'],c['from_zone'],c['to_zone'],c['reason']])
        cw_chg=[W*0.10,W*0.22,W*0.22,W*0.46]
        ex_chg=[('ALIGN',(0,0),(2,-1),'CENTER'),
                ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
                ('TEXTCOLOR',(0,1),(0,-1),NAVY),
                ('ALIGN',(3,1),(3,-1),'LEFT')]
        story.append(make_rl_table(chg_data,cw_chg,ex_chg))
        story.append(Paragraph(
            "Table E: ECU zone reassignment recommendations. All moves are physically feasible.",
            styles['Caption']))
    story+=[sp(8)]

    # pareto curve
    story.append(Paragraph("5.2  Pareto Tradeoff Curve",styles['SubHead']))
    story.append(Paragraph(
        "The chart below shows the tradeoff between wire length and communication efficiency. "
        "Moving from Option A to C reduces cross-zone runs but increases wire length. "
        "Option B sits at the knee of the curve — maximum communication benefit "
        "for minimum additional wire cost.",styles['Body'])); story+=[sp(6)]
    story.append(make_pareto_chart(
        three_way_result['pareto'], "Freightliner Cascadia 126 (2020)"))
    story.append(Paragraph(
        "Figure E: Pareto curve. Option B is the recommended operating point — "
        "it achieves most of the communication gain at a fraction of the wire cost penalty.",
        styles['Caption'])); story+=[sp(6),pb()]

    # ── SECTION 6: HARNESS ANALYSIS ───────────────────────────────────
    story.append(Paragraph("6. Harness Reduction Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Wire length, cross-zone run count, and weight reduction for each vehicle.",styles['Body'])); story+=[sp(8)]
    for i,(td,met,r) in enumerate(zip(all_truck_data,all_metrics,fleet_results)):
        story.append(Paragraph(f"6.{i+1}  {VN[i]}",styles['SubHead']))
        cd=[['Metric','Legacy\n(Point-to-Point)','Zonal\n(4-Zone)','Reduction'],
            ['Total wire length',f"{met['legacy_length_m']} m",f"{met['zonal_length_m']} m",f"{met['length_reduction_pct']}%"],
            ['Cross-zone wire runs',str(met['cross_zone_legacy']),str(met['cross_zone_zonal']),
             f"{round((met['cross_zone_legacy']-met['cross_zone_zonal'])/met['cross_zone_legacy']*100,1)}%"],
            ['Est. harness weight',f"{met['legacy_weight_kg']} kg",f"{met['zonal_weight_kg']} kg",
             f"{met['weight_saved_kg']} kg saved"]]
        cw_c=[W*0.34,W*0.20,W*0.20,W*0.26]
        ex_c=[('ALIGN',(1,1),(-1,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
              ('TEXTCOLOR',(1,1),(1,-1),RED),('TEXTCOLOR',(2,1),(2,-1),GREEN),
              ('TEXTCOLOR',(3,1),(3,-1),GREEN),('FONTNAME',(3,1),(3,-1),'Helvetica-Bold'),
              ('BACKGROUND',(3,1),(3,-1),LGREEN)]
        story.append(make_rl_table(cd,cw_c,ex_c))
        story.append(Paragraph(f"Table 6.{i+1}: Harness metrics — {VN[i]}",styles['Caption'])); story+=[sp(6)]
    story+=[sp(4)]
    s2=ai_sections.get('SECTION_2_HARNESS_REDUCTION','')
    story.append(Paragraph(s2,styles['Body'])); story+=[sp(10)]
    story.append(make_fleet_bar_chart(fleet_results))
    story.append(Paragraph("Figure A: Fleet-wide comparison. Wire length (left), cross-zone runs (centre), percentage savings (right).",styles['Caption'])); story+=[sp(6),pb()]

    # ── SECTION 9: FLEET COMPARISON ───────────────────────────────────
    story.append(Paragraph("7. Fleet-Wide Comparative Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Analysis across three vehicles reveals how zonal architecture benefit scales with vehicle size and complexity.",styles['Body'])); story+=[sp(8)]
    fld=[['Vehicle','ECUs','Connections','Legacy\nWire (m)','Zonal\nWire (m)',
          'Wire\nSaved','Weight\nSaved','Zone\nEfficiency']]
    for r in fleet_results:
        fld.append([r['model'].split('(')[0].strip(),str(r['ecu_count']),
                    str(r['connections']),f"{r['legacy_length_m']}m",
                    f"{r['zonal_length_m']}m",f"{r['length_reduction']}%",
                    f"{r['weight_saved_kg']}kg",f"{r['zone_efficiency']}%"])
    cw_fl2=[W*0.26,W*0.06,W*0.09,W*0.09,W*0.09,W*0.09,W*0.11,W*0.11]
    ex_fl2=[('ALIGN',(1,0),(-1,-1),'CENTER'),('ALIGN',(0,1),(0,-1),'LEFT'),
            ('FONTNAME',(5,1),(5,-1),'Helvetica-Bold'),('TEXTCOLOR',(3,1),(3,-1),RED),
            ('TEXTCOLOR',(4,1),(4,-1),GREEN),('TEXTCOLOR',(5,1),(5,-1),GREEN),
            ('BACKGROUND',(5,1),(5,-1),LGREEN)]
    story.append(make_rl_table(fld,cw_fl2,ex_fl2))
    story.append(Paragraph("Table 10: Fleet-wide comparison.",styles['Caption'])); story+=[sp(8)]
    story.append(make_scaling_chart(fleet_results))
    story.append(Paragraph("Figure C: Wire saved vs ECU count (left). Harness weight saved (right).",styles['Caption'])); story+=[sp(8)]
    s5=ai_sections.get('SECTION_5_FLEET_INSIGHTS','')
    story.append(Paragraph(s5,styles['Body'])); story+=[sp(6)]
    story.append(Paragraph("7.1  Key Cross-Fleet Findings",styles['SubHead']))
    findings=["Zonal wire savings do not scale linearly with ECU count. Physical spread of ECUs matters more than total count.",
              "Cross-zone wire runs always collapse to exactly 3 backbone segments in a 4-zone design — a structural property.",
              "Zone efficiency scores are consistently low across all vehicles — the physical-vs-communication tradeoff is fundamental to automotive E/E design.",
              "The Sprinter van (12 ECUs) saves 32.2% but the zone controller overhead is proportionally higher — suggesting a practical ROI threshold of ~15+ ECUs."]
    for i,f in enumerate(findings,1):
        story.append(Paragraph(f"<b>Finding {i}:</b>  {f}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(6),pb()]

    # ── SECTION 10: AI REVIEW ─────────────────────────────────────────
    story.append(Paragraph("8. AI-Assisted Engineering Review",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Generated by Groq Llama 3.3 70B from computed data. AI was instructed to act as a senior automotive E/E architect.",styles['Body'])); story+=[sp(8)]
    story.append(Paragraph("8.1  Design Recommendations",styles['SubHead']))
    s6=ai_sections.get('SECTION_6_RECOMMENDATIONS','')
    recs=[l.strip() for l in s6.split('\n') if l.strip().startswith('REC_')]
    if not recs: recs=[l.strip() for l in s6.split('\n') if l.strip()]
    for i,rec in enumerate(recs[:3],1):
        txt=rec[7:].strip() if rec.startswith('REC_') else rec
        story.append(Paragraph(f"<b>{i}.</b>  {txt}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(8)]
    story.append(Paragraph("8.2  Analysis Limitations",styles['SubHead']))
    s7=ai_sections.get('SECTION_7_LIMITATIONS','')
    lims=[l.strip() for l in s7.split('\n') if l.strip().startswith('LIM_')]
    if not lims: lims=[l.strip() for l in s7.split('\n') if l.strip()]
    for lim in lims[:2]:
        txt=lim[7:].strip() if lim.startswith('LIM_') else lim
        story.append(Paragraph(f"\u2022  {txt}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(6),pb()]

    # ── SECTION 11: METHODOLOGY ───────────────────────────────────────
    story.append(Paragraph("9. Methodology and Data Sources",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("9.1  How the Tool Works",styles['SubHead']))
    tool_steps=[
        ("Step 1 — Input (YAML config)","ECUs, zone assignments, connections, and zone distances described in a YAML text file."),
        ("Step 2 — Graph building (graph.py)","Two NetworkX graphs: legacy (ECU-to-ECU, weighted by wire length) and zonal (ECU-to-ZC stubs + backbone)."),
        ("Step 3 — Metrics (metrics.py)","Wire length, cross-zone run count, harness weight computed by summing edge weights."),
        ("Step 4 — Zone optimality (optimizer.py)","Greedy Modularity Community Detection finds communication-optimal zone groupings."),
        ("Step 5 — Three-way optimizer (constrained_optimizer.py)","Greedy iterative reassignment at three modes: physical, combined (alpha=0.5), communication. Pareto curve computed across modes."),
        ("Step 6 — Fleet comparison (fleet_compare.py)","Steps 1-4 run for all three vehicle configs."),
        ("Step 7 — AI review (reviewer.py)","Computed data passed to Groq Llama 3.3 70B with structured automotive engineering prompt."),
        ("Step 8 — PDF generation (build_pdf_report.py)","Matplotlib generates all diagrams. ReportLab assembles 18+ page PDF."),
    ]
    for title,desc in tool_steps:
        story.append(Paragraph(f"<b>{title}:</b>  {desc}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(8)]
    story.append(Paragraph("9.2  Data Sources",styles['SubHead']))
    sources=["DTNA SS-1033423 — J-1939 Fault Code Source Address Descriptions. Daimler Trucks North America. NHTSA public database.",
             "DTNA STI-503 — NGC sSAM, VPDM & BCA Wall Chart. Rev. Q, March 2020.",
             "Western Star Bodybuilder Manual Rev 3.1.",
             "Mercedes-Benz XENTRY public diagnostic documentation.",
             "Park C, Cui C, Park S. Sensors. 2024;24(10):3248. DOI: 10.3390/s24103248.",
             "SAE J1939 — Serial Control and Communications Heavy Duty Vehicle Network."]
    for i,src in enumerate(sources,1):
        story.append(Paragraph(f"{i}.  {src}",styles['BulletItem'])); story+=[sp(2)]
    story+=[sp(8)]
    story.append(Paragraph("9.3  Key Assumptions",styles['SubHead']))
    assumptions=["Wire lengths estimated from published chassis dimensions: Cascadia 126 ~8.5m, Western Star 49X ~7.5m, Sprinter ~5.5m",
                 "Harness weight uses 120 g/m bundled average for signal-wire harnesses (conservative)",
                 "Analysis covers signal and data wires only — power distribution excluded",
                 "Static ECU configuration — optional equipment not modelled",
                 "Three-way optimizer wire threshold: 3.0m (adjacent-zone range for combined mode)",
                 "All ECU data from public DTNA and Mercedes-Benz documents — no proprietary OEM data"]
    for a in assumptions:
        story.append(Paragraph(f"\u2022  {a}",styles['BulletItem'])); story+=[sp(2)]
    story+=[sp(16),hr()]
    story.append(Paragraph("Zonal E/E Architecture Analyzer  |  Open-source  |  https://github.com/Rish-736/zonal-ee-analyzer",styles['CoverMeta']))
    story.append(Paragraph("Built alongside DTICI internship research — Rishit, ECE '28, VIT Vellore — June 2026",styles['CoverMeta']))

    # ── BUILD ──────────────────────────────────────────────────────────
    def on_page(canvas,doc):
        canvas.saveState()
        if doc.page==1:
            canvas.setFillColor(colors.HexColor("#1F4E79"))
            canvas.rect(0,A4[1]-2.2*cm,A4[0],2.2*cm,fill=1,stroke=0)
            canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold',10)
            canvas.drawCentredString(A4[0]/2,A4[1]-1.4*cm,
                "DTICI INTERNSHIP RESEARCH  |  ZONAL E/E ARCHITECTURE STUDY  |  JUNE 2026")
        canvas.setFont('Helvetica',7); canvas.setFillColor(colors.HexColor("#595959"))
        canvas.drawString(2*cm,1.2*cm,"Zonal E/E Architecture Comparative Study Report")
        canvas.drawRightString(A4[0]-2*cm,1.2*cm,f"Page {doc.page}"); canvas.restoreState()

    doc=SimpleDocTemplate(output_path,pagesize=A4,
                          leftMargin=2*cm,rightMargin=2*cm,
                          topMargin=2*cm,bottomMargin=2*cm,
                          title="Zonal E/E Architecture Comparative Study Report",
                          author="Rishit — VIT Vellore / DTICI")
    doc.build(story,onFirstPage=on_page,onLaterPages=on_page)
    print(f"\n  PDF saved: {output_path}"); return output_path


# ── ENTRY POINT ───────────────────────────────────────────────────────────
if __name__=="__main__":
    from parser              import load_truck_config
    from graph               import build_legacy_graph,build_zonal_graph
    from metrics             import calculate_metrics
    from optimizer           import run_optimizer
    from fleet_compare       import run_fleet_comparison
    from reviewer            import build_review_prompt,call_groq,parse_ai_sections
    from constrained_optimizer import run_three_way_comparison

    CONFIGS=["configs/cascadia_126_2020.yaml",
             "configs/western_star_49x_2021.yaml",
             "configs/sprinter_van_2021.yaml"]

    print("Running full analysis pipeline...")
    atd,am,ao,al,az=[],[],[],[],[]
    for cfg in CONFIGS:
        td=load_truck_config(cfg); lg=build_legacy_graph(td)
        zn=build_zonal_graph(td); met=calculate_metrics(lg,zn,td)
        opt=run_optimizer(td)
        atd.append(td); am.append(met); ao.append(opt)
        al.append(lg); az.append(zn)

    fleet=run_fleet_comparison()
    for r,td,opt in zip(fleet,atd,ao):
        r['human_modularity']  =opt['human_score']
        r['optimal_modularity']=opt['optimal_score']
        r['connections']       =len(td['connections'])

    print("\nRunning three-way zone optimizer...")
    three_way = run_three_way_comparison(atd[0])

    print("\nCalling Groq API...")
    prompt   =build_review_prompt(atd[0],am[0],ao[0],fleet)
    ai_text  =call_groq(prompt)
    sections =parse_ai_sections(ai_text)

    print("Building PDF report..."); os.makedirs('outputs',exist_ok=True)
    output_path="outputs/ZonalEE_Comparative_Study_Report.pdf"
    build_pdf_report(atd,am,ao,al,az,fleet,sections,three_way,output_path)
    print(f"\nDone. Open: {output_path}")
