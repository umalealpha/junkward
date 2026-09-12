# -*- coding: utf-8 -*-
import html
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x0D,0x1B,0x2A); ORANGE = RGBColor(0xF4,0xA6,0x23); FONT="Book Antiqua"
DATE_LONG="04 September 2026"; DATE_SHORT="04/09/2026"

COLS=["Payment Reference","Amount (BWP)","Invoice No.","Invoice Date","Insured Name","Reason","Inputer","Verified By"]
secA=[["PROVIDENT FUND AUGUST 000060 (O)","78,356.00","N/A","N/A","N/A","Provident Fund Contribution – August","Pako Kago","Kago Tshutlhedi"]]
secB=[
["G2026004593 OPTIMUM PANEL BEAT","154,964.92","5486","08/07/2026 per Graphite (07/08/2026 on Finance request)","PST Sales and Distribution (Pty) Ltd","Motor – Scania G460 (B 231 BII) single-vehicle accident on the A1 near Jan Botswana dealership, 9 April 2026; second repair invoice from Optimum Panel Beaters (first payment BWP 171,404.18 made 2 July 2026)","Bontle Tendani","Kago Tshutlhedi"],
["G2026004824 NORS","155,080.34","7212109317","30/07/2026","Romcon Investments (Pty) Ltd","Motor – Volvo horse (B391BKJ) and trailers overturned on a curve, 2 June 2026; repair invoice from Nors Botswana. Settlement approved by Paul Beka on 6 July 2026 at BWP 195,934.08 (claim 223,408.80 less 10% excess and betterment)","Koketso Kgetse","Kago Tshutlhedi"],
["G2026005326 BOHUA","522,500.00","N/A (Agreement of Loss)","03/09/2026","Bohua (Pty) Ltd","Motor – Toyota Fortuner (B776BVE) written off, 8 August 2026: driver lost control avoiding a cow and the vehicle overturned. Sum insured 550,000.00 less 5% excess 27,500.00; valuation 637,075.60; salvage reserve 127,415.12. Recommended by Wangu Moses 27 August 2026","Bontle Tendani","Kago Tshutlhedi"],
["G2026005352 BUILDERS 000093 (O)","88,099.65","N/A (Agreement of Loss)","03/09/2026","Builders Maps Hardware","Motor – home-made trailer B869AYN hijacked near Mafikeng, South Africa, 7 June 2026, not recovered; reported 18 August 2026. Valuation 117,466.20; Claims recommended 111,592.89 after 5% excess; 88,099.65 loaded (75% of valuation)","Bontle Tendani","Kago Tshutlhedi"],
["G2026005353 BUILDERS 000094 (O)","88,099.64","N/A (Agreement of Loss)","03/09/2026","Builders Maps Hardware","Motor – home-made trailer B874AYN, same hijacking as above, 7 June 2026, not recovered. Valuation 117,466.20; Claims recommended 111,592.89 after 5% excess; Graphite payment 88,099.65 (Finance loaded 88,099.64)","Bontle Tendani","Kago Tshutlhedi"],
]
totA="78,356.00"; totB="1,008,744.55"; totAll="1,087,100.55"
summary=[["Total Current Account Payments (1)",totA],["Total Claims Payments (5)",totB],["Total Requested Payments (6)",totAll]]
bankCols=["Account","Balance Before (BWP)","Transfer (BWP)","Balance After Transfer (BWP)","Total Payments (BWP)","Balance After (BWP)"]
bank=[["Claims Account","222,309.10","+ 1,000,000.00","1,222,309.10","1,008,744.55","213,564.55"],
      ["Current Account","2,127,508.54","- 1,000,000.00","1,127,508.54","78,356.00","1,049,152.54"]]
funds=("SUFFICIENT FUNDS: after the BWP 1,000,000.00 transfer from the Current Account (effected by Finance), the Claims Account "
       "(BWP 1,222,309.10) covers the claims payments (BWP 1,008,744.55) in full, leaving BWP 213,564.55. The Current Account "
       "(BWP 1,127,508.54) covers the provident fund (BWP 78,356.00), leaving BWP 1,049,152.54. Balances are as stated by Finance on 4 September 2026 and were not independently re-read from FNB for this request.")
nbs=[
"NB (Graphite check, 4 September 2026): all five claim numbers exist in Graphite, are Open, and the insured company names, vehicles and payees agree with the Finance request. Points below need an answer before release.",
"NB – G2026005326 BOHUA (BWP 522,500.00): Paul Beka instructed on 28 August 2026 that the salvage be confirmed as secured. Graphite holds no confirmation. Salvage (reserve BWP 127,415.12) must be in the yard before this settlement is released. Also outstanding on file: the second page of the police report requested by Segolame Masilo on 25 August 2026, and a flagging form on file that carries a different claim number (G2026004449).",
"NB – G2026005352 / G2026005353 BUILDERS: Graphite records both payments at BWP 88,099.65. The request shows the second at 88,099.64. Two identical payments to one payee on one day would trip the duplicate-payment check, so the one-thebe change must be explained and the correct amount loaded. Separately, Claims recommended BWP 111,592.89 per trailer but BWP 88,099.65 (75% of valuation) was agreed; the extra 20% deduction (BWP 23,493.24 per trailer) is not documented in Graphite and should be recorded on the signed Agreements of Loss. The loss was reported 72 days after the event.",
"NB – G2026004824 NORS: the approved settlement was BWP 195,934.08; BWP 155,080.34 is loaded and Graphite shows the remaining BWP 45,987.58 released. Finance to confirm whether the balance is a genuine saving or a second invoice still to come, before the reserve is closed.",
"NB – G2026004593 OPTIMUM: Graphite records the invoice at BWP 154,964.93 dated 8 July 2026; the request shows 154,964.92 dated 07/08/2026. Confirm the invoice date and cents. No approval memo for either Optimum payment is recorded in Graphite; the approval sits outside the system. Claim status still reads Awaiting Invoice.",
"NB – Portfolio context: PST Sales and Distribution has 80 claims in 18 months; Romcon Investments 13; Builders Maps Hardware has received 994% of its premium in claims (3 claims). Underwriting to review these accounts at renewal.",
]
decl=[("Senior Accountant Declaration:","\"I confirm that I have checked the relevant bank balances, sufficient funds are available for the above payment(s), and all payments have been verified.\""),
      ("Finance Manager Declaration:","\"I confirm that I have reviewed the liquidity impact and cleared the above payment(s) for approval.\"")]

# ---------- DOCX ----------
doc=Document()
for s in doc.sections:
    s.left_margin=s.right_margin=Cm(1.6); s.top_margin=s.bottom_margin=Cm(1.5)
st=doc.styles['Normal']; st.font.name=FONT; st.font.size=Pt(10)
st.element.rPr.rFonts.set(qn('w:eastAsia'),FONT)

def para(text,size=10,bold=False,color=None,align=None,space=4):
    p=doc.add_paragraph(); r=p.add_run(text); r.font.name=FONT; r.font.size=Pt(size); r.bold=bold
    if color: r.font.color.rgb=color
    if align is not None: p.alignment=align
    p.paragraph_format.space_after=Pt(space); return p
def shade(cell,hexcolor):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto'); shd.set(qn('w:fill'),hexcolor); tcPr.append(shd)
def table(cols,rows,widths=None,total=None):
    t=doc.add_table(rows=1,cols=len(cols)); t.style='Table Grid'; t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,c in enumerate(cols):
        cell=t.rows[0].cells[i]; cell.text=""; r=cell.paragraphs[0].add_run(c); r.bold=True; r.font.size=Pt(8.5); r.font.name=FONT; r.font.color.rgb=RGBColor(0xFF,0xFF,0xFF); shade(cell,"0D1B2A")
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=""; r=cells[i].paragraphs[0].add_run(v); r.font.size=Pt(8.5); r.font.name=FONT
            if i==1 and len(cols)>2: cells[i].paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.RIGHT
    if total:
        cells=t.add_row().cells; a=cells[0].merge(cells[len(cols)-1]) if len(cols)>2 else cells[0]
        a.text=""; r=a.paragraphs[0].add_run(total); r.bold=True; r.font.size=Pt(9); r.font.name=FONT; shade(a,"FDF1DC")
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Cm(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(2)
    return t

para("Alpha Direct Insurance Company",16,True,NAVY)
para("Payment Authorisation",13,True,ORANGE)
para(f"To: Mr Arun Iyer – Chief Executive Officer\nDate: {DATE_LONG}\nSubject: Payment Approval – Current Account & Claims Payments",10)
para("Mr Iyer,",10)
para("Please find below the payment authorisation request for your review and approval. All payments have been loaded and verified in the banking platform.",10,space=8)
W=[3.3,1.9,1.6,1.9,2.6,4.6,1.5,1.7]
para("Section A: Current Account Payments Loaded & Verified",11,True,NAVY)
table(COLS,secA,W,total=f"Total Current Account Payments (1): BWP {totA}")
para("Section B: Claims Account Payments Loaded & Verified",11,True,NAVY)
table(COLS,secB,W,total=f"Total Claims Payments (5): BWP {totB}")
para("Summary of Requested Payments for Approval",11,True,NAVY)
table(["Payment Category","Amount (BWP)"],summary,[9,4])
para("Bank Position",11,True,NAVY)
table(bankCols,bank,[3.2,2.8,2.6,3.0,2.8,2.8])
para("TRANSFER EFFECTED: BWP 1,000,000.00 transferred from Current Account to Claims Account to fund claims payments. All approved payments are to be processed from their respective accounts.",9.5,True)
para(funds,9.5)
for n in nbs: para(n,9.5)
para("Declarations",11,True,NAVY)
for h,q in decl:
    p=doc.add_paragraph(); r=p.add_run(h+" "); r.bold=True; r.font.name=FONT; r.font.size=Pt(9.5); r2=p.add_run(q); r2.font.name=FONT; r2.font.size=Pt(9.5); p.paragraph_format.space_after=Pt(4)
para("Prepared & Submitted By",11,True,NAVY)
para(f"Name: Bontle Tendani, Assistant Accountant     Date: {DATE_SHORT}     Signature: ___________________",9.5)
para("Verified By (Finance Manager)",11,True,NAVY)
para(f"Name: Kago Tshutlhedi     Date: {DATE_SHORT}     Signature: ___________________",9.5)
para("Reviewed By (CFO – Graphite claim check)",11,True,NAVY)
para(f"Name: Prathap Ganesharajah, CFO     Date: {DATE_SHORT}     Signature: ___________________",9.5)
para("CEO Approval",11,True,NAVY)
para("Name: __________________     Date: __________________     Signature: __________________",9.5,space=10)
para("Alpha Direct Insurance Company  |  Confidential  |  For Internal Use Only",8.5,False,NAVY,WD_ALIGN_PARAGRAPH.CENTER)
out=r"C:/Users/PrathapAsus/OneDrive - Alpha Direct Insurance/Desktop/Largepayment/Large Payment Authorisation - 4 Sep 2026.docx"
doc.save(out); print("saved",out)

# ---------- HTML (email body, whole document) ----------
e=html.escape
def htable(cols,rows,total=None):
    s='<table style="border-collapse:collapse;width:100%;font-family:Book Antiqua,Palatino,serif;font-size:12px;margin:6px 0 14px 0">'
    s+='<tr>'+''.join(f'<th style="background:#0D1B2A;color:#fff;border:1px solid #0D1B2A;padding:6px;text-align:left">{e(c)}</th>' for c in cols)+'</tr>'
    for row in rows:
        cells=[]
        for i,v in enumerate(row):
            extra="text-align:right;white-space:nowrap" if (i==1 and len(cols)>2) else ""
            cells.append(f'<td style="border:1px solid #bbb;padding:6px;vertical-align:top;{extra}">{e(v)}</td>')
        s+='<tr>'+''.join(cells)+'</tr>'
    if total: s+=f'<tr><td colspan="{len(cols)}" style="border:1px solid #bbb;padding:6px;background:#FDF1DC;font-weight:bold">{e(total)}</td></tr>'
    return s+'</table>'
H3='<h3 style="color:#0D1B2A;margin:14px 0 4px 0">'
nb_html=''.join(f'<p style="background:#FDF1DC;border-left:4px solid #F4A623;padding:6px 8px">{e(n)}</p>' for n in nbs)
decl_html=''.join(f'<p><b>{e(a)}</b> {e(b)}</p>' for a,b in decl)
h=(f'<div style="font-family:Book Antiqua,Palatino,serif;color:#111;max-width:1000px;font-size:13px;line-height:1.45">'
f'<div style="font-size:22px;font-weight:bold;color:#0D1B2A">Alpha Direct Insurance Company</div>'
f'<div style="font-size:17px;font-weight:bold;color:#F4A623;margin-bottom:10px">Payment Authorisation</div>'
f'<p><b>To:</b> Mr Arun Iyer – Chief Executive Officer<br><b>Date:</b> {DATE_LONG}<br><b>Subject:</b> Payment Approval – Current Account &amp; Claims Payments</p>'
f'<p>Mr Iyer,</p><p>Please find below the payment authorisation request for your review and approval. All payments have been loaded and verified in the banking platform.</p>'
f'{H3}Section A: Current Account Payments Loaded &amp; Verified</h3>{htable(COLS,secA,f"Total Current Account Payments (1): BWP {totA}")}'
f'{H3}Section B: Claims Account Payments Loaded &amp; Verified</h3>{htable(COLS,secB,f"Total Claims Payments (5): BWP {totB}")}'
f'{H3}Summary of Requested Payments for Approval</h3>{htable(["Payment Category","Amount (BWP)"],summary)}'
f'{H3}Bank Position</h3>{htable(bankCols,bank)}'
f'<p><b>TRANSFER EFFECTED:</b> BWP 1,000,000.00 transferred from Current Account to Claims Account to fund claims payments. All approved payments are to be processed from their respective accounts.</p>'
f'<p>{e(funds)}</p>{nb_html}'
f'{H3}Declarations</h3>{decl_html}'
f'{H3}Prepared &amp; Submitted By</h3><p>Name: Bontle Tendani, Assistant Accountant &nbsp;&nbsp; Date: {DATE_SHORT} &nbsp;&nbsp; Signature: ___________________</p>'
f'{H3}Verified By (Finance Manager)</h3><p>Name: Kago Tshutlhedi &nbsp;&nbsp; Date: {DATE_SHORT} &nbsp;&nbsp; Signature: ___________________</p>'
f'{H3}Reviewed By (CFO – Graphite claim check)</h3><p>Name: Prathap Ganesharajah, CFO &nbsp;&nbsp; Date: {DATE_SHORT} &nbsp;&nbsp; Signature: ___________________</p>'
f'{H3}CEO Approval</h3><p>Name: __________________ &nbsp;&nbsp; Date: __________________ &nbsp;&nbsp; Signature: __________________</p>'
f'<p style="text-align:center;color:#0D1B2A;font-size:11px;margin-top:18px">Alpha Direct Insurance Company &nbsp;|&nbsp; Confidential &nbsp;|&nbsp; For Internal Use Only</p></div>')
open("body.html","w",encoding="utf-8").write(h)
open(r"C:/Users/PrathapAsus/OneDrive - Alpha Direct Insurance/Desktop/Largepayment/Large Payment Authorisation - 4 Sep 2026 (email body).html","w",encoding="utf-8").write('<meta charset="utf-8"><title>Payment Authorisation 4 Sep 2026</title>'+h)
print("html ok")
