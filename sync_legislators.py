"""
LegiScan → Supabase legislator sync for SERV at UVA
Pulls Virginia legislators from LegiScan and upserts into Supabase.
Runs via GitHub Actions weekly (see .github/workflows/sync_legislators.yml)
"""

import os, json, urllib.request, urllib.parse

LEGISCAN_KEY = os.environ['LEGISCAN_KEY']
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_SERVICE_KEY = os.environ['SUPABASE_SERVICE_KEY']

# ── LOCALITY MAP ──
# Maps LegiScan district numbers to Virginia localities.
# Senate districts are stable; House districts updated for 2023 redistricting.
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
    base = f'https://api.legiscan.com/?key={LEGISCAN_KEY}&op={op}'
    for k, v in params.items():
        base += f'&{k}={urllib.parse.quote(str(v))}'
    with urllib.request.urlopen(base, timeout=30) as r:
        return json.loads(r.read())

def initials(name):
    parts = name.split()
    if len(parts) >= 2:
        return (parts[-2][0] + parts[-1][0]).upper()
    return name[:2].upper()

def build_email(name, chamber):
    """Build email from name using verified formats."""
    last = name.split()[-1].lower()
    # Remove suffixes
    for suffix in ['jr.', 'jr', 'sr.', 'sr', 'iii', 'ii', 'iv']:
        if last == suffix:
            last = name.split()[-2].lower()
            break
    # Remove punctuation
    last = last.replace('.', '').replace("'", '').replace('-', '')
    if chamber == 'senate':
        return f'senator{last}@senate.virginia.gov'
    else:
        # House format: Del[FirstInitial][LastName]
        first_initial = name.split()[0][0].upper()
        last_cap = last.capitalize()
        return f'Del{first_initial}{last_cap}@house.virginia.gov'

def main():
    print("Fetching Virginia session list...")
    sessions_data = legiscan_get('getSessionList', state='VA')
    sessions = sessions_data.get('sessions', [])

    # Find most recent session
    current = sorted(sessions, key=lambda s: s.get('year_end', 0), reverse=True)[0]
    session_id = current['session_id']
    print(f"Using session: {current['session_name']} (ID: {session_id})")

    print("Fetching legislators...")
    people_data = legiscan_get('getSessionPeople', id=session_id)
    people = people_data.get('sessionpeople', {}).get('people', [])
    print(f"Found {len(people)} legislators")

    # Build locality map
    legislators = {}

    for person in people:
        name = person.get('name', '').strip()
        role = person.get('role', '').strip()   # e.g. "Sen" or "Rep"
        district_str = person.get('district', '').strip()  # e.g. "SD-001" or "HD-001"

        if not name or not district_str:
            continue

        # Parse district number
        try:
            dist_num = int(district_str.split('-')[-1])
        except ValueError:
            continue

        # Determine chamber
        if role in ('Sen', 'Senator') or district_str.startswith('SD'):
            chamber = 'senate'
            role_label = f'SD {dist_num}'
            locality_map = SENATE_DISTRICT_TO_LOCALITIES
        elif role in ('Rep', 'Delegate', 'Del') or district_str.startswith('HD'):
            chamber = 'house'
            role_label = f'HD {dist_num}'
            locality_map = HOUSE_DISTRICT_TO_LOCALITIES
        else:
            continue

        localities = locality_map.get(dist_num, [])
        if not localities:
            print(f"  WARNING: No localities mapped for {role_label} ({name})")
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
            # Avoid duplicates
            existing_roles = [l['role'] for l in legislators[loc][chamber]]
            if role_label not in existing_roles:
                legislators[loc][chamber].append(leg_entry)

    print(f"Mapped legislators to {len(legislators)} localities")

    # Push to Supabase
    print("Syncing to Supabase...")

    # Check if row exists
    req = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/legislators?select=id&limit=1',
        headers={
            'apikey': SUPABASE_SERVICE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        }
    )
    with urllib.request.urlopen(req) as r:
        existing = json.loads(r.read())

    payload = json.dumps([{'data': legislators}]).encode('utf-8')

    if existing:
        # Update existing row
        row_id = existing[0]['id']
        update_req = urllib.request.Request(
            f'{SUPABASE_URL}/rest/v1/legislators?id=eq.{row_id}',
            data=payload,
            headers={
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            },
            method='PATCH'
        )
        with urllib.request.urlopen(update_req) as r:
            print(f"Updated existing legislator row (ID: {row_id})")
    else:
        # Insert new row
        insert_req = urllib.request.Request(
            f'{SUPABASE_URL}/rest/v1/legislators',
            data=payload,
            headers={
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            },
            method='POST'
        )
        with urllib.request.urlopen(insert_req) as r:
            print("Inserted new legislator row")

    print(f"\nSync complete! {len(legislators)} localities updated.")

if __name__ == '__main__':
    main()
