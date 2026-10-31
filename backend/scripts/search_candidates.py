#!/usr/bin/env python3
"""
search_candidates.py - Query indiacode.gov.in Central Acts collection for target candidates.
"""

import requests
import json
import time

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
CENTRAL_ACTS_COL = '69a0c1fb-7b22-4481-b16a-1dc59b5d02e6'

candidates = [
    "Right to Information",
    "Consumer Protection Act, 2019",
    "Information Technology Act, 2000",
    "Contract Act",
    "Sale of Goods",
    "Negotiable Instruments",
    "Motor Vehicles Act, 1988",
    "Environment (Protection) Act, 1986",
    "Domestic Violence",
    "Rights of Persons with Disabilities",
    "Maternity Benefit",
    "Payment of Wages",
    "Right of Children to Free and Compulsory Education",
    "Insolvency and Bankruptcy Code",
    "Public Examinations (Prevention of Unfair Means)",
    "Biological Diversity",
    "Competition Act, 2002"
]

def search_candidate(name):
    query = f'"{name}"'
    url = f'https://indiacode.gov.in/server/api/discover/search/objects?scope={CENTRAL_ACTS_COL}&query={requests.utils.quote(query)}&size=5'
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []
    results = []
    data = r.json()
    for obj in data.get('_embedded', {}).get('searchResult', {}).get('_embedded', {}).get('objects', []):
        item = obj.get('_embedded', {}).get('indexableObject', {})
        item_id = item.get('id')
        item_name = item.get('name')
        
        # Check bundles
        b_url = f'https://indiacode.gov.in/server/api/core/items/{item_id}/bundles'
        br = requests.get(b_url, headers=headers, timeout=10)
        en_bs = None
        hi_bs = None
        for b in br.json().get('_embedded', {}).get('bundles', []):
            if b.get('name') == 'ORIGINAL':
                bs_url = b.get('_links', {}).get('bitstreams', {}).get('href')
                bsr = requests.get(bs_url, headers=headers, timeout=10)
                for bs in bsr.json().get('_embedded', {}).get('bitstreams', []):
                    fname = bs.get('name', '')
                    fid = bs.get('id')
                    fsize = bs.get('sizeBytes')
                    if fname.lower().startswith(('h', 'hindi')):
                        hi_bs = {'name': fname, 'id': fid, 'size': fsize}
                    elif fname.lower().startswith(('a', 'eng')):
                        en_bs = {'name': fname, 'id': fid, 'size': fsize}
                    else:
                        # Could be either
                        if not en_bs:
                            en_bs = {'name': fname, 'id': fid, 'size': fsize}
                        elif not hi_bs:
                            hi_bs = {'name': fname, 'id': fid, 'size': fsize}
        results.append({
            'id': item_id,
            'name': item_name,
            'en': en_bs,
            'hi': hi_bs
        })
    return results

if __name__ == '__main__':
    for c in candidates:
        time.sleep(1)
        res = search_candidate(c)
        print(f"\nCandidate: {c}")
        for r in res:
            has_both = (r['en'] is not None and r['hi'] is not None)
            marker = "[BOTH]" if has_both else "[PARTIAL]"
            print(f"  {marker} {r['name']}")
            if r['en']:
                print(f"      EN: {r['en']['name']} ({r['en']['id']})")
            if r['hi']:
                print(f"      HI: {r['hi']['name']} ({r['hi']['id']})")
