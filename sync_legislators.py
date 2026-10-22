"""
Open States -> Supabase legislator sync for SERV at UVA
"""
import os, json, urllib.request, urllib.parse, sys, time

OPENSTATES_KEY = os.environ.get('OPENSTATES_KEY', '').strip()
SUPABASE_URL   = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_SVC   = os.environ.get('SUPABASE_SERVICE_KEY', '').strip()

missing = [n for n,v in [('OPENSTATES_KEY',OPENSTATES_KEY),('SUPABASE_URL',SUPABASE_URL),('SUPABASE_SERVICE_KEY',SUPABASE_SVC)] if not v]
if missing:
    print(f"ERROR: Missing secrets: {', '.join(missing)}")
    sys.exit(1)

print(f"Open States key: {OPENSTATES_KEY[:8]}...")
print(f"Supabase URL:    {SUPABASE_URL}")

SENATE_LOCALITIES = {
    1:['Clarke County','Frederick County','Shenandoah County','Warren County','Winchester'],
    2:['Augusta County','Bath County','Highland County','Page County','Harrisonburg','Rockingham County'],
    3:['Alleghany County','Botetourt County','Buena Vista','Covington','Craig County','Lexington','Roanoke County','Rockbridge County'],
    4:['Roanoke City','Salem'],
    5:['Bland County','Buchanan County','Giles County','Montgomery County','Pulaski County','Radford','Smyth County','Tazewell County'],
    6:['Bristol','Dickenson County','Lee County','Norton','Russell County','Scott County','Washington County','Wise County'],
    7:['Carroll County','Floyd County','Franklin County','Galax','Grayson County','Henry County','Martinsville','Patrick County','Wythe County'],
    8:['Bedford County','Campbell County'],
    9:['Charlotte County','Danville','Halifax County','Lunenburg County','Mecklenburg County','Pittsylvania County'],
    10:['Amelia County','Cumberland County','Fluvanna County','Goochland County','Louisa County','Nottoway County','Powhatan County'],
    11:['Albemarle County','Amherst County','Charlottesville','Nelson County'],
    12:['Chesterfield County','Colonial Heights'],
    13:['Charles City County','Dinwiddie County','Hopewell','Petersburg','Prince George County','Surry County','Sussex County'],
    14:['Henrico County','Richmond City'],
    15:['Chesterfield County','Richmond City'],
    16:['Henrico County'],
    17:['Brunswick County','Dinwiddie County','Emporia','Franklin City','Greensville County','Isle of Wight County','Southampton County','Suffolk'],
    18:['Chesapeake','Portsmouth'],
    19:['Chesapeake','Virginia Beach'],
    20:['Accomack County','Norfolk','Northampton County','Virginia Beach'],
    21:['Norfolk'],
    22:['Virginia Beach'],
    23:['Hampton','Newport News'],
    24:['James City County','Newport News','Poquoson','Williamsburg','York County'],
    25:['Caroline County','Essex County','King and Queen County','King George County','King William County','Lancaster County','Middlesex County','Northumberland County','Richmond County','Westmoreland County'],
    26:['Gloucester County','Hanover County','James City County','Mathews County','New Kent County'],
    27:['Fredericksburg','Spotsylvania County','Stafford County'],
    28:['Culpeper County','Fauquier County','Greene County','Madison County','Orange County','Rappahannock County'],
    29:['Prince William County','Stafford County'],
    30:['Manassas','Manassas Park','Prince William County'],
    31:['Fauquier County','Loudoun County'],
    32:['Loudoun County'],
    33:['Fairfax County','Prince William County'],
    34:['Fairfax County'],
    35:['Fairfax County'],
    36:['Fairfax County'],
    37:['Fairfax City','Fairfax County','Falls Church'],
    38:['Fairfax County'],
    39:['Alexandria','Fairfax County'],
    40:['Arlington County'],
}

HOUSE_LOCALITIES = {
    1:['Arlington County'],
    2:['Arlington County'],
    3:['Alexandria','Arlington County'],
    4:['Alexandria','Fairfax County'],
    5:['Alexandria'],
    6:['Fairfax County'],
    7:['Fairfax County'],
    8:['Fairfax County'],
    9:['Fairfax County'],
    10:['Fairfax County'],
    11:['Fairfax City','Fairfax County'],
    12:['Fairfax County'],
    13:['Fairfax County','Falls Church'],
    14:['Fairfax County'],
    15:['Fairfax County'],
    16:['Fairfax County'],
    17:['Fairfax County'],
    18:['Fairfax County'],
    19:['Fairfax County','Prince William County'],
    20:['Manassas','Manassas Park','Prince William County'],
    21:['Prince William County'],
    22:['Prince William County'],
    23:['Prince William County','Stafford County'],
    24:['Prince William County'],
    25:['Prince William County'],
    26:['Loudoun County'],
    27:['Loudoun County'],
    28:['Loudoun County'],
    29:['Loudoun County'],
    30:['Fauquier County','Loudoun County'],
    31:['Clarke County','Frederick County','Warren County'],
    32:['Frederick County','Winchester'],
    33:['Page County','Rockingham County','Shenandoah County','Warren County'],
    34:['Harrisonburg','Rockingham County'],
    35:['Augusta County','Rockingham County'],
    36:['Augusta County','Rockbridge County','Staunton','Waynesboro'],
    37:['Alleghany County','Botetourt County','Buena Vista','Covington','Craig County','Lexington','Rockbridge County'],
    38:['Roanoke City'],
    39:['Franklin County','Roanoke County'],
    40:['Roanoke City','Roanoke County','Salem'],
    41:['Montgomery County','Roanoke County'],
    42:['Giles County','Montgomery County','Pulaski County','Radford'],
    43:['Bland County','Buchanan County','Dickenson County','Tazewell County'],
    44:['Bristol','Russell County','Washington County'],
    45:['Dickenson County','Lee County','Norton','Scott County','Wise County'],
    46:['Grayson County','Pulaski County','Smyth County','Wythe County'],
    47:['Carroll County','Floyd County','Galax','Henry County','Patrick County'],
    48:['Henry County','Martinsville','Pittsylvania County'],
    49:['Danville','Halifax County'],
    50:['Charlotte County','Halifax County','Lunenburg County','Mecklenburg County','Prince Edward County'],
    51:['Bedford County','Campbell County','Pittsylvania County'],
    52:['Campbell County','Lynchburg'],
    53:['Amherst County','Nelson County'],
    54:['Albemarle County','Charlottesville'],
    55:['Albemarle County','Fluvanna County','Louisa County','Nelson County'],
    56:['Cumberland County','Fluvanna County','Louisa County','Prince Edward County'],
    57:['Goochland County','Henrico County'],
    58:['Henrico County'],
    59:['Hanover County','Henrico County','Louisa County'],
    60:['Hanover County','New Kent County'],
    61:['Culpeper County','Fauquier County','Rappahannock County'],
    62:['Culpeper County','Greene County','Madison County','Orange County'],
    63:['Orange County','Spotsylvania County'],
    64:['Stafford County'],
    65:['Fredericksburg','Stafford County'],
    66:['Caroline County','Spotsylvania County'],
    67:['Caroline County','King George County','King William County','Lancaster County','Northumberland County','Richmond County','Westmoreland County'],
    68:['Essex County','King and Queen County','King William County','Lancaster County','Mathews County','Middlesex County'],
    69:['James City County','Newport News','York County'],
    70:['Newport News'],
    71:['James City County','New Kent County','Williamsburg'],
    72:['Amelia County','Chesterfield County','Nottoway County','Powhatan County'],
    73:['Chesterfield County'],
    74:['Chesterfield County','Colonial Heights'],
    75:['Chesterfield County','Hopewell','Prince George County'],
    76:['Chesterfield County'],
    77:['Chesterfield County','Richmond City'],
    78:['Richmond City'],
    79:['Richmond City'],
    80:['Henrico County'],
    81:['Charles City County','Chesterfield County','Henrico County','Richmond City'],
    82:['Dinwiddie County','Petersburg','Prince George County','Surry County'],
    83:['Brunswick County','Emporia','Greensville County','Southampton County','Sussex County'],
    84:['Chesapeake','Franklin City','Isle of Wight County'],
    85:['Newport News'],
    86:['Hampton','Poquoson','York County'],
    87:['Hampton'],
    88:['Portsmouth'],
    89:['Chesapeake','Suffolk'],
    90:['Chesapeake'],
    91:['Chesapeake','Portsmouth'],
    92:['Chesapeake','Norfolk'],
    93:['Norfolk'],
    94:['Norfolk'],
    95:['Norfolk','Virginia Beach'],
    96:['Virginia Beach'],
    97:['Virginia Beach'],
    98:['Virginia Beach'],
    99:['Virginia Beach'],
    100:['Accomack County','Northampton County','Virginia Beach'],
}

def openstates_get(path, params):
    url = 'https://v3.openstates.org/' + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'X-API-KEY': OPENSTATES_KEY,
        'User-Agent': 'SERV-UVA-Sync/1.0'
    })
    # 3 retries with increasing timeout
    for attempt in range(3):
        try:
            timeout = 60 * (attempt + 1)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
                return data
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            print(f"  HTTP {e.code}: {body[:300]}")
            raise
        except Exception as e:
            print(f"  Attempt {attempt+1} timed out: {e}")
            if attempt < 2:
                time.sleep(10)
    print("  All retries failed")
    sys.exit(1)

def initials(name):
    parts = [p for p in name.split() if p.lower() not in ('jr.','jr','sr.','sr','iii','ii','iv')]
    return (parts[-2][0]+parts[-1][0]).upper() if len(parts)>=2 else name[:2].upper()

def build_email(name, chamber):
    parts = name.split()
    last = parts[-1].lower()
    for sfx in ['jr.','jr','sr.','sr','iii','ii','iv']:
        if last==sfx and len(parts)>1: last=parts[-2].lower(); break
    last = last.replace('.','').replace("'",'').replace('-','').replace(',','')
    if chamber=='senate': return f'senator{last}@senate.virginia.gov'
    return f'Del{parts[0][0].upper()}{last.capitalize()}@house.virginia.gov'

def supabase(method, path, data=None):
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    body = json.dumps(data).encode('utf-8') if data is not None else None
    req = urllib.request.Request(url, data=body, headers={
        'apikey': SUPABASE_SVC,
        'Authorization': f'Bearer {SUPABASE_SVC}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    print('\n1. Fetching Virginia legislators from Open States...')
    people = []
    page = 1
    while True:
        print(f'   Page {page}...')
        resp = openstates_get('people', {
            'jurisdiction': 'va',
            'per_page': 50,
            'page': page
        })
        results = resp.get('results', [])
        people.extend(results)
        print(f'   Got {len(results)} (total: {len(people)})')
        pagination = resp.get('pagination', {})
        if page >= pagination.get('max_page', 1):
            break
        page += 1
        time.sleep(1)  # be polite to API

    if not people:
        print('ERROR: No legislators returned')
        sys.exit(1)

    # Print sample to verify field structure
    sample = people[0]
    print(f'   Sample fields: {list(sample.keys())}')
    print(f'   Sample current_role: {sample.get("current_role")}')

    print('\n2. Building locality map...')
    legislators = {}
    unmapped = []

    for person in people:
        name = person.get('name','').strip()
        if not name: continue

        role = person.get('current_role') or {}
        if isinstance(role, list): role = role[0] if role else {}

        chamber_class = role.get('org_classification','')
        district_raw  = str(role.get('district', role.get('district_name','')))

        if not chamber_class:
            continue

        if chamber_class == 'upper':
            chamber = 'senate'
            loc_map = SENATE_LOCALITIES
        elif chamber_class == 'lower':
            chamber = 'house'
            loc_map = HOUSE_LOCALITIES
        else:
            continue

        # Parse district number
        dist_num = None
        for part in district_raw.replace('-',' ').split():
            try: dist_num = int(part); break
            except ValueError: continue

        if dist_num is None:
            unmapped.append(f'{name} (district: {district_raw!r})')
            continue

        localities = loc_map.get(dist_num, [])
        if not localities:
            unmapped.append(f"{'SD' if chamber=='senate' else 'HD'} {dist_num} ({name})")
            continue

        role_label = f"{'SD' if chamber=='senate' else 'HD'} {dist_num}"
        entry = {'name':name,'role':role_label,'email':build_email(name,chamber),'initials':initials(name)}

        for loc in localities:
            if loc not in legislators:
                legislators[loc] = {'senate':[],'house':[]}
            if role_label not in [l['role'] for l in legislators[loc][chamber]]:
                legislators[loc][chamber].append(entry)

    print(f'   Mapped: {len(legislators)} localities')
    if unmapped:
        print(f'   Unmapped: {", ".join(unmapped[:10])}')

    print('\n3. Syncing to Supabase...')
    existing = supabase('GET','legislators?select=id&limit=1')
    if existing:
        row_id = existing[0]['id']
        supabase('PATCH', f'legislators?id=eq.{row_id}', [{'data': legislators}])
        print(f'   Updated row {row_id}')
    else:
        supabase('POST','legislators',[{'data':legislators}])
        print('   Inserted new row')

    total = sum(len(d['senate'])+len(d['house']) for d in legislators.values())
    print(f'\nDone! {len(legislators)} localities, {total} legislator entries.')

if __name__ == '__main__':
    main()
