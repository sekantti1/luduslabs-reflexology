import luadata
import pandas as pd
from time import time

translation = {'Protección': 'Protection',
               'Guardián': 'Guardian',
               'Caos': 'Havoc',
               'Treffsicherheit': 'Marksmanship',
               'Gardien': 'Guardian',
               'Sangre': 'Blood',
               'Elementar': 'Elemental',
               'Feuer': 'Fire',
               'Disziplin': 'Discipline',
               'Wiederherstellung': 'Restoration',
               'Waffen': 'Arms',
               'Rachsucht': 'Vengeance',
               'Schatten': 'Shadow',
               'Gleichgewicht': 'Balance',
               'Täuschung': 'Subtlety',
               'Braumeister': 'Brewmaster',
               'Verwüstung': 'Havoc',
               'Wildheit': 'Feral',
               'Nebelwirker': 'Mistweaver',
               'Unheilig': 'Unholy',
               'Heilig': 'Holy',
               'Vergeltung': 'Retribution',
               'Windläufer': 'Windwalker',
               'Gebrechen': 'Affliction',
               'Furor': 'Fury',
               'Schutz': 'Protection',
               'Blut': 'Blood',
               'Zerstörung': 'Destruction',
               'Meucheln': 'Assassination',
               'Tierherrschaft': 'Beast Mastery',
               'Überleben': 'Survival',
               'Arkan': 'Arcane',
               'Wächter': 'Guardian',
               'Maître brasseur': 'Brewmaster',
               'Forajido': 'Outlaw',
               'Forajida': 'Outlaw',
               'Verstärkung': 'Enhancement',
               'Gesetzlosigkeit': 'Outlaw',
               'Arcanes': 'Arcane',
               'Dämonologie': 'Demonology',
               'Guardiana': 'Guardian',
               'Guardiano': 'Guardian',
               'Venganza': 'Vengeance',
               'Bestias': 'Beast Mastery',
               'Maestro cervecero': 'Brewmaster',
               'Maestra cervecera': 'Brewmaster',
               'Sagrada': 'Holy',
               'Sagrado': 'Holy',
               'Reprensión': 'Retribution',
               'Disciplina': 'Discipline',
               'Sutileza': 'Subtlety',
               'Assassinat': 'Assassination',
               'Finesse': 'Subtlety',
               'Sacré': 'Holy',
               'Restauration': 'Restoration',
               'Feu': 'Fire',
               'Restauración': 'Restoration',
               'Armas': 'Arms',
               'Vindicte': 'Retribution',
               'Farouche': 'Feral',
               'Survie': 'Survival',
               'Givre': 'Frost',
               'Ombre': 'Shadow',
               'Viajero del viento': 'Windwalker',
               'Viajera del viento': 'Windwalker',
               'Escarcha': 'Frost',
               'Equilibrio': 'Balance',
               'Supervivencia': 'Survival',
               'Aflicción': 'Affliction',
               'Profano': 'Unholy',
               'Profana': 'Unholy',
               'Tejedor de niebla': 'Mistweaver',
               'Tejedora de niebla': 'Mistweaver',
               'Puntería': 'Marksmanship',
               'Punterío': 'Marksmanship',
               'Fuega': 'Fire',
               'Fuego': 'Fire',
               'Arcano': 'Arcane',
               'Arcana': 'Arcane',
               'Destrucción': 'Destruction',
               'Marche-vent': 'Windwalker',
               'Devastación': 'Havoc',
               'Tisse-brume': 'Mistweaver',
               'Armes': 'Arms',
               'Amélioration': 'Enhancement',
               'Équilibre': 'Balance',
               'Fureur': 'Fury',
               'Mejora': 'Enhancement',
               'Sombra': 'Shadow',
               'Précision': 'Marksmanship',
               'Élémentaire': 'Elemental',
               'Maîtrise des bêtes': 'Beast Mastery',
               'Dévastation': 'Havoc',
               'Démonologie': 'Demonology',
               'Impie': 'Unholy',
               'Hors-la-loi': 'Outlaw',
               "Стихии": "Elemental",
               "Совершенствование": "Enhancement",
               "Исцеление": "Restoration",
               "Оружие": "Arms",
               "Неистовство": "Fury",
               "Защита": "Protection",
               "Колдовство": "Affliction",
               "Демонология": "Demonology",
               "Разрушение": "Destruction",
               "Послушание": "Discipline",
               "Свет": "Holy",
               "Тьма": "Shadow",
               "Повелитель зверей": "Beast Mastery",
               "Стрельба": "Marksmanship",
               "Стрел": "Marksmanship",
               "Выживание": "Survival",
               "Ликвидация": "Assassination",
               "Головорез": "Outlaw",
               "Скрытность": "Subtlety",
               "Тайная магия": "Arcane",
               "Огонь": "Fire",
               "Лед": "Frost",
               "Хмелевар": "Brewmaster",
               "Ткач туманов": "Mistweaver",
               "Танцующий с ветром": "Windwalker",
               "Воздаяние": "Retribution",
               "Кровь": "Blood",
               "Нечестивость": "Unholy",
               "Баланс": "Balance",
               "Сила зверя": "Feral",
               "Страж": "Guardian",
               "Истребление": "Havoc",
               "Месть": "Vengeance",
               "Повелительница зверей": "Beast Mastery",
               "Танцующая с ветром": "Windwalker"
}

# Old format stepped every 3rd element; new format (17 elements) uses direct positions
# New format positions: Name=0, Team=5, Race=6, Class=7, Damage=9, Healing=10,
#                       Rating=11, RatingChange=12, Spec=15
cols_new = {
    'Name': 0, 'Team': 5, 'Race': 6, 'Class': 7,
    'Damage': 9, 'Healing': 10, 'Rating': 11, 'Rating change': 12, 'Spec': 15
}

# Old format (stepped every 3): kept for backwards compatibility
cols = ['Name', '', '', '', '', 'Team', 'Race', '', 'Class', 'Damage',
        'Healing', 'Rating', 'Rating change', '', '', 'Spec', '']


def timeit(func):
    def inner(*args, **kwargs):
        tic = time()
        x = func(*args, **kwargs)
        toc = time()
        print('%s took %.2f s'%(func.__name__, toc-tic))
        return x

    return inner


def translate(data):
    specCols = [k for k in data.columns if '_Spec' in k]
    for col in specCols:
        data.loc[:, col] = data.loc[:, col].replace(translation)

    return data

def fix_class(data):
    classCols = [k for k in data.columns if '_Class' in k]
    for col in classCols:
        data.loc[:, col] = data.loc[:, col].replace({'Demonhunter': 'Demon Hunter',
                                                    'Deathknight': 'Death Knight'})

    return data

def parse_player(player):
    # New addon format: 17 elements with direct positions
    if len(player) >= 16 and isinstance(player[5], int) and player[5] in (0, 1):
        return [(col, player[idx]) for col, idx in cols_new.items()]
    # Old addon format: every 3rd element
    return [(cols[i], player[k]) for i, k in enumerate(range(0, len(player), 3))]

@timeit
def get_arena(data, bracket, rated=True, soloshuffle=False):

    filteredData = [x for x in data if type(x) == dict]
    playersNum = {'2v2': 4, '3v3': 6}[bracket.lower()]
    z = []
    for x in filteredData:
        if 'isSoloShuffle' in x:
            is_solo_shuffle = x['isSoloShuffle']
        else:
            is_solo_shuffle = False


        if x['PlayersNum'] == playersNum\
            and x['isArena'] and x['isRated'] == rated and not x['isBrawl']\
            and is_solo_shuffle == soloshuffle:

            z.append(x)


    return z


def get_rbg(data, rated=True):
    filteredData = [x for x in data if type(x) == dict]
    playersNum = 20
    return [x for x in filteredData if x['PlayersNum'] == playersNum
            and not x['isArena'] and x['isRated'] == rated]


def parse_match_data(match):
    players = [dict(parse_player(k)) for k in match['Players'] if len(k) > 10]

    team1 = [k for k in players if k['Team'] == 0]
    team2 = [k for k in players if k['Team'] == 1]

    def parse_team(team):
        return {'T%iP%i_%s'%(player['Team'], k, col) : player[col] \
                for k, player in enumerate(team)\
                for col in player}

    matchData = {k: match[k] for k in ['Map', 'Season', 'Duration',
                                       'Version', 'Time', 'PlayerSide',
                                       'Winner']}

    
    # TeamData format changed between addon versions:
    # Old format: 4 entries, MMR at index [9]
    # New format: 2 entries (one per team), MMR at index [3]
    teamData = match.get('TeamData', [])
    if len(teamData) >= 4 and len(teamData[0]) > 9:
        # old format
        mmrData = {'T0_MMR': teamData[0][9], 'T1_MMR': teamData[3][9]}
    elif len(teamData) >= 2 and len(teamData[0]) > 3:
        # new format
        mmrData = {'T0_MMR': teamData[0][3], 'T1_MMR': teamData[1][3]}
    else:
        mmrData = {'T0_MMR': 0, 'T1_MMR': 0}

    data = dict(**matchData, **mmrData,
                **parse_team(team1),
                **parse_team(team2))

    return data


def capitalise_class(df):
    classCols = [k for k in df.columns if '_Class' in k]
    for c in classCols:
        df.loc[:, c] = df[c].str.title()

    return df


def _load_lua_data(file_name):
    """Load REFlexDatabase from a lua file or serialized string.
    Handles both single-variable and multi-variable lua files."""
    import re

    def extract_var(text, varname):
        m = re.search(r'\n?' + varname + r'\s*=\s*', text)
        if not m:
            return None
        start = m.end()
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return varname + ' = ' + text[start:i+1]
            i += 1
        return None

    if len(file_name) < 100:
        # It's a file path
        with open(file_name, encoding='utf-8') as f:
            text = f.read()
    else:
        # It's the file contents passed as a string
        text = file_name

    # Try extracting just REFlexDatabase (handles multi-variable files)
    chunk = extract_var(text, 'REFlexDatabase')
    if chunk:
        db = luadata.unserialize(chunk)
        # luadata returns {'REFlexDatabase': [...]} when given a named variable
        if isinstance(db, dict) and 'REFlexDatabase' in db:
            return db
        return {'REFlexDatabase': db}

    # Fallback: try parsing the whole thing
    return luadata.unserialize(text)


def parse_lua_file(file_name):
    data = _load_lua_data(file_name)

    raw2v2 = get_arena(data['REFlexDatabase'], '2v2')
    raw3v3 = get_arena(data['REFlexDatabase'], '3v3')
    rawSolo = get_arena(data['REFlexDatabase'], '3v3', soloshuffle=True)
    
    match2v2 = fix_class(translate(capitalise_class(pd.DataFrame([parse_match_data(k) for k in raw2v2]))))
    match3v3 = fix_class(translate(capitalise_class(pd.DataFrame([parse_match_data(k) for k in raw3v3]))))
    matchSs = fix_class(translate(capitalise_class(pd.DataFrame([parse_match_data(k) for k in rawSolo]))))

    return match2v2, match3v3, matchSs


def parse_lua_file_rbg(file_name):
    data = _load_lua_data(file_name)

    rawRbg = get_rbg(data['REFlexDatabase'])

    matchRbg = fix_class(translate(capitalise_class(pd.DataFrame([parse_match_data(k)
                                                                  for k in rawRbg]))))

    return matchRbg
