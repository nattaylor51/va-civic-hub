"""
LegiScan -> Supabase legislator sync for SERV at UVA
Pulls Virginia legislators from LegiScan and upserts into Supabase.
Runs via GitHub Actions weekly.
"""

import os, json, urllib.request, urllib.parse, sys

LEGISCAN_KEY = os.environ.get('LEGISCAN_KEY', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '').strip()

# Validate secrets are present
if not LEGISCAN_KEY:
    print("ERROR: LEGISCAN_KEY secret is missing or empty")
    sys.exit(1)
if not SUPABASE_URL:
    print("ERROR: SUPABASE_URL secret is missing or empty")
    sys.exit(1)
if not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_SERVICE_KEY secret is missing or empty")
    sys.exit(1)

print(f"LegiScan key present: {LEGISCAN_KEY[:6]}...")
print(f"Supabase URL: {SUPABASE_URL}")

# ── LOCALITY MAP ──
SENATE_DISTRICT_TO_LOCALITIES = {
    1:  ['Clarke County','Frederick County','Shenandoah County','Warren County','Winchester'],
    2:  ['Augusta County','Bath County','Highland County','Page County','Harrisonburg','Rockingham County'],
    3:  ['Alleghany County','Botetourt County','Buena Vista','Covington','Craig County','Lexington','Roanoke County','Rockbridge County'],
    4:  ['Roanoke City','Salem'],
    5:  ['Bland County','Buchanan County','Giles County','Montgomery County','Pulaski County','Radford','Smyth County','Tazewell County'],
    6:  ['Bristol','Dickenson County','Lee County','Norton','Russell County','Scott County','Washington County','Wise County'],
    7:  ['Carroll County','Floyd County','Franklin County','Galax','Grayson County','Henry County','Martinsville','Patrick County','Wythe County'],
    8:  ['Bedford County','Campbell County'],
    9:  ['Charlotte County','Danville','Halifax County','Lunenburg County','Mecklenburg County','Pittsylvania County'],
    10: ['Amelia County','Cumberland County','Fluvanna County','Goochland County','Louisa County','Nottoway County','Powhatan County'],
    11: ['Albemarle County','Amherst County','Charlottesville','Nelson County'],
    12: ['Chesterfield County','Colonial Heights'],
    13: ['Charles City County','Dinwiddie County','Hopewell','Petersburg','Prince George County','Surry County','Sussex County'],
    14: ['Henrico County','Richmond City'],
    15: ['Chesterfield County','Richmond City'],
    16: ['Henrico County'],
    17: ['Brunswick County','Dinwiddie County','Emporia','Franklin City','Greensville County','Isle of Wight County','Southampton County','Suffolk'],
    18: ['Chesapeake','Portsmouth'],
    19: ['Chesapeake','Virginia Beach'],
    20: ['Accomack County','Norfolk','Northampton County','Virginia Beach'],
    21: ['Norfolk'],
    22: ['Virginia Beach'],
    23: ['Hampton','Newport News'],
    24: ['James City County','Newport News','Poquoson','Williamsburg','York County'],
    25: ['Caroline County','Essex County','King and Queen County','King George County','King William County','Lancaster County','Middlesex County','Northumberland County','Richmond County','Westmoreland County'],
    26: ['Gloucester County','Hanover County','James City County','Mathews County','New Kent County'],
    27: ['Fredericksburg','Spotsylvania County','Stafford County'],
    28: ['Culpeper County','Fauquier County','Greene County','Madison County','Orange County','Rappahannock County'],
    29: ['Prince William County','Stafford County'],
    30: ['Manassas','Manassas Park','Prince William County'],
    31: ['Fauquier County','Loudoun County'],
    32: ['Loudoun County'],
    33: ['Fairfax County','Prince William County'],
    34: ['Fairfax County'],
    35: ['Fairfax County'],
    36: ['Fairfax County'],
    37: ['Fairfax City','Fairfax County','Falls Church'],
    38: ['Fairfax County'],
    39: ['Alexandria','Fairfax County'],
    40: ['Arlington County'],
}

HOUSE_DISTRICT_TO_LOCALITIES = {
    1:  ['Arlington County'],
    2:  ['Arlington County'],
    3:  ['Alexandria','Arlington County'],
    4:  ['Alexandria','Fairfax County'],
    5:  ['Alexandria'],
    6:  ['Fairfax County'],
    7:  ['Fairfax County'],
    8:  ['Fairfax County'],
    9:  ['Fairfax County'],
    10: ['Fairfax County'],
    11: ['Fairfax City','Fairfax County'],
    12: ['Fairfax County'],
    13: ['Fairfax County','Falls Church'],
    14: ['Fairfax County'],
    15: ['Fairfax County'],
    16: ['Fairfax County'],
    17: ['Fairfax County'],
    18: ['Fairfax County'],
    19: ['Fairfax County','Prince William County'],
    20: ['Manassas','Manassas Park','Prince William County'],
    21: ['Prince William County'],
    22: ['Prince William County'],
    23: ['Prince William County','Stafford County'],
    24: ['Prince William County'],
    25: ['Prince William County'],
    26: ['Loudoun County'],
    27: ['Loudoun County'],
    28: ['Loudoun County'],
    29: ['Loudoun County'],
    30: ['Fauquier County','Loudoun County'],
    31: ['Clarke County','Frederick County','Warren County'],
    32: ['Frederick County','Winchester'],
    33: ['Page County','Rockingham County','Shenandoah County','Warren County'],
    34: ['Harrisonburg','Rockingham County'],
    35: ['Augusta County','Rockingham County'],
    36: ['Augusta County','Rockbridge County','Staunton','Waynesboro'],
    37: ['Alleghany County','Botetourt County','Buena Vista','Covington','Craig County','Lexington','Rockbridge County'],
    38: ['Roanoke City'],
    39: ['Franklin County','Roanoke County'],
    40: ['Roanoke City','Roanoke County','Salem'],
    41: ['Montgomery County','Roanoke County'],
    42: ['Giles County','Montgomery County','Pulaski County','Radford'],
    43: ['Bland County','Buchanan County','Dickenson County','Tazewell County'],
    44: ['Bristol','Russell County','Washington County'],
    45: ['Dickenson County','Lee County','Norton','Scott County','Wise County'],
    46: ['Grayson County','Pulaski County','Smyth County','Wythe County'],
    47: ['Carroll County','Floyd County','Galax','Henry County','Patrick County'],
    48: ['Henry County','Martinsville','Pittsylvania County'],
    49: ['Danville','Halifax County'],
    50: ['Charlotte County','Halifax County','Lunenburg County','Mecklenburg County','Prince Edward County'],
    51: ['Bedford County','Campbell County','Pittsylvania County'],
    52: ['Campbell County','Lynchburg'],
    53: ['Amherst County','Nelson County'],
    54: ['Albemarle County','Charlottesville'],
    55: ['Albemarle County','Fluvanna County','Louisa County','Nelson County'],
    56: ['Cumberland County','Fluvanna County','Louisa County','Prince Edward County'],
    57: ['Goochland County','Henrico County'],
    58: ['Henrico County'],
    59: ['Hanover County','Henrico County','Louisa County'],
    60: ['Hanover County','New Kent County'],
    61: ['Culpeper County','Fauquier County','Rappahannock County'],
    62: ['Culpeper County','Greene County','Madison County','Orange County'],
    63: ['Orange County','Spotsylvania County'],
    64: ['Stafford County'],
    65: ['Fredericksburg','Stafford County'],
    66: ['Caroline County','Spotsylvania County'],
    67: ['Caroline County','King George County','King William County','Lancaster County','Northumberland County','Richmond County','Westmoreland County'],
    68: ['Essex County','King and Queen County','King William County','Lancaster County','Mathews County','Middlesex County'],
    69: ['James City County','Newport News','York County'],
    70: ['Newport News'],
    71: ['James City County','New Kent County','Williamsburg'],
    72: ['Amelia County','Chesterfield County','Nottoway County','Powhatan County'],
    73: ['Chesterfield County'],
    74: ['Chesterfield County','Colonial Heights'],
    75: ['Chesterfield County','Hopewell','Prince George County'],
    76: ['Chesterfield County'],
    77: ['Chesterfield County','Richmond City'],
    78: ['Richmond City'],
    79: ['Richmond City'],
    80: ['Henrico County'],
    81: ['Charles City County','Chesterfield County','Henrico County','Richmond City'],
    82: ['Dinwiddie County','Petersburg','Prince George County','Surry County'],
    83: ['Brunswick County','Emporia','Greensville County','Southampton County','Sussex County'],
    84: ['Chesapeake','Franklin City','Isle of Wight County'],
    85: ['Newport News'],
    86: ['Hampton','Poquoson','York County'],
    87: ['Hampton'],
    88: ['Portsmouth'],
    89: ['Chesapeake','Suffolk'],
    90: ['Chesapeake'],
    91: ['Chesapeake','Portsmouth'],
    92: ['Chesapeake','Norfolk'],
    93: ['Norfolk'],
    94: ['Norfolk'],
    95: ['Norfolk','Virginia Beach'],
    96: ['Virginia Beach'],
    97: ['Virginia Beach'],
    98: ['Virginia Beach'],
    99: ['Virginia Beach'],
    100: ['Accomack County','Northampton County','Virginia Beach'],
}

def legiscan_get(op, **params):
    """Call LegiScan API and return parsed JSON."""
    args = {'key': LEGISCAN_KEY, 'op': op}
    args.update(params)
    url = 'https://api.legiscan.com/?' + urllib.parse.urlencode(args)
    print(f"  Calling: {op} {params}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SERV-UVA-Sync/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            if data.get('status') == 'ERROR':
                print(f"  LegiScan error: {data.get('alert', {}).get('message', 'Unknown error')}")
                sys.exit(1)
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  HTTP {e.code} error: {body[:300]}")
        raise

def initials(name):
    parts = [p for p in name.split() if p not in ('Jr.','Jr','Sr.','Sr','III','II','IV')]
    if len(parts) >= 2:
        return (parts[-2][0] + parts[-1][0]).upper()
    return name[:2].upper()

def clean_last(name):
    """Extract cleaned last name for email building."""
    parts = name.split()
    last = parts[-1].lower()
    for suffix in ['jr.','jr','sr.','sr','iii','ii','iv']:
        if last == suffix and len(parts) > 1:
            last = parts[-2].lower()
            break
    return last.replace('.','').replace("'",'').replace('-','').replace(',','')

def build_email(name, chamber):
    last = clean_last(name)
    if chamber == 'senate':
        return f'senator{last}@senate.virginia.gov'
    else:
        first_initial = name.split()[0][0].upper()
        return f'Del{first_initial}{last.capitalize()}@house.virginia.gov'

def supabase_request(method, path, data=None):
    """Make an authenticated Supabase request."""
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    body = json.dumps(data).encode('utf-8') if data is not None else None
    headers = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  Supabase {method} {path} failed: HTTP {e.code}: {body[:300]}")
        raise

def main():
    # ── Step 1: Get current VA session ──
    print("\n1. Fetching Virginia session list...")
    sessions_data = legiscan_get('getSessionList', state='VA')
    sessions = sessions_data.get('sessions', [])
    if not sessions:
        print("ERROR: No sessions returned from LegiScan")
        sys.exit(1)

    # Pick most recent session by year_end
    current = sorted(sessions, key=lambda s: (s.get('year_end', 0), s.get('session_id', 0)), reverse=True)[0]
    session_id = current['session_id']
    print(f"   Using: {current['session_name']} (ID: {session_id})")

    # ── Step 2: Get legislators ──
    print("\n2. Fetching legislators...")
    people_data = legiscan_get('getSessionPeople', id=session_id)

    # Handle both possible response structures
    session_people = people_data.get('sessionpeople', {})
    people = session_people.get('people', [])

    if not people:
        print("ERROR: No people returned. Response keys:", list(people_data.keys()))
        sys.exit(1)

    print(f"   Found {len(people)} legislators")

    # ── Step 3: Build locality map ──
    print("\n3. Building locality map...")
    legislators = {}
    unmapped = []

    for person in people:
        name = person.get('name', '').strip()
        role = person.get('role', '').strip()
        district_str = str(person.get('district', '')).strip()

        if not name or not district_str:
            continue

        # Parse district number from formats like "SD-001", "HD-001", "001", "1"
        dist_num = None
        for part in district_str.replace('-', ' ').split():
            try:
                dist_num = int(part)
                break
            except ValueError:
                continue
        if dist_num is None:
            continue

        # Determine chamber from role or district prefix
        role_upper = role.upper()
        dist_upper = district_str.upper()
        if 'SEN' in role_upper or dist_upper.startswith('SD') or dist_upper.startswith('S'):
            chamber = 'senate'
            role_label = f'SD {dist_num}'
            locality_map = SENATE_DISTRICT_TO_LOCALITIES
        elif 'REP' in role_upper or 'DEL' in role_upper or dist_upper.startswith('HD') or dist_upper.startswith('H'):
            chamber = 'house'
            role_label = f'HD {dist_num}'
            locality_map = HOUSE_DISTRICT_TO_LOCALITIES
        else:
            # Guess by district number range
            if dist_num <= 40:
                chamber = 'senate'
                role_label = f'SD {dist_num}'
                locality_map = SENATE_DISTRICT_TO_LOCALITIES
            else:
                chamber = 'house'
                role_label = f'HD {dist_num}'
                locality_map = HOUSE_DISTRICT_TO_LOCALITIES

        localities = locality_map.get(dist_num, [])
        if not localities:
            unmapped.append(f"{role_label} ({name})")
            continue

        email = build_email(name, chamber)
        leg_entry = {
            'name': name,
            'role': role_label,
            'email': email,
            'initials': initials(name)
        }

        for loc in localities:
            if loc not in legislators:
                legislators[loc] = {'senate': [], 'house': []}
            existing_roles = [l['role'] for l in legislators[loc][chamber]]
            if role_label not in existing_roles:
                legislators[loc][chamber].append(leg_entry)

    print(f"   Mapped to {len(legislators)} localities")
    if unmapped:
        print(f"   Unmapped districts ({len(unmapped)}): {', '.join(unmapped[:10])}")

    # ── Step 4: Sync to Supabase ──
    print("\n4. Syncing to Supabase...")
    existing = supabase_request('GET', 'legislators?select=id&limit=1')

    if existing:
        row_id = existing[0]['id']
        supabase_request('PATCH', f'legislators?id=eq.{row_id}', [{'data': legislators}])
        print(f"   Updated existing row (ID: {row_id})")
    else:
        supabase_request('POST', 'legislators', [{'data': legislators}])
        print("   Inserted new row")

    print(f"\n✓ Sync complete! {len(legislators)} localities, {len(people)} legislators.")

if __name__ == '__main__':
    main()
