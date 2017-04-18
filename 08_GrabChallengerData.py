
# coding: utf-8

# In[1]:

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
import requests
from bs4 import BeautifulSoup


# In[2]:

riotapi.set_region("OCE")
riotapi.set_api_key("79428a9e-5d98-469b-9b9b-429c1a750d24")
riotapi.set_rate_limits((10, 10), (500, 600))
riotapi.print_calls(True)

client = MongoClient()
loladb = client.loladb_oce
summoners_collection = loladb.top_summoners
matches_collection = loladb.top_matches
matches_checked = loladb.top_matches_checked

if summoners_collection.count() == 0:
    #Save summoner information to mongodb
    challengers = riotapi.get_challenger()
    summoners_collection.insert_many([json.loads(entry.to_json()) for entry in challengers.data.entries])
    #masters = riotapi.get_master()
    #summoners_collection.insert_many([json.loads(entry.to_json()) for entry in masters.data.entries])


# In[4]:

print summoners_collection.count()
print matches_collection.count()


# In[39]:

#I'll try to find a small subset of players that we can find a lot of matches just between these players
#so we can use the adjusted plus/minus to analyze the player performance

#first pick the first challenger player and get all his games during patch 6.24.
#then check the player tier distribution
summoner_0 = summoners_collection.find_one()


# In[35]:

def GetTierFromOPGG(summoner_name):
    summonerURL = "http://www.op.gg/summoner/userName=" + summoner_name
    print summonerURL
    result = requests.get(summonerURL)
    soup = BeautifulSoup(result.content, 'html.parser')
    tier_part = soup.find("div", { "class" : "TierRank" })
    if tier_part == None:
        return None, None
    
    tier_text = tier_part.getText()
    #print tier_text
    tier_splits = tier_text.split()
    tier = tier_splits[0]
    division = ""
    #print len(tier_splits)
    if len(tier_splits) > 1:
        division = tier_splits[1]
    
    return tier,division


# In[14]:

#GetTierFromOPGG(summoner_0['playerOrTeamName'])


# In[5]:

topIds = []
for a_summoner in summoners_collection.find():
    topIds.append(a_summoner['playerOrTeamId'])
print topIds


# In[29]:

#print match_list[0].to_json()

# In[ ]:

import os.path
last_summoner_id = -1
if os.path.exists("LastTopSummonerId.txt"):
    with open("LastTopSummonerId.txt", "r") as f:
        last_summoner_id = int(f.readline())
        print "Read last summoner id " + str(last_summoner_id)
        
def IsSoloRank(match_type):
    if match_type == 'TEAM_BUILDER_RANKED_SOLO' or match_type == 'TEAM_BUILDER_DRAFT_RANKED_5x5':
        return True
    else:
        return False

def RecordTopMatchForSummoner(a_summoner):
    global last_summoner_id
    if last_summoner_id != -1:
        if last_summoner_id != int(a_summoner['playerOrTeamId']):
            return
        else:
            last_summoner_id = -1
    
    with open("LastTopSummonerId.txt", "w") as f:
        print "Write last top summoner id " + str(a_summoner['playerOrTeamId'])
        f.write(str(a_summoner['playerOrTeamId']))
        f.close()
        
    summoner = riotapi.get_summoner_by_id(a_summoner['playerOrTeamId'])
    match_list = summoner.match_list()
    list_size = len(match_list)

    match_count = 0
    tier_array = []

    for match_idx, match in enumerate(match_list):
        #print 'Checking %d of %d' % (match_idx, list_size)

        match_record = matches_checked.find_one({'matchId':match.id})
        if match_record != None:
            if match_record['shouldStop'] == False:
                continue
            else:
                break

        matches_checked.insert_one({'matchId':match.id, 'shouldStop':False})

        if IsSoloRank(match.data.queue) == False:
            print 'Continue for not being a solo rank with id ' + str(match.id)
            continue

        match_data = match.match()
        a_match = json.loads(match_data.to_json())
        if a_match['matchVersion'].startswith('6.24') == False:
            print 'Break for not being in 6.24 with id ' + str(match.id)
            matches_checked.update_one({'matchId':match.id}, {'$set': {'shouldStop': True}})
            break

        a_duration = a_match['matchDuration']
        a_minute = a_duration/60
        if a_minute < 20:
            print 'Continue for not being a full game with id ' + str(match.id)
            continue 

        match_count += 1

        isTopMatch = True

        #participants = a_match['participants'] 
        #for a_participant_idx,a_participantIdentity in enumerate(a_match['participantIdentities']):
        #    a_id = a_participantIdentity['player']['summonerId']
        #    isTopMatch = str(a_id) in topIds

        #    if isTopMatch == False:
        #        print 'Break for not being a top player ' + str(a_id)
        #        break

        if isTopMatch == True:
            if matches_collection.find_one({'matchId':match.id}) == None:
                matches_collection.insert_one(a_match)
                print 'A match saved'

for a_idx, a_summoner in enumerate(summoners_collection.find({}, no_cursor_timeout=True)):
    print 'Checking summoner ' + str(a_idx)
    try:
        RecordTopMatchForSummoner(a_summoner)
    except:
        print "Oops!  Error happened. Keep going..."



