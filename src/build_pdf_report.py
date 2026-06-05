"""
Zonal E/E Architecture — PDF Report Generator v2
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
def fig_to_image(fig,width_mm=145):
    buf=io.BytesIO()
    fig.savefig(buf,format='png',dpi=150,bbox_inches='tight',facecolor='white')
    plt.close(fig); buf.seek(16)
    raw=buf.read(8); px_w=struct.unpack('>I',raw[0:4])[0]; px_h=struct.unpack('>I',raw[4:8])[0]
    buf.seek(0); aspect=px_h/px_w; width_pt=width_mm*mm; height_pt=width_pt*aspect
    img=Image(buf,width=width_pt,height=height_pt); img.hAlign='CENTER'; return img
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
    pos2={};
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
        ax.scatter(e,s,s=220,color=c,zorder=5,edgecolors='white',linewidth=1.5); ax.annotate(n,(e,s),textcoords='offset points',xytext=(7,5),fontsize=9)
    ax.set_xlabel('ECU Count',fontsize=10); ax.set_ylabel('Wire Length Saved (%)',fontsize=10)
    ax.set_title('Zonal Benefit vs ECU Count',fontsize=11,fontweight='bold',color='#1F4E79')
    ax.set_facecolor('#F8F9FA'); ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True)
    ax=axes[1]; bars=ax.bar(names,wt,color=mc,edgecolor='white')
    for bar,w in zip(bars,wt): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.05,f'{w} kg',ha='center',va='bottom',fontsize=9,fontweight='bold')
    ax.set_title('Estimated Harness Weight Saved (kg)',fontsize=11,fontweight='bold',color='#1F4E79')
    ax.set_ylabel('Weight Saved (kg)',fontsize=10); ax.set_facecolor('#F8F9FA')
    ax.spines[['top','right']].set_visible(False); ax.yaxis.grid(True,alpha=0.4,linestyle='--'); ax.set_axisbelow(True); ax.tick_params(axis='x',labelsize=9)
    plt.tight_layout(); return fig_to_image(fig,width_mm=155)
def build_pdf_report(all_truck_data,all_metrics,all_opts,all_legacies,all_zonals,fleet_results,ai_sections,output_path):
    styles=make_styles(); story=[]; W=A4[0]-4*cm
    def sp(h=6): return Spacer(1,h)
    def hr(): return HRFlowable(width="100%",thickness=1.5,color=BLUE,spaceAfter=4,spaceBefore=4)
    def pb(): return PageBreak()
    truck_data=all_truck_data[0]; m=all_metrics[0]; opt=all_opts[0]
    VN=["Freightliner Cascadia 126","Western Star 49X","Mercedes-Benz Sprinter 519 CDI"]
    VS=["Cascadia 126","Western Star 49X","MB Sprinter 519"]
    # COVER
    story+=[sp(55)]
    story.append(Paragraph("ZONAL E/E ARCHITECTURE",styles['CoverTitle']))
    story.append(Paragraph("COMPARATIVE STUDY REPORT",styles['CoverTitle']))
    story+=[sp(8)]; story.append(Paragraph("Legacy Point-to-Point vs 4-Zone Ethernet Architecture",styles['CoverSub']))
    story+=[sp(14),hr(),sp(10)]; story.append(Paragraph("Fleet Scope:",styles['CoverSub']))
    story.append(Paragraph("Freightliner Cascadia 126 (2020)  |  Western Star 49X (2021)  |  Mercedes-Benz Sprinter 519 CDI (2021)",styles['CoverMeta']))
    total_ecus=sum(r['ecu_count'] for r in fleet_results); total_conn=sum(r['connections'] for r in fleet_results)
    story.append(Paragraph(f"Total ECUs modelled: {total_ecus}  |  Total connections modelled: {total_conn}",styles['CoverMeta']))
    story+=[sp(8)]; story.append(Paragraph("Tool: Zonal E/E Architecture Analyzer  |  AI Review: Groq Llama 3.3 70B",styles['CoverMeta']))
    story.append(Paragraph("Rishit — ECE '28, VIT Vellore  |  DTICI Intern  |  June 2026",styles['CoverMeta']))
    story.append(Paragraph("Primary data source: DTNA SS-1033423, NHTSA public database",styles['CoverMeta']))
    story+=[sp(18),hr(),pb()]
    # HOW TO READ
    story.append(Paragraph("How to Read This Report",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("This report compares two ways of wiring electronics inside a commercial truck. The <b>old way (Legacy / Point-to-Point)</b> connects every Electronic Control Unit (ECU) directly to every other ECU it talks to using individual wires. The <b>new way (Zonal Architecture)</b> divides the truck into 4 physical regions. Each ECU connects to a nearby hub (Zone Controller) with a short wire. The 4 hubs then talk to each other over one Ethernet cable running along the truck. This tool models 3 vehicles, calculates the exact difference in wire length, weight, and complexity, and checks whether the human-drawn zone boundaries are mathematically optimal. A full abbreviation guide is on the next page.",styles['Body']))
    story+=[sp(6),pb()]
    # ABBREVIATIONS
    story.append(Paragraph("Abbreviations and Full Forms",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Every shortform used in this report is listed below. Refer to this page if you encounter an unfamiliar term.",styles['Body'])); story+=[sp(8)]
    half=(len(ABBREVS)+1)//2; ab_rows=[['Abbreviation','Full Form','Abbreviation','Full Form']]
    for i in range(half):
        left=ABBREVS[i]; right=ABBREVS[i+half] if (i+half)<len(ABBREVS) else ('','')
        ab_rows.append([left[0],left[1],right[0],right[1]])
    cw_ab=[W*0.12,W*0.37,W*0.12,W*0.37]
    ex_ab=[('ALIGN',(0,0),(-1,-1),'LEFT'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,1),(2,-1),'Helvetica-Bold'),
           ('TEXTCOLOR',(0,1),(0,-1),NAVY),('TEXTCOLOR',(2,1),(2,-1),NAVY),
           ('BACKGROUND',(0,0),(1,0),NAVY),('BACKGROUND',(2,0),(3,0),NAVY),('LINEAFTER',(1,0),(1,-1),1,BLUE)]
    story.append(make_rl_table(ab_rows,cw_ab,ex_ab)); story+=[sp(6),pb()]
    # SECTION 1 EXEC SUMMARY
    story.append(Paragraph("1. Executive Summary",styles['SectionHead'])); story.append(hr())
    s1=ai_sections.get('SECTION_1_EXECUTIVE_SUMMARY',''); story.append(Paragraph(s1,styles['Body'])); story+=[sp(10)]
    story.append(Paragraph("1.1  Key Metrics — All Three Vehicles",styles['SubHead'])); story+=[sp(4)]
    sum_data=[['Metric','Freightliner\nCascadia 126','Western Star\n49X','MB Sprinter\n519 CDI']]
    mrows=[('ECU Count','ecu_count','',False),('Legacy Wire Length','legacy_length_m','m',False),
           ('Zonal Wire Length','zonal_length_m','m',False),('Wire Length Saved','length_reduction','%',True),
           ('Cross-Zone Runs: Legacy','cross_zone_legacy','',False),('Cross-Zone Runs: Zonal','cross_zone_zonal','',False),
           ('Harness Weight Saved','weight_saved_kg','kg',True),('Zone Efficiency Score','zone_efficiency','%',False)]
    for label,key,unit,_ in mrows:
        row=[label]+[f"{r[key]}{unit}" for r in fleet_results]; sum_data.append(row)
    cw_sum=[W*0.34,W*0.22,W*0.22,W*0.22]
    ex_sum=[('ALIGN',(1,0),(-1,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
            ('BACKGROUND',(1,4),(3,4),LGREEN),('BACKGROUND',(1,7),(3,7),LGREEN),
            ('TEXTCOLOR',(1,2),(3,2),RED),('TEXTCOLOR',(1,3),(3,3),GREEN),
            ('FONTNAME',(1,4),(3,4),'Helvetica-Bold'),('TEXTCOLOR',(1,4),(3,4),GREEN),
            ('BACKGROUND',(1,5),(3,5),LRED),('BACKGROUND',(1,6),(3,6),LGREEN),('TEXTCOLOR',(1,7),(3,7),BLUE)]
    story.append(make_rl_table(sum_data,cw_sum,ex_sum))
    story.append(Paragraph("Table 1: Key metrics — all three vehicles. Green = improvement. Red = legacy (higher is worse). Zone Efficiency = how well physical zones match communication-optimal groupings.",styles['Caption']))
    story+=[sp(6),pb()]
    # SECTION 2 BACKGROUND
    story.append(Paragraph("2. Background — What Is Zonal Architecture?",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("A modern truck has dozens of ECUs — small computers controlling everything from the engine and brakes to the dashboard display and door locks. Each ECU needs to send and receive data from other ECUs to do its job.",styles['Body'])); story+=[sp(5)]
    story.append(Paragraph("The Old Way — Legacy Point-to-Point Architecture",styles['SubHead']))
    story.append(Paragraph("If ECU A needs to talk to ECU B, a dedicated wire is run between them. With 22 ECUs and 25 communication pairs on a Cascadia 126, this creates a dense web of wires crossing the full length of the truck. The engine controller (MCM) talking to the dashboard (ICU) needs a wire running ~5.5 meters. Multiply this across all 25 connections and you get 52.5 meters of wire and 6.3 kg of copper just for signal wiring. This is expensive to manufacture, difficult to route, and hard to repair.",styles['Body'])); story+=[sp(5)]
    story.append(Paragraph("The New Way — 4-Zone Ethernet Architecture",styles['SubHead']))
    story.append(Paragraph("The truck is divided into 4 physical regions. Each ECU connects only to a nearby Zone Controller (ZC) with a short wire (0.5–1.5m). The 4 Zone Controllers then communicate over one Ethernet cable (100BASE-T1) running along the truck spine — about 7m total. When MCM needs to send data to ICU, it sends a message to ZC-PT, which forwards it over the backbone to ZC-CAB, which delivers it to ICU. No long individual wire needed. Result: 24.3m total wire, 2.9 kg, and only 3 cross-vehicle runs instead of 16.",styles['Body'])); story+=[sp(6)]
    explain_data=[['Feature','Legacy Architecture','Zonal Architecture'],
        ['Wiring principle','Direct wire between every communicating pair','Each ECU to local Zone Controller to Ethernet backbone'],
        ['Cross-truck runs','One per communication pair (up to 16 long runs)','Only 3 backbone segments total'],
        ['Wire length (Cascadia)','52.5 m','24.3 m  (-53.7%)'],
        ['Fault isolation','One broken wire can affect the whole system','Fault stays within the affected zone'],
        ['Scalability','Complexity grows fast with each new ECU','Each new ECU adds only one short local wire'],
        ['Industry status','Current standard on most trucks in service','Target for next-generation truck platforms']]
    cw_ex=[W*0.25,W*0.375,W*0.375]
    ex_ex=[('ALIGN',(0,0),(-1,-1),'LEFT'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
           ('BACKGROUND',(2,3),(2,3),LGREEN),('TEXTCOLOR',(2,3),(2,3),GREEN),('FONTNAME',(2,3),(2,3),'Helvetica-Bold')]
    story.append(make_rl_table(explain_data,cw_ex,ex_ex))
    story.append(Paragraph("Table 2: Plain-language comparison of legacy and zonal architecture.",styles['Caption'])); story+=[sp(6),pb()]
    # SECTION 3 VEHICLE CONFIGS
    story.append(Paragraph("3. Vehicle Configurations and Zone Layouts",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Three vehicles spanning the commercial vehicle spectrum were modelled. Each vehicle's ECUs were assigned to one of four physical zones based on their actual mounting location, cross-referenced with official DTNA and Mercedes-Benz service documentation.",styles['Body'])); story+=[sp(8)]
    for i,(td,r) in enumerate(zip(all_truck_data,fleet_results)):
        story.append(Paragraph(f"3.{i+1}  {VN[i]}",styles['SubHead']))
        story.append(Paragraph(f"<b>Total ECUs:</b> {td['metadata']['total_ecus']}  |  <b>Connections:</b> {len(td['connections'])}  |  <b>Source:</b> {td['metadata'].get('source','—')}",styles['BodyPlain'])); story+=[sp(4)]
        zd=[['Zone','ID','Zone Controller','ECUs in Zone','Count']]
        for z in td['zones']:
            eids=', '.join(e['id'] for e in z['ecus']); zd.append([z['name'],z['id'],z['zone_controller'],eids,str(len(z['ecus']))])
        cw_z=[W*0.22,W*0.07,W*0.16,W*0.46,W*0.09]
        ex_z=[('ALIGN',(0,0),(0,-1),'LEFT'),('ALIGN',(3,1),(3,-1),'LEFT'),('ALIGN',(4,0),(4,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold')]
        story.append(make_rl_table(zd,cw_z,ex_z))
        story.append(Paragraph(f"Table 3.{i+1}: Zone layout — {VN[i]}",styles['Caption'])); story+=[sp(6)]
    story+=[pb()]
    # SECTION 4 TOPOLOGY DIAGRAMS ALL 3
    story.append(Paragraph("4. Network Topology Diagrams — All Three Vehicles",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Each vehicle is shown twice: first in its current legacy wiring layout, then as it would look under the proposed 4-zone Ethernet architecture. Node colour indicates the physical zone. Red lines are cross-zone wire runs. In the zonal diagrams, dark hub nodes are Zone Controllers connected by the Ethernet backbone.",styles['Body'])); story+=[sp(10)]
    for i,(td,lg,zn) in enumerate(zip(all_truck_data,all_legacies,all_zonals)):
        story.append(Paragraph(f"4.{i+1}  {VN[i]}",styles['SubHead']))
        li,zi=make_topology_pair(lg,zn,td,VS[i]); r=fleet_results[i]
        story.append(li)
        story.append(Paragraph(f"Legacy: {r['ecu_count']} ECUs  |  {r['cross_zone_legacy']} cross-zone wire runs  |  {r['legacy_length_m']}m total wire",styles['Caption'])); story+=[sp(8)]
        story.append(zi)
        story.append(Paragraph(f"Zonal: {r['ecu_count']} ECUs + 4 Zone Controllers  |  3 backbone segments  |  {r['zonal_length_m']}m total wire  |  {r['length_reduction']}% reduction",styles['Caption']))
        if i<2: story+=[sp(6),pb()]
    story+=[sp(6),pb()]
    # SECTION 5 HARNESS
    story.append(Paragraph("5. Harness Reduction Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("The following analysis quantifies the wire length, cross-zone connection, and weight reduction achieved by switching from legacy to zonal architecture. The same ECUs and same logical communication connections are used in both cases — only the wiring topology changes.",styles['Body'])); story+=[sp(8)]
    for i,(td,met,r) in enumerate(zip(all_truck_data,all_metrics,fleet_results)):
        story.append(Paragraph(f"5.{i+1}  {VN[i]}",styles['SubHead']))
        cd=[['Metric','Legacy\n(Point-to-Point)','Zonal\n(4-Zone)','Reduction'],
            ['Total wire length',f"{met['legacy_length_m']} m",f"{met['zonal_length_m']} m",f"{met['length_reduction_pct']}%"],
            ['Cross-zone wire runs',str(met['cross_zone_legacy']),str(met['cross_zone_zonal']),f"{round((met['cross_zone_legacy']-met['cross_zone_zonal'])/met['cross_zone_legacy']*100,1)}%"],
            ['Est. harness weight',f"{met['legacy_weight_kg']} kg",f"{met['zonal_weight_kg']} kg",f"{met['weight_saved_kg']} kg saved"]]
        cw_c=[W*0.34,W*0.20,W*0.20,W*0.26]
        ex_c=[('ALIGN',(1,1),(-1,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),
              ('TEXTCOLOR',(1,1),(1,-1),RED),('TEXTCOLOR',(2,1),(2,-1),GREEN),
              ('TEXTCOLOR',(3,1),(3,-1),GREEN),('FONTNAME',(3,1),(3,-1),'Helvetica-Bold'),('BACKGROUND',(3,1),(3,-1),LGREEN)]
        story.append(make_rl_table(cd,cw_c,ex_c))
        story.append(Paragraph(f"Table 5.{i+1}: Harness metrics — {VN[i]}",styles['Caption'])); story+=[sp(6)]
    story+=[sp(4)]; s2=ai_sections.get('SECTION_2_HARNESS_REDUCTION',''); story.append(Paragraph(s2,styles['Body'])); story+=[sp(10)]
    story.append(make_fleet_bar_chart(fleet_results))
    story.append(Paragraph("Figure A: Fleet-wide comparison. Wire length (left), cross-zone runs (centre), percentage savings (right). Red = legacy, green = zonal.",styles['Caption'])); story+=[sp(6),pb()]
    # SECTION 6 HUB ANALYSIS
    story.append(Paragraph("6. Communication Hub Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Some ECUs communicate with many others and become natural hubs. Understanding which ECUs are hubs matters because: (1) they determine how much traffic each Zone Controller must handle, and (2) a hub ECU failing could disconnect many other ECUs — making it a single point of failure.",styles['Body'])); story+=[sp(6)]
    s3=ai_sections.get('SECTION_3_HUB_ANALYSIS',''); story.append(Paragraph(s3,styles['Body'])); story+=[sp(8)]
    story.append(Paragraph("6.1  Full Connection Map — Freightliner Cascadia 126",styles['SubHead']))
    cdata=[['From ECU','To ECU','What data flows']]
    for c in all_truck_data[0]['connections']:
        sig=c['signal'].replace('→','->').replace('\u2192','->'); cdata.append([c['from'],c['to'],sig])
    cw_conn=[W*0.13,W*0.13,W*0.74]
    ex_conn=[('ALIGN',(0,0),(1,-1),'CENTER'),('ALIGN',(2,1),(2,-1),'LEFT'),('FONTNAME',(0,1),(1,-1),'Helvetica-Bold'),('TEXTCOLOR',(0,1),(1,-1),NAVY)]
    story.append(make_rl_table(cdata,cw_conn,ex_conn))
    story.append(Paragraph("Table 6: All 25 connections. In legacy = one dedicated wire each. In zonal = one message route over Ethernet backbone.",styles['Caption'])); story+=[sp(6),pb()]
    # SECTION 7 ZONE OPTIMALITY
    story.append(Paragraph("7. Zone Boundary Optimality Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("<i>Are the zone boundaries drawn in the right place?</i><br/><br/>Zones are currently drawn based on physical location. But communication patterns do not always follow geography — the engine controller (MCM) talks heavily to the dashboard (ICU) even though they are in different zones.<br/><br/>A graph algorithm called <b>Greedy Modularity Community Detection</b> was applied to find the mathematically optimal zone groupings based purely on who talks to whom — ignoring physical location entirely. The result is compared to the human-designed zones using a score called <b>Modularity</b> (range 0–1, higher is better).",styles['Body'])); story+=[sp(8)]
    od=[['Design Approach','Zone Count','Modularity Score','What this means'],
        ['Human-defined (physical location)','4',str(opt['human_score']),'Current real-world zone layout'],
        ['Algorithm-optimal (communication pattern)','5',str(opt['optimal_score']),'Best possible grouping by algorithm']]
    cw_opt=[W*0.38,W*0.12,W*0.16,W*0.34]
    ex_opt=[('ALIGN',(1,0),(2,-1),'CENTER'),('TEXTCOLOR',(2,1),(2,1),RED),('FONTNAME',(2,1),(2,1),'Helvetica-Bold'),
            ('TEXTCOLOR',(2,2),(2,2),GREEN),('FONTNAME',(2,2),(2,2),'Helvetica-Bold'),('BACKGROUND',(0,1),(-1,1),LRED),('BACKGROUND',(0,2),(-1,2),LGREEN)]
    story.append(make_rl_table(od,cw_opt,ex_opt))
    story.append(Paragraph(f"Table 7: Zone boundary analysis. Zone efficiency score = {opt['efficiency']}% (human modularity / optimal modularity x 100).",styles['Caption'])); story+=[sp(8)]
    s4=ai_sections.get('SECTION_4_ZONE_BOUNDARY',''); story.append(Paragraph(s4,styles['Body'])); story+=[sp(8)]
    if opt['reassignments']:
        story.append(Paragraph("7.1  ECUs Flagged as Communication Boundary Nodes",styles['SubHead']))
        story.append(Paragraph("These ECUs are physically in one zone but communicate primarily with ECUs in other zones. They are not in the wrong physical location — they are flagged because their communication pattern crosses zone boundaries.",styles['Body'])); story+=[sp(4)]
        fd=[['ECU','Physical Zone','Algorithm Cluster','Main communication partners']]
        for f in opt['reassignments'][:12]: fd.append([f['ecu'],f['human_zone'],f"Cluster {f['algo_group']}",f['neighbors']])
        cw_fl=[W*0.10,W*0.21,W*0.15,W*0.54]
        ex_fl=[('ALIGN',(0,0),(2,-1),'CENTER'),('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),('TEXTCOLOR',(0,1),(0,-1),NAVY),('ALIGN',(3,1),(3,-1),'LEFT')]
        story.append(make_rl_table(fd,cw_fl,ex_fl))
        story.append(Paragraph("Table 8: Boundary ECUs. Not misplaced physically — flagged because communication partners span multiple zones.",styles['Caption']))
    story+=[sp(8),pb()]
    story.append(make_efficiency_chart(fleet_results))
    story.append(Paragraph("Figure B: Zone optimality across all 3 vehicles. Left: modularity scores. Right: zone efficiency scores. All vehicles show low efficiency — confirming this physical-vs-communication tradeoff is structural, not vehicle-specific.",styles['Caption'])); story+=[sp(6),pb()]
    # SECTION 8 FLEET
    story.append(Paragraph("8. Fleet-Wide Comparative Analysis",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("Running the same analysis across three different vehicles reveals how zonal architecture benefit scales with vehicle size and complexity.",styles['Body'])); story+=[sp(8)]
    fld=[['Vehicle','ECUs','Connections','Legacy\nWire (m)','Zonal\nWire (m)','Wire\nSaved','Weight\nSaved','Zone\nEfficiency']]
    for r in fleet_results:
        fld.append([r['model'].split('(')[0].strip(),str(r['ecu_count']),str(r['connections']),
                    f"{r['legacy_length_m']}m",f"{r['zonal_length_m']}m",f"{r['length_reduction']}%",f"{r['weight_saved_kg']}kg",f"{r['zone_efficiency']}%"])
    cw_fl2=[W*0.26,W*0.06,W*0.09,W*0.09,W*0.09,W*0.09,W*0.11,W*0.11]
    ex_fl2=[('ALIGN',(1,0),(-1,-1),'CENTER'),('ALIGN',(0,1),(0,-1),'LEFT'),
            ('FONTNAME',(5,1),(5,-1),'Helvetica-Bold'),('TEXTCOLOR',(3,1),(3,-1),RED),
            ('TEXTCOLOR',(4,1),(4,-1),GREEN),('TEXTCOLOR',(5,1),(5,-1),GREEN),('BACKGROUND',(5,1),(5,-1),LGREEN)]
    story.append(make_rl_table(fld,cw_fl2,ex_fl2))
    story.append(Paragraph("Table 9: Fleet-wide comparison — all three vehicles.",styles['Caption'])); story+=[sp(8)]
    story.append(make_scaling_chart(fleet_results))
    story.append(Paragraph("Figure C (left): Wire saved vs ECU count — savings do not scale linearly; physical spread matters more than ECU count. Figure C (right): Absolute harness weight saved per vehicle.",styles['Caption'])); story+=[sp(8)]
    s5=ai_sections.get('SECTION_5_FLEET_INSIGHTS',''); story.append(Paragraph(s5,styles['Body'])); story+=[sp(6)]
    story.append(Paragraph("8.1  Key Cross-Fleet Findings",styles['SubHead']))
    findings=["Zonal wire savings do not scale linearly with ECU count. Physical spread of ECUs across the chassis matters more than total ECU count.",
              "Cross-zone wire runs always collapse to exactly 3 backbone segments in a 4-zone design regardless of vehicle size — a structural property of the topology.",
              "Zone efficiency scores are consistently low (7.0%, -4.9%, 31.2%) across all vehicles — confirming the physical-vs-communication tradeoff is fundamental to automotive E/E architecture.",
              "The Sprinter van (12 ECUs) still saves 32.2% wire length. However, adding 4 zone controllers on a 12-ECU platform adds proportionally more hardware overhead — suggesting a practical ROI threshold of ~15+ ECUs."]
    for i,f in enumerate(findings,1): story.append(Paragraph(f"<b>Finding {i}:</b>  {f}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(6),pb()]
    # SECTION 9 AI REVIEW
    story.append(Paragraph("9. AI-Assisted Engineering Review",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("The following engineering review was generated by Groq Llama 3.3 70B based solely on the computed data above. The model was instructed to act as a senior automotive E/E architect and provide specific, physically valid recommendations.",styles['Body'])); story+=[sp(8)]
    story.append(Paragraph("9.1  Design Recommendations",styles['SubHead']))
    s6=ai_sections.get('SECTION_6_RECOMMENDATIONS','')
    recs=[l.strip() for l in s6.split('\n') if l.strip().startswith('REC_')]
    if not recs: recs=[l.strip() for l in s6.split('\n') if l.strip()]
    for i,rec in enumerate(recs[:3],1):
        txt=rec[7:].strip() if rec.startswith('REC_') else rec
        story.append(Paragraph(f"<b>{i}.</b>  {txt}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(8)]; story.append(Paragraph("9.2  Analysis Limitations",styles['SubHead']))
    s7=ai_sections.get('SECTION_7_LIMITATIONS','')
    lims=[l.strip() for l in s7.split('\n') if l.strip().startswith('LIM_')]
    if not lims: lims=[l.strip() for l in s7.split('\n') if l.strip()]
    for lim in lims[:2]:
        txt=lim[7:].strip() if lim.startswith('LIM_') else lim
        story.append(Paragraph(f"\u2022  {txt}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(6),pb()]
    # SECTION 10 METHODOLOGY
    story.append(Paragraph("10. Methodology and Data Sources",styles['SectionHead'])); story.append(hr())
    story.append(Paragraph("10.1  How the Tool Works",styles['SubHead']))
    tool_steps=[("Step 1 — Input (YAML config file)","Each vehicle's ECUs, zone assignments, and connections are described in a YAML text file. Wire length estimates are based on published chassis dimensions."),
                ("Step 2 — Graph building (graph.py)","Two NetworkX graphs are built: legacy (ECU-to-ECU edges weighted by wire length) and zonal (ECU-to-ZC stubs + backbone)."),
                ("Step 3 — Metrics (metrics.py)","Total wire length, cross-zone run count, and harness weight are computed by summing edge weights."),
                ("Step 4 — Zone optimality (optimizer.py)","Greedy Modularity Community Detection finds communication-optimal zone groupings. Modularity score and zone efficiency are calculated."),
                ("Step 5 — Fleet comparison (fleet_compare.py)","Steps 1-4 run for all three vehicles and results are compiled into cross-vehicle tables."),
                ("Step 6 — AI review (reviewer.py)","Computed data is passed to Groq Llama 3.3 70B with a structured automotive engineering prompt."),
                ("Step 7 — PDF generation (build_pdf_report.py)","Matplotlib generates all diagrams. ReportLab assembles them with tables and text into this PDF.")]
    for title,desc in tool_steps: story.append(Paragraph(f"<b>{title}:</b>  {desc}",styles['BulletItem'])); story+=[sp(3)]
    story+=[sp(8)]; story.append(Paragraph("10.2  Data Sources",styles['SubHead']))
    sources=["DTNA SS-1033423 — J-1939 Fault Code Source Address Descriptions. Daimler Trucks North America. NHTSA public database. Primary ECU list source for Cascadia 126.",
             "DTNA STI-503 — NGC sSAM, VPDM & BCA Wall Chart. Rev. Q, March 2020. Physical ECU location confirmation.",
             "Western Star Bodybuilder Manual Rev 3.1 — Western Star 49X ECU configuration.",
             "Mercedes-Benz XENTRY public diagnostic documentation — Sprinter 519 CDI ECU configuration.",
             "Park C, Cui C, Park S. Analysis of E2E Delay and Wiring Harness in Zonal Architecture. Sensors. 2024;24(10):3248. Academic methodology validation.",
             "SAE J1939 — Serial Control and Communications Heavy Duty Vehicle Network."]
    for i,src in enumerate(sources,1): story.append(Paragraph(f"{i}.  {src}",styles['BulletItem'])); story+=[sp(2)]
    story+=[sp(8)]; story.append(Paragraph("10.3  Key Assumptions",styles['SubHead']))
    assumptions=["Wire lengths estimated from published chassis dimensions: Cascadia 126 ~8.5m, Western Star 49X ~7.5m, Sprinter ~5.5m",
                 "Harness weight calculated using 120 g/m bundled average — conservative estimate for signal-wire harnesses",
                 "Analysis covers signal and data wires only — power distribution harness excluded",
                 "Static ECU configuration — optional equipment and variant builds not modelled",
                 "All ECU data sourced from public DTNA and Mercedes-Benz documents — no proprietary OEM data used"]
    for a in assumptions: story.append(Paragraph(f"\u2022  {a}",styles['BulletItem'])); story+=[sp(2)]
    story+=[sp(16),hr()]
    story.append(Paragraph("Zonal E/E Architecture Analyzer  |  Open-source personal R&D project  |  https://github.com/Rish-736/zonal-ee-analyzer",styles['CoverMeta']))
    story.append(Paragraph("Built alongside DTICI internship research — Rishit, ECE '28, VIT Vellore — June 2026",styles['CoverMeta']))
    def on_page(canvas,doc):
        canvas.saveState()
        if doc.page==1:
            canvas.setFillColor(colors.HexColor("#1F4E79"))
            canvas.rect(0,A4[1]-2.2*cm,A4[0],2.2*cm,fill=1,stroke=0)
            canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold',10)
            canvas.drawCentredString(A4[0]/2,A4[1]-1.4*cm,"DTICI INTERNSHIP RESEARCH  |  ZONAL E/E ARCHITECTURE STUDY  |  JUNE 2026")
        canvas.setFont('Helvetica',7); canvas.setFillColor(colors.HexColor("#595959"))
        canvas.drawString(2*cm,1.2*cm,"Zonal E/E Architecture Comparative Study Report")
        canvas.drawRightString(A4[0]-2*cm,1.2*cm,f"Page {doc.page}"); canvas.restoreState()
    doc=SimpleDocTemplate(output_path,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm,
                          title="Zonal E/E Architecture Comparative Study Report",author="Rishit — VIT Vellore / DTICI")
    doc.build(story,onFirstPage=on_page,onLaterPages=on_page)
    print(f"\n  PDF saved: {output_path}"); return output_path
if __name__=="__main__":
    from parser import load_truck_config
    from graph import build_legacy_graph,build_zonal_graph
    from metrics import calculate_metrics
    from optimizer import run_optimizer
    from fleet_compare import run_fleet_comparison
    from reviewer import build_review_prompt,call_groq,parse_ai_sections
    CONFIGS=["configs/cascadia_126_2020.yaml","configs/western_star_49x_2021.yaml","configs/sprinter_van_2021.yaml"]
    print("Running full analysis pipeline...")
    atd,am,ao,al,az=[],[],[],[],[]
    for cfg in CONFIGS:
        td=load_truck_config(cfg); lg=build_legacy_graph(td); zn=build_zonal_graph(td)
        met=calculate_metrics(lg,zn,td); opt=run_optimizer(td)
        atd.append(td); am.append(met); ao.append(opt); al.append(lg); az.append(zn)
    fleet=run_fleet_comparison()
    for r,td,opt in zip(fleet,atd,ao):
        r['human_modularity']=opt['human_score']; r['optimal_modularity']=opt['optimal_score']; r['connections']=len(td['connections'])
    print("\nCalling Groq API...")
    prompt=build_review_prompt(atd[0],am[0],ao[0],fleet); ai_text=call_groq(prompt); sections=parse_ai_sections(ai_text)
    print("Building PDF report..."); os.makedirs('outputs',exist_ok=True)
    output_path="outputs/ZonalEE_Comparative_Study_Report.pdf"
    build_pdf_report(atd,am,ao,al,az,fleet,sections,output_path)
    print(f"\nDone. Open: {output_path}")