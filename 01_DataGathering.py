#%% 
import json
import time
import random
import pymongo
import copy
import MyCommon
from pymongo import MongoClient
from collections import deque
import cassiopeia
from cassiopeia import riotapi

riotapi.set_region("KR")
riotapi.set_api_key("79428a9e-5d98-469b-9b9b-429c1a750d24")
riotapi.set_rate_limits((10, 10), (500, 600))
riotapi.print_calls(True)

#%% 

client = MongoClient()
loladb = client.loladb
summoners_collection = loladb.summoners
matches_collection = loladb.matches

if summoners_collection.count() == 0:
    #Save summoner information to mongodb
    masters = riotapi.get_master()
    summoners_collection.insert_many([json.loads(entry.to_json()) for entry in masters.data.entries])
    
print summoners_collection.count()
print matches_collection.count()

#%% 

def RecordSummonerLatestMatchId(summoner, matchId):
    summoners_collection.update_one({'playerOrTeamId':str(summoner.id)}, {'$set': {'latestGrabbedMatchId': matchId}})

def RecordSummonerForFullGrab(summoner):
    summoners_collection.update_one({'playerOrTeamId':str(summoner.id)}, {'$set': {'fullGrabbed': True}})
    
def IsLatestMatch(match_season):
    if match_season ==  "SEASON2017" or match_season ==  "PRESEASON2017":
        return True
    else:
        return False
    
def IsSoloRank(match_type):
    if match_type == 'TEAM_BUILDER_RANKED_SOLO' or match_type == 'TEAM_BUILDER_DRAFT_RANKED_5x5':
        return True
    else:
        return False
    
def IsRequiredMatch(match_dict):
    if IsSoloRank(match_dict['queueType']) and match_dict['matchMode'] == 'CLASSIC' and match_dict['matchType'] == 'MATCHED_GAME':
        return True
    else:
        return False
    
def RecordMatchesForSummoner(a_summoner):
    print a_summoner
    print 'Get matches for summoner with id :' + str(a_summoner['playerOrTeamId'])
    
    latestGrabbedMatchId = 0
    fullGrabbed = "fullGrabbed" in a_summoner.keys()
    if fullGrabbed == True:
        latestGrabbedMatchId = a_summoner['latestGrabbedMatchId']
        
    summoner = riotapi.get_summoner_by_id(a_summoner['playerOrTeamId'])
    match_list = summoner.match_list()
    list_size = len(match_list)
    print 'Total match list size:' + str(list_size)
    
    for match_idx, match in enumerate(match_list):
        print 'Checking %d of %d' % (match_idx, list_size)
        
        if fullGrabbed == True and match.id <= latestGrabbedMatchId:
            print 'Because we already full grabbed this summoner, break the loop while current match is already grabbed'
            if match_idx != 0:
                RecordSummonerLatestMatchId(summoner, match_list[0].id)
            break
            
        if IsSoloRank(match.data.queue) == False:
            print 'Continue for not being a solo rank with id ' + str(match.id)
            if match_idx == list_size - 1:
                #last one
                print 'Recording summoner for a full grab'
                RecordSummonerForFullGrab(summoner)
                RecordSummonerLatestMatchId(summoner, match_list[0].id)
            continue
    
        if matches_collection.find_one({'matchId':match.id}) == None:
            match_data = match.match()
            #print "wait 4 seconds"
            #time.sleep( 4 )
            match_dict = json.loads(match_data.to_json())
            print match_dict['matchId']
            print match_dict['matchCreation']
            if IsLatestMatch(match_dict['season']):
                if IsRequiredMatch(match_dict):
                    matches_collection.insert_one(match_dict)
                    print 'Match saved to db with id ' + str(match.id)
                else:
                    print 'Match not required with id ' + str(match.id)
            else:
                print 'Break for reaching outdated matches at ' + match_dict['season']
                print 'Recording summoner for a full grab'
                RecordSummonerForFullGrab(summoner)
                RecordSummonerLatestMatchId(summoner, match_list[0].id)
                break
        else:
            print 'Found match in db with id ' + str(match.id)
        
        
#summoner_0 = summoners_collection.find_one()
#RecordMatchesForSummoner(summoner_0)

for a_idx,current_summoner in enumerate(summoners_collection.find({}, no_cursor_timeout=True)):
    if a_idx < 560:
        continue
    try:
        RecordMatchesForSummoner(current_summoner)
    except (AttributeError, cassiopeia.type.api.exception.APIError) as apiError:
        print apiError
        print "Oops!  Error happened. Keep going..."
