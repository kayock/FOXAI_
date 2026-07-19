from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any

EXPECTED = [
    ('masterbook_core','MasterBook Corebook','Masterbook Corebook.pdf',True),
    ('world_of_necroscope','MasterBook — World of Necroscope','MasterBook - World of Necroscope.pdf',True),
    ('e_branch','E-Branch Guide to Psionics','MasterBook - World of Necroscope_ E-Branch Guide to Psionics.pdf',False),
    ('operation_nightside','Operation Nightside','[The World of Necroscope] - Operation Nightside.pdf',False),
    ('wamphyri','Wamphyri','MasterBook - World of Necroscope_ Wamphyri.pdf',False),
    ('deadspeak','Deadspeak Dossier','MasterBook - World of Necroscope_ Deadspeak Dossier.pdf',False),
]

KEYWORDS = {
    'deck_system':['masterdeck','master deck','action card','cards in hand','draw a card','discard','play a card','hand limit','subplot card'],
    'core_resolution':['value chart','result points','difficulty number','effect value','2d10','two ten-sided dice'],
    'character_creation':['character creation','attributes','skills','advantages','disadvantages','character points'],
    'necroscope_lore':['e-branch','deadspeak','wamphyri','necroscope','psychic','psionic'],
}

def norm(s:str)->str:
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s.casefold()).split())

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def add_runtime_paths(root:Path)->None:
    for p in [
        root/'Runtime'/'Desktop'/'python'/'Lib'/'site-packages',
        root/'Runtime'/'ComfyUI'/'site-packages',
        root/'Runtime'/'ComfyUI'/'python_embeded'/'Lib'/'site-packages',
        root/'Runtime'/'ComfyUI'/'python_embedded'/'Lib'/'site-packages',
    ]:
        if p.is_dir() and str(p) not in sys.path: sys.path.append(str(p))

def find_exe(root:Path,names:list[str])->Path|None:
    for name in names:
        found=shutil.which(name)
        if found: return Path(found)
    wanted={n.casefold() for n in names}
    for base in [root/'Tools',root/'Runtime',root/'System'/'Tools']:
        if not base.is_dir(): continue
        try:
            for p in base.rglob('*.exe'):
                if p.name.casefold() in wanted: return p
        except OSError: pass
    return None

class Extractor:
    name='raw PDF probe (inventory only)'
    raw=True
    def inspect(self,path:Path)->dict[str,Any]:
        data=path.read_bytes(); decoded=data.decode('latin-1','ignore')
        return {'page_count':len(re.findall(rb'/Type\s*/Page\b',data)) or None,'pages':[decoded],'encrypted':b'/Encrypt' in data}

class FitzExtractor(Extractor):
    name='PyMuPDF'; raw=False
    def __init__(self,m): self.m=m
    def inspect(self,path):
        doc=self.m.open(str(path))
        try: return {'page_count':doc.page_count,'pages':[doc.load_page(i).get_text('text') or '' for i in range(doc.page_count)],'encrypted':bool(getattr(doc,'is_encrypted',False))}
        finally: doc.close()

class PyPdfExtractor(Extractor):
    name='pypdf/PyPDF2'; raw=False
    def __init__(self,m): self.m=m
    def inspect(self,path):
        r=self.m.PdfReader(str(path)); enc=bool(getattr(r,'is_encrypted',False))
        if enc:
            try:r.decrypt('')
            except Exception:pass
        pages=[]
        for p in r.pages:
            try: pages.append(p.extract_text() or '')
            except Exception: pages.append('')
        return {'page_count':len(r.pages),'pages':pages,'encrypted':enc}

class PdftotextExtractor(Extractor):
    name='Poppler pdftotext'; raw=False
    def __init__(self,exe): self.exe=exe
    def inspect(self,path):
        r=subprocess.run([str(self.exe),'-layout',str(path),'-'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        if r.returncode: raise RuntimeError(r.stderr.strip() or 'pdftotext failed')
        pages=r.stdout.split('\f')
        if pages and not pages[-1].strip(): pages.pop()
        return {'page_count':len(pages),'pages':pages,'encrypted':False}

def choose(root:Path)->Extractor:
    add_runtime_paths(root)
    for name in ['fitz','pymupdf']:
        try:return FitzExtractor(importlib.import_module(name))
        except Exception:pass
    for name in ['pypdf','PyPDF2']:
        try:return PyPdfExtractor(importlib.import_module(name))
        except Exception:pass
    exe=find_exe(root,['pdftotext.exe','pdftotext'])
    return PdftotextExtractor(exe) if exe else Extractor()

def hits(pages:list[str])->dict[str,dict[str,list[int]]]:
    out={}
    for group,terms in KEYWORDS.items():
        found={}
        for term in terms:
            rx=re.compile(re.escape(term),re.I)
            nums=[i for i,t in enumerate(pages,1) if rx.search(t or '')]
            if nums: found[term]=nums[:30]
        if found: out[group]=found
    return out

def inspect_book(path:Path,ex:Extractor)->dict[str,Any]:
    row={'filename':path.name,'path':str(path),'size_bytes':path.stat().st_size,'sha256':sha(path),'extractor':ex.name}
    try:
        data=ex.inspect(path); pages=data.get('pages') or []; count=data.get('page_count') or len(pages)
        lengths=[len(re.sub(r'\s+','',t or '')) for t in pages]
        meaningful=sum(n>=80 for n in lengths); blank=sum(n<30 for n in lengths)
        if ex.raw: status='extractor_unavailable'
        elif meaningful==0: status='likely_image_scan_or_protected'
        elif meaningful/max(count,1)<.35: status='mixed_or_scan_heavy'
        else: status='text_extractable'
        row.update(page_count=count,encrypted=bool(data.get('encrypted')),text_characters=sum(len(t or '') for t in pages),meaningful_text_pages=meaningful,nearly_blank_pages=blank,keyword_hits=hits(pages),text_status=status)
    except Exception as e:
        row.update(page_count=None,encrypted=None,text_characters=0,meaningful_text_pages=0,nearly_blank_pages=0,keyword_hits={},text_status='inspection_error',error=f'{type(e).__name__}: {e}')
    return row

def report_md(report:dict[str,Any])->str:
    L=['# FOXAI Necroscope Source Preflight','',f"- Created: `{report['created']}`",f"- FOXAI root: `{report['foxai_root']}`",f"- Extractor: **{report['extractor']}**",f"- Classification: **{report['classification']}**",'','## Safety','','- Source PDFs were opened read-only.','- No PDF was modified, renamed, moved, copied, or uploaded.','- No network access was used.','- Reports were written only under `Projects\\NecroscopeCampaign\\Preflight`.','','## Books','']
    for b in report['books']:
        L += [f"### {b['title']}",'']
        if not b['found']:
            L += [f"**Missing** — expected `{b['expected_filename']}`",'']; continue
        i=b['inspection']; L += [f"- File: `{i['filename']}`",f"- Size: `{i['size_bytes']/(1024*1024):.2f} MB`",f"- SHA-256: `{i['sha256']}`",f"- Pages: `{i.get('page_count')}`",f"- Text status: **{i.get('text_status')}**",f"- Extracted characters: `{i.get('text_characters',0):,}`",f"- Meaningful text pages: `{i.get('meaningful_text_pages',0)}`",f"- Nearly blank pages: `{i.get('nearly_blank_pages',0)}`",'']
        for group,terms in (i.get('keyword_hits') or {}).items():
            L += [f"- **{group.replace('_',' ').title()} page leads**"]
            for term,pages in terms.items(): L += [f"  - `{term}`: {', '.join(map(str,pages))}"]
        if i.get('keyword_hits'): L.append('')
        if i.get('error'): L += [f"- Error: `{i['error']}`",'']
    L += ['## Readiness','',f"**{report['classification']}**",'']+[f'- {n}' for n in report['notes']]+['','## Next Step','','Upload this Markdown report to the FOXAI development chat. It will show whether the next build should use direct page indexing, selective OCR, or a small local extractor addition.','','Agent-Managed Deck remains the planned default. Exact card rules will be taken from the owned local books and recorded with page references.','']
    return '\n'.join(L)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--root'); a=ap.parse_args()
    script_dir=Path(__file__).resolve().parent; root=Path(a.root).resolve() if a.root else script_dir.parent.resolve(); lib=root/'Library'/'DnD'
    if not (root/'foxai.py').is_file(): print('ERROR: Extract directly inside Z:\\FOXAI'); return 2
    if not lib.is_dir(): print('ERROR: Library\\DnD is missing'); return 3
    pdfs=[p for p in lib.glob('*.pdf') if p.is_file()]; exact={p.name.casefold():p for p in pdfs}; normalized={norm(p.name):p for p in pdfs}; ex=choose(root); books=[]
    for key,title,filename,required in EXPECTED:
        p=exact.get(filename.casefold()) or normalized.get(norm(filename)); row={'key':key,'title':title,'required':required,'expected_filename':filename,'found':bool(p)}
        if p: print('Inspecting read-only:',p.name); row['inspection']=inspect_book(p,ex)
        books.append(row)
    missing=[b['title'] for b in books if b['required'] and not b['found']]
    if missing: classification='NEEDS_REQUIRED_BOOKS'; notes=['Missing required books: '+', '.join(missing)]
    elif ex.raw: classification='NEEDS_LOCAL_PDF_EXTRACTOR'; notes=['Books were inventoried and hashed, but no local PDF text extractor was found.']
    else:
        bad=[b['title'] for b in books if b['required'] and b.get('inspection',{}).get('text_status') not in {'text_extractable','mixed_or_scan_heavy'}]
        mixed=[b['title'] for b in books if b.get('inspection',{}).get('text_status')=='mixed_or_scan_heavy']
        if bad: classification='NEEDS_OCR_OR_EXTRACTION_REPAIR'; notes=['Required books need OCR or extraction repair: '+', '.join(bad)]
        elif mixed: classification='READY_WITH_SELECTIVE_OCR'; notes=['Some books may need selective OCR: '+', '.join(mixed)]
        else: classification='READY_FOR_NECROSCOPE_INDEX_V1'; notes=['Required books contain extractable text. Page-grounded indexing can proceed.']
    created=datetime.now().astimezone().isoformat(timespec='seconds'); report={'schema':'foxai.necroscope.source_preflight.v1','created':created,'read_only':True,'network_used':False,'foxai_root':str(root),'library_path':str(lib),'extractor':ex.name,'classification':classification,'notes':notes,'books':books}
    out=root/'Projects'/'NecroscopeCampaign'/'Preflight'; out.mkdir(parents=True,exist_ok=True); stamp=datetime.now().strftime('%Y%m%dT%H%M%S'); jp=out/f'necroscope_source_preflight_{stamp}.json'; mp=out/f'necroscope_source_preflight_{stamp}.md'; jp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8'); mp.write_text(report_md(report),encoding='utf-8'); (out/'LATEST.txt').write_text(f'{mp}\n{jp}\n',encoding='utf-8')
    print('\n'+'='*66); print('NECROSCOPE SOURCE PREFLIGHT COMPLETE'); print('='*66); print('Classification:',classification); print('Extractor:',ex.name); print('Markdown report:',mp); print('JSON report:',jp); print('\nNo source PDFs were modified.'); return 0

if __name__=='__main__': raise SystemExit(main())
