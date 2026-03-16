import dash
import os
import sys
import logging
import warnings


from furl import furl

import base64
import hashlib

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go

import pandas as pd
import numpy as np
import json
from time import time

from layout import (generate_layout, BGCOLOR, FONT_COLOR,
                    tableColumns)


OUTPUT_DIR = '/data/reflex/lua/raw'

baseDir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(baseDir)

from reflexology import rio, analysis

MATCHUP_URL = '/matchup/<bracket>'


HEALERS = ['Holy Paladin', 'Holy Priest', 'Discipline Priest',
           'Restoration Shaman', 'Restoration Druid', 'Mistweaver Monk']

SEASON_LABELS = {
    37: 'Dragonflight S4',
    36: 'Dragonflight S3',
    35: 'Dragonflight S2',
    34: 'Dragonflight S1',
    33: 'Shadowlands S4',    
    32: 'Shadowlands S3',
    31: 'Shadowlands S2',
    30: 'Shadowlands S1',
    29: 'BfA S4',
    28: 'BfA S3',
    27: 'BfA S2',
    26: 'BfA S1',
    25: 'Legion S7',
    24: 'Legion S6',
    23: 'Legion S5',
    22: 'Legion S4',
    21: 'Legion S3',
    20: 'Legion S2',
    19: 'Legion S1'
    }


if not os.path.isdir('/data'):
    warnings.warn(RuntimeWarning('You have not mounted a data directory. Any uploaded data will not be saved.'))

# Check if data directory structure exists, otherwise create it
if not os.path.isdir('/data/reflex'):
    os.mkdir('/data/reflex')

def get_season_label(k):
    if int(k) in SEASON_LABELS:
        return SEASON_LABELS[int(k)]
    else:
        return str(k)

def timeit(func):
    def inner(*args, **kwargs):
        tic = time()
        x = func(*args, **kwargs)
        toc = time()
        print('%s took %.2f s'%(func.__name__, toc-tic))
        return x

    return inner
    
    
def get_hash(df):
    return hashlib.sha256(str(df.values.ravel()).encode()).hexdigest()

logging.basicConfig(filename='reflex-app.log', level=logging.DEBUG)

dataFile = '../data/REFlex.lua'

# size given as (width, height)
SPEC_GRAPH_SIZE = (550, 500)
RATING_GRAPH_SIZE = (550, 450)
FONT_SIZE1 = 14

# For including a partner; need at least this many matches
MATCH_THRESHOLD = 5

app = dash.Dash('REFlex')

app.layout = generate_layout()

app.config['suppress_callback_exceptions'] = True

server = app.server


def filter_low_rating(data, name, theta=150, N=50):
    rating = analysis.get_player_rating(data, name)[1:]
    meanRating = np.mean(rating)
    idx = np.arange(len(rating))

    highIndex = (idx > 50) | (rating > (rating[N]-theta))
    # first
    firstIndex = data.index[np.where(highIndex)[0][0]:]
    return data.loc[firstIndex, :]

def get_spec(x):
    if 'Beast Mastery' in x:
        return 'Beast Mastery'
    else:
        return x.split(' ')[0]


def get_class(x):
    if 'Beast Mastery' in x:
        return 'Hunter'
    else:
        return ' '.join(x.split(' ')[1:])
    

@timeit
def filter_data(data, partners):
    if len(partners) > 0:
        playerTeams = analysis.get_player_teams(data)

        if len(partners) == 1:
            keepIndex = playerTeams.apply(lambda x: any([name in x for name in partners]))
        else:
            keepIndex = playerTeams.apply(lambda x: all([name in x for name in partners]))

        return data.loc[keepIndex, :]
    else:
        return data

@timeit
def make_spec_plot(data, col, player_name=None, group='spec'):

    winMatrix = timeit(analysis.build_win_matrix)(data, player_name=player_name,
                                          group=group)

    winMatrix['Class'] = winMatrix.index
    winMatrix = winMatrix.sort_values(by=col, ascending=True)

    if group == 'spec':
        cols = [analysis.classColors[get_class(k)]
                for k in winMatrix.index]
    else:
        cols = [analysis.classColors[k] for k in winMatrix.index]

    cols8bit = [tuple([k*255 for k in c]) for c in cols]
    plotlyCols = ['rgb(%i,%i,%i)'%col for col in cols8bit]

    xlabel = {'win rate': 'Win rate (%)',
              'avg rating change': 'Average rating change',
              'N': 'Number of games played',
              'total rating change': 'Total rating change'}[col]


    fig = go.Figure(
        data=[go.Bar(
        x=winMatrix[col],
        y=[k+'  ' for k in winMatrix['Class']],
        orientation='h',
        marker_color=plotlyCols
    )], layout={'margin': {'t': 0, 'r': 0},
                'paper_bgcolor': BGCOLOR,
                'plot_bgcolor': BGCOLOR,
                'font': {'color': FONT_COLOR, 'size': FONT_SIZE1},
                'xaxis_title': xlabel,
                'xaxis': {'fixedrange': True},
                'yaxis': {'fixedrange': True}
    })

    fig.update_yaxes(showgrid=False, dtick=1)
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.2)')
    
    return fig


@timeit
def make_rating_plot(data, name='', partner1=None,
                     partner2=None, keepIndex=None):

    SELF_COL = 'rgba(210, 40, 40, 0.9)'    
    partnerCol = 'rgb(210, 210, 210)'

    index = [0] + list(data.index)
    gamesPlayed = pd.Series(np.arange(0, data.shape[0]+1), index=index)

    # MMR trace
    teamMMR = analysis.get_team_mmr(data)

    # Main rating trace
    playerRating = pd.Series(analysis.get_player_rating(data, name),
                             index=index)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=gamesPlayed,
        y=teamMMR,
        name='Team MMR',
        line={'width': 1, 'color': 'rgba(150,150,255,0.5)'}

    ))

    fig.add_trace(go.Scatter(
        x=gamesPlayed,
        y=playerRating,
        name=name,
        line={'width': 3}
    ))

    first = True
    if partner1 is not None:
        teamName = '<br>'.join([partner1, partner2]) if partner2 is not None \
                   else partner1

        partnerData = analysis.filter_by_partner(data, partner1, partner2)
        G = partnerData.groupby('session')
    
        for g in G.groups:
            idx = G.groups[g]
            fig.add_trace(go.Scatter(
                x=gamesPlayed[idx],
                y=playerRating[idx],
                mode='lines',
                line={'width': 3, 'color': partnerCol},
                showlegend=first,
                name='Playing with:<br>'+teamName
            ))
            first = False

    if keepIndex is not None:
        x = gamesPlayed.iloc[1:][~keepIndex]
        y = playerRating.iloc[1:][~keepIndex]
        xd = np.diff(x)
        if any(xd > 1):
            d0 = np.where(xd>1)[0][0]
            x1 = x.iloc[:(d0+1)]
            y1 = y.iloc[:(d0+1)]
            x2 = x.iloc[(d0+1):]
            y2 = y.iloc[(d0+1):]
            xs = [x1, x2]
            ys = [y1, y2]
        else:
            xs = [x]
            ys = [y]

        for x, y in zip(xs, ys):
            fig.add_trace(go.Scatter(
                x=x,
                y=y,
                showlegend=False,
                line={'width': 3, 'color': 'rgba(80,80,80,1.0)'}

    ))


    fig.update_layout(xaxis_title='Games played',
                      yaxis_title='Rating',
                      legend=dict(yanchor='top',
                                  y=1.05,
                                  orientation='h',
                                  xanchor='left',
                                  x=0.1),
                      margin={'t': 0, 'r': 0},
                      paper_bgcolor=BGCOLOR,
                      plot_bgcolor=BGCOLOR,
                      dragmode='select',
                      font={'color': FONT_COLOR, 'size': FONT_SIZE1}
    )

    fig.update_xaxes(gridcolor='rgba(255,255,255,0.2)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.2)')

    return fig


def make_analysis_page(playerData, opponentData):
    pass


def make_comp_table(data, playerName):
    opponentSpecs = analysis.get_opponent_specs(data)

    outcomes = analysis.get_outcome(data)
    ratingChange = analysis.get_player_field(data, playerName, 'Rating change')

    sortedOpponentSpecs = '(' + opponentSpecs.apply(lambda x: ', '.join(sorted(x)),
                                                    axis=1) + ')'

    compOutcome = pd.DataFrame([sortedOpponentSpecs,
                                outcomes]).T

    compOutcome.columns = ['Comp', 'Win']
    compOutcome.loc[:, 'Rating change'] = ratingChange
    winCount = compOutcome.groupby('Comp')['Win'].sum()
    fightCount = compOutcome.groupby('Comp')['Win'].count()
    winRate = np.round(winCount.astype(float)/fightCount.astype(float) * 100, 1)
    avgRatingChange = compOutcome.groupby('Comp')['Rating change'].mean()
    lossCount = fightCount-winCount

    tic = time()
    comps = pd.Series(fightCount.index).apply(lambda x:x.strip('(').strip(')')).values


    compTable = pd.DataFrame([comps, winCount, lossCount,
                              winRate, np.round(avgRatingChange.astype(float), 1),
                              np.round(avgRatingChange.astype(float)*fightCount.astype(float), 0)],
                             index=['Comp', 'Wins', 'Losses', 'Win rate (%)',
                                    'Avg rating change', 'Total rating change']).T

    compTable.loc[:, 'N'] = compTable.Wins + compTable.Losses

    sortedCompTable = compTable.sort_values(by='N', ascending=False)\
                        .drop('N', axis=1)
    toc = time()
    logging.info('C took %.3f s'%(toc-tic))
                        
    return sortedCompTable


def get_player_match_count(*args):

    matchCountList = []
    for data in args:
        if data.shape[0] == 0:
            continue
        playerNameFields = [k for k in data.columns if '_Name' in k]
        if not playerNameFields:
            continue
        matchCount = pd.Series(data.loc[:,playerNameFields].values.ravel())\
                     .value_counts()
        if len(matchCount) > 0:
            matchCountList.append(matchCount)

    if not matchCountList:
        return pd.Series(dtype=float)

    combinedMatchCount = pd.concat(matchCountList).groupby(level=0).sum()
    return combinedMatchCount

def get_player_name_candidates(data2v2, data3v3):
    """Find the player name by picking whoever appears most frequently across all matches."""
    results = []
    for data in [data2v2, data3v3]:
        if data.shape[0] == 0:
            continue
        name_cols = [c for c in data.columns if '_Name' in c]
        results.extend(data[name_cols].values.ravel().tolist())
    if not results:
        return []
    counts = pd.Series(results).value_counts()
    return [counts.idxmax()]


def merge_player_names(data, candidates):
    """Replace all candidate names with the most common one so stats merge correctly."""
    if len(candidates) <= 1:
        return data, candidates[0] if candidates else None
    primary = candidates[0]
    nameCols = [c for c in data.columns if '_Name' in c]
    for col in nameCols:
        data[col] = data[col].replace({name: primary for name in candidates[1:]})
    return data, primary



@app.callback(
    [Output('partner1-selection', 'value'),
     Output('partner2-selection', 'value')],
    [Input('bracket-selection', 'value'),
     Input('season-selection', 'value')]
    )
@timeit
def reset_partner_on_bracket_or_season_change(bracket, season):
    return None, None


@app.callback(
    [Output('partner1-selection', 'options'),
     Output('partner2-selection', 'options')],
    [Input('player-name', 'children'),
     Input('bracket-selection', 'value'),
     Input('season-selection', 'value'),
     Input('partner1-selection', 'value'),
     Input('partner2-selection', 'value'),
     Input('rating-graph', 'selectedData')],
    [State('data-store', 'children')]
    )
@timeit
def update_partner_selection(player, bracket, season,
                             partner1, partner2, selected, json_data):

    tic = time()
    logging.info('UPDATE PARTNER SELECTION')
    if json_data is None:
        raise PreventUpdate
    logging.info('Updating partner selection')
    allData = json.loads(json_data)
    if bracket not in allData or not allData[bracket]:
        raise PreventUpdate
    allBracketData = pd.DataFrame(allData[bracket])
    if season is None:
        bracketData = allBracketData
    else:
        bracketData = allBracketData.loc[allBracketData.Season == int(season), :]
    

    if selected is not None:
        idx = np.arange(bracketData.shape[0])
        keepIndex = (idx >= selected['range']['x'][0]) &\
                    (idx <= selected['range']['x'][1])

        bracketData = bracketData.loc[keepIndex, :]
    else:
        keepIndex = None

    
    if bracketData.shape[0] == 0:
        raise PreventUpdate
    allTeamMates = timeit(analysis.get_team_mates)(bracketData).values.ravel()
    teamMates = set(allTeamMates) - set([player])
    teamMateCounts = pd.Series(allTeamMates).value_counts()
    
    filteredData = timeit(analysis.filter_by_partner)(bracketData, partner1, partner2)

    conditionalTeamMates = set(analysis.get_team_mates(filteredData).values.ravel())\
                           - set([player])

    partner1Options = [{'value': mate, 'label': mate}
                       for mate in teamMates if mate != partner2
                       and teamMateCounts[mate] >= MATCH_THRESHOLD]


    partner2Options = [{'value': mate, 'label': mate}
                       for mate in conditionalTeamMates if mate != partner1
                       and teamMateCounts[mate] >= MATCH_THRESHOLD]

    toc = time()
    logging.info('update_partner_selection: %.3f s'%(toc-tic))

    return partner1Options, partner2Options

    
@app.callback(
    [Output('data-store', 'children'),
     Output('player-name', 'children'),
     Output('linkshare', 'children')],
    [Input('upload', 'contents'),
     Input('button-demo', 'n_clicks'),
     Input('url', 'href')]
    )
@timeit
def load_data(content, n_clicks, href):
    f = furl(href)
    if 'id' in f.args:
        file_id = f.args['id'].split('/')[-1]
    else:
        file_id = None
        
    logging.info('Loading data.')
    # So after upload:
    # 1) update the data-store div with hidden JSON data
    # 2) update the partner selection option

    if content is None and n_clicks is None and file_id is None:
        logging.info('Content is None')
        raise PreventUpdate

    if content is not None:
        contentType, contentString = content.split(',')
        
        #if contentType != 'data:text/x-lua;base64':
        #    raise NotImplementedError('Data type is not lua')

        decoded = base64.b64decode(contentString)
        inputData = decoded.decode('utf-8')
        outputFile = hashlib.sha256(inputData.encode()).hexdigest()
        outputFileFullPath = '%s/%s.lua'%(OUTPUT_DIR, outputFile)
        if not os.path.isfile(outputFileFullPath):        
            with open(outputFileFullPath, 'w',
                      encoding='utf-8') as f:
                f.write(inputData)

        link = outputFile

    elif file_id is not None:
        inputData = OUTPUT_DIR+'/'+file_id+'.lua'
        link = file_id

    else:
        inputData = dataFile
        link = ''

    try:
        data2v2, data3v3, dataShuffle = timeit(rio.parse_lua_file)(inputData)
    except FileNotFoundError:
        return '{}', 'No data found', 'https://luduslabs.org/reflexology'
        

    if data2v2.shape[0] > 0:
        N = data2v2.shape[0]
        data2v2 = data2v2.dropna(axis=1, thresh=data2v2.shape[0]//2)\
                         .dropna(subset=['T0P0_Class','T0P1_Class',
                                         'T1P0_Class','T1P1_Class'],
                                 how='any', axis=0)
        M = data2v2.shape[0]
        if N != M:
            logging.warn('REMOVED COLUMNS FROM DATA!')

        data2v2['session'] = analysis.get_sessions(data2v2)

    if data3v3.shape[0] > 0:
        N = data3v3.shape[0]

        data3v3 = data3v3.dropna(axis=1, thresh=data3v3.shape[0]//2)\
                         .dropna(subset=['T0P0_Class','T0P1_Class', 'T0P2_Class',
                                         'T1P0_Class','T1P1_Class', 'T1P2_Class'],
                                 how='any', axis=0)
        M = data3v3.shape[0]
        
        if N != M:
            logging.warn('REMOVED COLUMNS FROM DATA!')

        data3v3['session'] = analysis.get_sessions(data3v3)

    if dataShuffle.shape[0] > 0:
        N = dataShuffle.shape[0]
        
        dataShuffle = dataShuffle.dropna(axis=1, thresh=dataShuffle.shape[0]//2)\
                         .dropna(subset=['T0P0_Class','T0P1_Class', 'T0P2_Class',
                                         'T0P3_Class','T0P4_Class', 'T0P5_Class'],
                                 how='any', axis=0)
        M = dataShuffle.shape[0]
        
        if N != M:
            logging.warn('REMOVED COLUMNS FROM DATA!')

        dataShuffle['session'] = np.arange(0, dataShuffle.shape[0])

    matchCount = get_player_match_count(data2v2, data3v3)
    if len(matchCount) == 0:
        return '{}', 'No data found', 'https://luduslabs.org/reflexology'

    candidates = get_player_name_candidates(data2v2, data3v3)
    logging.info('Player name candidates: %s' % candidates)

    # Merge all candidate names (handles character renames) into the primary name
    if data2v2.shape[0] > 0:
        data2v2, playerName = merge_player_names(data2v2, candidates)
    if data3v3.shape[0] > 0:
        data3v3, playerName = merge_player_names(data3v3, candidates)
    playerName = candidates[0]

    jsonData = '{"2v2":%s, "3v3":%s}'%(data2v2.to_json(),
                                       data3v3.to_json())

    size = sys.getsizeof(jsonData)/1e3
    logging.info('Data is %.2fKB in size.'%size)

    return jsonData, playerName, ['https://luduslabs.org/reflexology?id=%s' % link]


@app.callback(
    Output('hidden-comp-table', 'children'),
    [Input('partner1-selection', 'value'),
     Input('partner2-selection', 'value'),
     Input('season-selection', 'value'),
     Input('bracket-selection', 'value'),
     Input('player-name', 'children'),
     Input('rating-graph', 'selectedData')],
    [State('data-store', 'children')]
    )
@timeit
def update_hidden_comp_table(partner1, partner2, season, bracket, 
                             player_name, selected, json_data):
    logging.info('UPDATING HIDDEN COMP TABLE')

    if json_data is None:
        raise PreventUpdate
    logging.info('Updating hidden comp table.')
    partners = [a for a in [partner1, partner2] if a is not None]
    allData = json.loads(json_data)
    if bracket not in allData or not allData[bracket]:
        raise PreventUpdate
    allBracketData = pd.DataFrame(allData[bracket])
    if season is None:
        bracketData = allBracketData
    else:
        bracketData = allBracketData.loc[allBracketData.Season == int(season), :]


    if selected is not None:
        idx = np.arange(bracketData.shape[0])
        keepIndex = (idx >= selected['range']['x'][0]) &\
                    (idx <= selected['range']['x'][1])

        bracketData = bracketData.loc[keepIndex, :]

    if bracketData.shape[0] == 0:
        raise PreventUpdate

    logging.info('Filtering data')
    filteredData = filter_data(bracketData, partners)

    compTable = make_comp_table(filteredData, player_name).to_json()

    return compTable


@app.callback(
    [Output('spec-graph', 'figure'),
     Output('spec-graph', 'style'),
     Output('rating-graph', 'figure'),
     Output('rating-graph', 'style'),
     Output('analysis', 'children')],
    [Input('metric-selection', 'value'),
     Input('partner1-selection', 'value'),
     Input('partner2-selection', 'value'),
     Input('season-selection', 'value'),
     Input('bracket-selection', 'value'),
     Input('radio-class-spec', 'value'),
     Input('player-name', 'children'),
     Input('rating-graph', 'selectedData')],
    [State('data-store', 'children')])
@timeit
def update_plots(metric, partner1, partner2, season,
                 bracket, group_by,
                 player, selected, json_data):

    logging.info('UPDATE PLOTS')
    if json_data is None:
        raise PreventUpdate
    
    logging.info('Updating plots.')
    partners = [a for a in [partner1, partner2] if a is not None]
    allData = json.loads(json_data)
    if bracket not in allData or not allData[bracket]:
        raise PreventUpdate
    allBracketData = pd.DataFrame(allData[bracket])
    if season is None:
        bracketData = allBracketData
    else:
        bracketData = allBracketData.loc[allBracketData.Season == int(season), :]
    

    if selected is not None:
        idx = np.arange(bracketData.shape[0])
        keepIndex = (idx >= selected['range']['x'][0]) &\
                    (idx <= selected['range']['x'][1])

        keptBracketData = bracketData.loc[keepIndex, :]

    else:
        keptBracketData = bracketData
        keepIndex = None

    if bracketData.shape[0] == 0:
        raise PreventUpdate

    logging.info('Filtering data')
    filteredData = filter_data(keptBracketData, partners)
    

    return (make_spec_plot(filteredData, metric, player, group_by),
            {'display': 'block'},
            make_rating_plot(bracketData, player, partner1, partner2, keepIndex),
            {'display': 'block'},
            [])


@app.callback(
    Output('spec-selection-1','value'),
    [Input('class-selection-1', 'value')]
    )
@timeit
def reset_spec_1_value(_):
    logging.info('RESET SPEC VALUE 1')
    return None


@app.callback(
    Output('spec-selection-2','value'),
    [Input('class-selection-2', 'value')]
    )
@timeit
def reset_spec_2_value(_):
    logging.info('RESET SPEC VALUE 2')    
    return None


def strip_and_append_healer(x):
    if 'Healer' in x:
        return x.replace('Healer, ','').replace(', Healer','') + ', Healer'

    return x


def aggregate_fields(x):
    wins = x['Wins'].sum()
    losses = x['Losses'].sum()
    games = wins + losses

    ratingChange = x['Total rating change'].sum()
    return pd.Series([
        x.loc[:, 'Comp'].iloc[0],
        wins,
        losses,
        np.round(wins/games * 100, 1),
        np.round(ratingChange/games, 1),
        np.round(ratingChange, 0)], index=x.columns)


@app.callback(
    Output('download-csv', 'data'),
    [Input('download-button', 'n_clicks')],
    [State('comp-table', 'data')],
    prevent_initial_call=True
    )
def export_to_csv(_, compTable):
    compTable = pd.DataFrame(compTable)

    compTable.loc[:, 'Comp'] = compTable.loc[:, 'Comp']\
                                        .str.findall('(".*?")')\
                                            .apply(lambda x: ', '.join(x).replace('"', ''))

    return dcc.send_data_frame(compTable.to_csv, 'ludus_labs_reflexology_extract.csv')


@app.callback(
    Output('comp-table', 'data'),
    [Input('hidden-comp-table', 'children'),
     Input('class-selection-1', 'value'),
     Input('spec-selection-1', 'value'),
     Input('class-selection-2', 'value'),
     Input('spec-selection-2', 'value'),
     Input('group-healers', 'value')
    ])
@timeit
def display_comp_table(comp_data, class1, spec1, class2, spec2, group_healers):
    logging.info('DISPLAY COMP TABLE')
    if comp_data is None:
        raise PreventUpdate

    compTable = pd.DataFrame(json.loads(comp_data))

    if group_healers is not None:
        if 'grouped' in group_healers:
            compTable.loc[:, 'Comp'] = compTable.loc[:, 'Comp'].replace(
                regex='('+'|'.join(HEALERS)+')',
                value='Healer').apply(strip_and_append_healer)

            compTable = compTable.groupby('Comp').apply(aggregate_fields)
            compTable.loc[:, 'N'] = compTable['Wins'] + compTable['Losses']
            compTable = compTable.sort_values(by='N', ascending=False)\
                                 .drop('N', axis=1)



    def _get_spec_markdown(x):
        x = x.strip()
        if x.lower() == 'healer':
            return '![classicon](/static/spec-icons/healer.png "Healer")'

        spec = get_spec(x).replace(' ','').lower()
        wowclass = get_class(x).replace(' ', '').lower()
        return '![classicon](/static/spec-icons/%s-%s.png "%s")'%(wowclass, spec, x)

    
    def _get_comp_markdown(comp):
        return ' '.join([_get_spec_markdown(x) for x in comp.split(',')])

    def get_filter(filterClass, filterSpec, opponentClassSpec1, opponentClassSpec2):
        filterClassSpec = None
        if filterClass is not None:
            if filterSpec is not None:
                filterClassSpec = filterSpec + ' ' + filterClass

        if filterClass is None:
            return np.ones(len(opponentClassSpec1), dtype=bool)
        
        elif filterClassSpec is None:
            opponentClass1 = opponentClassSpec1.apply(get_class)
            opponentClass2 = opponentClassSpec2.apply(get_class)
            return (opponentClass1 == filterClass) | (opponentClass2 == filterClass)

        else:
            return (opponentClassSpec1 == filterClassSpec) |\
                   (opponentClassSpec2 == filterClassSpec)

    opponentClassSpec1 = compTable.Comp.apply(lambda x:x.split(',')[0])
    opponentClassSpec2 = compTable.Comp.apply(lambda x:x.split(', ')[1])

    filter1 = get_filter(class1, spec1, opponentClassSpec1, opponentClassSpec2)
    filter2 = get_filter(class2, spec2, opponentClassSpec1, opponentClassSpec2)
    filterIndex = filter1 & filter2
    
    dispCompTable = compTable.loc[filterIndex, :]

    compsHTML = np.array([_get_comp_markdown(x) for x in dispCompTable.Comp])
    dispCompTable.loc[:, 'Comp'] = compsHTML

    dispCompTable.loc[:, 'Games'] = dispCompTable['Wins'] + dispCompTable['Losses']
    dispCompTable.loc[:, 'Record'] = dispCompTable['Wins'].astype(np.int64).astype(str) + \
                                     ' - ' + dispCompTable['Losses'].astype(np.int64).astype(str)

    dispTable = dispCompTable.loc[:, tableColumns].to_dict('records')
    return dispTable



@app.callback(
    Output('div-dropdown-partner2', 'style'),
    [Input('bracket-selection', 'value')]
    )
@timeit
def hide_show_partner2_selection(bracket):
    logging.info('SHOW/HIDE PARTNER 2 SELECTION')    
    if bracket == '2v2':
        logging.info('Hiding partner2 selection.')
        return {'display': 'none'}

    else:
        logging.info('Showing partner2 selection.')
        return {'display': 'inline-block'}


def get_class_from_markdown_string(comp, get_spec=False):

    specClass = comp.str.findall('"(.*?)"')\
                   .explode()\
                   .str.strip()

    if get_spec:
        return specClass.apply(lambda x: x.split(' ')[0] \
                               if 'Beast Mastery' not in x else 'Beast Mastery')

    
    return specClass.apply(lambda x: ' '.join(x.split(' ')[1:]) if 'Beast Mastery'\
                           not in x else 'Hunter')



@app.callback(
    Output('class-selection-1', 'options'),
    [Input('hidden-comp-table', 'children')]
    )
@timeit
def update_class1_selection(data):
    logging.info('UPDATE CLASS SELECTION 1')
    if data is None:
        raise PreventUpdate
    df = pd.DataFrame(json.loads(data))
    specClasses = df.Comp.str.split(',').explode().str.strip()
    classes = specClasses.apply(lambda x: get_class(x))
    classSelection = [{'label': c, 'value': c} for c in sorted(set(classes))]
    
    return classSelection

@app.callback(
    Output('spec-selection-1', 'options'),
    [Input('class-selection-1', 'value')],
    [State('hidden-comp-table', 'children')]
)
@timeit
def update_spec1_selection(class1, data):
    logging.info('UPDATE SPEC SELECTION 1')    
    if class1 is None:
        return []
    
    df = pd.DataFrame(json.loads(data))
    specClasses = df.Comp.str.split(',').explode().str.strip()
    classes = specClasses.apply(get_class)
    specs = specClasses.apply(get_spec)
    currentSpecs = specs[classes == class1]
    specSelection = [{'label': c, 'value': c} for c in sorted(set(currentSpecs))]

    return specSelection

@app.callback(
    [Output('class-selection-2', 'options'),
     Output('div-class-selection-2', 'style')],
    [Input('class-selection-1', 'value'),
     Input('spec-selection-1', 'value')],
    [State('hidden-comp-table', 'children'),
     State('class-selection-2', 'value')])
@timeit
def update_class2_selection(class1, spec1, data, class2):
    logging.info('UPDATE CLASS SELECTION 2')
    if data is None:
        return [], {}

    df = pd.DataFrame(json.loads(data))
    specClasses = df.Comp.str.split(',').explode().str.strip()
    classes = specClasses.apply(get_class)
    specs = specClasses.apply(get_spec)

    if spec1 is None:
        idx = (classes == class1)
    else:
        idx = (classes == class1) & (specs == spec1)

    targetIndex = pd.unique(classes.index[idx])
    boolTargetIndex = np.in1d(classes.index, targetIndex)
    partnerIndices = ~idx & boolTargetIndex

    currentClasses = classes[partnerIndices]

    return ([{'label': c, 'value': c} for c in sorted(set(currentClasses))],
            {'display': 'inline-block'})

@app.callback(
    Output('spec-selection-2', 'options'),
    [Input('class-selection-2', 'value')],
    [State('class-selection-1', 'value'),
     State('spec-selection-1', 'value'),
     State('hidden-comp-table', 'children')])
@timeit
def update_spec2_selection(class2, class1, spec1, data):
    logging.info('UPDATE SPEC SELECTION 2')
    if class2 is None or data is None:
        return []

    df = pd.DataFrame(json.loads(data))

    specClasses = df.Comp.str.split(',').explode().str.strip()
    classes = specClasses.apply(lambda x: ' '.join(x.split(' ')[1:]))
    specs = specClasses.apply(lambda x: x.split(' ')[0])

    if spec1 is None:
        idx = (classes == class1)
    else:
        idx = (classes == class1) & (specs == spec1)

    targetIndex = pd.unique(classes.index[idx])
    boolTargetIndex = np.in1d(classes.index, targetIndex)
    partnerIndices = ~idx & boolTargetIndex

    currentSpecs = specs[partnerIndices & (classes == class2)]

    return [{'label': c, 'value': c} for c in sorted(set(currentSpecs))]

@app.callback(
    [Output('metric-rating-change', 'children'),
     Output('metric-games-played', 'children'),
     Output('metric-sessions-played', 'children'),
     Output('metric-rating-change', 'style')],
    [Input('bracket-selection', 'value'),
     Input('season-selection', 'value'),
     Input('player-name', 'children'),
     Input('partner1-selection', 'value'),
     Input('partner2-selection', 'value'),
     Input('rating-graph', 'selectedData')],
    [State('data-store', 'children')]
    )
@timeit
def update_kpis(bracket, season, player, partner1, partner2, selected, json_data):
    logging.info('UPDATE KPIs')
    if json_data is None:
        raise PreventUpdate
    green = '#090'
    red = '#900'
    allData = json.loads(json_data)
    if bracket not in allData or not allData[bracket]:
        raise PreventUpdate
    partners = [p for p in [partner1, partner2] if p is not None]
    bracketData = pd.DataFrame(allData[bracket])
    allBracketData = pd.DataFrame(allData[bracket])
    if season is None:
        bracketData = allBracketData
    else:
        bracketData = allBracketData.loc[allBracketData.Season == int(season), :]
    
    
    if selected is not None:
        idx = np.arange(bracketData.shape[0])
        keepIndex = (idx >= selected['range']['x'][0]) &\
                    (idx <= selected['range']['x'][1])

        bracketData = bracketData.loc[keepIndex, :]
    
    filteredData = filter_data(bracketData, partners)
    if filteredData.shape[0] == 0:
        raise PreventUpdate

    ratingChange = analysis.get_player_field(filteredData, player, 'Rating change').sum()


    symbol = '+' if ratingChange >= 0 else ''

    ratingChangeString = '%s%i'%(symbol, ratingChange)
    gamesPlayed = '%i'%filteredData.shape[0]
    sessionsPlayed = '%i'%len(pd.unique(filteredData['session']))

    ratingChangeStyle = {'color' : green if ratingChange >= 0 else red}

    return ratingChangeString, gamesPlayed, sessionsPlayed, ratingChangeStyle


@app.callback(
    [Output('div-tab-1', 'style'),
     Output('div-tab-2', 'style'),
     Output('div-tab-3', 'style')],
    [Input('main-tab', 'value')])
@timeit
def display_tab(tab):
    if tab == 'graph':
        return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
    elif tab == 'comp':
        return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
    elif tab == 'analysis':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}


@app.callback(
    [Output('div-main-content', 'style'),
     Output('div-main-greet', 'style')],
    [Input('data-store', 'children')],
    [State('button-demo', 'n_clicks'),
     State('upload', 'filename'),
     State('url', 'href')
     ]
    )
@timeit
def show_main_content(data, n_clicks, filename, href):
    f = furl(href)
    if 'id' in f.args:
        file_id = f.args['id'].split('/')[-1]
    else:
        file_id = None
    
    logging.info('SHOW MAIN CONTENT')
    if (n_clicks is not None) or\
       (filename is not None) or (file_id is not None):
        return [{'display': 'block'}, {'display': 'none'}]

    return [{'display': 'none'}, {'display': 'block'}]


@app.callback(
    [Output('season-selection', 'options'),
     Output('season-selection', 'value')],
    [Input('data-store', 'children')]
    )
@timeit
def update_season_selection(json_data):

    logging.info('Updating season selection')
    if json_data is None:
        raise PreventUpdate
    
    allData = json.loads(json_data)
    
    seasons = set()
    for bracket in allData:
        x = pd.DataFrame(allData[bracket])
        if x.shape[0] > 0:
            seasons |= set(x['Season'])

    logging.info(seasons)
    sortedSeasons = list(seasons)[::-1]
    seasonList = [{'label': get_season_label(k), 'value': k } for k in sortedSeasons
                  if k > 0]
    validSeasons = [s for s in seasons if s > 0]
    if not validSeasons:
        raise PreventUpdate
    return seasonList, max(validSeasons)
    
    
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8050, debug=True)
